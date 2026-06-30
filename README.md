# CD-Center

> A clean capability dispatch center for AI-assisted workflows.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Static App](https://img.shields.io/badge/static-html%20%2B%20json-blue.svg)](#local-use)
[![Privacy First](https://img.shields.io/badge/privacy-clean%20template-green.svg)](#boundary)

CD-Center is a clean, standalone capability dispatch interface for AI-assisted work. It helps a person or an AI operator choose the right capability before executing a task.

This repository is intentionally generic. It does not include private machine paths, private tool inventories, account data, tokens, cookies, internal deployment details, or any user-specific capability list.

## Project Scale

| Capability Examples | Categories | Execution Scopes | Runtime |
|:---:|:---:|:---:|:---:|
| **10** | **6** | **3** | **Static HTML + JSON** |

## What It Does

- Shows capabilities from a JSON registry.
- Filters by scenario and execution scope.
- Searches by task, capability name, description, or tag.
- Displays a recommended prompt for the selected capability.
- Copies the prompt for use in another AI or automation environment.

CD-Center does not execute tools directly. It is a planning and routing layer.

## Screenshot-Free Preview

The default interface is a three-column workbench:

- Left: scenario filters.
- Center: searchable capability cards.
- Right: detail panel with a copyable prompt.

## Files

```text
.
├── index.html
├── capability-registry.public.json
├── .gitignore
├── CATALOG.md
├── LICENSE
├── README.md
└── docs
    └── MAINTENANCE_WORKFLOW.md
```

## Registry Format

Each capability is stored as one JSON object:

```json
{
  "name": "web-research",
  "displayName": "网页调研",
  "cat": "网页 / 自动化",
  "env": ["remote"],
  "icon": "WEB",
  "score": "8.7",
  "desc": "用于读取公开网页、文档、社区资料或产品页面，并整理可信证据。",
  "tags": ["网页", "调研", "证据"],
  "prompt": "请先读取公开资料并给出来源，再总结结论、证据和不确定项。"
}
```

Supported categories in the default UI:

- `UI / 前端`
- `代码 / 后端`
- `网页 / 自动化`
- `视频 / 内容`
- `知识 / 记忆`
- `部署`

Supported execution scopes:

- `local`
- `remote`
- `shared`

## Capability Catalog

See [CATALOG.md](CATALOG.md) for the default clean example catalog. Replace the examples with your own sanitized registry when adapting CD-Center for a team.

## Local Use

Use any static file server from the project root:

```bash
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

Opening `index.html` directly may fail in some browsers because the page fetches `./capability-registry.public.json`.

## Validation

Run:

```bash
python3 -m json.tool capability-registry.public.json >/dev/null
grep -n "capability-registry.public.json" index.html
```

Also check that the repository does not contain private paths, credentials, account identifiers, or private capability inventories.

## Maintenance

- Modify UI in `index.html`.
- Modify capability data in `capability-registry.public.json`.
- Modify project guidance in `README.md` or `docs/`.
- Validate locally before committing.
- Keep the repository private unless you have reviewed the registry and documentation for public release.

## Suggested Repository Topics

`ai-tools`, `agent-workflow`, `capability-routing`, `static-site`, `prompt-engineering`, `ai-operations`, `workflow-tools`

## Boundary

CD-Center is a generic capability router template. It is not a deployment system, credential store, agent runtime, browser controller, or secret manager.

## License

MIT License.
