# Usage Guide

CD-Center is a local capability discovery skill plus a dispatch page. The intended order is:

1. Scan the machine.
2. Generate the local registry.
3. Open the page.
4. Route the task.
5. Execute the task in the target AI or automation environment.

## Run Locally

From the repository root:

```bash
python3 scripts/scan_capabilities.py
python3 scripts/serve.py --open
```

If you already have a local registry and do not want to rescan:

```bash
python3 scripts/serve.py --no-scan --open
```

The default local page runs on `127.0.0.1` and will pick an open port automatically if `8765` is busy.

## Operator Workflow

1. Run the scanner or use `cd-center open`.
2. Use the left sidebar to choose a scenario.
3. Search by task, capability name, tag, or description.
4. Select the most relevant discovered capability.
5. Read the description and tags.
6. Copy the recommended prompt from the right panel.
7. Paste the prompt into the AI or automation environment that will perform the work.
8. Run task-specific validation before committing or publishing.

## Supported Input Modes

### Prompt Mode

Give the templates in [PROMPTS.md](PROMPTS.md) to an AI tool and have it route through CD-Center first.

### Launcher Mode

After `bash scripts/install.sh`:

```bash
cd-center doctor
cd-center scan
cd-center open
```

### Page Mode

Open the local page after scanning and route manually.

## Capability Scope

The page uses three execution scopes:

- `local`: local scripts, local repo checks, local tools, or desktop workflows.
- `remote`: APIs, web services, hosted tools, or internet research.
- `shared`: capabilities that can apply in both local and remote contexts.

The `全部能力` filter shows every capability. The other scope filters only change the view.

## Local Registry Format

The scanner can emit an object with metadata and capability entries:

```json
{
  "meta": {
    "generatedAt": "2026-07-01T00:00:00+00:00",
    "scannerVersion": "0.2.0",
    "capabilityCount": 42
  },
  "capabilities": []
}
```

The page also accepts a plain array for fallback/example data.

## Edit The Registry

Edit `capability-registry.public.json`.

Each item must include:

```json
{
  "name": "security-review",
  "displayName": "安全审查",
  "cat": "代码 / 后端",
  "env": ["shared"],
  "icon": "SEC",
  "score": "9.2",
  "desc": "用于检查敏感信息泄露、权限边界、依赖风险、输入校验和发布前安全缺口。",
  "tags": ["安全", "敏感信息", "权限"],
  "prompt": "请先做安全审查..."
}
```

Keep `env` and `tags` as arrays.

Generated local inventory should be edited sparingly. The normal workflow is to rerun the scanner.

## Categories

The default UI supports these category labels:

- `UI / 前端`
- `代码 / 后端`
- `网页 / 自动化`
- `视频 / 内容`
- `知识 / 记忆`
- `部署`

If you rename or add categories in the registry, update the `scenes` array in `index.html`.

## Validate Before Commit

Run:

```bash
python3 -m json.tool capability-registry.public.json >/dev/null
grep -n "capability-registry.public.json" index.html
python3 - <<'PY'
import json
from collections import Counter

with open("capability-registry.public.json", encoding="utf-8") as f:
    data = json.load(f)

required = {"name", "displayName", "cat", "env", "icon", "score", "desc", "tags", "prompt"}
print("count:", len(data))
print("categories:", Counter(item.get("cat") for item in data))
print("env:", Counter(scope for item in data for scope in item.get("env", [])))
print("required_fields_ok:", all(required.issubset(item) for item in data))
print("env_arrays_ok:", all(isinstance(item.get("env"), list) for item in data))
print("tags_arrays_ok:", all(isinstance(item.get("tags"), list) for item in data))
PY
```

## Security Review

Before every push, search for disclosure risk:

```bash
grep -RInE "(/Users/|token|cookie|secret|password|\\.env|private key|BEGIN .*KEY)" --exclude-dir=.git .
```

Every match must be reviewed. Documentation can mention security concepts, but the repository must not contain real credentials, account identifiers, private machine paths, internal deployment URLs, logs, or committed local inventory.

## Release Checklist

- Public example JSON validates.
- Local page loads through `scripts/serve.py`.
- The page prefers `capability-registry.local.json` when present.
- The screenshot in `assets/product-page.png` matches the current UI.
- Example registry remains generic.
- `capability-registry.local.json` stays uncommitted.
- No private context remains in committed files.
- Repository visibility is private.
