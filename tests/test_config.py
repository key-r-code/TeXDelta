from pathlib import Path

import pytest

from texdelta.config import load_config
from texdelta.errors import UsageError


def test_default_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_config(None)
    assert config.build.style == "underline"
    assert "wrapfigure" in config.figures.environments


def test_config_and_pairs(tmp_path: Path) -> None:
    path = tmp_path / "custom.toml"
    path.write_text(
        """
schema_version = 1
[build]
style = "font-strike"
[figures]
layout = "columns"
exclude_old = ["fig:skip"]
[[figures.pairs]]
old = "fig:before"
new = "fig:after"
heading = "Renamed"
"""
    )
    config = load_config(path)
    assert config.build.style == "font-strike"
    assert config.figures.layout == "columns"
    assert config.figures.pairs[0].heading == "Renamed"


@pytest.mark.parametrize(
    "content,message",
    [
        ("schema_version = 2", "Unsupported"),
        ("mystery = true", "Unknown top-level"),
        ("[build]\nstyle='rainbow'", "build.style"),
        ("[figures]\nlayout='diagonal'", "figures.layout"),
        ("[figures]\nenvironments=[]", "cannot be empty"),
        ("not valid toml", "Cannot read"),
        ("build = 1", "build.*table"),
        ("figures = 1", "figures.*table"),
        ("[figures]\npairs = 1", "pairs must"),
        ("[[figures.pairs]]\nold='x'", "Invalid figure pair"),
    ],
)
def test_invalid_config(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(content)
    with pytest.raises(UsageError, match=message):
        load_config(path)
