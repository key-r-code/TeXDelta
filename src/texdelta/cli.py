"""TeXDelta command-line interface."""

import argparse
import importlib.resources
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from . import __version__
from .config import load_config
from .errors import TexDeltaError
from .pipeline import build_diff
from .toolchain import doctor_text


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="texdelta", description="LaTeX diffs with automatic figure comparisons"
    )
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    diff = commands.add_parser("diff", help="compare two LaTeX projects")
    diff.add_argument("old_main", type=Path)
    diff.add_argument("new_main", type=Path)
    diff.add_argument("--old-root", type=Path)
    diff.add_argument("--new-root", type=Path)
    diff.add_argument("--output-dir", type=Path, default=Path("texdelta-output"))
    diff.add_argument("--config", type=Path)
    diff.add_argument("--style", choices=("underline", "font-strike"))
    diff.add_argument("--force", action="store_true")
    diff.add_argument("--rebuild", action="store_true")
    diff.add_argument("--keep-workdir", action="store_true")
    diff.add_argument("--allow-shell-escape", action="store_true")
    diff.add_argument("--strict-abstract", action="store_true")
    diff.add_argument("--no-figures", action="store_true")
    commands.add_parser("doctor", help="check required local tools")
    init = commands.add_parser("init-overleaf", help="copy the bundled Overleaf project")
    init.add_argument("destination", type=Path)
    init.add_argument("--force", action="store_true")
    return root


def _init_overleaf(destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        raise TexDeltaError(f"Destination exists: {destination}; use --force")
    resource = importlib.resources.files("texdelta").joinpath("overleaf_template.zip")
    if not resource.is_file():
        raise TexDeltaError("Bundled Overleaf example is unavailable in this installation")
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        importlib.resources.as_file(resource) as archive_path,
        zipfile.ZipFile(archive_path) as archive,
    ):
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise TexDeltaError("Bundled Overleaf archive contains an unsafe path")
        with tempfile.TemporaryDirectory(
            prefix=".texdelta-overleaf-", dir=destination.parent
        ) as raw:
            staged = Path(raw) / "project"
            archive.extractall(staged)
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            staged.rename(destination)


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            text = doctor_text()
            print(text)
            return 0 if text.startswith("TeXDelta doctor: OK") else 3
        if args.command == "init-overleaf":
            _init_overleaf(args.destination, args.force)
            print(f"Created Overleaf project at {args.destination}")
            return 0
        config = load_config(args.config)
        if args.style:
            config.build.style = args.style
        if args.allow_shell_escape:
            config.build.shell_escape = True
        if args.strict_abstract:
            config.build.strict_abstract = True
        if args.no_figures:
            config.build.figures = False
        report = build_diff(
            args.old_main,
            args.new_main,
            args.output_dir,
            config,
            args.old_root,
            args.new_root,
            args.force,
            args.rebuild,
            args.keep_workdir,
        )
        counts: dict[str, int] = {}
        for figure in report.get("figures", []):
            status = figure["status"]
            counts[status] = counts.get(status, 0) + 1
        summary = (
            ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
            or "figures disabled"
        )
        print(f"TeXDelta {report['status']}: {args.output_dir / 'diff.pdf'} ({summary})")
        return 0
    except KeyboardInterrupt:
        print("TeXDelta interrupted", file=sys.stderr)
        return 130
    except TexDeltaError as exc:
        print(f"texdelta: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"texdelta: internal error: {exc}", file=sys.stderr)
        return 5
