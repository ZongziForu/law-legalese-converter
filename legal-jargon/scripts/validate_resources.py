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
    return reports


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "data" / "source_manifest.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "data" / "catalog.json").read_text(encoding="utf-8"))
    routes = json.loads((root / "data" / "routes.json").read_text(encoding="utf-8"))
    records = load_records(root / "data" / "records.jsonl")
    _, entries = validate_schema(records, manifest)
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
