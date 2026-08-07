#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$PROJECT_ROOT/.run"
PID_FILE="$RUN_DIR/dashboard.pid"

stop_saved_process() {
  [[ -f "$PID_FILE" ]] || return 0

  local pid command
  pid="$(<"$PID_FILE")"
  if kill -0 "$pid" 2>/dev/null; then
    command="$(ps -p "$pid" -o args=)"
    if [[ "$command" == *"http.server 5500"* ]]; then
      kill "$pid"
      echo "Stopped dashboard process $pid."
    fi
  fi
  rm -f "$PID_FILE"
}

stop_port_listener() {
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:5500 -sTCP:LISTEN 2>/dev/null || true)"
    for pid in $pids; do kill "$pid" 2>/dev/null || true; done
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp 5500 2>/dev/null || true)"
    for pid in $pids; do kill "$pid" 2>/dev/null || true; done
  elif command -v netstat.exe >/dev/null 2>&1 && command -v taskkill.exe >/dev/null 2>&1; then
    while read -r protocol local_address foreign_address state pid; do
      if [[ "$protocol" == "TCP" && "$local_address" == *":5500" && "$state" == "LISTENING" ]]; then
        taskkill.exe /PID "${pid//$'\r'/}" /T /F >/dev/null 2>&1 || true
      fi
    done < <(netstat.exe -ano)
  fi
}

stop_saved_process
stop_port_listener
echo "Dashboard stopped."
