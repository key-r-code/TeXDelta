import subprocess
from pathlib import Path

import pytest

from texdelta.errors import BuildError
from texdelta.latex import (
    _local_dependencies,
    _resolve_graphics_from_text,
    _resolved_graphics,
    move_abstract,
    run_logged,
)


def test_abstract_and_graphic_resolution(tmp_path: Path) -> None:
    images = tmp_path / "Images"
    images.mkdir()
    graphic = images / "plot.png"
    graphic.write_bytes(b"png")
    text = r"\graphicspath{{Images/}}\includegraphics{plot}"
    assert _resolve_graphics_from_text(text, tmp_path, Path("main.tex")) == [graphic]
    moved, changed = move_abstract(r"\begin{abstract}A\end{abstract}\begin{document}")
    assert changed is True
    assert moved.index(r"\begin{document}") < moved.index(r"\begin{abstract}")
    assert move_abstract("plain") == ("plain", False)


def test_graphic_resolution_failures(tmp_path: Path) -> None:
    with pytest.raises(BuildError, match="does not exist"):
        _resolve_graphics_from_text(r"\includegraphics{missing}", tmp_path, Path("main.tex"))
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(b"outside")
    with pytest.raises(BuildError, match="escapes"):
        _resolve_graphics_from_text(
            rf"\graphicspath{{{{{outside.parent}/}}}}\includegraphics{{{outside.name}}}",
            tmp_path,
            Path("main.tex"),
        )
    with pytest.raises(BuildError, match="escapes"):
        _resolved_graphics(str(outside), tmp_path)


def test_dependencies_and_logged_failure(tmp_path: Path) -> None:
    assert _local_dependencies(tmp_path / "missing.fls", tmp_path) == []
    style = tmp_path / "local.sty"
    style.write_text("style")
    fls = tmp_path / "job.fls"
    fls.write_text(f"OUTPUT ignored\nINPUT {style}\nINPUT /outside/system.sty\n")
    assert _local_dependencies(fls, tmp_path) == [style]
    log = tmp_path / "command.log"
    with pytest.raises(BuildError, match="Command failed"):
        run_logged(
            ["python3", "-c", "import sys; print('failed'); sys.exit(7)"],
            tmp_path,
            log,
        )
    assert "failed" in log.read_text()
    result = run_logged(["python3", "-c", "import sys; sys.exit(2)"], tmp_path, log, check=False)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 2
