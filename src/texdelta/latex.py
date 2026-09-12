"""Prepare one staged LaTeX document for differencing."""

import os
import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from .errors import BuildError
from .figures import GRAPHICS_RE, parse_figures, replace_graphics
from .models import FigureConfig, Graphic, PreparedDocument
from .toolchain import ToolInfo

ABSTRACT_RE = re.compile(
    r"(\\begin\{abstract\}.*?\\end\{abstract\})\s*(\\begin\{document\})",
    re.DOTALL,
)
REFERENCE_WARNING_RE = re.compile(
    r"(?:There were undefined references|Citation .+ undefined|Reference .+ undefined)",
    re.IGNORECASE,
)


def run_logged(
    args: Sequence[str],
    cwd: Path,
    log: Path,
    env: Optional[dict[str, str]] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args), cwd=cwd, env=env, text=True, capture_output=True, check=False
    )
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if check and result.returncode:
        raise BuildError(f"Command failed ({result.returncode}): {' '.join(args)}; see {log.name}")
    return result


def move_abstract(text: str) -> tuple[str, bool]:
    replaced, count = ABSTRACT_RE.subn(r"\2\n\1", text, count=1)
    return replaced, bool(count)


def _local_dependencies(fls: Path, root: Path) -> list[Path]:
    if not fls.is_file():
        return []
    found: list[Path] = []
    for line in fls.read_text(errors="replace").splitlines():
        if not line.startswith("INPUT "):
            continue
        candidate = Path(line[6:])
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file() and candidate.suffix.lower() in {".cls", ".sty", ".def", ".bst"}:
            found.append(candidate)
    return sorted(set(found))


def _resolved_graphics(stderr: str, root: Path) -> list[Path]:
    resolved: list[Path] = []
    for raw in stderr.splitlines():
        line = raw.strip()
        if not line:
            continue
        candidate = Path(line)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}:
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise BuildError(f"Referenced graphic escapes project root: {line}") from exc
            resolved.append(candidate)
    return resolved


def _graphic_directories(text: str) -> list[Path]:
    directories: list[Path] = []
    for match in re.finditer(r"\\graphicspath\s*\{((?:\s*\{[^{}]*\}\s*)+)\}", text):
        directories.extend(Path(value) for value in re.findall(r"\{([^{}]*)\}", match.group(1)))
    return directories


def _resolve_graphics_from_text(text: str, root: Path, main: Path) -> list[Path]:
    search_roots = [root, root / main.parent]
    for directory in _graphic_directories(text):
        if directory.is_absolute():
            search_roots.append(directory)
        else:
            search_roots.extend((root / directory, root / main.parent / directory))
    resolved: list[Path] = []
    for match in GRAPHICS_RE.finditer(text):
        reference = Path(match.group(1))
        suffixes = [""] if reference.suffix else ["", ".pdf", ".png", ".jpg", ".jpeg"]
        candidates = [base / f"{reference}{suffix}" for base in search_roots for suffix in suffixes]
        source = next(
            (candidate.resolve() for candidate in candidates if candidate.is_file()), None
        )
        if source is None:
            raise BuildError(f"Referenced graphic does not exist: {reference}")
        try:
            source.relative_to(root)
        except ValueError as exc:
            raise BuildError(f"Referenced graphic escapes project root: {reference}") from exc
        resolved.append(source)
    return resolved


def _copy_graphics(graphics: Sequence[Graphic], output_root: Path) -> None:
    asset_dir = output_root / "support" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for graphic in graphics:
        suffix = graphic.source.suffix.lower()
        name = f"{graphic.digest[:16]}{suffix}"
        destination = asset_dir / name
        if not destination.exists():
            shutil.copy2(graphic.source, destination)
        graphic.output_path = f"support/assets/{name}"


def _diagnostics(log_text: str) -> list[str]:
    patterns = ("Overfull", "Underfull", "LaTeX Warning", "Package ")
    lines = [
        line.strip() for line in log_text.splitlines() if any(item in line for item in patterns)
    ]
    return list(dict.fromkeys(lines))[:100]


def prepare_document(
    side: str,
    root: Path,
    main: Path,
    output_root: Path,
    logs: Path,
    config: FigureConfig,
    tools: dict[str, ToolInfo],
    shell_escape: bool,
) -> PreparedDocument:
    job = f"texdelta_{side}"
    shell_flag = "-shell-escape" if shell_escape else "-no-shell-escape"
    latex_args = [
        tools["pdflatex"].path,
        "-interaction=nonstopmode",
        "-file-line-error",
        "-recorder",
        shell_flag,
        f"-jobname={job}",
        str(main),
    ]
    first = run_logged(latex_args, root, logs / f"{side}-pdflatex-1.log", check=True)
    source_text = (root / main).read_text(encoding="utf-8")
    has_bibliography = bool(re.search(r"\\bibliography\s*\{", source_text))
    bbl: Optional[Path] = None
    if has_bibliography:
        run_logged([tools["bibtex"].path, job], root, logs / f"{side}-bibtex.log", check=True)
        bbl = root / f"{job}.bbl"
        if not bbl.is_file():
            raise BuildError(f"{side}: BibTeX completed without producing {bbl.name}")
        run_logged(latex_args, root, logs / f"{side}-pdflatex-2.log", check=True)

    command = [tools["latexpand"].path, "--fatal", "--show-graphics"]
    if bbl:
        command.extend(["--expand-bbl", str(bbl)])
    command.append(str(main))
    expanded = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    fallback_note = ""
    if expanded.returncode:
        fallback = [item for item in command if item != "--fatal"]
        expanded = subprocess.run(fallback, cwd=root, text=True, capture_output=True, check=False)
        fallback_note = (
            "latexpand --fatal could not resolve a project graphic; used root-bound resolver\n"
        )
    (logs / f"{side}-latexpand.log").write_text(fallback_note + expanded.stderr, encoding="utf-8")
    if expanded.returncode:
        raise BuildError(f"{side}: latexpand failed; see {side}-latexpand.log")
    resolved = _resolved_graphics(expanded.stderr, root)
    if len(resolved) != len(list(GRAPHICS_RE.finditer(expanded.stdout))):
        resolved = _resolve_graphics_from_text(expanded.stdout, root, main)
    figures, graphics = parse_figures(expanded.stdout, side, resolved, config.environments)
    _copy_graphics(graphics, output_root)
    rewritten = replace_graphics(expanded.stdout, graphics)
    abstract_flat, _ = move_abstract(rewritten)
    fls = root / f"{job}.fls"
    combined_log = first.stdout + first.stderr
    return PreparedDocument(
        side=side,
        root=root,
        main=main,
        raw_flat=rewritten,
        abstract_flat=abstract_flat,
        graphics=graphics,
        figures=figures,
        local_dependencies=_local_dependencies(fls, root),
        diagnostics=([fallback_note.strip()] if fallback_note else []) + _diagnostics(combined_log),
    )


def copy_local_dependencies(documents: Sequence[PreparedDocument], output_root: Path) -> None:
    target = output_root / "support" / "tex"
    target.mkdir(parents=True, exist_ok=True)
    # Revised files win; copy it last.
    for document in sorted(documents, key=lambda item: item.side == "new"):
        for source in document.local_dependencies:
            relative = source.relative_to(document.root)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def tex_environment(output_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    tex_path = str((output_root / "support" / "tex").resolve()) + "//:"
    env["TEXINPUTS"] = tex_path
    env["BSTINPUTS"] = tex_path
    return env
