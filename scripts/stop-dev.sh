#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$PROJECT_ROOT/scripts/stop-dashboard.sh"
"$PROJECT_ROOT/scripts/stop-dev-api.sh"
rmdir "$PROJECT_ROOT/.run" 2>/dev/null || true
