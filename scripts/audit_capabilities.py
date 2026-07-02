#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


HIGH_RISK_CATEGORIES = {"UI / 前端", "部署", "知识 / 记忆", "网页 / 自动化"}
COMMON_CAPABILITY_TYPES = {"skill", "plugin", "cli", "external-api-provider", "content-source"}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Audit capability registry quality.")
    parser.add_argument("--registry", type=Path, default=repo_root / "capability-registry.local.json")
    parser.add_argument("--json-output", type=Path, default=repo_root / "reports" / "capability-audit.json")
    parser.add_argument("--md-output", type=Path, default=repo_root / "reports" / "capability-audit.md")
    parser.add_argument("--query", default="agency", help="Search probe used to verify recall.")
    return parser.parse_args()


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def search_blob(item: dict[str, object]) -> str:
    fields = [
        "name",
        "displayName",
        "displayNameEn",
        "desc",
        "descEn",
        "cat",
        "sourceType",
        "host",
        "sourcePath",
        "sourcePathDisplay",
        "repoUrl",
        "installKind",
        "installKindLabel",
        "metadataCategory",
        "categorySource",
        "descSource",
        "searchText",
    ]
    parts = [str(item.get(field, "")) for field in fields]
    for field in ("availableIn", "sceneTags", "tags", "localDocDisplays"):
        value = item.get(field)
        if isinstance(value, list):
            parts.extend(str(entry) for entry in value)
    return " ".join(parts).lower()


def issue_item(item: dict[str, object], reason: str) -> dict[str, object]:
    return {
        "name": item.get("name"),
        "displayName": item.get("displayName"),
        "cat": item.get("cat"),
        "host": item.get("host"),
        "sourceType": item.get("sourceType"),
        "reason": reason,
        "repoUrl": item.get("repoUrl"),
        "descSource": item.get("descSource"),
        "categorySource": item.get("categorySource"),
        "sourcePathDisplay": item.get("sourcePathDisplay"),
    }


