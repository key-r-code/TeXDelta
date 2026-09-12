from pathlib import Path

import pytest

import texdelta.cli as cli
from texdelta.errors import ToolchainError


def test_doctor_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "doctor_text", lambda: "TeXDelta doctor: OK\n- pdfLaTeX")
    assert cli.main(["doctor"]) == 0
    monkeypatch.setattr(cli, "doctor_text", lambda: "TeXDelta doctor: FAILED\nmissing")
    assert cli.main(["doctor"]) == 3
    assert "FAILED" in capsys.readouterr().out


def test_diff_options_and_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, object] = {}

    def fake_build(*args: object) -> dict[str, object]:
        captured["args"] = args
        config = args[3]
        captured["config"] = config
        return {"status": "success", "figures": [{"status": "changed"}]}

    monkeypatch.setattr(cli, "build_diff", fake_build)
    output = tmp_path / "output"
    result = cli.main(
        [
            "diff",
            "old.tex",
            "new.tex",
            "--output-dir",
            str(output),
            "--style",
            "font-strike",
            "--allow-shell-escape",
            "--strict-abstract",
            "--no-figures",
            "--force",
            "--rebuild",
            "--keep-workdir",
        ]
    )
    assert result == 0
    config = captured["config"]
    assert config.build.style == "font-strike"  # type: ignore[union-attr]
    assert config.build.shell_escape is True  # type: ignore[union-attr]
    assert config.build.strict_abstract is True  # type: ignore[union-attr]
    assert config.build.figures is False  # type: ignore[union-attr]
    assert "changed=1" in capsys.readouterr().out


def test_cli_errors_and_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli, "load_config", lambda _path: (_ for _ in ()).throw(ToolchainError("x"))
    )
    assert cli.main(["diff", "old.tex", "new.tex"]) == 3
    monkeypatch.setattr(
        cli, "load_config", lambda _path: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    assert cli.main(["diff", "old.tex", "new.tex"]) == 130


def test_init_overleaf_force(tmp_path: Path) -> None:
    destination = tmp_path / "project"
    cli._init_overleaf(destination, False)
    with pytest.raises(Exception, match="--force"):
        cli._init_overleaf(destination, False)
    (destination / "stale").write_text("old")
    assert cli.main(["init-overleaf", str(destination), "--force"]) == 0
    assert not (destination / "stale").exists()
    file_destination = tmp_path / "file"
    file_destination.write_text("old")
    cli._init_overleaf(file_destination, True)
    assert file_destination.is_dir()
