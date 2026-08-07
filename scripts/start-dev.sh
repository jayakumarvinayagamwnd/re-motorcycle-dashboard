#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$PROJECT_ROOT/scripts/start-dev-api.sh"

echo "Waiting 30 seconds before starting the dashboard..."
sleep 30

"$PROJECT_ROOT/scripts/start-dashboard.sh"
