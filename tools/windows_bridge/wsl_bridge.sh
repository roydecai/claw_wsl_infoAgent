#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <health|shell|ui> [args...]"
  exit 1
fi

CMD="$1"
shift || true

BRIDGE_PORT="${WINDOWS_BRIDGE_PORT:-8765}"
if [[ -n "${WINDOWS_BRIDGE_HOST:-}" ]]; then
  BRIDGE_HOST="$WINDOWS_BRIDGE_HOST"
else
  BRIDGE_HOST="$(awk '/nameserver/ {print $2; exit}' /etc/resolv.conf 2>/dev/null || true)"
  if [[ -z "$BRIDGE_HOST" ]]; then
    BRIDGE_HOST="127.0.0.1"
  fi
fi

BASE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"
TOKEN="${WINDOWS_BRIDGE_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "WINDOWS_BRIDGE_TOKEN is required."
  exit 2
fi

post_json() {
  local body="$1"
  curl -sS -X POST "${BASE_URL}/run" -H 'Content-Type: application/json' -d "$body"
}

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/}
  value=${value//$'\t'/\\t}
  printf '%s' "$value"
}

case "$CMD" in
  health)
    curl -sS "${BASE_URL}/health"
    ;;
  shell)
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 shell \"PowerShell command\""
      exit 1
    fi
    payload_cmd="$(json_escape "$*")"
    post_json "{\"token\":\"${TOKEN}\",\"type\":\"shell\",\"cmd\":\"${payload_cmd}\"}"
    ;;
  ui)
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 ui <open_notepad_and_type|launch_windows_terminal> [text]"
      exit 1
    fi
    action="$1"
    shift || true
    text="$(json_escape "$*")"
    post_json "{\"token\":\"${TOKEN}\",\"type\":\"ui\",\"action\":\"${action}\",\"text\":\"${text}\"}"
    ;;
  *)
    echo "Unsupported command: ${CMD}"
    echo "Usage: $0 <health|shell|ui> [args...]"
    exit 1
    ;;
esac
