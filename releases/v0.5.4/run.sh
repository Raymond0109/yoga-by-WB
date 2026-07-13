#!/bin/bash
# Launch the Yoga Pose Analyzer (Phase 0 + 1) on http://127.0.0.1:8000
# Uses the managed Python 3.13 venv (MediaPipe has no wheels for 3.14).
set -e
cd "$(dirname "$0")"

PY="${YOGA_PY:-/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python}"
if [ ! -x "$PY" ]; then
  echo "Managed venv not found at $PY" >&2
  echo "Set YOGA_PY to your Python 3.11/3.12/3.13 venv interpreter." >&2
  exit 1
fi

exec "$PY" -m uvicorn app:app --host 127.0.0.1 --port 8000
