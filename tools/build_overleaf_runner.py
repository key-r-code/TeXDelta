#!/usr/bin/env python3
"""Build the deterministic standalone Overleaf runner and packaged template."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "texdelta"
EXAMPLE = ROOT / "examples" / "overleaf"
RUNNER = EXAMPLE / "texdelta.pyz"
TEMPLATE = SOURCE / "overleaf_template.zip"
EPOCH = (1980, 1, 1, 0, 0, 0)


def _zip_tree(source: Path, destination: Path, prefix: str = "") -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_STORED) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path == destination:
                continue
            relative = Path(prefix) / path.relative_to(source)
            info = zipfile.ZipInfo(relative.as_posix(), EPOCH)
            info.external_attr = (0o644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_STORED)


def build_runner(destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="texdelta-zipapp-") as raw:
        stage = Path(raw)
        shutil.copytree(
            SOURCE,
            stage / "texdelta",
            ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "overleaf_template.zip"),
        )
        (stage / "__main__.py").write_text(
            "from texdelta.cli import main\nraise SystemExit(main())\n", encoding="utf-8"
        )
        shutil.copyfile(ROOT / "THIRD_PARTY_NOTICES.md", stage / "THIRD_PARTY_NOTICES.md")
        try:
            import tomli  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            tomli = None
        if tomli is not None:
            package = Path(tomli.__file__).resolve().parent
            shutil.copytree(
                package,
                stage / "tomli",
                ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
            )
        _zip_tree(stage, destination)


def build_template(destination: Path, runner: Path = RUNNER) -> None:
    with tempfile.TemporaryDirectory(prefix="texdelta-template-") as raw:
        stage = Path(raw) / "overleaf"
        shutil.copytree(EXAMPLE, stage, ignore=shutil.ignore_patterns("texdelta.pyz", ".*"))
        shutil.copyfile(runner, stage / "texdelta.pyz")
        _zip_tree(stage, destination)


def _archive_contents(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when committed files drift")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="texdelta-overleaf-check-") as raw:
        runner = Path(raw) / "texdelta.pyz" if args.check else RUNNER
        template = Path(raw) / "overleaf_template.zip" if args.check else TEMPLATE
        build_runner(runner)
        if args.check:
            build_template(template, runner)
            if not RUNNER.is_file() or _archive_contents(RUNNER) != _archive_contents(runner):
                raise SystemExit("examples/overleaf/texdelta.pyz is out of date")
            if not TEMPLATE.is_file():
                raise SystemExit("src/texdelta/overleaf_template.zip is out of date")
            committed_template = _archive_contents(TEMPLATE)
            generated_template = _archive_contents(template)
            if committed_template.get("texdelta.pyz") != RUNNER.read_bytes():
                raise SystemExit("Packaged template contains a stale Overleaf runner")
            committed_template.pop("texdelta.pyz", None)
            generated_template.pop("texdelta.pyz", None)
            if committed_template != generated_template:
                raise SystemExit("src/texdelta/overleaf_template.zip is out of date")
        else:
            build_template(template)
    if not args.check:
        os.chmod(RUNNER, 0o755)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
