"""Parse figure-like environments and normalize their referenced graphics."""

import hashlib
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from .errors import BuildError
from .models import Figure, Graphic

GRAPHICS_RE = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}")


def _braced_argument(text: str, command: str) -> str:
    found = re.search(r"\\" + re.escape(command) + r"\s*\{", text)
    if not found:
        return ""
    start = found.end()
    depth = 1
    index = start
    while index < len(text) and depth:
        if text[index] == "{" and (index == 0 or text[index - 1] != "\\"):
            depth += 1
        elif text[index] == "}" and (index == 0 or text[index - 1] != "\\"):
            depth -= 1
        index += 1
    return text[start : index - 1] if depth == 0 else ""


def _environment_blocks(text: str, environments: Iterable[str]) -> list[tuple[int, str, str]]:
    names = "|".join(re.escape(name) for name in sorted(environments, key=len, reverse=True))
    pattern = re.compile(
        rf"\\begin\{{(?P<env>{names})\}}(?:\[[^\]]*\])?.*?\\end\{{(?P=env)\}}",
        re.DOTALL,
    )
    return [(match.start(), match.group("env"), match.group(0)) for match in pattern.finditer(text)]


def parse_figures(
    text: str,
    side: str,
    resolved_paths: Sequence[Path],
    environments: Iterable[str],
) -> tuple[list[Figure], list[Graphic]]:
    all_graphics = list(GRAPHICS_RE.finditer(text))
    if len(all_graphics) != len(resolved_paths):
        raise BuildError(
            f"{side}: latexpand resolved {len(resolved_paths)} graphics but "
            f"{len(all_graphics)} includegraphics commands were found"
        )
    global_graphics: list[Graphic] = []
    by_start: dict[int, tuple[re.Match[str], Graphic]] = {}
    for match, source in zip(all_graphics, resolved_paths):
        if not source.is_file():
            raise BuildError(f"{side}: referenced graphic does not exist: {source}")
        graphic = Graphic(
            source=source,
            original=match.group(1),
            digest=hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        global_graphics.append(graphic)
        by_start[match.start()] = (match, graphic)
    figures: list[Figure] = []
    for ordinal, (start, environment, block) in enumerate(
        _environment_blocks(text, environments), 1
    ):
        end = start + len(block)
        graphics: list[Graphic] = []
        for position, (_match, graphic) in by_start.items():
            if start <= position < end:
                graphics.append(graphic)
        if not graphics:
            continue
        label_match = re.search(r"\\label\s*\{([^{}]+)\}", block)
        figures.append(
            Figure(
                side=side,
                ordinal=ordinal,
                environment=environment,
                label=label_match.group(1).strip() if label_match else None,
                caption=_braced_argument(block, "caption").strip(),
                graphics=graphics,
            )
        )
    return figures, global_graphics


def replace_graphics(text: str, graphics: Sequence[Graphic]) -> str:
    matches = list(GRAPHICS_RE.finditer(text))
    if len(matches) != len(graphics):
        raise BuildError("Cannot rewrite graphics: parser and resolver counts differ")
    pieces: list[str] = []
    cursor = 0
    for match, graphic in zip(matches, graphics):
        pieces.append(text[cursor : match.start(1)])
        pieces.append(graphic.output_path)
        cursor = match.end(1)
    pieces.append(text[cursor:])
    return "".join(pieces)


def all_graphics(figures: Sequence[Figure]) -> list[Graphic]:
    return [graphic for figure in figures for graphic in figure.graphics]
