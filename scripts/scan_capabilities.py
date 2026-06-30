#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


VERSION = "0.2.0"

HOST_LABELS = {
    "codex": {"zh": "Codex / CDX", "en": "Codex / CDX"},
    "agents": {"zh": "通用 skills", "en": "Generic skills"},
    "hermes": {"zh": "Hermes", "en": "Hermes"},
    "workbuddy": {"zh": "WorkBuddy", "en": "WorkBuddy"},
    "codewhale": {"zh": "CodeWhale", "en": "CodeWhale"},
    "claude-code": {"zh": "Claude Code", "en": "Claude Code"},
    "github-copilot": {"zh": "GitHub Copilot", "en": "GitHub Copilot"},
    "cursor": {"zh": "Cursor", "en": "Cursor"},
    "trae": {"zh": "Trae", "en": "Trae"},
    "qoder": {"zh": "Qoder", "en": "Qoder"},
    "qwen": {"zh": "Qwen Code", "en": "Qwen Code"},
    "opencode": {"zh": "OpenCode", "en": "OpenCode"},
    "local-config": {"zh": "本机配置", "en": "Local config"},
    "project": {"zh": "当前项目", "en": "Current project"},
}


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
    if any(token in value for token in ("ui", "ux", "frontend", "front end", "design", "cursor", "component", "visual", "css", "accessibility", "brand")):
        return "UI / 前端"
    if any(token in value for token in ("deploy", "release", "vercel", "netlify", "render", "wrangler", "ops", "devops", "sre", "platform", "infrastructure")):
        return "部署"
    if any(token in value for token in ("web", "browser", "search", "scrape", "http", "automation", "mcp", "crawler", "api", "integration")):
        return "网页 / 自动化"
    if any(token in value for token in ("video", "audio", "media", "caption", "podcast", "editing", "voice", "animation", "storyboard")):
        return "视频 / 内容"
    if any(token in value for token in ("memory", "knowledge", "docs", "document", "research", "prompt", "writer", "study", "brief")):
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


def english_title(value: str) -> str:
    return slug_to_title(value)


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


def host_label(host: str, lang: str) -> str:
    return HOST_LABELS.get(host, {}).get(lang, host)


def default_description(host: str, source_type: str, raw_name: str) -> tuple[str, str]:
    host_zh = host_label(host, "zh")
    host_en = host_label(host, "en")
    if source_type == "skill":
        return (
            f"从 {host_zh} 发现的本地 skill，可用于任务路由或在对应环境中执行。",
            f"Discovered local skill from {host_en}. Use it for routing or execution in the matching host.",
        )
    if source_type == "agent":
        return (
            f"从 {host_zh} 发现的 agent / prompt 入口，适合在对应工具里直接调用。",
            f"Discovered agent or prompt entry from {host_en}. Best used inside the matching tool.",
        )
    if source_type == "rule":
        return (
            f"从 {host_zh} 发现的规则文件，适合作为该工具内的约束或提示上下文。",
            f"Discovered rule file from {host_en}. Best used as guidance inside the matching tool.",
        )
    if source_type == "plugin":
        return (
            f"从 {host_zh} 发现的插件目录，通常需要在宿主工具中调用，而不是在 CD-Center 中直接执行。",
            f"Discovered plugin directory from {host_en}. Usually used through its host tool, not directly inside CD-Center.",
        )
    if source_type == "mcp":
        return (
            f"从本机配置中发现的 MCP 服务 `{raw_name}`，通常需要通过支持 MCP 的执行器接入。",
            f"Discovered MCP service '{raw_name}' from local config. Usually used through an MCP-capable runtime.",
        )
    return (
        f"从 {host_zh} 发现的能力项。",
        f"Discovered capability from {host_en}.",
    )


def infer_requires_subskills(raw_name: str, description: str) -> bool:
    value = " ".join([raw_name, description]).lower()
    markers = ("suite", "toolkit", "collection", "workflow", "orchestrator", "framework", "stack", "multi-agent", "agency", "platform")
    return any(marker in value for marker in markers)


