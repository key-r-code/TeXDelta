"""External TeX tool discovery and capability checks."""

import platform
import shutil
import subprocess
from dataclasses import dataclass

from .errors import ToolchainError


@dataclass(frozen=True)
class ToolInfo:
    name: str
    path: str
    version: str


REQUIRED = ("pdflatex", "bibtex", "latexpand", "latexdiff", "perl")


def _output(args: list[str]) -> str:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    return (result.stdout + result.stderr).strip()


def inspect_toolchain(strict: bool = True) -> dict[str, ToolInfo]:
    missing = [name for name in REQUIRED if shutil.which(name) is None]
    if missing and strict:
        system = platform.system()
        hint = "Install TeX Live" if system == "Linux" else "Install MacTeX"
        raise ToolchainError(f"Missing required tool(s): {', '.join(missing)}. {hint} and retry.")
    found: dict[str, ToolInfo] = {}
    for name in REQUIRED:
        path = shutil.which(name)
        if path is None:
            continue
        raw = _output([path, "--version"])
        first = raw.splitlines()[0] if raw else "version unavailable"
        found[name] = ToolInfo(name, path, first[:200])
    if "latexpand" in found:
        help_text = _output([found["latexpand"].path, "--help"])
        absent = [
            flag for flag in ("--expand-bbl", "--show-graphics", "--fatal") if flag not in help_text
        ]
        if absent and strict:
            raise ToolchainError(f"latexpand lacks required capability: {', '.join(absent)}")
    if "latexdiff" in found:
        help_text = _output([found["latexdiff"].path, "--help"])
        absent = [flag for flag in ("--graphics-markup", "--math-markup") if flag not in help_text]
        if absent and strict:
            raise ToolchainError(f"latexdiff lacks required capability: {', '.join(absent)}")
    return found


def doctor_text() -> str:
    try:
        tools = inspect_toolchain(strict=True)
    except ToolchainError as exc:
        return f"TeXDelta doctor: FAILED\n{exc}"
    rows = ["TeXDelta doctor: OK"]
    rows.extend(f"- {name}: {info.version}" for name, info in sorted(tools.items()))
    return "\n".join(rows)
