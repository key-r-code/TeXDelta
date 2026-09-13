import json
import shutil
import subprocess
from pathlib import Path

import pytest
from jsonschema import validate

import texdelta.pipeline as pipeline
from texdelta.config import load_config
from texdelta.pipeline import build_diff
from texdelta.toolchain import REQUIRED

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in REQUIRED), reason="TeX toolchain unavailable"
)


def test_end_to_end_and_cache(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "basic"
    output = tmp_path / "output"
    report = build_diff(
        fixture / "old" / "main.tex",
        fixture / "new" / "main.tex",
        output,
        load_config(None),
    )
    assert (output / "diff.pdf").stat().st_size > 1_000
    assert (output / "diff.tex").is_file()
    assert (output / "support" / "assets").is_dir()
    statuses = [item["status"] for item in report["figures"]]
    assert statuses == ["changed", "changed", "added", "removed", "unchanged"]
    assert all(("/" + "Users/") not in json.dumps(item) for item in report["figures"])
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "report-v1.json").read_text())
    validate(report, schema)
    if shutil.which("pdfinfo"):
        info = subprocess.check_output(["pdfinfo", str(output / "diff.pdf")], text=True)
        assert (
            int(
                next(
                    line.split(":", 1)[1] for line in info.splitlines() if line.startswith("Pages:")
                )
            )
            >= 3
        )
    if shutil.which("pdftotext"):
        text = subprocess.check_output(["pdftotext", str(output / "diff.pdf"), "-"], text=True)
        assert "FIGURE COMPARISON: OLD VS. NEW" in text
        assert all(marker in text for marker in ("OLD", "NEW", "ADDED", "REMOVED"))
    if shutil.which("pdfimages"):
        images = subprocess.check_output(
            ["pdfimages", "-list", str(output / "diff.pdf")], text=True
        )
        assert len(images.splitlines()) > 2
    cached = build_diff(
        fixture / "old" / "main.tex",
        fixture / "new" / "main.tex",
        output,
        load_config(None),
    )
    assert cached["status"] == "cached"


def test_compile_fallback_and_kept_workdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "basic"
    output = tmp_path / "fallback"
    original = pipeline._compile_diff
    calls = 0

    def fail_once(*args: object, **kwargs: object) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise pipeline.BuildError("synthetic primary failure")
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pipeline, "_compile_diff", fail_once)
    report = build_diff(
        fixture / "old" / "main.tex",
        fixture / "new" / "main.tex",
        output,
        load_config(None),
        keep_workdir=True,
    )
    assert report["fallbacks"] == [
        "abstract relocation disabled after primary compile failure",
        "latexdiff retried with math-markup=whole",
    ]
    assert output.with_name("fallback-workdir").is_dir()
