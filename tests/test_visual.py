import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

from texdelta.config import load_config
from texdelta.pipeline import build_diff
from texdelta.toolchain import REQUIRED

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_VISUAL_SNAPSHOT") != "1"
    or shutil.which("pdftoppm") is None
    or any(shutil.which(tool) is None for tool in REQUIRED),
    reason="Linux visual snapshot gate not enabled",
)


def test_appendix_snapshot(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "basic"
    output = tmp_path / "output"
    build_diff(
        fixture / "old" / "main.tex",
        fixture / "new" / "main.tex",
        output,
        load_config(None),
    )
    prefix = tmp_path / "appendix"
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-f",
            "3",
            "-singlefile",
            "-r",
            "110",
            str(output / "diff.pdf"),
            str(prefix),
        ],
        check=True,
        capture_output=True,
    )
    baseline = Image.open(Path(__file__).parents[1] / "docs" / "texdelta-demo.png").convert("RGB")
    actual = Image.open(prefix.with_suffix(".png")).convert("RGB")
    assert actual.size == baseline.size
    difference = ImageChops.difference(actual, baseline)
    rms = sum(ImageStat.Stat(difference).rms) / 3
    assert rms < 12
