#!/usr/bin/env bash
# Create or repair the virtual environment, install missing dependencies,
# and start the Flask app.

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PLATFORM_ID="$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv-$PLATFORM_ID}"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  BOOTSTRAP_PYTHON="$PYTHON_BIN"
elif command -v python3 >/dev/null 2>&1; then
  BOOTSTRAP_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  BOOTSTRAP_PYTHON="python"
else
  echo "Python 3 is required. Install Python 3, then run ./start.sh again." >&2
  exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]] \
  || [[ ! -x "$VENV_PYTHON" ]] \
  || [[ ! -f "$VENV_DIR/pyvenv.cfg" ]] \
  || ! "$VENV_PYTHON" -c "import sys; raise SystemExit(sys.prefix == sys.base_prefix)" >/dev/null 2>&1; then
  echo "Creating or repairing virtual environment at $VENV_DIR..."
  if ! "$BOOTSTRAP_PYTHON" -m venv --clear "$VENV_DIR"; then
    echo "Could not create the virtual environment. Install your system's Python venv package, then try again." >&2
    exit 1
  fi
fi

if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "pip is unavailable in $VENV_DIR. Recreate the virtual environment and try again." >&2
  exit 1
fi

missing_modules="$(
  "$VENV_PYTHON" - <<'PY'
import importlib.util

modules = ("flask", "werkzeug", "Adyen", "dotenv", "requests", "gunicorn")
print(" ".join(module for module in modules if importlib.util.find_spec(module) is None))
PY
)"

if [[ "${FORCE_INSTALL:-0}" == "1" || -n "$missing_modules" ]]; then
  echo "Installing application dependencies..."
  PIP_DISABLE_PIP_VERSION_CHECK=1 "$VENV_PYTHON" -m pip install -r requirements.txt
fi

exec "$VENV_PYTHON" run.py
