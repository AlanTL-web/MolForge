#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON:-python3}"
"$python_bin" -m pip install "$project_dir${MOLFORGE_EXTRAS:-}"
"$python_bin" -m molforge_linux --version
