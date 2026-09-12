import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from texdelta.cli import _init_overleaf, main, parser


def test_report_schema_accepts_integration_report(tmp_path: Path) -> None:
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "report-v1.json").read_text())
    Draft202012Validator.check_schema(schema)


def test_cli_help_and_version() -> None:
    command = parser()
    help_text = command.format_help()
    assert "diff" in help_text
    assert "doctor" in help_text
    assert "init-overleaf" in help_text
    with pytest.raises(SystemExit, match="0"):
        main(["--version"])


def test_init_overleaf_from_packaged_archive(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "project"
    _init_overleaf(destination, False)
    assert (destination / "texdelta.pyz").is_file()
    assert (destination / "Old" / "main.tex").is_file()
    assert (destination / "New" / "main.tex").is_file()
