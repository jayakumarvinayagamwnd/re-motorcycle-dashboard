#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$PROJECT_ROOT/.run"
PID_FILE="$RUN_DIR/api.pid"

stop_saved_process() {
  [[ -f "$PID_FILE" ]] || return 0

  local pid command
  pid="$(<"$PID_FILE")"
  if kill -0 "$pid" 2>/dev/null; then
    command="$(ps -p "$pid" -o args=)"
    if [[ "$command" == *"uvicorn backend.app.main:app"* ]]; then
      kill "$pid"
      echo "Stopped API process $pid."
    fi
  fi
  rm -f "$PID_FILE"
}

stop_port_listener() {
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)"
    for pid in $pids; do kill "$pid" 2>/dev/null || true; done
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp 8000 2>/dev/null || true)"
    for pid in $pids; do kill "$pid" 2>/dev/null || true; done
  elif command -v netstat.exe >/dev/null 2>&1 && command -v taskkill.exe >/dev/null 2>&1; then
    while read -r protocol local_address foreign_address state pid; do
      if [[ "$protocol" == "TCP" && "$local_address" == *":8000" && "$state" == "LISTENING" ]]; then
        taskkill.exe /PID "${pid//$'\r'/}" /T /F >/dev/null 2>&1 || true
      fi
    done < <(netstat.exe -ano)
  fi
}

stop_saved_process
stop_port_listener
echo "API stopped."
