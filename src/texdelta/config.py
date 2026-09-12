"""Strict TOML configuration loading."""

import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised in the Python 3.9 CI job
    import tomli as tomllib

from .errors import UsageError
from .models import BuildConfig, Config, FigureConfig, PairOverride


def _unknown(data: Mapping[str, Any], allowed: Iterable[str], context: str) -> None:
    keys = sorted(set(data) - set(allowed))
    if keys:
        raise UsageError(f"Unknown {context} key(s): {', '.join(keys)}")


def load_config(path: Optional[Path]) -> Config:
    if path is None:
        candidate = Path.cwd() / "texdelta.toml"
        path = candidate if candidate.is_file() else None
    if path is None:
        return Config()
    try:
        with path.open("rb") as stream:
            data: dict[str, Any] = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise UsageError(f"Cannot read configuration {path}: {exc}") from exc
    _unknown(data, {"schema_version", "build", "figures"}, "top-level")
    version = data.get("schema_version", 1)
    if version != 1:
        raise UsageError(f"Unsupported configuration schema_version: {version!r}")

    build_data = data.get("build", {})
    if not isinstance(build_data, dict):
        raise UsageError("[build] must be a table")
    _unknown(
        build_data,
        {"style", "abstract_diff", "strict_abstract", "shell_escape", "figures"},
        "build",
    )
    build = BuildConfig(**build_data)
    if build.style not in {"underline", "font-strike"}:
        raise UsageError("build.style must be 'underline' or 'font-strike'")

    figure_data = data.get("figures", {})
    if not isinstance(figure_data, dict):
        raise UsageError("[figures] must be a table")
    _unknown(
        figure_data,
        {"environments", "layout", "caption_words", "exclude_old", "exclude_new", "pairs"},
        "figures",
    )
    pairs_data = figure_data.pop("pairs", [])
    if not isinstance(pairs_data, list):
        raise UsageError("figures.pairs must be an array of tables")
    pairs = []
    for item in pairs_data:
        if not isinstance(item, dict):
            raise UsageError("Each figures.pairs entry must be a table")
        _unknown(item, {"old", "new", "heading", "layout"}, "figure pair")
        try:
            pairs.append(PairOverride(**item))
        except TypeError as exc:
            raise UsageError(f"Invalid figure pair: {exc}") from exc
    figures = FigureConfig(**figure_data, pairs=pairs)
    if figures.layout not in {"auto", "columns", "stacked"}:
        raise UsageError("figures.layout must be auto, columns, or stacked")
    if not figures.environments:
        raise UsageError("figures.environments cannot be empty")
    return Config(schema_version=1, build=build, figures=figures)
