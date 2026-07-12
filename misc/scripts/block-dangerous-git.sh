#!/usr/bin/env bash
# Read a Claude Code PreToolUse JSON payload and reject destructive Git commands.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "BLOCKED: jq is required to inspect the hook payload safely." >&2
  exit 2
fi

input=$(cat)
command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')
pattern='^git[[:space:]]+(push|reset([[:space:]].*)?[[:space:]]+--hard|clean[[:space:]]+-[[:alnum:]]*f[[:alnum:]]*|branch[[:space:]]+-D|checkout[[:space:]]+\.|restore[[:space:]]+\.)'

if printf '%s\n' "$command" | grep -qE "$pattern"; then
  echo "BLOCKED: dangerous git command requires explicit user authorization." >&2
  exit 2
fi
