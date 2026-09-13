"""End-to-end TeXDelta orchestration."""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .appendix import generate_appendix, inject_appendix
from .errors import BuildError
from .latex import (
    REFERENCE_WARNING_RE,
    copy_local_dependencies,
    prepare_document,
    run_logged,
    tex_environment,
)
from .matching import match_figures
from .models import Config
from .output import ensure_destination, fingerprint, promote
from .report import file_hash, read_report, write_report
from .toolchain import inspect_toolchain
from .workspace import resolve_input, stage_project


def _latexdiff(
    old_text: str,
    new_text: str,
    output_root: Path,
    logs: Path,
    config: Config,
    math_mode: str,
    tools: dict[str, Any],
) -> str:
    old_path = output_root / ".old-flat.tex"
    new_path = output_root / ".new-flat.tex"
    old_path.write_text(old_text, encoding="utf-8")
    new_path.write_text(new_text, encoding="utf-8")
    style = "UNDERLINE" if config.build.style == "underline" else "FONTSTRIKE"
    args = [
        tools["latexdiff"].path,
        f"--type={style}",
        "--disable-citation-markup",
        "--graphics-markup=none",
        f"--math-markup={math_mode}",
        old_path.name,
        new_path.name,
    ]
    result = run_logged(args, output_root, logs / f"latexdiff-{math_mode}.log", check=True)
    return result.stdout


def _compile_diff(
    text: str,
    output_root: Path,
    logs: Path,
    tools: dict[str, Any],
    shell_escape: bool,
    suffix: str,
) -> str:
    diff_tex = output_root / "diff.tex"
    diff_tex.write_text(text, encoding="utf-8")
    shell_flag = "-shell-escape" if shell_escape else "-no-shell-escape"
    args = [
        tools["pdflatex"].path,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        shell_flag,
        "-jobname=diff",
        "diff.tex",
    ]
    result = None
    for number in range(1, 4):
        result = run_logged(
            args,
            output_root,
            logs / f"diff-{suffix}-{number}.log",
            env=tex_environment(output_root),
            check=True,
        )
    assert result is not None
    log_text = (output_root / "diff.log").read_text(errors="replace")
    if REFERENCE_WARNING_RE.search(log_text):
        raise BuildError("Final diff contains unresolved citations or references")
    if not (output_root / "diff.pdf").is_file():
        raise BuildError("pdfLaTeX completed without producing diff.pdf")
    return log_text


def build_diff(
    old_main: Path,
    new_main: Path,
    destination: Path,
    config: Config,
    old_root_override: Optional[Path] = None,
    new_root_override: Optional[Path] = None,
    force: bool = False,
    rebuild: bool = False,
    keep_workdir: bool = False,
) -> dict[str, Any]:
    tools = inspect_toolchain(strict=True)
    old_root, old_relative = resolve_input(old_main, old_root_override)
    new_root, new_relative = resolve_input(new_main, new_root_override)
    destination = destination.expanduser().resolve()
    current_fingerprint = fingerprint(
        [old_root, new_root], [old_main.resolve(), new_main.resolve()], config, __version__
    )
    prior = read_report(destination / "report.json")
    if (
        not rebuild
        and prior
        and prior.get("fingerprint") == current_fingerprint
        and (destination / "diff.pdf").is_file()
        and (destination / "diff.tex").is_file()
    ):
        prior["status"] = "cached"
        return prior
    ensure_destination(destination, force)
    destination.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=".texdelta-", dir=destination.parent))
    output_root = scratch / "output"
    logs = output_root / "logs"
    logs.mkdir(parents=True)
    fallbacks: list[str] = []
    try:
        old_stage = scratch / "old"
        new_stage = scratch / "new"
        stage_project(old_root, old_stage)
        stage_project(new_root, new_stage)
        old_doc = prepare_document(
            "old",
            old_stage,
            old_relative,
            output_root,
            logs,
            config.figures,
            tools,
            config.build.shell_escape,
        )
        new_doc = prepare_document(
            "new",
            new_stage,
            new_relative,
            output_root,
            logs,
            config.figures,
            tools,
            config.build.shell_escape,
        )
        copy_local_dependencies([old_doc, new_doc], output_root)
        matches = (
            match_figures(old_doc.figures, new_doc.figures, config.figures)
            if config.build.figures
            else []
        )
        appendix = generate_appendix(matches, config.figures) if config.build.figures else ""
        use_abstract = config.build.abstract_diff
        old_text = old_doc.abstract_flat if use_abstract else old_doc.raw_flat
        new_text = new_doc.abstract_flat if use_abstract else new_doc.raw_flat
        try:
            diff_text = _latexdiff(old_text, new_text, output_root, logs, config, "coarse", tools)
            final_text = inject_appendix(diff_text, appendix)
            final_log = _compile_diff(
                final_text, output_root, logs, tools, config.build.shell_escape, "primary"
            )
        except BuildError:
            if config.build.strict_abstract:
                retry_old, retry_new = old_text, new_text
            else:
                retry_old, retry_new = old_doc.raw_flat, new_doc.raw_flat
                if use_abstract:
                    fallbacks.append("abstract relocation disabled after primary compile failure")
            fallbacks.append("latexdiff retried with math-markup=whole")
            diff_text = _latexdiff(retry_old, retry_new, output_root, logs, config, "whole", tools)
            final_text = inject_appendix(diff_text, appendix)
            final_log = _compile_diff(
                final_text, output_root, logs, tools, config.build.shell_escape, "fallback"
            )
        diagnostics = old_doc.diagnostics + new_doc.diagnostics
        diagnostics.extend(
            list(
                dict.fromkeys(
                    line.strip()
                    for line in final_log.splitlines()
                    if "Warning" in line or "Overfull" in line or "Underfull" in line
                )
            )[:100]
        )
        for transient in [output_root / ".old-flat.tex", output_root / ".new-flat.tex"]:
            transient.unlink(missing_ok=True)
        for generated in output_root.glob("diff.*"):
            if generated.suffix not in {".pdf", ".tex"}:
                generated.unlink(missing_ok=True)
        shutil.rmtree(logs)
        latexmkrc = output_root / "latexmkrc"
        latexmkrc.write_text(
            "$ENV{'TEXINPUTS'} = './support/tex//:';\n$ENV{'BSTINPUTS'} = './support/tex//:';\n",
            encoding="utf-8",
        )
        outputs = {
            "diff.pdf": file_hash(output_root / "diff.pdf"),
            "diff.tex": file_hash(output_root / "diff.tex"),
        }
        report = write_report(
            output_root / "report.json",
            "success",
            current_fingerprint,
            tools,
            config,
            matches,
            diagnostics,
            fallbacks,
            outputs,
        )
        promote(output_root, destination, force)
        return report
    except Exception:
        if logs.exists():
            failure_target = destination.parent / f"{destination.name}-failed-logs"
            if failure_target.exists():
                shutil.rmtree(failure_target)
            shutil.copytree(logs, failure_target)
        raise
    finally:
        if keep_workdir:
            kept = destination.parent / f"{destination.name}-workdir"
            if kept.exists():
                shutil.rmtree(kept)
            if scratch.exists():
                shutil.copytree(scratch, kept)
        shutil.rmtree(scratch, ignore_errors=True)
