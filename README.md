# CD-Center 本地 skill、插件等能力可视化调度中心

> 扫描本机已有能力，先路由，再执行。  
> Scan local capabilities first, route work second, execute last.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Local Scan](https://img.shields.io/badge/local-capability%20scan-blue.svg)](#快速开始--quick-start)
[![Prompt + CLI + UI](https://img.shields.io/badge/usage-prompt%20cli%20ui-green.svg)](#使用方式--how-to-use)

CD-Center 是一个本地优先的能力发现与调度工具。它会扫描用户电脑上已经安装的 skill、plugin、MCP、agent 和规则文件，生成本地能力清单，再用一个本地页面把这些能力组织起来，帮助用户和 AI 工具先做能力路由，再进入执行。

CD-Center is a local-first capability discovery and dispatch tool. It scans installed skills, plugins, MCP servers, agents, and rule files on a user's machine, generates a local registry, and presents that registry in a local page so users and AI tools can route work before execution.

## 产品截图 · Product Preview

![CD-Center product page](assets/product-page.png)

## 这是什么 · What It Is

- 扫描本机常见能力根目录：`.codex`、`.agents`、`.hermes`、`.claude`、`.cursor`、项目级 agent/rule 目录，以及 MCP 配置文件。
- 生成 `capability-registry.local.json`，供本地页面优先加载。
- 提供三种使用入口：提示词、命令行、可视化页面。
- 对每个能力给出摘要、宿主信息、提示词和路由建议。

- Scan common local capability roots such as `.codex`, `.agents`, `.hermes`, `.claude`, `.cursor`, project-local agent/rule folders, and MCP config files.
- Generate `capability-registry.local.json` and prefer it at runtime.
- Offer three entry points: prompts, CLI, and a local visual page.
- Show a summary, host information, prompt, and routing guidance for each capability.

## 使用方式 · How To Use

### 1. 提示词方式 · Prompt mode

看 [docs/PROMPTS.md](docs/PROMPTS.md)。  
Use the prompt templates in [docs/PROMPTS.md](docs/PROMPTS.md).

### 2. 一键安装方式 · One-command setup

```bash
git clone https://github.com/mahlongit/capability-dispatch-center
cd capability-dispatch-center
bash scripts/install.sh all
cd-center doctor
cd-center open
```

### 3. 手动命令方式 · Manual CLI mode

```bash
python3 scripts/scan_capabilities.py
python3 scripts/serve.py --open
```

### 4. 本地页面方式 · Local page mode

先扫描，再打开本地页面，在页面里筛选、搜索、排序、复制提示词。  
Scan first, then open the local page to filter, search, sort, and copy routing prompts.

## 快速开始 · Quick Start

### 主流工具一键接入 · One-step integration stubs

```bash
bash scripts/install.sh codex
bash scripts/install.sh claude-code
bash scripts/install.sh copilot
bash scripts/install.sh cursor
bash scripts/install.sh trae
bash scripts/install.sh qoder
bash scripts/install.sh hermes
bash scripts/install.sh openclaw
```

`scripts/install.sh all` 会安装本地 launcher，并为主流工具写入最小接入文件。  
`scripts/install.sh all` installs the local launcher and writes minimal integration files for common tools.

### 常用命令 · Common commands

```bash
cd-center scan
cd-center open
cd-center doctor
cd-center prompt
```

或者：

```bash
python3 scripts/scan_capabilities.py
python3 scripts/serve.py --open
bash scripts/doctor.sh
```

## 当前支持 · Current Coverage

| Tool | Mode | Notes |
|---|---|---|
| Codex / CDX | stub + page | local scan, prompt routing, project agent stub |
| Claude Code | stub + page | local scan, prompt routing, agent stub |
| GitHub Copilot | stub + page | local scan, prompt routing, agent stub |
| Cursor | stub + page | local scan, prompt routing, rule stub |
| Trae | stub + page | local scan, prompt routing, rule stub |
| Qoder | stub + page | local scan, prompt routing, agent stub |
| Hermes | stub + page | local scan, prompt routing, skill stub |
| OpenClaw | stub + page | local scan, prompt routing, skill stub |

更详细的说明在 [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) 和 [integrations/](integrations/README.md)。  
More detail lives in [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) and [integrations/](integrations/README.md).

## 项目结构 · Project Structure

```text
.
├── SKILL.md
├── README.md
├── CATALOG.md
├── LICENSE
├── package.json
├── capability-registry.public.json
├── scripts/
├── templates/
├── docs/
├── integrations/
├── assets/
└── index.html
```

## 数据源 · Data Sources

- `capability-registry.local.json`
  用户本机扫描结果。运行时优先加载，不应提交到仓库。

- `capability-registry.public.json`
  仓库附带的纯净示例库。没有本机扫描结果时回退到这里。

- `capability-registry.local.json`
  Local scan result. This is the preferred runtime source and should not be committed.

- `capability-registry.public.json`
  Clean example registry shipped with the repository. Used as a fallback when no local scan result exists.

## 安全边界 · Security Boundary

- 仓库只附带纯净示例库和公开文档。
- 用户本机扫描结果默认只留在本地。
- 页面不会自动把本机能力库上传出去。
- 这个项目是“发现与路由层”，不是自动执行器、密钥库或云端控制台。

- The repository ships only clean example data and public-safe docs.
- Local scan results stay local by default.
- The page does not silently upload local inventory.
- The project is a discovery and routing layer, not an execution engine, secret store, or cloud control plane.

## 文档 · Docs

- [docs/INSTALL.md](docs/INSTALL.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)
- [docs/PROMPTS.md](docs/PROMPTS.md)
- [docs/MAINTENANCE_WORKFLOW.md](docs/MAINTENANCE_WORKFLOW.md)

## License

MIT License.
