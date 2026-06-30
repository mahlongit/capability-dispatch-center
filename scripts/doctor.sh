#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_REGISTRY="$ROOT_DIR/capability-registry.local.json"

check_bin() {
  local bin_name="$1"
  if command -v "$bin_name" >/dev/null 2>&1; then
    printf "OK    %s -> %s\n" "$bin_name" "$(command -v "$bin_name")"
  else
    printf "MISS  %s\n" "$bin_name"
  fi
}

printf "CD-Center doctor\n"
printf "Root: %s\n" "$ROOT_DIR"

check_bin python3
check_bin bash
check_bin open

for candidate in \
  "$HOME/.codex/skills" \
  "$HOME/.agents/skills" \
  "$HOME/.claude/agents" \
  "$HOME/.cursor/rules" \
  "$HOME/.hermes/skills" \
  "$ROOT_DIR/.codex/agents" \
  "$ROOT_DIR/.cursor/rules"
do
  if [ -e "$candidate" ]; then
    printf "FOUND %s\n" "$candidate"
  else
    printf "MISS  %s\n" "$candidate"
  fi
done

if [ -f "$LOCAL_REGISTRY" ]; then
  printf "OK    local registry -> %s\n" "$LOCAL_REGISTRY"
else
  printf "MISS  local registry -> %s\n" "$LOCAL_REGISTRY"
fi
