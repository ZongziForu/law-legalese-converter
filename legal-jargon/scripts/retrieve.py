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


def required_chunk_ids(route: dict, mode: str, preset: str) -> list[str]:
    selectors = list(route["defaults"].get("base_chunk_selectors", []))
    selectors.extend(route["modes"].get(mode, {}).get("chunk_selectors", []))
    selectors.extend(route["profiles"].get(preset, {}).get("chunk_selectors", []))
    return selectors


def select_chunks(
    chunks: list[dict],
    route: dict,
    mode: str,
    domain: str,
    preset: str,
    query_tokens: list[str],
    explicit_chunk_ids: list[str],
    heading_filters: list[str],
    limit: int,
    broaden: bool,
) -> list[dict]:
    required_selectors = required_chunk_ids(route, mode, preset)
    selected: list[dict] = []
    selected_ids: set[str] = set()
    for chunk in chunks:
        if chunk["id"] in explicit_chunk_ids or (
            heading_filters and any(value in " ".join(chunk.get("heading_path", [])) for value in heading_filters)
        ):
            if chunk["id"] not in selected_ids and len(chunk.get("text", "").splitlines()) > 1:
                selected.append(chunk)
                selected_ids.add(chunk["id"])
    for selector in required_selectors:
        for chunk in chunks:
            if selector_matches(chunk, selector) and chunk["id"] not in selected_ids:
                if len(chunk.get("text", "").splitlines()) <= 1:
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
    target_limit = limit * (2 if broaden else 1)
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


def select_records(
    records: list[dict],
    route: dict,
    mode: str,
    domain: str,
    preset: str,
    query_tokens: list[str],
    explicit_sources: list[str],
    headings: list[str],
    tags: list[str],
    limit: int,
    intensity: int | None,
    actor_scope: str,
    direction: str | None,
    broaden: bool,
    include_excluded: bool,
) -> list[dict]:
    priorities = source_priority(route, domain, preset, explicit_sources)
    heading_keywords = list(route["domains"].get(domain, {}).get("heading_keywords", []))
    candidates: list[dict] = []
    for record in records:
        risks = set(record.get("risk_flags", []))
        if "excluded_from_generation" in risks and not include_excluded:
            continue
        if explicit_sources and record["source"] not in explicit_sources:
            continue
        heading_text = " ".join(record.get("source_heading_path", []))
        if headings and not any(value in heading_text for value in headings):
            continue
        if tags and not set(tags).intersection(record.get("tags", [])):
            continue
        if "historical_context_required" in risks and preset not in {"republican_judgment", "traditional_law"}:
            continue
        if record["source"] in {"10", "13", "14", "16"} and preset not in record.get("presets", []):
            continue
        if not actor_allowed(record.get("actor_scope"), actor_scope):
            continue
        item_direction = record_direction(record)
        if direction in {"positive", "negative"} and item_direction in {"positive", "negative"} and item_direction != direction:
            continue
        if direction in {"compliant", "noncompliant", "no_rule"} and item_direction in {"compliant", "noncompliant", "no_rule"} and item_direction != direction:
            continue
        if not broaden and priorities and record["source"] not in priorities:
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
                preset,
                heading_keywords,
                mode,
                intensity,
            ),
            -item.get("row_index", 0),
        ),
        reverse=True,
    )

    target_limit = limit * (2 if broaden else 1)
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
    for key in ("pairs", "strength", "actor_scope", "risk_flags", "tags"):
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
    official_pairs: list[tuple[str, str, str, list[str]]] = []
    for record in records:
        fields = "；".join(f"{key}={value}" for key, value in record["fields"].items() if value)
        extras: list[str] = []
        if record.get("strength") is not None:
            extras.append(f"强度={record['strength']}")
        if record.get("actor_scope"):
            extras.append(f"主体端={record['actor_scope']}")
        if record.get("risk_flags"):
            extras.append("门控=" + ",".join(record["risk_flags"]))
        line = f"- [{record['id']}] {fields}"
        if extras:
            line += "；" + "；".join(extras)
        if len("\n".join(lines)) + len(line) + 2 > max_chars * 0.90:
            break
        lines.append(line)
        if record.get("official_backtranslation"):
            for pair in record.get("pairs", []):
                if pair.get("term") and pair.get("anchor"):
                    official_pairs.append((record["id"], pair["term"], pair["anchor"], record.get("risk_flags", [])))

    if official_pairs:
        lines.extend(["", "## 官方回译锚点"])
        for record_id, term, anchor, risks in official_pairs:
            gate = f"；门控={','.join(risks)}" if risks else ""
            line = f"- [{record_id}] {term} -> {anchor}{gate}"
            if len("\n".join(lines)) + len(line) + 2 > max_chars:
                break
            lines.append(line)
        lines.extend([
            "",
            "生成后，将实际采用的左侧词条压缩回右侧锚点，并与命题核逐项比对；方向、主体端或情态不一致时必须撤回该词条。",
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
    parser.add_argument(
        "--actor-scope",
        choices=["neutral", "adjudicator", "party", "sentencing_adjudicator", "family_court"],
        default="neutral",
    )
    parser.add_argument("--direction", choices=["positive", "negative", "compliant", "noncompliant", "no_rule"])
    parser.add_argument("--source", action="append", default=[], help="Restrict to a two-digit source prefix")
    parser.add_argument("--heading", action="append", default=[], help="Require a source heading substring")
    parser.add_argument("--chunk-id", action="append", default=[], help="Include an exact Markdown chunk")
    parser.add_argument("--tag", action="append", default=[], help="Require any function tag")
    parser.add_argument("--record-limit", type=int)
    parser.add_argument("--chunk-limit", type=int)
    parser.add_argument("--max-chars", type=int)
    parser.add_argument("--broaden", action="store_true")
    parser.add_argument("--include-excluded", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    route = load_json(root / "data" / "routes.json")
    catalog = load_json(root / "data" / "catalog.json")["chunks"]
    records = load_records(root / "data" / "records.jsonl")
    chunks = read_chunks(root, catalog)
    defaults = route["defaults"]
    record_limit = args.record_limit or defaults["record_limit"]
    chunk_limit = args.chunk_limit or defaults["chunk_limit"]
    max_chars = args.max_chars or defaults["max_chars"]
    keyword_text = " ".join(filter(None, [args.query, args.keywords]))
    query_tokens = tokenize(keyword_text)
    profile = args.profile or args.preset

    selected_chunks = select_chunks(
        chunks,
        route,
        args.mode,
        args.domain,
        profile,
        query_tokens,
        args.chunk_id,
        args.heading,
        chunk_limit,
        args.broaden,
    )
    selected_records = select_records(
        records,
        route,
        args.mode,
        args.domain,
        profile,
        query_tokens,
        args.source,
        args.heading,
        args.tag,
        record_limit,
        args.intensity,
        args.actor_scope,
        args.direction,
        args.broaden,
        args.include_excluded,
    )
    config = {
        "mode": args.mode,
        "domain": args.domain,
        "preset": args.preset,
        "profile": profile,
        "actor_scope": args.actor_scope,
        "direction": args.direction,
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
