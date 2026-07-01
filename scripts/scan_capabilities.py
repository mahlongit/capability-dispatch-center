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


VERSION = "0.2.3"

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
    "local-cli": {"zh": "本地命令", "en": "Local CLI"},
    "template-library": {"zh": "模板库", "en": "Template Library"},
    "reference": {"zh": "知识参考", "en": "Reference"},
}

CATEGORY_OVERRIDES = {
    "gsap-skills": "UI / 前端",
    "huashu-nuwa": "网页 / 自动化",
    "nuwaskill": "网页 / 自动化",
    "easy-vibe": "知识 / 记忆",
    "design-md": "UI / 前端",
    "design-md-templates": "UI / 前端",
}

DAS_CATEGORY_MAP = {
    "motion-animation": "UI / 前端",
    "design": "UI / 前端",
    "frontend": "UI / 前端",
    "ui": "UI / 前端",
    "knowledge": "知识 / 记忆",
    "docs": "知识 / 记忆",
    "tutorial": "知识 / 记忆",
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


def clean_scalar(value: str) -> object:
    stripped = value.strip().strip('"').strip("'")
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    if stripped.startswith("[") and stripped.endswith("]"):
        return [
            item.strip().strip('"').strip("'")
            for item in stripped[1:-1].split(",")
            if item.strip()
        ]
    return stripped


def parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---\n"):
        return {}
    _, _, remainder = text.partition("\n")
    frontmatter, marker, _ = remainder.partition("\n---")
    if not marker:
        return {}

    data: dict[str, object] = {}
    lines = frontmatter.splitlines()
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            index += 1
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent != 0 or ":" not in line:
            index += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if value in {"|", ">"}:
            block: list[str] = []
            index += 1
            while index < len(lines):
                next_raw = lines[index]
                next_indent = len(next_raw) - len(next_raw.lstrip(" "))
                if next_raw.strip() and next_indent == 0 and ":" in next_raw:
                    break
                block.append(next_raw[2:] if next_indent >= 2 else next_raw.strip())
                index += 1
            data[key] = "\n".join(block).strip()
            continue

        if value == "":
            nested: dict[str, object] = {}
            values: list[object] = []
            index += 1
            while index < len(lines):
                next_raw = lines[index]
                next_indent = len(next_raw) - len(next_raw.lstrip(" "))
                next_line = next_raw.strip()
                if next_line and next_indent == 0 and ":" in next_line:
                    break
                if not next_line:
                    index += 1
                    continue
                if next_line.startswith("- "):
                    values.append(clean_scalar(next_line[2:]))
                elif ":" in next_line:
                    nested_key, _, nested_value = next_line.partition(":")
                    nested[nested_key.strip()] = clean_scalar(nested_value)
                index += 1
            if values:
                data[key] = values
            for nested_key, nested_value in nested.items():
                data[f"{key}.{nested_key}"] = nested_value
            continue

        data[key] = clean_scalar(value)
        index += 1
    return data


def metadata_text(metadata: dict[str, object]) -> str:
    values: list[str] = []
    for value in metadata.values():
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return " ".join(values)


def infer_category(text: str, *, raw_name: str = "", source_type: str = "", metadata: dict[str, object] | None = None) -> str:
    value = text.lower()
    name = raw_name.lower()
    metadata = metadata or {}
    normalized_name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    if normalized_name in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[normalized_name]
    das_category = str(metadata.get("das.category", "")).lower()
    if das_category in DAS_CATEGORY_MAP:
        return DAS_CATEGORY_MAP[das_category]
    ui_terms = (
        "ui", "ux", "frontend", "front-end", "front end", "interface", "component",
        "visual", "css", "accessibility", "brand", "figma", "design-system",
        "wireframe", "layout", "motion", "typography", "gsap", "greensock",
        "scrolltrigger", "usegsap", "timeline", "animation",
    )
    ui_name_terms = (
        "ui", "ux", "frontend", "front-end", "interface", "visual", "design",
        "figma", "wireframe", "layout", "component", "motion", "brand",
        "gsap", "greensock", "scrolltrigger",
    )
    deploy_terms = (
        "cloudflare", "deploy", "deployment", "release", "vercel", "netlify",
        "render", "wrangler", "ops", "devops", "sre", "platform", "infrastructure",
        "gateway", "zero trust", "network", "tunnel", "pages",
    )
    deploy_name_terms = (
        "cloudflare", "deploy", "deployment", "release", "wrangler", "vercel",
        "netlify", "devops", "sre", "infrastructure", "tunnel",
    )
    if source_type == "template-library":
        return "UI / 前端"
    if source_type == "cli" and "design-md" in name:
        return "UI / 前端"
    if any(token in value for token in ("教程", "文档", "知识参考", "knowledge", "docs", "documentation", "tutorial", "reference", "easy-vibe", "datawhale")):
        return "知识 / 记忆"
    if any(token in value for token in ("女娲", "造skill", "蒸馏", "人物skill", "deep research", "skill generation", "agent reach")):
        return "网页 / 自动化"
    if "design" in name:
        return "UI / 前端"
    if any(re.search(rf"(^|[-_\s/]){re.escape(token)}($|[-_\s/])", name) for token in ui_name_terms):
        return "UI / 前端"
    if any(re.search(rf"(^|[-_\s/]){re.escape(token)}($|[-_\s/])", name) for token in deploy_name_terms):
        return "部署"
    if any(token in value for token in deploy_terms):
        return "部署"
    if any(token in value for token in ui_terms):
        return "UI / 前端"
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
    if source_type in {"cli", "template-library"}:
        return ["local"]
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
        "cli": "8.8",
        "template-library": "8.7",
        "reference": "8.2",
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


def summarize_text(text: str) -> tuple[str | None, str | None]:
    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    heading_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    paragraph_match = re.search(r"\n\n([^\n#][^\n]+)", text)
    return (
        str(name) if name else (heading_match.group(1).strip() if heading_match else None),
        str(description) if description else (paragraph_match.group(1).strip() if paragraph_match else None),
    )


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
    if source_type == "cli":
        return (
            f"从本地命令中发现的能力 `{raw_name}`，通常需要在终端里直接使用。",
            f"Discovered local CLI capability '{raw_name}'. Usually used directly from the terminal.",
        )
    if source_type == "template-library":
        return (
            f"从本地模板库发现的能力 `{raw_name}`，适合在 UI/设计任务里作为风格或结构参考。",
            f"Discovered template-library capability '{raw_name}'. Best used as a UI or design reference.",
        )
    if source_type == "reference":
        return (
            f"从安装/使用记录中发现的知识参考 `{raw_name}`，不部署，只作为资料或上下文来源。",
            f"Discovered reference source '{raw_name}' from install or usage records. Use it as knowledge context, not as a deployable tool.",
        )
    return (
        f"从 {host_zh} 发现的能力项。",
        f"Discovered capability from {host_en}.",
    )


def infer_requires_subskills(raw_name: str, description: str) -> bool:
    value = " ".join([raw_name, description]).lower()
    markers = ("suite", "toolkit", "collection", "workflow", "orchestrator", "framework", "stack", "multi-agent", "agency", "platform", "templates", "library")
    return any(marker in value for marker in markers)


def first_string(value: object) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value) if value is not None else ""


