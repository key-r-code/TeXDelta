"""Safe source validation and isolated staging."""

import shutil
from pathlib import Path
from typing import Optional

from .errors import UsageError

IGNORED_SUFFIXES = {".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".synctex.gz"}
IGNORED_NAMES = {".git", ".venv", "__pycache__", "texdelta-output"}


def resolve_input(main: Path, root: Optional[Path]) -> tuple[Path, Path]:
    main = main.expanduser().resolve()
    if not main.is_file() or main.suffix.lower() != ".tex":
        raise UsageError(f"Main document is not a readable .tex file: {main}")
    project_root = root.expanduser().resolve() if root else main.parent
    try:
        relative = main.relative_to(project_root)
    except ValueError as exc:
        raise UsageError(f"Main document {main} is outside project root {project_root}") from exc
    if not project_root.is_dir():
        raise UsageError(f"Project root is not a directory: {project_root}")
    return project_root, relative


def validate_symlinks(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            try:
                path.resolve().relative_to(root)
            except ValueError as exc:
                raise UsageError(f"Symlink escapes project root: {path.relative_to(root)}") from exc


def _ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        path = Path(name)
        if name in IGNORED_NAMES or path.suffix in IGNORED_SUFFIXES:
            ignored.add(name)
    return ignored


def stage_project(root: Path, destination: Path) -> None:
    validate_symlinks(root)
    shutil.copytree(root, destination, symlinks=False, ignore=_ignore)
