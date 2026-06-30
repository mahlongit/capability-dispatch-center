#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_BIN_DIR="${CD_CENTER_BIN_DIR:-$HOME/.local/bin}"
PROJECT_DIR="${CD_CENTER_PROJECT_DIR:-$PWD}"
TOOL="${1:-all}"
LAUNCHER_PATH="$HOME_BIN_DIR/cd-center"

mkdir -p "$HOME_BIN_DIR"

install_launcher() {
  cat >"$LAUNCHER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$ROOT_DIR"

case "\${1:-open}" in
  scan)
    shift
    exec python3 "\$ROOT_DIR/scripts/scan_capabilities.py" "\$@"
    ;;
  open|serve|ui)
    shift
    exec python3 "\$ROOT_DIR/scripts/serve.py" --open "\$@"
    ;;
  doctor)
    shift
    exec bash "\$ROOT_DIR/scripts/doctor.sh" "\$@"
    ;;
  prompt)
    shift
    exec sed -n '1,240p' "\$ROOT_DIR/docs/PROMPTS.md"
    ;;
  *)
    echo "Usage: cd-center [scan|open|serve|ui|doctor|prompt]"
    exit 1
    ;;
esac
EOF
  chmod +x "$LAUNCHER_PATH"
  echo "Installed launcher: $LAUNCHER_PATH"
}

write_file() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  cat >"$target"
  echo "Installed: $target"
}

install_codex() {
  write_file "$PROJECT_DIR/.codex/agents/cd-center.toml" <<'EOF'
name = "cd-center"
description = "Scan local skills, plugins, MCP services, and agents before execution. Route first, execute second."
prompt = """
Use CD-Center before task execution.

1. Run or request a scan of local skills, plugins, MCP servers, and agents.
2. Open or reference the local dispatch page.
3. Produce a capability routing table: candidates, selected capability, excluded capability and reason.
4. Only then execute the user task.
"""
EOF
}

install_claude_code() {
  write_file "$HOME/.claude/agents/cd-center.md" <<'EOF'
# CD-Center

Before executing a task, scan the machine for installed skills, plugins, MCP services, and agents. Route the task first, then execute.

Preferred local commands:

```bash
cd-center scan
cd-center open
```
EOF
}

install_copilot() {
  write_file "$HOME/.github/agents/cd-center.md" <<'EOF'
# CD-Center

Use CD-Center to scan local capabilities before execution. Prefer host-native skills and agents when available.
EOF
  write_file "$HOME/.copilot/agents/cd-center.md" <<'EOF'
# CD-Center

Use CD-Center to scan local capabilities before execution. Prefer host-native skills and agents when available.
EOF
}

install_cursor() {
  write_file "$PROJECT_DIR/.cursor/rules/cd-center.mdc" <<'EOF'
---
description: Use CD-Center to scan local skills, plugins, MCP services, and agents before execution. Route first, execute second.
globs: []
alwaysApply: false
---

Before starting work:

1. Scan local capabilities.
2. Review the local dispatch page.
3. Decide the capability route.
4. Execute only after the route is explicit.
EOF
}

install_trae() {
  write_file "$PROJECT_DIR/.trae/rules/cd-center.md" <<'EOF'
---
description: Use CD-Center to scan local skills, plugins, MCP services, and agents before execution. Route first, execute second.
globs: []
alwaysApply: false
---

Before starting work:

1. Scan local capabilities.
2. Review the local dispatch page.
3. Decide the capability route.
4. Execute only after the route is explicit.
EOF
}

install_qoder() {
  write_file "$HOME/.qoder/agents/cd-center.md" <<'EOF'
---
name: cd-center
description: Scan local skills, plugins, MCP services, and agents before execution. Route first, execute second.
---

Use CD-Center to scan the machine before execution. Prefer host-native capabilities where applicable.
EOF
}

install_hermes() {
  write_file "$HOME/.hermes/skills/cd-center/SKILL.md" <<EOF
$(sed -n '1,240p' "$ROOT_DIR/SKILL.md")
EOF
}

install_openclaw() {
  write_file "$HOME/.openclaw/skills/cd-center/SKILL.md" <<EOF
$(sed -n '1,240p' "$ROOT_DIR/SKILL.md")
EOF
}

case "$TOOL" in
  all)
    install_launcher
    install_codex
    install_claude_code
    install_copilot
    install_cursor
    install_trae
    install_qoder
    install_hermes
    install_openclaw
    ;;
  launcher) install_launcher ;;
  codex) install_codex ;;
  claude-code) install_claude_code ;;
  copilot) install_copilot ;;
  cursor) install_cursor ;;
  trae) install_trae ;;
  qoder) install_qoder ;;
  hermes) install_hermes ;;
  openclaw) install_openclaw ;;
  *)
    echo "Usage: bash scripts/install.sh [all|launcher|codex|claude-code|copilot|cursor|trae|qoder|hermes|openclaw]"
    exit 1
    ;;
esac

echo "If '$HOME_BIN_DIR' is not in PATH, add:"
echo "export PATH=\"$HOME_BIN_DIR:\$PATH\""
