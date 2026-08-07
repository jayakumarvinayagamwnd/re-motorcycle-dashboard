#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$PROJECT_ROOT/.run"
PID_FILE="$RUN_DIR/api.pid"
LOG_FILE="$RUN_DIR/api.log"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  :
elif [[ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

port_is_listening() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "$port" >/dev/null 2>&1
  elif command -v netstat.exe >/dev/null 2>&1; then
    netstat.exe -ano | grep -Eq "^ *TCP .*:${port} .*LISTENING"
  else
    return 1
  fi
}

if port_is_listening 8000; then
  echo "API is already listening on port 8000." >&2
  exit 1
fi

mkdir -p "$RUN_DIR"
cd "$PROJECT_ROOT"

nohup "$PYTHON_BIN" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 >"$LOG_FILE" 2>&1 &
api_pid=$!
echo "$api_pid" > "$PID_FILE"

for _ in {1..30}; do
  if port_is_listening 8000; then
    echo "API started: http://localhost:8000"
    exit 0
  fi
  sleep 1
done

echo "API did not start within 30 seconds. Check $LOG_FILE." >&2
rm -f "$PID_FILE"
exit 1
