#!/usr/bin/env python3
"""Update this managed skill copy while refusing to overwrite local edits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/asd-ste100"


def inventory(folder: Path) -> dict[str, str]:
    if folder.is_symlink():
        raise ValueError("A managed skill directory cannot be a symbolic link.")
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symbolic links are not supported in managed skill files.")
        if path.is_file():
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def safe_child(folder: Path, relative: str) -> Path:
    parts = Path(relative).parts
    if Path(relative).is_absolute() or ".." in parts or not parts:
        raise ValueError("Installation record contains a path outside the skill.")
    target = folder.joinpath(*parts)
    if not target.resolve().is_relative_to(folder.resolve()):
        raise ValueError("Installation target resolves outside the skill directory.")
    return target


def synchronize(source: Path, destination: Path, record_path: Path, *, adopt: bool = False, check: bool = False) -> str:
    source = source.resolve()
    if destination.is_symlink() or record_path.is_symlink():
        raise ValueError("Symbolic links are not supported for managed installation paths.")
    destination = destination.resolve()
    if source == destination or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("Source and installed copy must be separate directories.")
    desired = inventory(source)
    if "SKILL.md" not in desired:
        raise ValueError("Source skill entrypoint is missing.")
    current = inventory(destination) if destination.exists() else {}
    if adopt:
        if current != desired:
            raise ValueError("Adoption requires an installed copy identical to this checkout.")
    else:
        if not record_path.is_file():
            raise ValueError("No managed installation record. Use the Codex installer, then --adopt.")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("destination") != str(destination) or record.get("skill") != "asd-ste100":
            raise ValueError("Installation record does not identify this skill destination.")
        previous = record["files"]
        for relative in previous:
            safe_child(destination, relative)
        changed = [name for name, digest in previous.items() if current.get(name) != digest]
        conflicts = [name for name in desired if name in current and name not in previous]
        if changed or conflicts:
            raise ValueError("Local edits or new conflicting files detected: " + ", ".join(sorted(set(changed + conflicts))))
        if check:
            return "Installed copy is current." if all(current.get(k) == v for k, v in desired.items()) and set(previous) == set(desired) else "Managed update available."
        # Exact file operations only. No recursive deletion or directory replacement.
        for relative in sorted(set(previous) - set(desired)):
            safe_child(destination, relative).unlink()
        for relative in desired:
            target = safe_child(destination, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            if current.get(relative) != desired[relative]:
                target.write_bytes(safe_child(source, relative).read_bytes())
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps({"schema_version": 1, "skill": "asd-ste100", "destination": str(destination), "files": desired}, indent=2) + "\n", encoding="utf-8")
    return "Installed copy adopted." if adopt else "Installed copy synchronized."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    args = parser.parse_args(argv)
    if args.adopt and args.check:
        parser.error("Use --adopt or --check separately.")
    try:
        print(synchronize(SOURCE, args.codex_home / "skills/asd-ste100", args.codex_home / "skill-state/asd-ste100.json", adopt=args.adopt, check=args.check))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Installation unchanged or incomplete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
