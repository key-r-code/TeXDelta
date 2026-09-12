import json
from pathlib import Path

import pytest

from texdelta.errors import UsageError
from texdelta.models import Config
from texdelta.output import ensure_destination, fingerprint, promote
from texdelta.report import _redact, read_report


def test_fingerprint_changes(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    main = root / "main.tex"
    main.write_text("one")
    first = fingerprint([root], [main], Config(), "v")
    main.write_text("two")
    second = fingerprint([root], [main], Config(), "v")
    assert first != second


def test_destination_and_promote(tmp_path: Path) -> None:
    destination = tmp_path / "out"
    destination.mkdir()
    (destination / "old").write_text("old")
    with pytest.raises(UsageError, match="--force"):
        ensure_destination(destination, False)
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new").write_text("new")
    promote(staged, destination, True)
    assert (destination / "new").read_text() == "new"
    assert not destination.with_name("out.previous").exists()
    second = tmp_path / "second"
    second.mkdir()
    with pytest.raises(UsageError, match="exists"):
        promote(second, destination, False)


def test_read_report(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    assert read_report(path) is None
    path.write_text("not json")
    assert read_report(path) is None
    path.write_text(json.dumps({"schema_version": 1, "status": "success"}))
    assert read_report(path)["status"] == "success"
    private_path = "/" + "Users/person/project/main.tex"
    assert _redact(f"failed at {private_path}:10") == "failed at <redacted-path>:10"
