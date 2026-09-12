from pathlib import Path

import pytest

from texdelta.appendix import generate_appendix, inject_appendix
from texdelta.models import Figure, FigureConfig, FigureMatch, Graphic


def item(side: str, label: str, digest: str, path: str) -> Figure:
    graphic = Graphic(Path(path), path, digest, f"support/assets/{path}")
    return Figure(side, 1, "figure", label, r"Caption with 50\% and $x$.", [graphic])


def test_appendix_changed_added_and_empty() -> None:
    old = item("old", "fig:x", "old", "old.png")
    new = item("new", "fig:x", "new", "new.png")
    added = item("new", "fig:y", "added", "added.png")
    matches = [
        FigureMatch(old, new, "changed", "high", ["label"]),
        FigureMatch(None, added, "added", "ambiguous", ["none"]),
    ]
    appendix = generate_appendix(matches, FigureConfig())
    assert "FIGURE COMPARISON" in appendix
    assert "OLD" in appendix and "ADDED" in appendix
    assert r"50\%" in appendix
    assert generate_appendix([FigureMatch(old, old, "unchanged", "high", [])], FigureConfig()) == ""


def test_inject_appendix() -> None:
    result = inject_appendix(r"x\end{document}", "APPENDIX")
    assert result.index("APPENDIX") < result.index(r"\end{document}")
    with pytest.raises(ValueError, match="end"):
        inject_appendix("x", "APPENDIX")
