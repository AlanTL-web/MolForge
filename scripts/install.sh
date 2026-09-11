#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
profile=conformers
prefix=
mode=install
assume_yes=0
adgpu_backend=auto

usage() {
  cat <<'EOF'
MolForge Linux environment installer

Usage: bash scripts/install.sh [options]

  --profile NAME    conformers, dock, repair, md, or all
  --prefix PATH     existing/new conda environment (default: active conda or .molforge/envs/PROFILE)
  --check           inspect the environment without installing
  --plan            show planned packages and downloads
  --yes             skip confirmation
  --adgpu BACKEND   auto, cuda11, cuda12, ocl, or skip
  -h, --help        show this help

The installer uses conda, mamba, or micromamba. If none is available, it downloads
micromamba from its official distribution service. HDOCKlite remains a manual install
because users must accept the HDOCK authors' download terms.
EOF
}

while (($#)); do
  case "$1" in
    --profile) profile="${2:?missing profile}"; shift 2 ;;
    --prefix) prefix="${2:?missing prefix}"; shift 2 ;;
    --check) mode=check; shift ;;
    --plan) mode=plan; shift ;;
    --yes) assume_yes=1; shift ;;
    --adgpu) adgpu_backend="${2:?missing backend}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$profile" in conformers|dock|repair|md|all) ;; *) echo 'Invalid profile' >&2; exit 2 ;; esac
case "$adgpu_backend" in auto|cuda11|cuda12|ocl|skip) ;; *) echo 'Invalid backend' >&2; exit 2 ;; esac
[[ $(uname -s) == Linux ]] || { echo 'Run in Linux or WSL.' >&2; exit 2; }
prefix="${prefix:-${CONDA_PREFIX:-$project_dir/.molforge/envs/$profile}}"
prefix=$(realpath -m -- "$prefix")
packages=(pip)
[[ -d "$prefix/conda-meta" ]] || packages+=(python=3.11)
checks=()
case "$profile" in
  conformers) packages+=(rdkit); checks+=(conformers) ;;
  dock) packages+=(rdkit meeko gemmi autogrid); checks+=(conformers dock) ;;
  repair) packages+=(pdbfixer openmm); checks+=(repair) ;;
  md) packages+=(rdkit gromacs ambertools acpype 'gmx_mmpbsa>=1.5.6' openbabel openmpi mpi4py); checks+=(md convert) ;;
  all) packages+=(rdkit meeko gemmi autogrid pdbfixer openmm gromacs ambertools acpype 'gmx_mmpbsa>=1.5.6' openbabel openmpi mpi4py); checks+=(conformers dock repair md convert hdock) ;;
esac
export PATH="$prefix/bin:$PATH"
check_environment() {
  local failed=0 stage
  [[ -x "$prefix/bin/python" ]] || { echo "Environment missing: $prefix"; return 1; }
  for stage in "${checks[@]}"; do
    "$prefix/bin/python" -m molforge_linux doctor --stage "$stage" || failed=1
  done
  if [[ "$profile" == md || "$profile" == all ]]; then
    for stage in acpype gmx_MMPBSA antechamber parmchk2 tleap sqm; do
      command -v "$stage" >/dev/null || { echo "Missing executable: $stage"; failed=1; }
    done
    "$prefix/bin/python" -c 'import unigbsa.pipeline, mpi4py.MPI, lickit' || failed=1
  fi
  if [[ "$profile" == dock || "$profile" == all ]]; then
    "$prefix/bin/python" -c 'import meeko, gemmi' || failed=1
    if command -v autodock_gpu_128wi >/dev/null && command -v ldd >/dev/null; then
      if ldd "$(command -v autodock_gpu_128wi)" 2>/dev/null | grep 'not found'; then
        echo 'AutoDock-GPU shared libraries are missing.'; failed=1
      fi
    fi
  fi
  return "$failed"
}
printf 'Environment: %s\nProfile: %s\nPackages: %s\n' "$prefix" "$profile" "${packages[*]}"
if [[ "$mode" == check ]]; then check_environment; exit $?; fi
if [[ "$mode" == plan ]]; then
  echo 'Existing packages are resolved by the environment manager; missing packages are downloaded.'
  echo 'dock/all: reuse AutoDock-GPU from PATH or download official v1.6 binary.'
  echo 'md/all: install Uni-GBSA. all: HDOCK executables must already be on PATH.'
  exit 0
