"""Internal typed models. Only the serialized configuration/report are public."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class BuildConfig:
    style: str = "underline"
    abstract_diff: bool = True
    strict_abstract: bool = False
    shell_escape: bool = False
    figures: bool = True


@dataclass
class PairOverride:
    old: str
    new: str
    heading: Optional[str] = None
    layout: Optional[str] = None


@dataclass
class FigureConfig:
    environments: list[str] = field(default_factory=lambda: ["figure", "figure*", "wrapfigure"])
    layout: str = "auto"
    caption_words: int = 24
    exclude_old: list[str] = field(default_factory=list)
    exclude_new: list[str] = field(default_factory=list)
    pairs: list[PairOverride] = field(default_factory=list)


@dataclass
class Config:
    schema_version: int = 1
    build: BuildConfig = field(default_factory=BuildConfig)
    figures: FigureConfig = field(default_factory=FigureConfig)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Graphic:
    source: Path
    original: str
    digest: str
    output_path: str = ""


@dataclass
class Figure:
    side: str
    ordinal: int
    environment: str
    label: Optional[str]
    caption: str
    graphics: list[Graphic]

    @property
    def identifier(self) -> str:
        return self.label or f"{self.environment}@{self.ordinal}"


@dataclass
class FigureMatch:
    old: Optional[Figure]
    new: Optional[Figure]
    status: str
    confidence: str
    signals: list[str]
    heading: Optional[str] = None
    layout: Optional[str] = None


@dataclass
class PreparedDocument:
    side: str
    root: Path
    main: Path
    raw_flat: str
    abstract_flat: str
    graphics: list[Graphic]
    figures: list[Figure]
    local_dependencies: list[Path]
    diagnostics: list[str]
