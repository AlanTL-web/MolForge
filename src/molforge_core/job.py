"""Workflow job creation and provenance manifests."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from contextlib import contextmanager
from contextvars import ContextVar

_task_name = ContextVar('molforge_task_name', default='')


@contextmanager
def named_task(name):
    clean = name.strip()
    if clean and (len(clean) > 80 or not re.fullmatch(r'[A-Za-z0-9 _.-]+', clean)):
        raise ValueError('Task name must use at most 80 English letters, numbers, spaces, _ . or -.')
    token = _task_name.set(clean)
    try:
        yield
    finally:
        _task_name.reset(token)


GENERIC_INPUT_NAMES = {
    "protein", "receptor", "receptor_original", "receptor_repaired",
    "ligand", "best_ligand", "best_complex", "complex",
}


def _input_label(path: Path, *, depth: int = 0) -> str:
    """Recover a useful input name, following nearby manifest provenance when needed."""
    label = path.stem
    if label.lower() not in GENERIC_INPUT_NAMES or depth >= 3:
        return label
    for parent in path.resolve().parents:
        manifest = parent / "manifest.json"
        if not manifest.is_file():
            continue
        try:
            parameters = json.loads(manifest.read_text(encoding="utf-8"))["parameters"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            break
        keys = ("source", "receptor") if "receptor" in label or "protein" in label else ("ligand",)
        for key in keys:
            source = parameters.get(key)
            if source:
                return _input_label(Path(source), depth=depth + 1)
        break
    return label


def descriptive_job_name(operation: str, *inputs: Path) -> str:
    """Build a readable operation and input label."""
    parts = [operation]
    for path in inputs:
        label = re.sub(r"[^A-Za-z0-9]+", "-", _input_label(path)).strip("-")
        if label and label.lower() not in {part.lower() for part in parts}:
            parts.append(label[:48])
    return "_".join(parts)


def create_job(output_root: Path, name: str) -> tuple[Path, str]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    display_name = _task_name.get() or name.strip()
    safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '-', display_name).strip('.-')[:64] or 'workflow-job'
    output_root.mkdir(parents=True, exist_ok=True)
    suffix = 0
    while True:
        job_dir = output_root / f"{stamp}_{safe_name}{'-' + str(suffix) if suffix else ''}"
        try:
            job_dir.mkdir(exist_ok=False)
            break
        except FileExistsError:
            suffix += 1
    (job_dir / 'run_metadata.json').write_text(json.dumps({
        'task_name': display_name, 'operation': name, 'created_at_utc': stamp,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return job_dir, stamp


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(job_dir: Path, stamp: str, node: str, parameters: dict, summary: dict, output_dir: Path) -> None:
    files = [path for path in sorted(output_dir.rglob("*")) if path.is_file()]
    manifest = {
        "schema_version": 1, "status": "completed", "created_at_utc": stamp,
        "node": node, "parameters": parameters, "summary": summary,
        "outputs": [
            {"path": str(path.relative_to(job_dir)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
    }
    (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