fi
if [[ -x "$prefix/bin/python" ]] && check_environment; then
  echo 'All requested checks passed; no downloads required.'
  exit 0
fi
if [[ -d "$prefix" && ! -d "$prefix/conda-meta" ]]; then
  echo 'Existing prefix is not a conda environment. Choose a new --prefix; existing files were preserved.' >&2
  exit 1
fi
if (( ! assume_yes )); then
  read -r -p 'Install missing dependencies here (MD may require several GB)? [y/N] ' reply
  [[ "$reply" == y || "$reply" == Y ]] || exit 0
fi
manager=
for candidate in micromamba mamba conda; do
  if command -v "$candidate" >/dev/null; then manager=$(command -v "$candidate"); break; fi
done
if [[ -z "$manager" && -x "$project_dir/.molforge/tools/bin/micromamba" ]]; then
  manager="$project_dir/.molforge/tools/bin/micromamba"
fi
if [[ -z "$manager" ]]; then
  case $(uname -m) in
    x86_64) subdir=linux-64 ;;
    aarch64) subdir=linux-aarch64 ;;
    *) echo 'Unsupported architecture; install a conda-compatible manager.' >&2; exit 1 ;;
  esac
  archive=$(mktemp)
  trap 'rm -f -- "$archive"' EXIT
  curl -fL --retry 3 --connect-timeout 20 --max-time 600 \
    "https://micro.mamba.pm/api/micromamba/$subdir/latest" -o "$archive"
  mkdir -p "$project_dir/.molforge/tools"
  tar -xjf "$archive" -C "$project_dir/.molforge/tools" bin/micromamba
  manager="$project_dir/.molforge/tools/bin/micromamba"
fi
action=create
[[ -d "$prefix/conda-meta" ]] && action=install
"$manager" "$action" -y -p "$prefix" --override-channels -c conda-forge -c bioconda --strict-channel-priority "${packages[@]}"
if [[ "$profile" == md || "$profile" == all ]]; then
  "$prefix/bin/python" -m pip install unigbsa lickit
fi
"$prefix/bin/python" -m pip install --no-deps "$project_dir"
if [[ "$profile" == dock || "$profile" == all ]]; then
  if ! command -v autodock_gpu_128wi >/dev/null && [[ "$adgpu_backend" != skip ]]; then
    backend=$adgpu_backend
    if [[ "$backend" == auto ]]; then
      backend=ocl
      if command -v nvidia-smi >/dev/null; then
        gpu_info=$(nvidia-smi 2>/dev/null || true)
        if [[ "$gpu_info" =~ CUDA\ Version:\ ([0-9]+) ]]; then
          if (( BASH_REMATCH[1] >= 12 )); then backend=cuda12;
          elif (( BASH_REMATCH[1] >= 11 )); then backend=cuda11; fi
        fi
      fi
    fi
    case $(uname -m) in
      x86_64) arch=x64 ;;
      aarch64) arch=aarch64; [[ "$backend" == ocl ]] || { echo 'ARM requires OpenCL'; exit 1; } ;;
      *) echo 'No AutoDock-GPU binary for this architecture'; exit 1 ;;
    esac
    target="$prefix/bin/autodock_gpu_128wi"
    url="https://github.com/ccsb-scripps/AutoDock-GPU/releases/download/v1.6/adgpu-v1.6_linux_${arch}_${backend}_128wi"
    curl -fL --retry 3 --connect-timeout 20 --max-time 600 "$url" -o "$target.part"
    chmod 755 "$target.part"
    mv -- "$target.part" "$target"
    sha256sum "$target" > "$prefix/autodock-download.sha256"
  fi
fi
printf '\nActivate using your environment manager:\n  %q activate %q\n' "$manager" "$prefix"
printf 'Or run without shell initialization:\n  %q run -p %q molforge --help\n' "$manager" "$prefix"
echo 'Checking installation. Missing HDOCK or hardware runtime support will be reported.'
check_environment