def infer_repo_url(metadata: dict[str, object], text: str) -> str | None:
    for key in ("das.upstream", "upstream", "repo", "repository", "homepage", "url"):
        value = first_string(metadata.get(key)).strip()
        if value.startswith("https://github.com/"):
            return value.rstrip(".,)")
    match = re.search(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text)
    return match.group(0).rstrip(".,)") if match else None


def infer_install_kind(host: str, source_type: str, source_path: Path, metadata: dict[str, object]) -> tuple[str, str]:
    path = str(source_path)
    if source_type == "reference":
        return "reference", "知识参考"
    if source_type == "template-library":
        return "template-library", "模板库"
    if source_type == "cli":
        return "local-tool", "本地命令"
    if source_type in {"plugin", "mcp", "extension"}:
        return source_type, {"plugin": "插件", "mcp": "MCP", "extension": "扩展"}.get(source_type, source_type)
    if "/.codex/skills/.system/" in path or "/plugins/cache/openai-" in path:
        return "native", "原生自带"
    if host in {"codex", "agents", "hermes", "workbuddy", "codewhale"} and source_type == "skill":
        return "user-installed", "后装能力"
    if metadata.get("das.upstream") or metadata.get("das.category"):
        return "user-installed", "后装能力"
    return "local", "本机发现"


