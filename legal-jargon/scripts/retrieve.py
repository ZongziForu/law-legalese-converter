#!/usr/bin/env python3
"""Build a compact, route-aware context packet for legal-jargon."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


CHUNK_MARKER = re.compile(r"^<!-- chunk: ([a-z0-9.]+) -->$")
TABLE_MARKER = re.compile(r"^<!-- table-data: [^>]+ -->$")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
CHINESE_RUN = re.compile(r"[\u3400-\u9fff]+")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
            if record.get("record_type") == "entry":
                records.append(record)
    return records


def ordered_union(current: list[str] | None, additions: list[str] | None) -> list[str]:
    result = list(current or [])
    for value in additions or []:
        if value not in result:
            result.append(value)
    return result


def apply_retrieval_policy(item: dict, policy: dict) -> dict:
    result = dict(item)
    for key in (
        "modes",
        "strength",
        "actor_scope",
        "direction",
        "reversibility",
        "archaism_min",
        "foreign_terms_min",
        "portable_profiles",
        "portable_archaism_min",
        "safe_backtranslation",
        "required_cues",
    ):
        if key in policy:
            result[key] = policy[key]
    result["tags"] = ordered_union(result.get("tags"), policy.get("tags_add"))
    risks = ordered_union(result.get("risk_flags"), policy.get("risk_flags_add"))
    removed = set(policy.get("risk_flags_remove", []))
    result["risk_flags"] = [value for value in risks if value not in removed]
    return result


def apply_safe_backtranslation(unit: dict) -> dict:
    safe_anchor = unit.get("safe_backtranslation")
    if not safe_anchor or not unit.get("pairs"):
        return unit
    result = dict(unit)
    pair = dict(result["pairs"][0])
    original_anchor = pair.get("anchor", "")
    if original_anchor and original_anchor != safe_anchor:
        pair["official_anchor"] = original_anchor
    pair["anchor"] = safe_anchor
    pair["anchor_type"] = "conditional_backtranslation"
    result["pairs"] = [pair]
    if "官方锚点" in result.get("fields", {}):
        fields = dict(result["fields"])
        fields["原表锚点"] = fields.pop("官方锚点")
        fields["安全回译锚点"] = safe_anchor
        result["fields"] = fields
    elif "功能等值" in result.get("fields", {}):
        fields = dict(result["fields"])
        fields["原表功能等值"] = fields.pop("功能等值")
        fields["安全回译锚点"] = safe_anchor
        result["fields"] = fields
    result["search_text"] = " ".join(
        filter(
            None,
            [
                result.get("search_text", ""),
                safe_anchor,
                " ".join(result.get("required_cues", [])),
            ],
        )
    )
    return result


def build_retrieval_units(records: list[dict], policy: dict) -> list[dict]:
    table_policies = policy.get("table_policies", {})
    record_policies = policy.get("record_policies", {})
    unit_policies = policy.get("unit_policies", {})
    units: list[dict] = []
    for source_record in records:
        record = apply_retrieval_policy(source_record, table_policies.get(source_record["source_table"], {}))
        record = apply_retrieval_policy(record, record_policies.get(source_record["id"], {}))
        pairs = record.get("pairs", [])
        if not pairs:
            unit = apply_retrieval_policy(record, unit_policies.get(record["id"], {}))
            unit["parent_id"] = record["id"]
            unit["unit_key"] = record["id"]
            if unit.get("reversibility") == "non_reversible":
                unit["risk_flags"] = ordered_union(unit.get("risk_flags"), ["non_reversible_mapping"])
            units.append(unit)
            continue
        for pair_index, pair in enumerate(pairs, start=1):
            unit_key = f"{record['id']}#p{pair_index}"
            unit = dict(record)
            unit["parent_id"] = record["id"]
            unit["unit_key"] = unit_key
            unit["id"] = record["id"] if len(pairs) == 1 else unit_key
            unit["pairs"] = [dict(pair)]
            unit["selected_pair"] = dict(pair)
            if len(pairs) > 1:
                unit["fields"] = {
                    "词条": pair.get("term", ""),
                    "官方锚点": pair.get("anchor", ""),
                }
                unit["search_text"] = " ".join(
                    filter(
                        None,
                        [
                            " ".join(record.get("source_heading_path", [])),
                            pair.get("term", ""),
                            pair.get("anchor", ""),
                        ],
                    )
                )
            unit = apply_retrieval_policy(unit, unit_policies.get(unit_key, {}))
            unit = apply_safe_backtranslation(unit)
            if unit.get("reversibility") == "non_reversible":
                unit["risk_flags"] = ordered_union(unit.get("risk_flags"), ["non_reversible_mapping"])
            units.append(unit)
    return units


def tokenize(text: str) -> list[str]:
    tokens = [word.lower() for word in LATIN_WORD.findall(text)]
    for run in CHINESE_RUN.findall(text):
        if len(run) <= 4:
            tokens.append(run)
        tokens.extend(run[index:index + 2] for index in range(max(0, len(run) - 1)))
        if len(run) >= 3:
            tokens.extend(run[index:index + 3] for index in range(len(run) - 2))
    return tokens


def read_chunks(root: Path, catalog: list[dict]) -> list[dict]:
    metadata = {item["id"]: item for item in catalog}
    chunks: list[dict] = []
    for path in sorted((root / "references").glob("*.md")):
        current_id: str | None = None
        current_lines: list[str] = []

        def flush() -> None:
            if current_id is None:
                return
            body_lines = [line for line in current_lines if not TABLE_MARKER.match(line)]
            while body_lines and not body_lines[-1].strip():
                body_lines.pop()
            text = "\n".join(body_lines).strip()
            item = dict(metadata[current_id])
            item["text"] = text
            item["search_text"] = " ".join(item.get("heading_path", [])) + " " + text
            chunks.append(item)

        for line in path.read_text(encoding="utf-8").splitlines():
            marker = CHUNK_MARKER.match(line)
            if marker:
                flush()
                current_id = marker.group(1)
                current_lines = []
            elif current_id is not None:
                current_lines.append(line)
        flush()
    return chunks


def source_priority(route: dict, domain: str, preset: str, explicit: list[str]) -> list[str]:
    ordered: list[str] = []

    def add(values: list[str]) -> None:
        for value in values:
            if value not in ordered:
                ordered.append(value)

    add(explicit)
    add(route["profiles"].get(preset, {}).get("record_sources", []))
    add(route["domains"].get(domain, {}).get("record_sources", []))
    add(route["defaults"].get("base_record_sources", []))
    return ordered


def bm25_scores(items: list[dict], query_tokens: list[str]) -> dict[str, float]:
    if not query_tokens or not items:
        return {item["id"]: 0.0 for item in items}
    token_counts: dict[str, Counter] = {}
    lengths: dict[str, int] = {}
    document_frequency: Counter = Counter()
    for item in items:
        counts = Counter(tokenize(item.get("search_text", "")))
        token_counts[item["id"]] = counts
        lengths[item["id"]] = sum(counts.values())
        document_frequency.update(set(counts))
    average_length = sum(lengths.values()) / max(1, len(lengths))
    scores: dict[str, float] = {}
    query_counts = Counter(query_tokens)
    for item in items:
        score = 0.0
        counts = token_counts[item["id"]]
        length = lengths[item["id"]]
        for token, query_frequency in query_counts.items():
            frequency = counts.get(token, 0)
            if not frequency:
                continue
            frequency_docs = document_frequency[token]
            inverse_frequency = math.log(1 + (len(items) - frequency_docs + 0.5) / (frequency_docs + 0.5))
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * length / max(1, average_length))
            score += query_frequency * inverse_frequency * frequency * 2.5 / denominator
        scores[item["id"]] = score
    return scores


def selector_matches(chunk: dict, selector: dict) -> bool:
    if selector.get("file") and chunk.get("source") != selector["file"]:
        return False
    if selector.get("heading_contains") and selector["heading_contains"] not in chunk.get("heading", ""):
        return False
    return True


def chunk_policy_map(policy: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for group in policy.get("chunk_policy_groups", []):
        values = {key: value for key, value in group.items() if key != "ids"}
        for chunk_id in group.get("ids", []):
            result.setdefault(chunk_id, {}).update(values)
    return result


def chunk_allowed(
    chunk: dict,
    policies: dict[str, dict],
    mode: str,
    domain: str,
    profile: str,
    historical_register: str,
) -> bool:
    policy = policies.get(chunk["id"], {})
    if policy.get("modes") and mode not in policy["modes"]:
        return False
    if policy.get("profiles") and profile not in policy["profiles"]:
        return False
    if policy.get("domains") and domain not in policy["domains"]:
        return False
    if policy.get("historical_context_required") and historical_register == "contemporary":
        return False
    return True


def required_chunk_ids(route: dict, mode: str, preset: str) -> list[str]:
    selectors = list(route["defaults"].get("base_chunk_selectors", []))
    selectors.extend(route["modes"].get(mode, {}).get("chunk_selectors", []))
    selectors.extend(route["profiles"].get(preset, {}).get("chunk_selectors", []))
    return selectors


def select_chunks(
    chunks: list[dict],
    route: dict,
    policy: dict,
    mode: str,
    domain: str,
    preset: str,
    historical_register: str,
    query_tokens: list[str],
    explicit_chunk_ids: list[str],
    heading_filters: list[str],
    limit: int,
    broaden: bool,
) -> list[dict]:
    required_selectors = required_chunk_ids(route, mode, preset)
    chunk_policies = chunk_policy_map(policy)
    selected: list[dict] = []
    selected_ids: set[str] = set()
    for chunk in chunks:
        if chunk["id"] in explicit_chunk_ids or (
            heading_filters and any(value in " ".join(chunk.get("heading_path", [])) for value in heading_filters)
        ):
            if (
                chunk["id"] not in selected_ids
                and len(chunk.get("text", "").splitlines()) > 1
                and chunk_allowed(chunk, chunk_policies, mode, domain, preset, historical_register)
            ):
                selected.append(chunk)
                selected_ids.add(chunk["id"])
    for selector in required_selectors:
        for chunk in chunks:
            if selector_matches(chunk, selector) and chunk["id"] not in selected_ids:
                if len(chunk.get("text", "").splitlines()) <= 1:
                    continue
                if not chunk_allowed(chunk, chunk_policies, mode, domain, preset, historical_register):
                    continue
                selected.append(chunk)
                selected_ids.add(chunk["id"])

    preset_route = route["profiles"].get(preset, {})
    candidate_files = set(route["defaults"].get("base_chunk_files", []))
    candidate_files.update(preset_route.get("chunk_files", []))
    candidate_files.update(route["domains"].get(domain, {}).get("chunk_files", []))
    if broaden:
        candidate_files.add("11")
    sensitive_sources = {"10", "13", "14", "16"}
    candidates = [
        chunk for chunk in chunks
        if chunk["source"] in candidate_files
        and chunk["id"] not in selected_ids
        and (chunk["source"] not in sensitive_sources or preset in chunk.get("presets", []))
        and chunk_allowed(chunk, chunk_policies, mode, domain, preset, historical_register)
    ]
    lexical = bm25_scores(candidates, query_tokens)
    ranked = sorted(
        candidates,
        key=lambda item: (
            lexical[item["id"]],
            1 if item["source"] != "11" else 0,
            -item["level"],
        ),
        reverse=True,
    )
    target_limit = limit
    example_used = False
    for source in sorted(candidate_files):
        if len(selected) >= target_limit or source == "11":
            continue
        best = next((chunk for chunk in ranked if chunk["source"] == source), None)
        if best is not None and best["id"] not in selected_ids:
            selected.append(best)
            selected_ids.add(best["id"])
    for chunk in ranked:
        if len(selected) >= target_limit:
            break
        if chunk["id"] in selected_ids:
            continue
        if not chunk.get("text") or chunk.get("text", "").strip().startswith("#") and len(chunk.get("text", "").splitlines()) == 1:
            continue
        if chunk["source"] == "11":
            if example_used or lexical[chunk["id"]] <= 0:
                continue
            example_used = True
        selected.append(chunk)
        selected_ids.add(chunk["id"])
    return selected[:target_limit]


def record_score(
    record: dict,
    lexical: float,
    priorities: list[str],
    domain: str,
    preset: str,
    heading_keywords: list[str],
    mode: str,
    intensity: int | None,
) -> float:
    score = lexical * 4.0
    if record["source"] in priorities:
        score += max(2.0, 18.0 - priorities.index(record["source"]) * 3.0)
    if domain in record.get("domains", []):
        score += 8.0
    if preset in record.get("presets", []):
        score += 8.0
    if mode in record.get("modes", []):
        score += 1.0
    heading = " ".join(record.get("source_heading_path", []))
    if any(keyword in heading for keyword in heading_keywords):
        score += 10.0
    if preset == "judicial_formal" and record.get("official_backtranslation"):
        score += 7.0
    if intensity is not None and isinstance(record.get("strength"), int):
        score -= max(0, record["strength"] - intensity) * 1.5
    risks = set(record.get("risk_flags", []))
    if "historical_context_required" in risks and preset not in {
        "republican_judgment", "traditional_law", "classical_legalese"
    }:
        score -= 30.0
    if "double_negation_limited" in risks:
        score -= 3.0
    if "high_risk" in risks:
        score -= 8.0
    if "source_evaluation_required" in risks:
        score -= 4.0
    return score


def record_direction(record: dict) -> str | None:
    if record.get("direction"):
        return record["direction"]
    strength = str(record.get("strength", ""))
    if "肯定" in strength:
        return "positive"
    if "否定" in strength:
        return "negative"
    direction = record.get("fields", {}).get("方向")
    return {"符合": "compliant", "不符合": "noncompliant", "无明文": "no_rule"}.get(direction)


def actor_allowed(record_scope: str | None, requested_scope: str) -> bool:
    if not record_scope:
        return True
    allowed = {
        "neutral": set(),
        "adjudicator": {"adjudicator"},
        "party": {"party"},
        "sentencing_adjudicator": {"adjudicator", "sentencing_adjudicator"},
        "family_court": {"adjudicator", "family_court"},
    }
    return record_scope in allowed[requested_scope]


def profile_allowed(record: dict, profile: str, policy: dict, archaism: int) -> bool:
    original_profiles = set(record.get("presets", []))
    if profile in original_profiles:
        return True
    portable_profiles = set(record.get("portable_profiles", []))
    if profile not in portable_profiles:
        return record["source"] not in set(policy.get("profile_scoped_sources", []))
    return archaism >= int(record.get("portable_archaism_min", 0))


def historical_allowed(risks: set[str], historical_register: str) -> bool:
    if "historical_context_required" not in risks:
        return True
    return historical_register in {
        "source_bound",
        "late_qing",
        "republican",
        "traditional_law",
        "comparative_history",
    }


def select_records(
    records: list[dict],
    route: dict,
    policy: dict,
    mode: str,
    domain: str,
    profile: str,
    query_text: str,
    query_tokens: list[str],
    explicit_sources: list[str],
    headings: list[str],
    tags: list[str],
    limit: int,
    intensity: int | None,
    actor_scope: str,
    direction: str | None,
    archaism: int,
    foreign_terms: int,
    historical_register: str,
    authority_policy: str,
    source_evaluation: bool,
    record_context: bool,
    allow_high_risk: bool,
    double_negation_budget: int,
    jurisdiction: str,
    broaden: bool,
    include_excluded: bool,
    include_non_reversible: bool,
) -> list[dict]:
    priorities = source_priority(route, domain, profile, explicit_sources)
    heading_keywords = list(route["domains"].get(domain, {}).get("heading_keywords", []))
    compatible_domains = set(policy.get("domain_compatibility", {}).get(domain, [domain, "general"]))
    normalized_query = query_text.lower()
    candidates: list[dict] = []
    for record in records:
        risks = set(record.get("risk_flags", []))
        if "excluded_from_generation" in risks and not include_excluded:
            continue
        if "non_reversible_mapping" in risks and not include_non_reversible:
            continue
        if explicit_sources and record["source"] not in explicit_sources:
            continue
        if priorities and record["source"] not in priorities:
            continue
        heading_text = " ".join(record.get("source_heading_path", []))
        if headings and not any(value in heading_text for value in headings):
            continue
        if tags and not set(tags).intersection(record.get("tags", [])):
            continue
        required_cues = record.get("required_cues", [])
        if required_cues and not any(cue.lower() in normalized_query for cue in required_cues):
            continue
        if mode not in record.get("modes", []):
            continue
        if not set(record.get("domains", [])).intersection(compatible_domains) and profile not in record.get("portable_profiles", []):
            continue
        if not profile_allowed(record, profile, policy, archaism):
            continue
        if archaism < int(record.get("archaism_min", 0)):
            continue
        if int(record.get("foreign_terms_min", 0)) > foreign_terms:
            continue
        if not historical_allowed(risks, historical_register):
            continue
        if not actor_allowed(record.get("actor_scope"), actor_scope):
            continue
        item_direction = record_direction(record)
        if "direction_locked" in risks and direction is None:
            continue
        if direction in {"positive", "negative"} and item_direction in {"positive", "negative"} and item_direction != direction:
            continue
        legal_directions = {"compliant", "noncompliant", "no_rule", "not_prohibited"}
        if direction in legal_directions and item_direction in legal_directions and item_direction != direction:
            continue
        if "legal_basis_required" in risks and direction not in legal_directions:
            continue
        if "source_evaluation_required" in risks and not source_evaluation:
            continue
        if "record_context_required" in risks and not record_context:
            continue
        if "authority_required" in risks and authority_policy == "none":
            continue
        if "jurisdiction_required" in risks and not jurisdiction:
            continue
        if "taiwan_register" in risks and "taiwan" not in jurisdiction.lower() and "台湾" not in jurisdiction:
            continue
        if "double_negation_limited" in risks and double_negation_budget < 1:
            continue
        if "high_risk" in risks and not allow_high_risk:
            continue
        candidates.append(record)

    lexical = bm25_scores(candidates, query_tokens)
    ranked = sorted(
        candidates,
        key=lambda item: (
            record_score(
                item,
                lexical[item["id"]],
                priorities,
                domain,
                profile,
                heading_keywords,
                mode,
                intensity,
            ),
            -item.get("row_index", 0),
        ),
        reverse=True,
    )

    if query_tokens:
        ranked = [record for record in ranked if lexical[record["id"]] > 0]

    target_limit = limit
    source_counts: defaultdict[str, int] = defaultdict(int)
    table_counts: defaultdict[str, int] = defaultdict(int)
    selected: list[dict] = []
    max_per_source = max(8, target_limit // 2)
    max_per_table = max(4, target_limit // 6)
    for record in ranked:
        if len(selected) >= target_limit:
            break
        if source_counts[record["source"]] >= max_per_source:
            continue
        if table_counts[record["source_table"]] >= max_per_table:
            continue
        selected.append(record)
        source_counts[record["source"]] += 1
        table_counts[record["source_table"]] += 1
    return selected


def compact_record(record: dict) -> dict:
    result = {
        "id": record["id"],
        "source": record["source_file"],
        "section": record["source_heading_path"][-1] if record.get("source_heading_path") else "",
        "fields": record["fields"],
    }
    if record.get("parent_id") and record["parent_id"] != record["id"]:
        result["parent_id"] = record["parent_id"]
    for key in ("pairs", "strength", "actor_scope", "risk_flags", "tags", "reversibility", "required_cues"):
        if record.get(key):
            result[key] = record[key]
    if record.get("official_backtranslation"):
        result["official_backtranslation"] = True
    return result


def render_markdown(config: dict, chunks: list[dict], records: list[dict], max_chars: int) -> str:
    lines = [
        "# 检索素材包",
        "",
        f"- 路由：mode={config['mode']}；domain={config['domain']}；preset={config['preset']}；resource_profile={config['profile']}；actor_scope={config['actor_scope']}；direction={config['direction'] or 'unspecified'}",
        f"- 门控：archaism={config['archaism']}；foreign_terms={config['foreign_terms']}；historical_register={config['historical_register']}；authority_policy={config['authority_policy']}；double_negation_budget={config['double_negation_budget']}；jurisdiction={config['jurisdiction'] or 'unspecified'}",
        f"- 关键词：{config['keywords'] or '无'}",
        "- 使用规则：只在命题核、模式权限和门控允许范围内采用下列素材。",
    ]
    if chunks:
        lines.extend(["", "## 必要规则与风格片段"])
        for chunk in chunks:
            block = f"\n<!-- {chunk['id']} | {chunk['file']} -->\n{chunk['text']}"
            if len("\n".join(lines)) + len(block) > max_chars * 0.58:
                break
            lines.append(block)

    lines.extend(["", "## 召回词条"])
    official_pairs: list[tuple[str, str, str, list[str], str, str]] = []
    for record in records:
        fields = "；".join(f"{key}={value}" for key, value in record["fields"].items() if value)
        extras: list[str] = []
        if record.get("strength") is not None:
            extras.append(f"强度={record['strength']}")
        if record.get("actor_scope"):
            extras.append(f"主体端={record['actor_scope']}")
        if record.get("risk_flags"):
            extras.append("门控=" + ",".join(record["risk_flags"]))
        if record.get("reversibility"):
            extras.append(f"回译可逆性={record['reversibility']}")
        if record.get("required_cues"):
            extras.append("语义召唤词=" + ",".join(record["required_cues"]))
        line = f"- [{record['id']}] {fields}"
        if extras:
            line += "；" + "；".join(extras)
        if len("\n".join(lines)) + len(line) + 2 > max_chars * 0.90:
            break
        lines.append(line)
        if record.get("official_backtranslation"):
            for pair in record.get("pairs", []):
                if pair.get("term") and pair.get("anchor"):
                    official_pairs.append(
                        (
                            record["id"],
                            pair["term"],
                            pair["anchor"],
                            record.get("risk_flags", []),
                            record.get("reversibility", "conditional"),
                            pair.get("official_anchor", ""),
                        )
                    )

    if official_pairs:
        lines.extend(["", "## 回译锚点"])
        for record_id, term, anchor, risks, reversibility, official_anchor in official_pairs:
            gate = f"；门控={','.join(risks)}" if risks else ""
            line = f"- [{record_id}] {term} -> {anchor}；可逆性={reversibility}{gate}"
            if official_anchor:
                line += f"；原表锚点={official_anchor}"
            if len("\n".join(lines)) + len(line) + 2 > max_chars:
                break
            lines.append(line)
        lines.extend([
            "",
            "生成后，将实际采用的左侧词条压缩回右侧锚点，并与命题核逐项比对；conditional 仅在门控条件均满足时可逆用，non_reversible 默认不召回；方向、主体端或情态不一致时必须撤回该词条。",
        ])
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="", help="Target text or a compact semantic summary")
    parser.add_argument("--keywords", default="", help="Comma/space-separated legal concepts and style cues")
    parser.add_argument("--mode", choices=["rewrite", "expand", "analyze"], default="rewrite")
    parser.add_argument("--domain", default="general")
    parser.add_argument("--preset", default="general_blacktalk")
    parser.add_argument("--profile", help="Optional resource profile when it differs from the style preset")
    parser.add_argument("--intensity", type=int)
    parser.add_argument("--archaism", type=int, choices=range(0, 6))
    parser.add_argument("--foreign-terms", type=int, choices=range(0, 6))
    parser.add_argument(
        "--historical-register",
        choices=["contemporary", "source_bound", "late_qing", "republican", "traditional_law", "comparative_history"],
    )
    parser.add_argument("--authority-policy", choices=["none", "provided_only", "verified"])
    parser.add_argument(
        "--actor-scope",
        choices=["neutral", "adjudicator", "party", "sentencing_adjudicator", "family_court"],
        default="neutral",
    )
    parser.add_argument("--direction", choices=["positive", "negative", "compliant", "noncompliant", "no_rule", "not_prohibited"])
    parser.add_argument("--source-evaluation", action="store_true", help="Input already supports the requested evaluative judgment")
    parser.add_argument("--record-context", action="store_true", help="Input supplies the referenced record/file context")
    parser.add_argument("--allow-high-risk", action="store_true", help="Allow explicitly requested high-risk register items")
    parser.add_argument("--double-negation-budget", type=int, choices=range(0, 3))
    parser.add_argument("--jurisdiction", default="", help="Applicable jurisdiction when a term is jurisdiction-bound")
    parser.add_argument("--source", action="append", default=[], help="Restrict to a two-digit source prefix")
    parser.add_argument("--heading", action="append", default=[], help="Require a source heading substring")
    parser.add_argument("--chunk-id", action="append", default=[], help="Include an exact Markdown chunk")
    parser.add_argument("--tag", action="append", default=[], help="Require any function tag")
    parser.add_argument("--record-limit", type=int)
    parser.add_argument("--chunk-limit", type=int)
    parser.add_argument("--max-chars", type=int)
    parser.add_argument("--broaden", action="store_true")
    parser.add_argument("--include-excluded", action="store_true")
    parser.add_argument("--include-non-reversible", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    route = load_json(root / "data" / "routes.json")
    policy = load_json(root / "data" / "retrieval_policy.json")
    catalog = load_json(root / "data" / "catalog.json")["chunks"]
    records = build_retrieval_units(load_records(root / "data" / "records.jsonl"), policy)
    chunks = read_chunks(root, catalog)
    defaults = route["defaults"]
    record_limit = args.record_limit or defaults["record_limit"] * (2 if args.broaden else 1)
    chunk_limit = args.chunk_limit or defaults["chunk_limit"] * (2 if args.broaden else 1)
    max_chars = args.max_chars or defaults["max_chars"]
    keyword_text = " ".join(filter(None, [args.query, args.keywords]))
    query_tokens = tokenize(keyword_text)
    profile = args.profile or args.preset
    profile_defaults = policy.get("preset_defaults", {}).get(profile, {})
    archaism = args.archaism if args.archaism is not None else int(profile_defaults.get("archaism", 0))
    foreign_terms = args.foreign_terms if args.foreign_terms is not None else int(profile_defaults.get("foreign_terms", 0))
    historical_register = args.historical_register or profile_defaults.get("historical_register", "contemporary")
    authority_policy = args.authority_policy or profile_defaults.get("authority_policy", "none")
    double_negation_budget = (
        args.double_negation_budget
        if args.double_negation_budget is not None
        else int(profile_defaults.get("double_negation_budget", 0))
    )
    if double_negation_budget == 2 and archaism < 3:
        raise SystemExit("--double-negation-budget 2 requires --archaism 3 or higher")

    selected_chunks = select_chunks(
        chunks,
        route,
        policy,
        args.mode,
        args.domain,
        profile,
        historical_register,
        query_tokens,
        args.chunk_id,
        args.heading,
        chunk_limit,
        args.broaden,
    )
    selected_records = select_records(
        records,
        route,
        policy,
        args.mode,
        args.domain,
        profile,
        keyword_text,
        query_tokens,
        args.source,
        args.heading,
        args.tag,
        record_limit,
        args.intensity,
        args.actor_scope,
        args.direction,
        archaism,
        foreign_terms,
        historical_register,
        authority_policy,
        args.source_evaluation,
        args.record_context,
        args.allow_high_risk,
        double_negation_budget,
        args.jurisdiction,
        args.broaden,
        args.include_excluded,
        args.include_non_reversible,
    )
    config = {
        "mode": args.mode,
        "domain": args.domain,
        "preset": args.preset,
        "profile": profile,
        "actor_scope": args.actor_scope,
        "direction": args.direction,
        "archaism": archaism,
        "foreign_terms": foreign_terms,
        "historical_register": historical_register,
        "authority_policy": authority_policy,
        "source_evaluation": args.source_evaluation,
        "record_context": args.record_context,
        "double_negation_budget": double_negation_budget,
        "jurisdiction": args.jurisdiction or None,
        "keywords": args.keywords,
        "broaden": args.broaden,
    }
    if args.format == "json":
        output = {
            "config": config,
            "chunks": [{"id": item["id"], "file": item["file"], "heading": item["heading"], "text": item["text"]} for item in selected_chunks],
            "records": [compact_record(item) for item in selected_records],
        }
        rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    else:
        rendered = render_markdown(config, selected_chunks, selected_records, max_chars)
    if len(rendered) > max_chars and args.format == "markdown":
        rendered = rendered[: max_chars - 18].rstrip() + "\n[素材包已按上限截断]\n"
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
