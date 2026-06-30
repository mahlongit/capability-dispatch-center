#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${CD_CENTER_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER_PATH="$BIN_DIR/cd-center"

mkdir -p "$BIN_DIR"

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
    exec sed -n '1,220p' "\$ROOT_DIR/docs/PROMPTS.md"
    ;;
  *)
    echo "Usage: cd-center [scan|open|serve|ui|doctor|prompt]"
    exit 1
    ;;
esac
EOF

chmod +x "$LAUNCHER_PATH"

echo "Installed launcher: $LAUNCHER_PATH"
echo "If '$BIN_DIR' is not in PATH, add:"
echo "export PATH=\"$BIN_DIR:\$PATH\""
