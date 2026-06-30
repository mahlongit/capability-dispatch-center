# Maintenance Workflow

This document defines how to maintain CD-Center without leaking private operational context.

## Principles

- Keep the registry generic unless the repository is intentionally private for a specific team.
- Do not commit credentials, account names, cookies, tokens, private machine paths, internal logs, or private capability inventories.
- Treat `capability-registry.public.json` as data and `index.html` as the static UI.
- Validate before every commit.
- Do not enable public hosting until the registry and documentation have been reviewed for disclosure risk.

## Common Changes

### Add A Capability

1. Confirm that the capability is not already represented.
2. Add one object to `capability-registry.public.json`.
3. Use one of the existing categories unless the UI is also updated.
4. Use `env` as an array containing `local`, `remote`, or `shared`.
5. Write a clear prompt that tells the operator what to do first.

### Edit A Capability

Common fields:

- `displayName`
- `cat`
- `env`
- `score`
- `desc`
- `tags`
- `prompt`

### Remove A Capability

1. Remove the object from `capability-registry.public.json`.
2. Validate JSON.
3. Confirm category counts still render in the UI.

## Validation Commands

From the project root:

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

Run a disclosure scan before every commit:

```bash
grep -RInE "(/Users/|token|cookie|secret|password|\\.env|private key|BEGIN .*KEY)" .
```

Every match must be reviewed. Generic documentation may mention security concepts such as `token` or `cookie`, but the repository must not contain real credentials, private machine paths, account identifiers, private deployment context, or private capability inventories.

For a team-specific fork, add your own forbidden project names, internal tool names, and deployment identifiers to the scan before release. Do not commit that private forbidden-term list to a reusable template repository unless it has also been sanitized.

## Release Acceptance

Before pushing a release or handoff commit:

- JSON validation passes.
- `index.html` still loads `./capability-registry.public.json`.
- Registry entries use generic capability examples only.
- Category counts render correctly in the UI.
- Security review has no unresolved private-context matches.
- Repository visibility is private unless a separate public-release review has been completed.
- The commit message describes the change.
- Rollback is possible through git history.

## Git Workflow

```bash
git status --short
git add index.html capability-registry.public.json .gitignore README.md docs
git commit -m "Update CD-Center"
git push
```

If there are no changes, do not create an empty commit.

If `git push` fails, record the exact error and determine whether the cause is authentication, permissions, missing remote, branch conflict, or network access.

## Disclosure Checklist

Before pushing, search for private context:

```bash
grep -RInE "(/Users/|token|cookie|secret|password|\\.env|private key|BEGIN .*KEY)" .
```

Review any match before committing.