def infer_scene_tags(
    *,
    raw_name: str,
    category: str,
    host: str,
    source_type: str,
    metadata: dict[str, object],
    description: str,
    repo_url: str | None,
    install_label: str,
) -> list[str]:
    text = " ".join([raw_name, description, metadata_text(metadata), repo_url or ""]).lower()
    tags = [category, install_label, host, source_type]
    das_category = first_string(metadata.get("das.category"))
    if das_category:
        tags.append(das_category)
    if "gsap" in text or "greensock" in text:
        tags.extend(["GSAP", "GreenSock", "动效", "前端动画"])
    if "scrolltrigger" in text:
        tags.append("ScrollTrigger")
    if "女娲" in text or "huashu" in text or "nuwa" in text:
        tags.extend(["女娲", "能力生成", "深度调研", "内容生产"])
    if "easy-vibe" in text or "datawhale" in text:
        tags.extend(["教程", "文档", "知识参考", "Datawhale"])
    if "design-md" in text:
        tags.extend(["design-md", "设计模板"])
    if "mcp" in text:
        tags.append("MCP")
    if "agent" in text:
        tags.append("agent")
    return list(dict.fromkeys(str(tag) for tag in tags if tag))


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
    source_text = safe_read(source_path)
    metadata = parse_frontmatter(source_text)
    display_name = slug_to_title(raw_name)
    display_name_en = english_title(raw_name)
    default_zh, default_en = default_description(host, source_type, raw_name)
    description = raw_description or default_en
    description_zh = raw_description if raw_description and re.search(r"[\u4e00-\u9fff]", raw_description) else default_zh
    description_en = raw_description if raw_description and not re.search(r"[\u4e00-\u9fff]", raw_description) else default_en
    category = infer_category(
        " ".join([raw_name, display_name, description, source_type, metadata_text(metadata)]),
        raw_name=raw_name,
        source_type=source_type,
        metadata=metadata,
    )
    env = infer_env(host, source_type)
    repo_url = infer_repo_url(metadata, source_text)
    install_kind, install_label = infer_install_kind(host, source_type, source_path, metadata)
    scene_tags = infer_scene_tags(
        raw_name=raw_name,
        category=category,
        host=host,
        source_type=source_type,
        metadata=metadata,
        description=description,
        repo_url=repo_url,
        install_label=install_label,
    )
    tags = list(dict.fromkeys([host, source_type, source_path.parent.name or source_path.name, *scene_tags[:8]]))
    source_path_str = str(source_path)
    source_display = source_path_str.replace(str(Path.home()), "~")
    needs_subskills = infer_requires_subskills(raw_name, description)
    prompt_zh, prompt_en = build_prompts(display_name, description_zh, description_en, host, source_type, needs_subskills)
    installed_at = datetime.fromtimestamp(source_path.stat().st_mtime, tz=timezone.utc).isoformat()
    available_in = [host]
    if host == "agents" and source_type == "skill":
        available_in = ["codex", "hermes", "agents"]
    elif source_type == "cli":
        available_in = ["codex", "hermes", "local-cli"]
    elif source_type == "template-library":
        available_in = ["codex", "hermes", "template-library"]

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
        "availableIn": available_in,
        "requiresSubskills": needs_subskills,
        "installKind": install_kind,
        "installKindLabel": install_label,
        "sceneTags": scene_tags,
        "repoUrl": repo_url,
        "metadataCategory": first_string(metadata.get("das.category")),
    }


def scan_skill_root(root: ScanRoot) -> Iterable[dict[str, object]]:
    if not root.path.exists():
        return []
    results = []
    markers = list(root.path.rglob(root.pattern or "SKILL.md"))
    for marker in markers:
        relative_parts = marker.relative_to(root.path).parts
        if len(relative_parts) > 4:
            continue
        parent_has_skill = False
        ancestor = marker.parent.parent
        while root.path in (ancestor, *ancestor.parents):
            if ancestor == root.path:
                break
            if (ancestor / "SKILL.md").exists():
                parent_has_skill = True
                break
            ancestor = ancestor.parent
        if parent_has_skill:
            continue
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


def scan_cli_tools(home: Path) -> Iterable[dict[str, object]]:
    cli_dir = home / ".local" / "bin"
    candidates = ["design-md"]
    results = []
    if not cli_dir.exists():
        return results
    for name in candidates:
        path = cli_dir / name
        if not path.exists():
            continue
        results.append(
            build_capability(
                host="local-cli",
                source_type="cli",
                source_path=path,
                raw_name=name,
                raw_description=f"本地命令 `{name}`，适合列出、定位或安装 UI 模板与设计规范。",
            )
        )
    return results


