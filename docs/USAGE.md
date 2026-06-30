# Usage Guide

CD-Center is a static capability routing workbench. It helps an operator select the right capability before starting work, then copy a focused prompt into the execution environment.

It does not execute tools directly, store credentials, or connect to private systems by itself.

## Run Locally

From the repository root:

```bash
python3 -m http.server 8080
```

Open:

```text
http://localhost:8080
```

Do not rely on opening `index.html` directly in a browser, because some browsers block local JSON loading from `file://` pages.

## Operator Workflow

1. Open the CD-Center page.
2. Use the left sidebar to choose a scenario.
3. Search by task, capability name, tag, or description.
4. Select the most relevant capability card.
5. Read the description and tags.
6. Copy the recommended prompt from the right panel.
7. Paste the prompt into the AI or automation environment that will perform the work.
8. Run the task-specific validation before committing or publishing.

## Capability Scope

The default registry uses three execution scopes:

- `local`: local scripts, local repo checks, local tools, or desktop workflows.
- `remote`: APIs, web services, hosted tools, or internet research.
- `shared`: capabilities that can apply in both local and remote contexts.

The `全部能力` filter shows every capability. The other scope filters only change the view; they do not execute anything.

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

Every match must be reviewed. Documentation can mention security concepts, but the repository must not contain real credentials, account identifiers, private machine paths, internal deployment URLs, logs, or private tool inventories.

## Release Checklist

- JSON validation passes.
- The product page loads through a local HTTP server.
- The screenshot in `assets/product-page.png` matches the current UI.
- Registry examples are generic.
- No private context remains in committed files.
- Repository visibility is private.
- Git working tree is clean after commit.
- Remote `main` points to the expected commit.
