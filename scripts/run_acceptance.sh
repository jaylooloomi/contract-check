#!/usr/bin/env sh
# Full acceptance run for macOS/Linux (NOT tested; Windows is the tested platform).
# Usage (repo root, venv activated): sh scripts/run_acceptance.sh
cd "$(dirname "$0")/.." || exit 1
PY="${PYTHON:-python}"
export PYTHONIOENCODING=utf-8
mkdir -p acceptance_logs
LOG="acceptance_logs/acceptance_$(date +%Y%m%d_%H%M%S).log"
step() {
  name=$1; shift; t=$(date +%s)
  echo "==== $name :: $PY $*" | tee -a "$LOG"
  "$PY" "$@" 2>&1 | tee -a "$LOG"
  echo "==== $name done $(( $(date +%s) - t ))s" | tee -a "$LOG"
}
step check_env scripts/check_env.py
step unit -m pytest tests -m "not e2e" -q
step e2e -m pytest tests/e2e -m e2e -q
step eval eval/run_eval.py
echo "log: $LOG"
