#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


VERSION = "0.2.0"


@dataclass(frozen=True)
class ScanRoot:
    host: str
    source_type: str
    path: Path
    pattern: str | None = None


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Scan local capability roots and generate a registry.")
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home directory to scan.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root to scan for local agent folders.")
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "capability-registry.local.json",
        help="Output JSON path.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def slug_to_title(value: str) -> str:
    cleaned = re.sub(r"[-_./]+", " ", value).strip()
    if not cleaned:
        return value
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return cleaned
    return " ".join(token.capitalize() for token in cleaned.split())


def infer_category(text: str) -> str:
    value = text.lower()
    if any(token in value for token in ("ui", "frontend", "design", "cursor", "component", "visual", "css")):
        return "UI / 前端"
    if any(token in value for token in ("deploy", "release", "vercel", "netlify", "cloud", "render", "wrangler", "ops")):
        return "部署"
    if any(token in value for token in ("web", "browser", "search", "scrape", "http", "automation", "mcp")):
        return "网页 / 自动化"
    if any(token in value for token in ("video", "audio", "media", "caption", "podcast", "content")):
        return "视频 / 内容"
    if any(token in value for token in ("memory", "knowledge", "docs", "document", "research", "prompt", "agent")):
        return "知识 / 记忆"
    return "代码 / 后端"


def infer_env(host: str, source_type: str) -> list[str]:
    remote_hosts = {"plugin", "mcp", "extension"}
    if source_type in remote_hosts:
        return ["remote"]
    if host in {"cursor", "claude-code", "github-copilot", "qoder", "trae"}:
        return ["shared"]
    return ["local"]


def score_for(source_type: str) -> str:
    return {
        "skill": "8.9",
        "agent": "8.5",
        "plugin": "8.3",
        "mcp": "8.4",
        "rule": "8.1",
        "extension": "8.0",
    }.get(source_type, "8.0")


def icon_for(name: str) -> str:
    letters = [char for char in name.upper() if char.isalnum()]
    return ("".join(letters[:3]) or "CAP")[:3]