def scan_template_library(home: Path) -> Iterable[dict[str, object]]:
    library_root = home / ".local" / "share" / "awesome-design-md" / "design-md"
    if not library_root.exists():
        return []
    templates = [candidate for candidate in sorted(library_root.iterdir()) if candidate.is_dir() and not candidate.name.startswith(".")]
    capability = build_capability(
        host="template-library",
        source_type="template-library",
        source_path=library_root,
        raw_name="design-md templates",
        raw_description=f"本地 design-md 模板库，共 {len(templates)} 套模板。可用 `design-md list`、`design-md path <name>` 和 `design-md install <name> <project>` 查看或安装模板。",
    )
    capability["templateItems"] = [
        {
            "name": candidate.name,
            "displayName": slug_to_title(candidate.name),
            "sourcePathDisplay": str(candidate).replace(str(Path.home()), "~"),
        }
        for candidate in templates
    ]
    results = [capability]
    return results


def reference_capability(
    *,
    name: str,
    display_name: str,
    description_zh: str,
    description_en: str,
    category: str,
    repo_url: str,
    installed_at: str,
    evidence: str,
) -> dict[str, object]:
    prompt_zh, prompt_en = build_prompts(display_name, description_zh, description_en, "reference", "reference", False)
    scene_tags = infer_scene_tags(
        raw_name=name,
        category=category,
        host="reference",
        source_type="reference",
        metadata={"das.upstream": repo_url, "das.category": "knowledge"},
        description=description_zh,
        repo_url=repo_url,
        install_label="知识参考",
    )
    return {
        "name": name,
        "displayName": display_name,
        "displayNameEn": display_name,
        "cat": category,
        "env": ["shared"],
        "icon": icon_for(display_name),
        "score": score_for("reference"),
        "desc": description_zh,
        "descEn": description_en,
        "tags": list(dict.fromkeys(["reference", "knowledge", *scene_tags[:8]])),
        "prompt": prompt_zh,
        "promptEn": prompt_en,
        "sourceType": "reference",
        "host": "reference",
        "sourcePath": evidence,
        "sourcePathDisplay": evidence,
        "installedAt": installed_at,
        "availableIn": ["codex", "hermes", "reference"],
        "requiresSubskills": False,
        "installKind": "reference",
        "installKindLabel": "知识参考",
        "sceneTags": scene_tags,
        "repoUrl": repo_url,
        "metadataCategory": "knowledge",
        "installEvidence": evidence,
    }


def scan_reference_records(home: Path) -> Iterable[dict[str, object]]:
    del home
    return [
        reference_capability(
            name="easy-vibe",
            display_name="Easy Vibe",
            description_zh="DatawhaleChina easy-vibe 教程/文档仓库；不部署，只作为知识参考源，可供 Codex 和 Hermes 在任务中引用。",
            description_en="DatawhaleChina easy-vibe tutorial and documentation repository. Use it as a knowledge reference for Codex and Hermes, not as a deployable tool.",
            category="知识 / 记忆",
            repo_url="https://github.com/datawhalechina/easy-vibe",
            installed_at="2026-06-30T00:00:00+08:00",
            evidence="thread:安装并使用能力路由; user-reported 2026-06-30 install/reference",
        )
    ]


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
        key = "::".join([
            str(item["sourceType"]),
            re.sub(r"[^a-z0-9]+", "-", str(item["name"]).lower()).strip("-"),
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
        merged["availableIn"] = list(dict.fromkeys(list(merged.get("availableIn", [])) + list(item.get("availableIn", [item["host"]]))))
        merged["sourcePaths"] = list(dict.fromkeys(list(merged.get("sourcePaths", [])) + [item["sourcePath"]]))
        merged["sourcePathDisplays"] = list(dict.fromkeys(list(merged.get("sourcePathDisplays", [])) + [item["sourcePathDisplay"]]))
        merged["tags"] = list(dict.fromkeys(list(merged.get("tags", [])) + list(item.get("tags", []))))
        merged["sceneTags"] = list(dict.fromkeys(list(merged.get("sceneTags", [])) + list(item.get("sceneTags", []))))
        if str(item.get("installedAt", "")) > str(merged.get("installedAt", "")):
            merged["installedAt"] = item["installedAt"]
            merged["sourcePath"] = item["sourcePath"]
            merged["sourcePathDisplay"] = item["sourcePathDisplay"]
            merged["installKind"] = item.get("installKind", merged.get("installKind"))
            merged["installKindLabel"] = item.get("installKindLabel", merged.get("installKindLabel"))
            merged["installEvidence"] = item.get("installEvidence", merged.get("installEvidence"))
        if item.get("repoUrl") and not merged.get("repoUrl"):
            merged["repoUrl"] = item["repoUrl"]
        if item.get("metadataCategory") and not merged.get("metadataCategory"):
            merged["metadataCategory"] = item["metadataCategory"]
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
    capabilities.extend(scan_cli_tools(home))
    capabilities.extend(scan_template_library(home))
    capabilities.extend(scan_reference_records(home))

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
