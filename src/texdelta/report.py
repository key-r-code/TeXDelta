"""Versioned, privacy-preserving report serialization."""

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .models import Config, FigureMatch
from .toolchain import ToolInfo

PRIVATE_PATH_RE = re.compile(r"(?:/Users|/home|/private/tmp|/tmp)/[^\s:]+")


def _redact(value: str) -> str:
    return PRIVATE_PATH_RE.sub("<redacted-path>", value)


def _figure(match: FigureMatch) -> dict[str, Any]:
    def side(value: Any) -> Optional[dict[str, Any]]:
        if value is None:
            return None
        return {
            "id": value.identifier,
            "ordinal": value.ordinal,
            "environment": value.environment,
            "label": value.label,
            "caption_excerpt": " ".join(value.caption.split())[:240],
            "graphics": [
                {
                    "path": (
                        f"<project>/{Path(graphic.original).name}"
                        if Path(graphic.original).is_absolute()
                        else graphic.original
                    ),
                    "sha256": graphic.digest,
                    "output": graphic.output_path,
                }
                for graphic in value.graphics
            ],
        }

    return {
        "status": match.status,
        "confidence": match.confidence,
        "signals": match.signals,
        "old": side(match.old),
        "new": side(match.new),
    }


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(
    path: Path,
    status: str,
    fingerprint: str,
    tools: dict[str, ToolInfo],
    config: Config,
    matches: Sequence[FigureMatch],
    diagnostics: Sequence[str],
    fallbacks: Sequence[str],
    outputs: dict[str, str],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "texdelta_version": __version__,
        "fingerprint": fingerprint,
        "toolchain": {
            name: {"name": name, "version": info.version} for name, info in tools.items()
        },
        "config": config.as_dict(),
        "stages": [
            {"name": "toolchain", "status": "success"},
            {"name": "workspace", "status": "success"},
            {"name": "document-preparation", "status": "success"},
            {"name": "figure-matching", "status": "success"},
            {"name": "latexdiff", "status": "success"},
            {"name": "pdf-compilation", "status": "success"},
            {"name": "output-promotion", "status": "success"},
        ],
        "figures": [_figure(match) for match in matches],
        "diagnostics": [_redact(item) for item in diagnostics],
        "fallbacks": list(fallbacks),
        "outputs": outputs,
    }
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def read_report(path: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("schema_version") == 1 else None