def safe_read(path: Path, limit: int = 6000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    _, _, remainder = text.partition("\n")
    frontmatter, marker, _ = remainder.partition("\n---")
    if not marker:
        return {}
    data: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def summarize_text(text: str) -> tuple[str | None, str | None]:
    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    heading_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    paragraph_match = re.search(r"\n\n([^\n#][^\n]+)", text)
    return name or (heading_match.group(1).strip() if heading_match else None), description or (paragraph_match.group(1).strip() if paragraph_match else None)


def build_prompt(display_name: str, description: str, host: str, source_type: str) -> str:
    return (
        f"先检查并调用 {display_name}。\n"
        f"用途：{description}\n"
        f"来源：{host} {source_type}\n"
        "要求：先说明为什么选它，再决定是否要组合其他 skill / plugin / MCP / agent。"
    )


def build_capability(
    *,
    host: str,
    source_type: str,
    source_path: Path,
    raw_name: str,
    raw_description: str | None,
) -> dict[str, object]:
    display_name = slug_to_title(raw_name)
    description = raw_description or f"Discovered {source_type} from {host}."
    category = infer_category(" ".join([raw_name, display_name, description, host, source_type]))
    env = infer_env(host, source_type)
    tags = [host, source_type, source_path.parent.name or source_path.name]
    source_path_str = str(source_path)
    source_display = source_path_str.replace(str(Path.home()), "~")
    return {
        "name": raw_name,
        "displayName": display_name,
        "cat": category,
        "env": env,
        "icon": icon_for(display_name),
        "score": score_for(source_type),
        "desc": description,
        "tags": tags,
        "prompt": build_prompt(display_name, description, host, source_type),
        "sourceType": source_type,
        "host": host,
        "sourcePath": source_path_str,
        "sourcePathDisplay": source_display,
    }


def scan_skill_root(root: ScanRoot) -> Iterable[dict[str, object]]:
    if not root.path.exists():
        return []
    results = []
    for marker in root.path.rglob(root.pattern or "SKILL.md"):
        text = safe_read(marker)
        raw_name, raw_description = summarize_text(text)
        name = raw_name or marker.parent.name
        results.append(
            build_capability(
                host=root.host,
                source_type=root.source_type,
                source_path=marker,
                raw_name=name,
                raw_description=raw_description,
            )
        )
    return results


def scan_agent_files(root: ScanRoot, glob_pattern: str) -> Iterable[dict[str, object]]:
    if not root.path.exists():
        return []
    results = []
    for candidate in root.path.rglob(glob_pattern):
        if candidate.name.startswith("."):
            continue
        text = safe_read(candidate)
        raw_name, raw_description = summarize_text(text)
        name = raw_name or candidate.stem
        results.append(
            build_capability(
                host=root.host,
                source_type=root.source_type,
                source_path=candidate,
                raw_name=name,
                raw_description=raw_description,
            )
        )
    return results


def scan_plugin_roots(path: Path) -> Iterable[dict[str, object]]:
    if not path.exists():
        return []
    results = []
    for candidate in sorted(path.iterdir()):
        if candidate.name.startswith(".") or not candidate.is_dir():
            continue
        name = candidate.name
        if re.fullmatch(r"\d+\.\d+\.\d+", name):
            continue
        results.append(
            build_capability(
                host="codex",
                source_type="plugin",
                source_path=candidate,
                raw_name=name,
                raw_description=f"Discovered plugin directory in {candidate.parent.name}.",
            )
        )
    return results


def scan_mcp_configs(search_roots: list[Path]) -> Iterable[dict[str, object]]:
    results = []
    seen: set[str] = set()
    for root in search_roots:
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if candidate.suffix not in {".json", ".toml"} or not candidate.is_file():
                continue
            if candidate.stat().st_size > 512_000:
                continue
            data = load_config(candidate)
            if not isinstance(data, dict):
                continue
            mcp_servers = data.get("mcpServers") or data.get("mcp_servers")
            if not isinstance(mcp_servers, dict):
                continue
            for name, payload in mcp_servers.items():
                key = f"{candidate}:{name}"
                if key in seen:
                    continue
                seen.add(key)
                description = f"Discovered MCP server '{name}' in {candidate.name}."
                if isinstance(payload, dict):
                    command = payload.get("command")
                    if command:
                        description = f"{description} Command: {command}."
                results.append(
                    build_capability(
                        host="local-config",
                        source_type="mcp",
                        source_path=candidate,
                        raw_name=str(name),
                        raw_description=description,
                    )
                )
    return results


def load_config(path: Path) -> dict[str, object] | None:
    try:
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if path.suffix == ".toml":
            with path.open("rb") as handle:
                return tomllib.load(handle)
    except Exception:
        return None
    return None


def scan_single_files(project_root: Path) -> Iterable[dict[str, object]]:
    results = []
    for relative in [".windsurfrules", "AGENTS.md", "SOUL.md"]:
        candidate = project_root / relative
        if not candidate.exists():
            continue
        text = safe_read(candidate)
        raw_name, raw_description = summarize_text(text)
        name = raw_name or candidate.stem
        results.append(
            build_capability(
                host="project",
                source_type="agent",
                source_path=candidate,
                raw_name=name,
                raw_description=raw_description,
            )
        )
    return results


def unique_capabilities(items: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        key = f"{item['host']}::{item['sourceType']}::{item['sourcePath']}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return sorted(deduped, key=lambda entry: (str(entry["cat"]), str(entry["displayName"]).lower()))


def common_roots(home: Path, project_root: Path) -> tuple[list[ScanRoot], list[Path], list[Path]]:
    skill_roots = [
        ScanRoot("codex", "skill", home / ".codex" / "skills", "SKILL.md"),
        ScanRoot("agents", "skill", home / ".agents" / "skills", "SKILL.md"),
        ScanRoot("hermes", "skill", home / ".hermes" / "skills", "SKILL.md"),
        ScanRoot("workbuddy", "skill", home / ".workbuddy" / "skills", "SKILL.md"),
        ScanRoot("codewhale", "skill", home / ".codewhale" / "skills", "SKILL.md"),
    ]
    file_roots = [
        ScanRoot("claude-code", "agent", home / ".claude" / "agents"),
        ScanRoot("github-copilot", "agent", home / ".github" / "agents"),
        ScanRoot("github-copilot", "agent", home / ".copilot" / "agents"),
        ScanRoot("cursor", "rule", home / ".cursor" / "rules"),
        ScanRoot("trae", "rule", home / ".trae" / "rules"),
        ScanRoot("qoder", "agent", home / ".qoder" / "agents"),
        ScanRoot("qwen", "agent", home / ".qwen" / "agents"),
        ScanRoot("opencode", "agent", project_root / ".opencode" / "agents"),
        ScanRoot("codex", "agent", project_root / ".codex" / "agents"),
        ScanRoot("cursor", "rule", project_root / ".cursor" / "rules"),
        ScanRoot("trae", "rule", project_root / ".trae" / "rules"),
        ScanRoot("qoder", "agent", project_root / ".qoder" / "agents"),
    ]
    plugin_roots = [
        home / ".codex" / "plugins",
        home / ".codex" / "plugins" / "cache",
        home / ".gemini" / "extensions",
    ]
    return skill_roots, file_roots, plugin_roots


def main() -> int:
    args = parse_args()
    home = args.home.expanduser().resolve()
    project_root = args.project.resolve()
    output = args.output.resolve()

    skill_roots, file_roots, plugin_roots = common_roots(home, project_root)

    capabilities: list[dict[str, object]] = []
    for root in skill_roots:
        capabilities.extend(scan_skill_root(root))
    for root in file_roots:
        pattern = "*.mdc" if root.source_type == "rule" else "*.md"
        if root.path.name == "agents" and root.host == "codex":
            pattern = "*.toml"
        capabilities.extend(scan_agent_files(root, pattern))
    for root in plugin_roots:
        capabilities.extend(scan_plugin_roots(root))
    capabilities.extend(scan_mcp_configs([home / ".codex", project_root]))
    capabilities.extend(scan_single_files(project_root))

    deduped = unique_capabilities(capabilities)
    summary = Counter(item["sourceType"] for item in deduped)
    hosts = Counter(item["host"] for item in deduped)

    payload = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "scannerVersion": VERSION,
            "home": str(home),
            "projectRoot": str(project_root),
            "capabilityCount": len(deduped),
            "sourceTypeSummary": dict(summary),
            "hostSummary": dict(hosts),
            "rootsScanned": sorted({str(root.path) for root in skill_roots + file_roots if root.path.exists()} | {str(path) for path in plugin_roots if path.exists()}),
        },
        "capabilities": deduped,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2 if args.pretty else 2)
        handle.write("\n")

    print(json.dumps({"output": str(output), "count": len(deduped), "sourceTypeSummary": dict(summary), "hostSummary": dict(hosts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
