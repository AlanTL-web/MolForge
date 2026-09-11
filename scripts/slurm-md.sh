#!/usr/bin/env bash
#SBATCH --job-name=molforge-md
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --output=molforge-%j.log
set -euo pipefail
# Activate the MD environment and set PATH before sbatch (or add site module commands here).
if [[ $# -ne 3 ]]; then
    echo "Usage: sbatch scripts/slurm-md.sh receptor.pdb reviewed-pose.sdf output-root" >&2
    exit 2
fi
molforge doctor --stage md --accelerator gpu
exec molforge md --receptor "$1" --ligand "$2" --output-root "$3" \
    --threads "${SLURM_CPUS_PER_TASK:-4}" --accelerator gpu
