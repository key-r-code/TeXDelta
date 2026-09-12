from pathlib import Path

import pytest

from texdelta.errors import UsageError
from texdelta.workspace import resolve_input, stage_project, validate_symlinks


def test_resolve_and_stage(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    main = root / "main.tex"
    main.write_text("hello")
    (root / "main.aux").write_text("generated")
    resolved, relative = resolve_input(main, None)
    assert resolved == root
    assert relative == Path("main.tex")
    destination = tmp_path / "copy"
    stage_project(root, destination)
    assert (destination / "main.tex").is_file()
    assert not (destination / "main.aux").exists()


def test_bad_inputs_and_root(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="readable"):
        resolve_input(tmp_path / "missing.tex", None)
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    main = other / "main.tex"
    main.write_text("x")
    with pytest.raises(UsageError, match="outside"):
        resolve_input(main, root)


def test_escaping_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "secret.tex"
    outside.write_text("secret")
    (root / "escape.tex").symlink_to(outside)
    with pytest.raises(UsageError, match="escapes"):
        validate_symlinks(root)
