#!/usr/bin/env python3
"""Validate lossless resources, routing, and compact retrieval behavior."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from retrieve import build_retrieval_units


CHUNK_MARKER = re.compile(r"^<!-- chunk: ([a-z0-9.]+) -->$")
TABLE_MARKER = re.compile(r"^<!-- table-data: ([a-z0-9.]+) records=(\d+) -->$")


class ValidationError(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"records.jsonl line {line_number}: {exc}") from exc
    return records


def validate_reconstruction(root: Path, records: list[dict], manifest: dict) -> None:
    tables = {item["id"]: item for item in records if item.get("record_type") == "table"}
    entries: defaultdict[str, list[dict]] = defaultdict(list)
    for item in records:
        if item.get("record_type") == "entry":
            entries[item["source_table"]].append(item)

    for name, metadata in manifest["files"].items():
        reconstructed: list[str] = []
        path = root / "references" / name
        check(path.exists(), f"missing reference: {name}")
        for line in path.read_text(encoding="utf-8").splitlines():
            if CHUNK_MARKER.match(line):
                continue
            marker = TABLE_MARKER.match(line)
            if not marker:
                reconstructed.append(line)
                continue
            table_id, declared_count = marker.groups()
            check(table_id in tables, f"missing table metadata: {table_id}")
            rows = sorted(entries[table_id], key=lambda item: item["row_index"])
            check(len(rows) == int(declared_count), f"marker count mismatch: {table_id}")
            table = tables[table_id]
            reconstructed.extend([table["raw_header"], table["raw_separator"]])
            reconstructed.extend(item["raw_markdown"] for item in rows)
        text = "\n".join(reconstructed) + ("\n" if metadata["trailing_newline"] else "")
        overlays = [item for item in manifest.get("authorized_overlays", []) if item["file"] == name]
        for overlay in reversed(overlays):
            check(text.count(overlay["new"]) == 1, f"authorized overlay mismatch: {name}")
            text = text.replace(overlay["new"], overlay["old"], 1)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        check(digest == metadata["sha256"], f"lossless reconstruction failed: {name}")


def validate_schema(records: list[dict], manifest: dict) -> tuple[list[dict], list[dict]]:
    ids = [item.get("id") for item in records]
    check(all(ids), "record without id")
    check(len(ids) == len(set(ids)), "duplicate record id")
    tables = [item for item in records if item.get("record_type") == "table"]
    entries = [item for item in records if item.get("record_type") == "entry"]
    check(len(tables) == manifest["totals"]["tables"], "table total differs from manifest")
    check(len(entries) == manifest["totals"]["entries"], "entry total differs from manifest")
    table_ids = {item["id"] for item in tables}
    counts: defaultdict[str, int] = defaultdict(int)
    for item in entries:
        check(item["source_table"] in table_ids, f"orphan entry: {item['id']}")
        check(len(item["columns"]) == len(item["cells"]), f"column mismatch: {item['id']}")
        check(item.get("raw_markdown", "").startswith("|"), f"missing raw row: {item['id']}")
        counts[item["source_table"]] += 1
    for table in tables:
        check(counts[table["id"]] == table["row_count"], f"row count mismatch: {table['id']}")
    return tables, entries


def validate_retrieval_policy(policy: dict, entries: list[dict], catalog: dict) -> list[dict]:
    check(policy.get("version") == 2, "unsupported retrieval policy version")
    table_ids = {item["source_table"] for item in entries}
    entry_ids = {item["id"] for item in entries}
    available_units: set[str] = set()
    for item in entries:
        pairs = item.get("pairs", [])
        if pairs:
            available_units.update(f"{item['id']}#p{index}" for index in range(1, len(pairs) + 1))
        else:
            available_units.add(item["id"])
    check(
        set(policy.get("table_policies", {})) <= table_ids,
        "retrieval policy references a missing table",
    )
    check(
        set(policy.get("record_policies", {})) <= entry_ids,
        "retrieval policy references a missing record",
    )
    check(
        set(policy.get("unit_policies", {})) <= available_units,
        "retrieval policy references a missing pair/unit",
    )
    chunk_ids = {item["id"] for item in catalog.get("chunks", [])}
    policy_chunk_ids = {
        chunk_id
        for group in policy.get("chunk_policy_groups", [])
        for chunk_id in group.get("ids", [])
    }
    check(policy_chunk_ids <= chunk_ids, "retrieval policy references a missing chunk")

    effective = build_retrieval_units(entries, policy)
    effective_ids = [item["id"] for item in effective]
    check(len(effective_ids) == len(set(effective_ids)), "duplicate effective retrieval unit id")
    valid_tags = {
        item.get("fields", {}).get("标签ID")
        for item in entries
        if item.get("source_table") in {"r04.t001", "r04.t002"}
    }
    valid_tags.discard(None)
    valid_profiles = set(policy.get("preset_defaults", {}))
    for item in effective:
        risks = set(item.get("risk_flags", []))
        if "excluded_from_generation" not in risks:
            check(bool(item.get("tags")), f"effective unit lacks function tag: {item['id']}")
        check(set(item.get("tags", [])) <= valid_tags, f"effective unit has unknown tag: {item['id']}")
        check(
            not any(value.startswith(("SEM-", "SYNTAX-")) for value in risks),
            f"function tag was stored as a risk flag: {item['id']}",
        )
        check(
            set(item.get("portable_profiles", [])) <= valid_profiles,
            f"effective unit has unknown portable profile: {item['id']}",
        )
        check(
            set(item.get("modes", [])) <= {"rewrite", "expand", "analyze"},
            f"effective unit has invalid mode: {item['id']}",
        )
        check(
            item.get("direction") in {None, "positive", "negative", "compliant", "noncompliant", "no_rule", "not_prohibited"},
            f"effective unit has invalid direction: {item['id']}",
        )
        if item.get("required_cues"):
            check(
                all(isinstance(value, str) and value.strip() for value in item["required_cues"]),
                f"effective unit has an empty semantic cue: {item['id']}",
            )
            check(
                item.get("reversibility") == "conditional",
                f"semantic-cue unit is not conditional: {item['id']}",
            )
        if item.get("safe_backtranslation"):
            check(item.get("pairs"), f"safe backtranslation lacks a term pair: {item['id']}")
            check(
                item["pairs"][0].get("anchor") == item["safe_backtranslation"],
                f"safe backtranslation was not applied: {item['id']}",
            )
        strength = item.get("strength")
        if isinstance(strength, int):
            check(1 <= strength <= 5, f"effective strength outside 1..5: {item['id']}")
        if item.get("reversibility") == "non_reversible":
            check("non_reversible_mapping" in risks, f"non-reversible unit lacks hard gate: {item['id']}")

    official = [item for item in effective if item.get("official_backtranslation")]
    check(len(official) == 226, "official pairs were not split into 226 retrieval units")
    check(
        all(item.get("reversibility") in {"exact", "conditional", "non_reversible"} for item in official),
        "official pair lacks a valid reversibility class",
    )
    return effective


def validate_catalog(root: Path, catalog: dict, manifest: dict) -> None:
    chunks = catalog.get("chunks", [])
    ids = [item.get("id") for item in chunks]
    check(len(ids) == len(set(ids)), "duplicate chunk id")
    check(len(ids) == manifest["totals"]["chunks"], "chunk total differs from manifest")
    found: list[str] = []
    for path in sorted((root / "references").glob("*.md")):
        found.extend(
            match.group(1)
            for line in path.read_text(encoding="utf-8").splitlines()
            if (match := CHUNK_MARKER.match(line))
        )
    check(found == ids, "catalog order or marker coverage mismatch")


def validate_routes(routes: dict, catalog: dict, entries: list[dict]) -> None:
    available_sources = {item["source"] for item in entries}
    chunks = catalog["chunks"]
    referenced_sources: set[str] = set(routes["defaults"].get("base_record_sources", []))
    selectors: list[dict] = list(routes["defaults"].get("base_chunk_selectors", []))
    for source in routes["defaults"].get("base_chunk_files", []):
        check(any(chunk["source"] == source for chunk in chunks), f"default chunk source missing: {source}")
    for group_name in ("domains", "profiles", "modes"):
        for item in routes[group_name].values():
            referenced_sources.update(item.get("record_sources", []))
            selectors.extend(item.get("chunk_selectors", []))
            for source in item.get("chunk_files", []):
                check(any(chunk["source"] == source for chunk in chunks), f"route chunk source missing: {source}")
    check(referenced_sources <= available_sources, f"route record sources missing: {sorted(referenced_sources - available_sources)}")
    for selector in selectors:
        matches = [
            chunk for chunk in chunks
            if (not selector.get("file") or chunk["source"] == selector["file"])
            and (not selector.get("heading_contains") or selector["heading_contains"] in chunk["heading"])
        ]
        check(bool(matches), f"route selector has no chunk: {selector}")


def validate_official_register(entries: list[dict]) -> None:
    register = [item for item in entries if item["source"] == "16"]
    check(len(register) == 211, "source 16 entry count changed")
    excluded = [item for item in register if "excluded_from_generation" in item.get("risk_flags", [])]
    official = [item for item in register if item.get("official_backtranslation")]
    check(len(excluded) == 4, "source 16 exclusion count changed")
    check(len(official) == 207, "source 16 official record count changed")
    pairs = [pair for item in official for pair in item.get("pairs", [])]
    check(len(pairs) == 226, "source 16 term/anchor pair count changed")
    check(all(pair.get("term") and pair.get("anchor") for pair in pairs), "source 16 has empty official anchor")
    expected_tables = {
        "r16.t001": 10,
        "r16.t002": 10,
        "r16.t003": 12,
        "r16.t004": 9,
        "r16.t006": 16,
        "r16.t007": 8,
        "r16.t008": 17,
        "r16.t009": 16,
        "r16.t020": 12,
        "r16.t021": 3,
        "r16.t022": 8,
        "r16.t023": 4,
    }
    counts: defaultdict[str, int] = defaultdict(int)
    for item in register:
        counts[item["source_table"]] += 1
    for table_id, expected in expected_tables.items():
        check(counts[table_id] == expected, f"source 16 section count changed: {table_id}")


def validate_reference_structure(root: Path, manifest: dict) -> None:
    existing = {path.name for path in (root / "references").glob("*.md")}
    mention_pattern = re.compile(r"(?:references/)?(\d{2}_[A-Za-z0-9_]+\.md)")
    checked_files = [root / "SKILL.md", *(root / "references").glob("*.md")]
    for path in checked_files:
        for target in mention_pattern.findall(path.read_text(encoding="utf-8")):
            check(target in existing, f"missing referenced file {target} in {path.name}")

    separator = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
    migrated = set(manifest["migrated_prefixes"])
    for path in (root / "references").glob("*.md"):
        if path.name[:2] not in migrated:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        check(
            not any(index > 0 and "|" in lines[index - 1] and separator.match(line) for index, line in enumerate(lines)),
            f"unmigrated Markdown table remains: {path.name}",
        )


def retrieve(root: Path, arguments: list[str]) -> dict:
    command = [sys.executable, str(root / "scripts" / "retrieve.py"), *arguments, "--format", "json"]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def validate_retrieval(root: Path) -> list[dict]:
    def ids(packet: dict) -> set[str]:
        return {item["id"] for item in packet["records"]}

    def terms(packet: dict) -> list[str]:
        return [pair.get("term", "") for item in packet["records"] for pair in item.get("pairs", [])]

    cases = [
        (["--query", "这个说法没有充分理由", "--keywords", "否定 重构 妥当", "--domain", "general", "--preset", "general_blacktalk"], "05", None),
        (["--query", "一直控制这套设备", "--keywords", "占有 事实管领 物权", "--domain", "property", "--preset", "old_school_civilist"], "07", ("物权", "占有")),
        (["--query", "要求对方依约付款", "--keywords", "债 履行 金钱给付", "--domain", "obligation", "--preset", "old_school_civilist"], "07", ("债", "履行")),
        (["--query", "劳动者受公司管理", "--keywords", "劳动关系 从属性", "--domain", "labor", "--preset", "doctrinal_dense"], "07", ("劳动",)),
        (["--query", "行为人制造了不被允许的风险", "--keywords", "客观归责 风险实现", "--domain", "criminal", "--preset", "doctrinal_dense", "--mode", "expand"], "06", None),
        (["--query", "从事实描述转入规范评价", "--keywords", "事实 规范 方法论 转场", "--domain", "legal_theory", "--preset", "doctrinal_dense", "--mode", "expand"], "08", None),
        (["--query", "合同的效力需要进一步判断", "--keywords", "效力 法律关系 谨慎断语", "--domain", "civil", "--preset", "old_school_civilist"], "09", None),
        (["--query", "证据没有根据，法院不予采信", "--keywords", "否定 无据 不予采信 证据评价", "--domain", "procedure", "--preset", "judicial_formal", "--actor-scope", "adjudicator", "--direction", "negative"], "16", ("弱否定", "强否定")),
        (["--query", "婚姻已经严重破裂", "--keywords", "家事 婚姻破裂", "--domain", "family", "--preset", "judicial_formal", "--actor-scope", "family_court"], "16", ("家事",)),
        (["--query", "用古典法言说明前述理由", "--keywords", "古典法言 按断", "--domain", "general", "--preset", "classical_legalese"], "10", None),
        (["--query", "改成民国判牍式裁判文字", "--keywords", "判牍 判旨 函复", "--domain", "procedure", "--preset", "republican_judgment", "--actor-scope", "adjudicator"], "14", None),
        (["--query", "以历代刑法考方式辨析名实沿革", "--keywords", "刑法考 沿革 名实 按断", "--domain", "legal_history", "--preset", "classical_legalese", "--profile", "traditional_law"], "13", None),
        (["--query", "为法学论文写一段有文采的序言", "--keywords", "序言 价值 正义", "--domain", "legal_theory", "--preset", "general_blacktalk", "--profile", "preface_rhetoric", "--mode", "expand"], "15", None),
    ]
    reports: list[dict] = []
    for arguments, required_source, required_sections in cases:
        packet = retrieve(root, arguments)
        sources = {item["source"][:2] for item in packet["records"]}
        check(required_source in sources, f"retrieval missed source {required_source}: {arguments}")
        if required_sections:
            matching_sections = [item["section"] for item in packet["records"] if item["source"].startswith(required_source)]
            check(
                any(any(value in section for value in required_sections) for section in matching_sections),
                f"retrieval missed section {required_sections}: {arguments}",
            )
        check(all(item.get("section") != "十四、未收录项与排除理由" for item in packet["records"]), "excluded row retrieved")
        check(any(item["file"].startswith("03_") for item in packet["chunks"]), f"sentence templates missing: {arguments}")
        reports.append({"required_source": required_source, "records": len(packet["records"]), "chunks": len(packet["chunks"])})

    judicial = retrieve(root, cases[7][0])
    official = [item for item in judicial["records"] if item.get("official_backtranslation")]
    check(bool(official), "judicial packet lacks official backtranslation anchors")
    check(
        all("肯定" not in str(item.get("strength", "")) for item in official),
        "negative judicial route crossed evidence direction",
    )
    check(
        all("historical_context_required" not in item.get("risk_flags", []) for item in judicial["records"]),
        "judicial route leaked historical resources",
    )

    markdown_command = [sys.executable, str(root / "scripts" / "retrieve.py"), *cases[7][0]]
    markdown = subprocess.run(markdown_command, check=True, capture_output=True, text=True).stdout
    check(len(markdown) <= 9000, "default Markdown packet exceeds context budget")
    broadened = subprocess.run([*markdown_command, "--broaden"], check=True, capture_output=True, text=True).stdout
    check(len(broadened) <= 9000, "broadened Markdown packet exceeds context budget")

    party = retrieve(
        root,
        ["--query", "当事人请求法院判决", "--keywords", "当事人 主张 诉讼行为", "--domain", "procedure", "--preset", "judicial_formal", "--actor-scope", "party"],
    )
    check(
        all(item.get("actor_scope") in {None, "party"} for item in party["records"]),
        "party route leaked adjudicator-side records",
    )
    targeted = retrieve(root, ["--domain", "procedure", "--preset", "judicial_formal", "--chunk-id", "r16.h008", "--source", "16"])
    check(any(item["id"] == "r16.h008" for item in targeted["chunks"]), "exact chunk retrieval failed")

    portable = retrieve(
        root,
        ["--query", "简言之，这与本案没有关系", "--keywords", "简言之 没有关系", "--domain", "general", "--preset", "general_blacktalk"],
    )
    check("质言之" in terms(portable) and "无涉" in terms(portable), "portable source-16 terms remain siloed")
    split = next(item for item in portable["records"] if item["id"] == "r16.t018.e007#p2")
    check(terms({"records": [split]}) == ["无涉"], "multi-pair official row was not isolated")

    neutral_actor = retrieve(
        root,
        ["--query", "参考前述材料", "--keywords", "参酌 参考", "--domain", "general", "--preset", "general_blacktalk"],
    )
    check("参酌" in terms(neutral_actor), "neutral portable term remained trapped behind adjudicator actor scope")

    legal_arguments = [
        "--query", "这个做法符合法律规定", "--keywords", "符合法律规定",
        "--mode", "rewrite", "--domain", "general", "--preset", "general_blacktalk",
    ]
    legal_closed = retrieve(root, legal_arguments)
    legal_open = retrieve(root, [*legal_arguments, "--direction", "compliant"])
    check("r16.t007.e001" not in ids(legal_closed), "legality term bypassed direction gate")
    check("r16.t007.e001" in ids(legal_open), "legality term failed its explicit direction gate")

    evaluation_arguments = [
        "--query", "这种说法不能作为准则", "--keywords", "不能作为准则 未可为训",
        "--mode", "rewrite", "--domain", "general", "--preset", "general_blacktalk",
    ]
    evaluation_closed = retrieve(root, evaluation_arguments)
    evaluation_open = retrieve(root, [*evaluation_arguments, "--source-evaluation"])
    check("未可为训" not in terms(evaluation_closed), "evaluative term bypassed source gate")
    check("未可为训" in terms(evaluation_open), "portable source-13 evaluation term remained siloed")

    authority_arguments = [
        "--query", "这背离了立法原意", "--keywords", "立法之本意 立法原意",
        "--mode", "rewrite", "--domain", "legal_theory", "--preset", "doctrinal_dense",
    ]
    authority_closed = retrieve(root, authority_arguments)
    authority_open = retrieve(root, [*authority_arguments, "--authority-policy", "provided_only"])
    check("立法之本意" not in terms(authority_closed), "authority-dependent term bypassed authority policy")
    check("立法之本意" in terms(authority_open), "authority-dependent term failed provided authority policy")

    foreign_arguments = [
        "--query", "构成要件", "--keywords", "Tatbestand 构成要件",
        "--mode", "rewrite", "--domain", "legal_theory", "--preset", "doctrinal_dense",
    ]
    foreign_closed = retrieve(root, [*foreign_arguments, "--foreign-terms", "0"])
    foreign_open = retrieve(root, [*foreign_arguments, "--foreign-terms", "1"])
    check("r08.t001.e001" not in ids(foreign_closed), "foreign term bypassed foreign_terms=0")
    check("r08.t001.e001" in ids(foreign_open), "foreign term failed foreign_terms opt-in")

    method_arguments = [
        "--query", "解释不能只看字面", "--keywords", "文义 目的 解释 续造",
        "--domain", "legal_theory", "--preset", "doctrinal_dense",
    ]
    method_rewrite = retrieve(root, [*method_arguments, "--mode", "rewrite"])
    method_expand = retrieve(root, [*method_arguments, "--mode", "expand"])
    check(not any(value.startswith("r08.t002") for value in ids(method_rewrite)), "methodology mechanism leaked into rewrite")
    check(any(value.startswith("r08.t002") for value in ids(method_expand)), "methodology mechanism missing from expand")

    history_arguments = [
        "--query", "古代刑名制度的沿革", "--keywords", "沿革 古者 后世",
        "--domain", "legal_history", "--preset", "classical_legalese",
    ]
    history_closed = retrieve(root, history_arguments)
    history_open = retrieve(root, [*history_arguments, "--historical-register", "traditional_law"])
    check(not any(value.startswith("r13.t002") for value in ids(history_closed)), "historical terms leaked into contemporary classical style")
    check(any(value.startswith("r13.t002") for value in ids(history_open)), "historical terms failed explicit historical register")

    broadened_packet = retrieve(
        root,
        [
            "--query", "欠钱不还，应当承担责任", "--keywords", "债务 履行 责任",
            "--mode", "rewrite", "--domain", "obligation", "--preset", "old_school_civilist",
            "--broaden", "--record-limit", "24",
        ],
    )
    broadened_sources = {item["source"][:2] for item in broadened_packet["records"]}
    broadened_chunks = {item["id"] for item in broadened_packet["chunks"]}
    check(len(broadened_packet["records"]) <= 24, "explicit record limit was not a hard ceiling")
    check(not broadened_sources.intersection({"06", "08", "15"}), "broaden crossed a domain/profile hard route")
    check("r11.h008" not in broadened_chunks, "broaden leaked a judicial example into old-school civil style")
    check(
        not broadened_chunks.intersection({f"r03.h{index:03d}" for index in range(10, 17)}),
        "rewrite packet leaked expand-only sentence templates",
    )

    double_arguments = [
        "--query", "这个说法并非毫无根据", "--keywords", "尚非无据 弱肯定",
        "--domain", "procedure", "--preset", "judicial_formal", "--direction", "positive",
    ]
    double_closed = retrieve(root, [*double_arguments, "--double-negation-budget", "0"])
    double_open = retrieve(root, [*double_arguments, "--double-negation-budget", "1"])
    check(not any(term.startswith("尚非无") for term in terms(double_closed)), "double negation bypassed dosage gate")
    check(any(term.startswith("尚非无") for term in terms(double_open)), "double negation failed dosage opt-in")

    old_school_double = retrieve(
        root,
        [
            "--query", "这个说法并非毫无根据", "--keywords", "并非毫无根据 尚非无据",
            "--mode", "rewrite", "--domain", "civil", "--preset", "old_school_civilist",
            "--direction", "positive",
        ],
    )
    check(any(term.startswith("尚非无") for term in terms(old_school_double)), "double negation remained siloed from old-school civil style")

    general_double_arguments = [
        "--query", "这个说法并非毫无根据", "--keywords", "并非毫无根据 尚非无据",
        "--mode", "rewrite", "--domain", "general", "--preset", "general_blacktalk",
        "--direction", "positive",
    ]
    general_double_closed = retrieve(root, general_double_arguments)
    general_double_open = retrieve(
        root,
        [*general_double_arguments, "--archaism", "3", "--double-negation-budget", "1"],
    )
    check(not any(term.startswith("尚非无") for term in terms(general_double_closed)), "modern style bypassed double-negation archaism gate")
    check(any(term.startswith("尚非无") for term in terms(general_double_open)), "modern style failed explicit double-negation opt-in")

    high_double_arguments = [
        "--query", "这个结论似乎不是没有理由", "--keywords", "似乎不是没有 尚难谓非",
        "--mode", "rewrite", "--domain", "civil", "--preset", "old_school_civilist",
        "--direction", "positive",
    ]
    high_double_closed = retrieve(root, high_double_arguments)
    high_double_open = retrieve(root, [*high_double_arguments, "--allow-high-risk"])
    check("尚难谓非" not in terms(high_double_closed), "high-risk double negation bypassed opt-in")
    check("尚难谓非" in terms(high_double_open), "high-risk double negation failed explicit opt-in")

    record_arguments = [
        "--query", "已有材料证明", "--keywords", "业据 已据 已有",
        "--domain", "civil", "--preset", "old_school_civilist",
    ]
    record_closed = retrieve(root, record_arguments)
    record_open = retrieve(root, [*record_arguments, "--record-context"])
    check("业据" not in terms(record_closed), "record-dependent term bypassed record context gate")
    check("业据" in terms(record_open), "record-dependent term failed explicit record context")

    taiwan_arguments = [
        "--query", "婚姻已经破裂", "--keywords", "婚姻破绽 婚姻破裂",
        "--domain", "family", "--preset", "judicial_formal", "--actor-scope", "family_court",
    ]
    taiwan_closed = retrieve(root, taiwan_arguments)
    taiwan_open = retrieve(root, [*taiwan_arguments, "--jurisdiction", "Taiwan"])
    check("婚姻破绽" not in terms(taiwan_closed), "Taiwan-specific term bypassed jurisdiction gate")
    check("婚姻破绽" in terms(taiwan_open), "Taiwan-specific term failed jurisdiction opt-in")

    pronoun_arguments = [
        "--query", "他们已经提出意见", "--keywords", "渠等 他们",
        "--domain", "procedure", "--preset", "judicial_formal",
    ]
    pronoun_closed = retrieve(root, [*pronoun_arguments, "--archaism", "0"])
    pronoun_open = retrieve(root, [*pronoun_arguments, "--archaism", "3"])
    check("渠等" not in terms(pronoun_closed), "archaic pronoun bypassed archaism gate")
    check("渠等" in terms(pronoun_open), "archaic pronoun failed archaism opt-in")

    supervision_closed = retrieve(
        root,
        [
            "--query", "甲与乙共同办理此事", "--keywords", "与 共同办理",
            "--mode", "rewrite", "--domain", "general", "--preset", "old_school_civilist",
        ],
    )
    supervision_open = retrieve(
        root,
        [
            "--query", "甲监督乙共同办理此事", "--keywords", "监督共同办理",
            "--mode", "rewrite", "--domain", "general", "--preset", "old_school_civilist",
        ],
    )
    check("督同" not in terms(supervision_closed), "督同 was recalled from a bare conjunction")
    check("督同" in terms(supervision_open), "督同 failed its supervisory semantic cue")
    supervision_record = next(item for item in supervision_open["records"] if "督同" in terms({"records": [item]}))
    check(
        supervision_record["pairs"][0]["anchor"].startswith("监督并会同"),
        "督同 did not use its safe backtranslation anchor",
    )

    not_prohibited_base = [
        "--query", "该事项法律并未禁止", "--keywords", "法律并未禁止",
        "--mode", "rewrite", "--domain", "general", "--preset", "general_blacktalk",
        "--archaism", "3", "--double-negation-budget", "1", "--allow-high-risk",
    ]
    not_prohibited_wrong = retrieve(root, [*not_prohibited_base, "--direction", "compliant"])
    not_prohibited_open = retrieve(root, [*not_prohibited_base, "--direction", "not_prohibited"])
    check("即非法所不许" not in terms(not_prohibited_wrong), "non-prohibition was conflated with positive compliance")
    check("即非法所不许" in terms(not_prohibited_open), "non-prohibition expression failed its exact direction gate")
    not_prohibited_record = next(
        item for item in not_prohibited_open["records"] if "即非法所不许" in terms({"records": [item]})
    )
    check(
        "法律并未禁止" in not_prohibited_record["pairs"][0]["anchor"],
        "non-prohibition expression retained the overbroad official anchor",
    )

    support_closed = retrieve(
        root,
        [
            "--query", "还有其他证据", "--keywords", "其他证据",
            "--mode", "rewrite", "--domain", "general", "--preset", "general_blacktalk",
            "--source-evaluation",
        ],
    )
    support_open = retrieve(
        root,
        [
            "--query", "该材料可以作为补充证明", "--keywords", "补充证明",
            "--mode", "rewrite", "--domain", "general", "--preset", "general_blacktalk",
            "--source-evaluation",
        ],
    )
    check("r16.t005.e021" not in ids(support_closed), "佐证 was recalled from bare other-evidence wording")
    check("r16.t005.e021" in ids(support_open), "佐证 failed its supplemental-proof semantic cue")

    non_reversible_arguments = [
        "--query", "假执行", "--keywords", "假执行", "--domain", "procedure",
        "--preset", "judicial_formal", "--source", "16", "--jurisdiction", "Taiwan",
    ]
    non_reversible_closed = retrieve(root, non_reversible_arguments)
    non_reversible_open = retrieve(root, [*non_reversible_arguments, "--include-non-reversible"])
    check("假执行" not in terms(non_reversible_closed), "truly non-reversible mapping entered normal generation")
    check("假执行" in terms(non_reversible_open), "non-reversible mapping unavailable for explicit audit")

    invalid_budget = subprocess.run(
        [
            sys.executable, str(root / "scripts" / "retrieve.py"), "--archaism", "2",
            "--double-negation-budget", "2",
        ],
        capture_output=True,
        text=True,
    )
    check(invalid_budget.returncode != 0, "double-negation budget 2 ignored the archaism floor")
    return reports


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "data" / "source_manifest.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "data" / "catalog.json").read_text(encoding="utf-8"))
    routes = json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))
    policy = json.loads((root / "data" / "retrieval_policy.json").read_text(encoding="utf-8"))
    records = load_records(root / "data" / "records.jsonl")
    _, entries = validate_schema(records, manifest)
    effective = validate_retrieval_policy(policy, entries, catalog)
    validate_reconstruction(root, records, manifest)
    validate_catalog(root, catalog, manifest)
    validate_routes(routes, catalog, entries)
    validate_official_register(entries)
    validate_reference_structure(root, manifest)
    reports = validate_retrieval(root)

    checked_text_files = [root / "SKILL.md"]
    checked_text_files.extend((root / "references").glob("*.md"))
    checked_text_files.extend(path for path in (root / "data").glob("*") if path.is_file())
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in checked_text_files)
    check("無" not in all_text, "traditional character residue found: 無")
    result = {
        "status": "ok",
        "tables": manifest["totals"]["tables"],
        "entries": manifest["totals"]["entries"],
        "chunks": manifest["totals"]["chunks"],
        "effective_units": len(effective),
        "source_16": {"rows": 211, "official_pairs": 226, "excluded_rows": 4},
        "retrieval_cases": reports,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
