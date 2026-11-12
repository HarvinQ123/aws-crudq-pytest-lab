#!/usr/bin/env bash
# One-step setup for macOS / Linux:
#   creates .venv, installs pinned dependencies, runs the unit tests.
# Usage (from the repo root):  ./scripts/setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: $PY not found. Install Python 3.10+ (macOS: brew install python)." >&2
  exit 1
fi

if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "ERROR: Python 3.10+ required; found $("$PY" --version)." >&2
  echo "       Point the script at a newer one, e.g.  PYTHON=python3.13 ./scripts/setup.sh" >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "==> Creating virtual environment in .venv ($("$PY" --version))"
  "$PY" -m venv .venv
else
  echo "==> Reusing existing .venv"
fi

echo "==> Installing dependencies"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

echo "==> Running unit tests (mocked AWS, no credentials needed)"
.venv/bin/python -m pytest tests/unit -q

echo
echo "Setup complete. Activate the environment in your shell with:"
echo "    source .venv/bin/activate"