def build_prompts(display_name: str, description_zh: str, description_en: str, host: str, source_type: str, needs_subskills: bool) -> tuple[str, str]:
    host_zh = host_label(host, "zh")
    host_en = host_label(host, "en")
    external_hosts = {"claude-code", "github-copilot", "cursor", "trae", "qoder", "qwen", "hermes", "workbuddy", "codewhale", "opencode"}
    if host in external_hosts or source_type in {"plugin", "mcp", "rule"}:
        zh = [
            f"先检查 {display_name} 是否应该在 {host_zh} 中使用。",
            f"用途：{description_zh}",
            f"来源：{host_zh} / {source_type}",
            "说明：这类能力通常在对应宿主工具中直接使用；如果当前不在对应工具里，先把它当作外部能力或参考规则，不要假设能在 CD-Center 内直接执行。",
        ]
        en = [
            f"First confirm whether {display_name} should be used inside {host_en}.",
            f"Purpose: {description_en}",
            f"Source: {host_en} / {source_type}",
            "Note: This kind of capability is usually executed in its host tool. If you are not in that tool, treat it as an external capability or reference rule rather than directly runnable inside CD-Center.",
        ]
    else:
        zh = [
            f"先检查并调用 {display_name}。",
            f"用途：{description_zh}",
            f"来源：{host_zh} / {source_type}",
            "要求：先说明为什么选它，再决定是否要组合其他 skill / plugin / MCP / agent。",
        ]
        en = [
            f"Check and use {display_name} first.",
            f"Purpose: {description_en}",
            f"Source: {host_en} / {source_type}",
            "Requirement: explain why it was selected before combining it with other skills, plugins, MCP services, or agents.",
        ]
    if needs_subskills:
        zh.append("附加说明：这更像父级能力或工具箱。执行前先判断是否需要继续细分到子 skill / 子规则 / 子代理。")
        en.append("Extra note: this looks like a parent capability or toolkit. Check whether you should route further into child skills, rules, or sub-agents before execution.")
    return "\n".join(zh), "\n".join(en)


def build_capability(
    *,
    host: str,
    source_type: str,
    source_path: Path,
    raw_name: str,
    raw_description: str | None,
) -> dict[str, object]:
    display_name = slug_to_title(raw_name)
    display_name_en = english_title(raw_name)
    default_zh, default_en = default_description(host, source_type, raw_name)
    description = raw_description or default_en
    description_zh = raw_description if raw_description and re.search(r"[\u4e00-\u9fff]", raw_description) else default_zh
    description_en = raw_description if raw_description and not re.search(r"[\u4e00-\u9fff]", raw_description) else default_en
    category = infer_category(" ".join([raw_name, display_name, description, host, source_type]))
    env = infer_env(host, source_type)
    tags = [host, source_type, source_path.parent.name or source_path.name]
    source_path_str = str(source_path)
    source_display = source_path_str.replace(str(Path.home()), "~")
    needs_subskills = infer_requires_subskills(raw_name, description)
    prompt_zh, prompt_en = build_prompts(display_name, description_zh, description_en, host, source_type, needs_subskills)
    installed_at = datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "name": raw_name,
        "displayName": display_name,
        "displayNameEn": display_name_en,
        "cat": category,
        "env": env,
        "icon": icon_for(display_name),
        "score": score_for(source_type),
        "desc": description_zh,
        "descEn": description_en,
        "tags": tags,
        "prompt": prompt_zh,
        "promptEn": prompt_en,
        "sourceType": source_type,
        "host": host,
        "sourcePath": source_path_str,
        "sourcePathDisplay": source_display,
        "installedAt": installed_at,
        "availableIn": [host],
        "requiresSubskills": needs_subskills,
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
    grouped: dict[str, dict[str, object]] = {}
    for item in items:
        desc_basis = str(item.get("descEn") or item.get("desc") or "")[:160].lower()
        key = "::".join([
            str(item["sourceType"]),
            re.sub(r"[^a-z0-9]+", "-", str(item["name"]).lower()).strip("-"),
            desc_basis,
        ])
        if key not in grouped:
            grouped[key] = item
            grouped[key]["sourcePaths"] = [item["sourcePath"]]
            grouped[key]["sourcePathDisplays"] = [item["sourcePathDisplay"]]
            grouped[key]["availableIn"] = list(dict.fromkeys(item.get("availableIn", [item["host"]])))
            grouped[key]["sourceCount"] = 1
            continue
        merged = grouped[key]
        merged["sourceCount"] = int(merged.get("sourceCount", 1)) + 1
        merged["availableIn"] = list(dict.fromkeys(list(merged.get("availableIn", [])) + [item["host"]]))
        merged["sourcePaths"] = list(dict.fromkeys(list(merged.get("sourcePaths", [])) + [item["sourcePath"]]))
        merged["sourcePathDisplays"] = list(dict.fromkeys(list(merged.get("sourcePathDisplays", [])) + [item["sourcePathDisplay"]]))
        if str(item.get("installedAt", "")) > str(merged.get("installedAt", "")):
            merged["installedAt"] = item["installedAt"]
            merged["sourcePath"] = item["sourcePath"]
            merged["sourcePathDisplay"] = item["sourcePathDisplay"]
        if item["host"] not in str(merged.get("host", "")):
            merged["host"] = "/".join(merged["availableIn"])
        if item.get("requiresSubskills"):
            merged["requiresSubskills"] = True
    deduped = list(grouped.values())
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
