import platform

import pytest

import texdelta.toolchain as toolchain
from texdelta.errors import ToolchainError


def test_missing_toolchain_strict_and_non_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(toolchain.shutil, "which", lambda _name: None)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    with pytest.raises(ToolchainError, match="TeX Live"):
        toolchain.inspect_toolchain()
    assert toolchain.inspect_toolchain(strict=False) == {}
    assert "FAILED" in toolchain.doctor_text()


def test_capabilities_and_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(toolchain.shutil, "which", lambda name: f"/bin/{name}")

    def output(args: list[str]) -> str:
        if args[-1] == "--version":
            return f"{args[0]} version\nextra"
        if "latexpand" in args[0]:
            return "--expand-bbl --show-graphics --fatal"
        return "--graphics-markup --math-markup"

    monkeypatch.setattr(toolchain, "_output", output)
    found = toolchain.inspect_toolchain()
    assert found["perl"].version.endswith("version")
    assert "doctor: OK" in toolchain.doctor_text()


@pytest.mark.parametrize(
    "name,flag", [("latexpand", "--expand-bbl"), ("latexdiff", "--math-markup")]
)
def test_missing_capability(monkeypatch: pytest.MonkeyPatch, name: str, flag: str) -> None:
    monkeypatch.setattr(toolchain.shutil, "which", lambda item: f"/bin/{item}")

    def output(args: list[str]) -> str:
        if args[-1] == "--version":
            return "version"
        if "latexpand" in args[0]:
            value = "--expand-bbl --show-graphics --fatal"
        else:
            value = "--graphics-markup --math-markup"
        return value.replace(flag, "") if name in args[0] else value

    monkeypatch.setattr(toolchain, "_output", output)
    with pytest.raises(ToolchainError, match=flag):
        toolchain.inspect_toolchain()
