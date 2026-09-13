"""Input fingerprints and atomic output promotion."""

import hashlib
import json
import shutil
from collections.abc import Iterable
from pathlib import Path

from .errors import UsageError
from .models import Config

RELEVANT_SUFFIXES = {
    ".tex",
    ".bib",
    ".bst",
    ".cls",
    ".sty",
    ".def",
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
}


def fingerprint(roots: Iterable[Path], mains: Iterable[Path], config: Config, version: str) -> str:
    digest = hashlib.sha256()
    digest.update(version.encode())
    digest.update(json.dumps(config.as_dict(), sort_keys=True).encode())
    main_set = {path.resolve() for path in mains}
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in RELEVANT_SUFFIXES:
                continue
            if ".git" in path.parts or "texdelta-output" in path.parts:
                continue
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    for main in sorted(main_set):
        digest.update(str(main).encode())
    return digest.hexdigest()


def ensure_destination(destination: Path, force: bool) -> None:
    if destination.exists() and any(destination.iterdir()) and not force:
        raise UsageError(
            f"Output directory already exists and is not empty: {destination}; use --force"
        )


def promote(staged: Path, destination: Path, force: bool) -> None:
    backup = destination.with_name(destination.name + ".previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        if not force:
            raise UsageError(f"Output directory exists: {destination}")
        destination.rename(backup)
    try:
        staged.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)
