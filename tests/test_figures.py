import hashlib
from pathlib import Path

import pytest

from texdelta.errors import BuildError
from texdelta.figures import parse_figures, replace_graphics


def test_parse_and_rewrite(tmp_path: Path) -> None:
    first = tmp_path / "a.png"
    second = tmp_path / "b.png"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    text = r"""
\includegraphics{logo.png}
\begin{figure}\includegraphics[width=2cm]{a.png}\caption{Nested {caption}.}\label{fig:a}\end{figure}
\begin{wrapfigure}{r}{2cm}\includegraphics{b.png}\end{wrapfigure}
"""
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"logo")
    figures, graphics = parse_figures(text, "old", [logo, first, second], ["figure", "wrapfigure"])
    assert [item.identifier for item in figures] == ["fig:a", "wrapfigure@2"]
    assert figures[0].caption == "Nested {caption}."
    assert graphics[1].digest == hashlib.sha256(b"a").hexdigest()
    for index, graphic in enumerate(graphics):
        graphic.output_path = f"support/{index}.png"
    rewritten = replace_graphics(text, graphics)
    assert "support/1.png" in rewritten


def test_graphic_count_errors(tmp_path: Path) -> None:
    text = r"\includegraphics{x.png}"
    with pytest.raises(BuildError, match="resolved 0"):
        parse_figures(text, "old", [], ["figure"])
    with pytest.raises(BuildError, match="parser and resolver"):
        replace_graphics(text, [])
