#!/usr/bin/python3
"""Sincronizare unidirectionala, conservatoare, spre repository-ul RehabRob.

Sursa canonica este directorul pachetului care contine acest script. Destinatia
implicita este /home/ubuntu/RehabRob/rehab_exo_description. Instrumentul nu sterge
fisiere, nu executa Git commit/push si refuza conflictele bilaterale.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


DEFAULT_DESTINATION = Path("/home/ubuntu/RehabRob/rehab_exo_description")
IGNORED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".swp", "~"}
STATE_NAME = "rehab_sync_state_v1.json"


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRECTORIES for part in path.parts) or any(
        path.name.endswith(suffix) for suffix in IGNORED_SUFFIXES
    )


def inventory(root: Path) -> dict[str, Path]:
    """Returneaza numai fisiere regulate; legaturile simbolice sunt refuzate."""
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if _ignored(relative):
            continue
        if path.is_symlink():
            raise RuntimeError(f"legatura simbolica refuzata: {path}")
        if path.is_file():
            files[relative.as_posix()] = path
    return files


def digest(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def git_root(destination: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(destination), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    root = Path(result.stdout.strip()).resolve()
    destination.resolve().relative_to(root)
    return root


def state_path(repository: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--git-dir"],
        check=True,
        capture_output=True,
        text=True,
    )
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = repository / git_dir
    return git_dir.resolve() / STATE_NAME


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "files": {}}
    with path.open(encoding="utf-8") as stream:
        state = json.load(stream)
    if state.get("version") != 1 or not isinstance(state.get("files"), dict):
        raise RuntimeError(f"stare de sincronizare incompatibila: {path}")
    return state


def dirty_package(repository: Path, destination: Path) -> list[str]:
    relative = destination.resolve().relative_to(repository.resolve()).as_posix()
    result = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1",
         "--untracked-files=all", "--", relative],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def analyse(source: Path, destination: Path, state: dict) -> dict:
    source_files = inventory(source)
    destination_files = inventory(destination)
    changes: list[str] = []
    conflicts: list[str] = []
    unchanged: list[str] = []
    previous = state.get("files", {})

    for relative, source_path in source_files.items():
        destination_path = destination_files.get(relative)
        source_hash = digest(source_path)
        destination_hash = digest(destination_path)
        baseline = previous.get(relative)
        if source_hash == destination_hash:
            unchanged.append(relative)
            continue
        if baseline:
            source_changed = source_hash != baseline.get("source_sha256")
            destination_changed = destination_hash != baseline.get("destination_sha256")
            if source_changed and destination_changed:
                conflicts.append(relative)
                continue
            if destination_changed and not source_changed:
                # Modificare facuta numai de colega: nu o suprascriem.
                conflicts.append(relative)
                continue
        changes.append(relative)

    destination_only = sorted(set(destination_files) - set(source_files))
    return {
        "source_files": source_files,
        "changes": sorted(changes),
        "conflicts": sorted(conflicts),
        "unchanged": sorted(unchanged),
        "destination_only": destination_only,
    }


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.rehab-sync-", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def write_state(path: Path, source: Path, destination: Path, source_files: dict[str, Path]) -> None:
    files = {}
    for relative, source_path in source_files.items():
        destination_path = destination / relative
        files[relative] = {
            "source_sha256": digest(source_path),
            "destination_sha256": digest(destination_path),
        }
    payload = {
        "version": 1,
        "source": str(source.resolve()),
        "destination": str(destination.resolve()),
        "updated_unix_ns": time.time_ns(),
        "files": files,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def synchronize(source: Path, destination: Path, apply: bool, check: bool = False) -> int:
    source = source.resolve()
    destination = destination.resolve()
    if not (source / "package.xml").is_file():
        raise RuntimeError(f"sursa nu pare un pachet ROS: {source}")
    if not (destination / "package.xml").is_file():
        raise RuntimeError(f"destinatia nu pare pachetul RehabRob: {destination}")

    repository = git_root(destination)
    state_file = state_path(repository)
    state_exists = state_file.exists()
    state = load_state(state_file)
    report = analyse(source, destination, state)

    print(f"Sursa:       {source}")
    print(f"Destinatie:  {destination}")
    print(f"De copiat:   {len(report['changes'])}")
    print(f"Conflicte:   {len(report['conflicts'])}")
    print(f"Doar destinatie (pastrate): {len(report['destination_only'])}")
    for relative in report["changes"]:
        print(f"  COPY {relative}")
    for relative in report["conflicts"]:
        print(f"  CONFLICT {relative}")
    for relative in report["destination_only"]:
        print(f"  KEEP {relative}")

    if report["conflicts"]:
        print("REFUZ: exista modificari independente; rezolva manual conflictele.", file=sys.stderr)
        return 2
    if check:
        return 1 if report["changes"] else 0
    if not apply:
        print("Dry-run: nu s-a scris nimic. Foloseste --apply sau --watch.")
        return 0

    if not state_exists:
        dirty = dirty_package(repository, destination)
        if dirty:
            print("REFUZ initial: destinatia are modificari Git locale in pachet:", file=sys.stderr)
            for line in dirty:
                print(f"  {line}", file=sys.stderr)
            return 3

    for relative in report["changes"]:
        copy_atomic(report["source_files"][relative], destination / relative)
    write_state(state_file, source, destination, report["source_files"])
    print(f"Sincronizare completa: {len(report['changes'])} fisiere copiate; 0 sterse; 0 commit-uri.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="copiaza diferentele sigure")
    mode.add_argument("--watch", action="store_true", help="urmareste sursa si sincronizeaza salvarile")
    mode.add_argument("--check", action="store_true", help="iese cu 1 daca sunt diferente")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--interval", type=float, default=1.0, help="secunde intre verificarile --watch")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(__file__).resolve().parents[1]
    try:
        if not args.watch:
            return synchronize(source, args.dest, args.apply, args.check)
        if args.interval < 0.2:
            raise RuntimeError("--interval trebuie sa fie >= 0.2 s")
        print("Watch activ; Ctrl+C opreste. Nu se fac delete/commit/push.")
        while True:
            result = synchronize(source, args.dest, apply=True)
            if result != 0:
                return result
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Watch oprit.")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"EROARE: {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
