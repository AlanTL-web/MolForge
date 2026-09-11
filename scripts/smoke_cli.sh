#!/usr/bin/env bash
# Public CLI smoke test. Pass an empty results root or let mktemp create one.
set -euo pipefail
export MOLFORGE_RUNS_DIR="${1:-$(mktemp -d -t molforge-smoke-XXXXXXXX)}"
export MOLFORGE_LANG=en
molforge --version
molforge conf --help --lang en
molforge conf --help --lang zh
molforge conf --smiles CCO -n 2 -t 1 --job-name ethanol
molforge ls --stage conf --status completed
molforge st latest --json
molforge f latest --pattern '*.sdf'
molforge p latest --artifact ranking
molforge sel --sdf "$(molforge p latest --artifact sdf)" --record 1 --job-name selected
cd "$(molforge p latest)"
test -s outputs/selected_ligand.sdf
molforge st latest
printf 'Smoke results: %s\n' "$MOLFORGE_RUNS_DIR"