def has_chinese(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def has_usage_language(item: dict[str, object]) -> bool:
    text = " ".join(str(item.get(field, "")) for field in ("desc", "prompt", "installEvidence"))
    return has_chinese(text) and any(token in text for token in ("什么时候", "使用", "用途", "调用", "不要", "默认", "父级", "子级", "外部", "本地"))


def has_shortest_usage(item: dict[str, object]) -> bool:
    text = " ".join(str(item.get(field, "")) for field in ("prompt", "desc", "installEvidence"))
    return any(token in text for token in ("最短", "调用方式", "用法", "rtk ", "OpenAI-compatible", "SKILL.md", "README", "provider"))


def has_parent_child_policy(item: dict[str, object]) -> bool:
    text = " ".join(str(item.get(field, "")) for field in ("desc", "prompt", "installEvidence", "searchText"))
    if item.get("requiresSubskills") or int(item.get("childCount") or 0) > 0 or int(item.get("sourceCount") or 1) > 1:
        return any(token in text for token in ("父级", "子级", "子项", "child", "parent", "专项", "默认"))
    return True


def audit(items: list[dict[str, object]], query: str) -> dict[str, object]:
    anomalies: dict[str, list[dict[str, object]]] = {
        "missingRepoUrl": [],
        "shortOrGenericDescription": [],
        "fallbackCategory": [],
        "hostConflict": [],
        "sameNameMultiHost": [],
        "parentSourceCountAnomaly": [],
        "missingLocalDocs": [],
        "missingChineseUsage": [],
        "missingShortestUsage": [],
        "missingParentChildPolicy": [],
    }

    grouped_names: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in items:
        grouped_names[norm(str(item.get("name", "")))].append(item)
        source_type = str(item.get("sourceType") or "")
        install_kind = str(item.get("installKind") or "")
        desc = str(item.get("desc") or item.get("descEn") or "")
        desc_source = str(item.get("descSource") or "")
        category_source = str(item.get("categorySource") or "")
        repo_url = str(item.get("repoUrl") or "")
        available = item.get("availableIn") if isinstance(item.get("availableIn"), list) else []
        local_docs = item.get("localDocs") if isinstance(item.get("localDocs"), list) else []

        if source_type in {"skill", "agent", "plugin", "reference", "external-api-provider"} and not repo_url:
            anomalies["missingRepoUrl"].append(issue_item(item, "source usually benefits from a repo URL but none was found locally"))
        if desc_source == "default" or len(desc.strip()) < 42:
            anomalies["shortOrGenericDescription"].append(issue_item(item, "description is short or generated from default fallback"))
        if category_source.startswith("fallback"):
            anomalies["fallbackCategory"].append(issue_item(item, "category fell back to backend default"))
        if item.get("host") == "hermes" and "codex" in available:
            anomalies["hostConflict"].append(issue_item(item, "host is hermes but availableIn includes codex"))
        if item.get("host") == "codex" and "hermes" in available and source_type != "plugin":
            anomalies["hostConflict"].append(issue_item(item, "host is codex but availableIn includes hermes"))
        if int(item.get("sourceCount") or 1) > 20:
            anomalies["parentSourceCountAnomaly"].append(issue_item(item, "sourceCount is high enough to require manual review"))
        if install_kind == "user-installed" and source_type == "skill" and not local_docs:
            anomalies["missingLocalDocs"].append(issue_item(item, "user-installed skill has no local README/USAGE beside SKILL.md"))
        if source_type in COMMON_CAPABILITY_TYPES and not has_usage_language(item):
            anomalies["missingChineseUsage"].append(issue_item(item, "common capability lacks Chinese when-to-use / when-not-to-use wording"))
        if source_type in COMMON_CAPABILITY_TYPES and not has_shortest_usage(item):
            anomalies["missingShortestUsage"].append(issue_item(item, "common capability lacks a shortest usage path"))
        if source_type in COMMON_CAPABILITY_TYPES and not has_parent_child_policy(item):
            anomalies["missingParentChildPolicy"].append(issue_item(item, "parent/toolkit capability lacks parent-child routing wording"))

    for key, records in grouped_names.items():
        hosts = sorted({str(item.get("host") or "") for item in records})
        cats = sorted({str(item.get("cat") or "") for item in records})
        if key and len(records) > 1 and (len(hosts) > 1 or len(cats) > 1):
            for item in records:
                anomalies["sameNameMultiHost"].append(issue_item(item, f"same normalized name appears across hosts={hosts}, cats={cats}"))

    risk_samples = {}
    for category in sorted(HIGH_RISK_CATEGORIES):
        candidates = [
            item for item in items
            if item.get("cat") == category
            and (str(item.get("categorySource") or "").startswith("fallback") or str(item.get("descSource") or "") == "default" or not item.get("repoUrl"))
        ]
        risk_samples[category] = [issue_item(item, "high-risk category sample") for item in candidates[:20]]

    query_lower = query.lower()
    search_matches = [issue_item(item, f"matches query '{query}'") for item in items if query_lower in search_blob(item)]

    return {
        "summary": {
            "count": len(items),
            "sourceTypes": dict(Counter(str(item.get("sourceType") or "") for item in items)),
            "hosts": dict(Counter(str(item.get("host") or "") for item in items)),
            "categories": dict(Counter(str(item.get("cat") or "") for item in items)),
            "descSources": dict(Counter(str(item.get("descSource") or "") for item in items)),
            "categorySources": dict(Counter(str(item.get("categorySource") or "") for item in items)),
        },
        "anomalyCounts": {key: len(value) for key, value in anomalies.items()},
        "anomalies": anomalies,
        "riskSamples": risk_samples,
        "searchProbe": {
            "query": query,
            "matchCount": len(search_matches),
            "matches": search_matches[:100],
        },
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    lines = ["# Capability Audit", ""]
    summary = report["summary"]
    lines.append(f"- Total: {summary['count']}")
    lines.append(f"- Source types: `{summary['sourceTypes']}`")
    lines.append(f"- Categories: `{summary['categories']}`")
    lines.append(f"- Description sources: `{summary['descSources']}`")
    lines.append(f"- Category sources: `{summary['categorySources']}`")
    lines.append("")
    lines.append("## Anomaly Counts")
    for key, count in report["anomalyCounts"].items():
        lines.append(f"- {key}: {count}")
    lines.append("")
    lines.append("## Search Probe")
    probe = report["searchProbe"]
    lines.append(f"- Query: `{probe['query']}`")
    lines.append(f"- Matches: {probe['matchCount']}")
    for item in probe["matches"][:20]:
        lines.append(f"  - `{item['name']}` · {item['cat']} · {item['host']} · {item['sourcePathDisplay']}")
    lines.append("")
    lines.append("## Top Anomalies")
    for key, records in report["anomalies"].items():
        lines.append(f"### {key}")
        for item in records[:30]:
            lines.append(f"- `{item['name']}` · {item['cat']} · {item['host']} · {item['reason']}")
        if len(records) > 30:
            lines.append(f"- ... {len(records) - 30} more")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    items = payload["capabilities"] if isinstance(payload, dict) else payload
    report = audit(items, args.query)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.md_output)
    print(json.dumps({"json": str(args.json_output), "md": str(args.md_output), "summary": report["summary"], "anomalyCounts": report["anomalyCounts"], "searchProbe": report["searchProbe"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
