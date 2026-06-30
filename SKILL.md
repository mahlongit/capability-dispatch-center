---
name: cd-center
description: Local capability discovery and dispatch center. Use when the user wants to discover installed skills, plugins, MCP servers, or agents on their machine, open a local routing page, or generate a registry before choosing capabilities.
triggers:
  - capability dispatch
  - capability routing
  - scan my skills
  - scan my plugins
  - scan my MCP
  - open local capability page
  - discover local tools
metadata:
  project:
    type: proprietary-skill
---

# CD-Center

CD-Center is a local-first capability discovery skill.

## Invocation Contract

When the user wants capability routing on their own machine:

1. Scan local capability roots first.
2. Generate `capability-registry.local.json`.
3. Open or serve the local page.
4. Route the user's task using discovered capabilities before falling back to generic reasoning.

## Default Workflow

```bash
python3 scripts/scan_capabilities.py
python3 scripts/serve.py --open
```

## Commands

```bash
# Scan local and project-level capability roots
python3 scripts/scan_capabilities.py

# Scan and write to a custom path
python3 scripts/scan_capabilities.py --output /tmp/cd-center-scan.json

# Start the local dispatch page and auto-scan first
python3 scripts/serve.py --open

# Validate local environment
bash scripts/doctor.sh
```

## Supported Discovery Targets

- Codex / CDX skills and plugins
- `.agents` skills
- Claude Code agents
- Cursor and Trae rules
- Gemini extensions
- Hermes / WorkBuddy / CodeWhale skills
- GitHub Copilot agents
- Project-local agent/rule directories
- JSON and TOML files containing MCP server configuration

## Boundary

CD-Center discovers and organizes capabilities. It does not install third-party tools silently, exfiltrate machine state, or publish local inventory.
