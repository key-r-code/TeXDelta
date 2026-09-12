"""Generate the accessible visual comparison appendix."""

import re
from collections.abc import Sequence
from importlib import resources
from pathlib import Path

from .models import Figure, FigureConfig, FigureMatch, Graphic


def _plain_caption(value: str, words: int) -> str:
    value = re.sub(r"\$.*?\$", "[math]", value)
    value = re.sub(r"\\([%_&#])", r"\1", value)
    value = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", "", value)
    value = value.replace("{", "").replace("}", "")
    value = " ".join(value.split())
    selected = value.split()[:words]
    suffix = "..." if len(value.split()) > words else ""
    return " ".join(selected) + suffix


def _escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _heading(match: FigureMatch, config: FigureConfig) -> str:
    if match.heading:
        return _escape(match.heading)
    figure = match.new or match.old
    assert figure is not None
    label = _escape(figure.identifier)
    caption = _escape(_plain_caption(figure.caption, config.caption_words))
    return f"{label} -- {caption}" if caption else label


def _pair_graphics(
    old: Figure, new: Figure
) -> tuple[list[tuple[Graphic, Graphic]], list[Graphic], list[Graphic]]:
    pairs: list[tuple[Graphic, Graphic]] = []
    old_left = list(old.graphics)
    new_left = list(new.graphics)
    for predicate in (
        lambda a, b: a.digest == b.digest,
        lambda a, b: Path(a.original).stem.lower() == Path(b.original).stem.lower(),
    ):
        for old_graphic in list(old_left):
            candidates = [
                new_graphic for new_graphic in new_left if predicate(old_graphic, new_graphic)
            ]
            if len(candidates) == 1:
                new_graphic = candidates[0]
                pairs.append((old_graphic, new_graphic))
                old_left.remove(old_graphic)
                new_left.remove(new_graphic)
    while old_left and new_left:
        pairs.append((old_left.pop(0), new_left.pop(0)))
    return pairs, old_left, new_left


def _single(status: str, graphic: Graphic) -> str:
    color = "blue" if status == "ADDED" else "red"
    return (
        rf"{{\color{{{color}}}\bfseries {status}}}\par\vspace{{2pt}}"
        "\n"
        rf"\fcolorbox{{{color}}}{{white}}{{\includegraphics[width=.88\linewidth,height=.55\textheight,keepaspectratio]{{{graphic.output_path}}}}}\par"
    )


def _paired(old: Graphic, new: Graphic, layout: str) -> str:
    old_box = rf"\fcolorbox{{red}}{{white}}{{\includegraphics[width=.92\linewidth,height=.38\textheight,keepaspectratio]{{{old.output_path}}}}}"
    new_box = rf"\fcolorbox{{blue}}{{white}}{{\includegraphics[width=.92\linewidth,height=.38\textheight,keepaspectratio]{{{new.output_path}}}}}"
    columns = (
        r"\begin{minipage}[t]{.48\linewidth}{\color{red}\bfseries OLD}\par\vspace{2pt}"
        + old_box
        + r"\end{minipage}\hfill"
        + r"\begin{minipage}[t]{.48\linewidth}{\color{blue}\bfseries NEW}\par\vspace{2pt}"
        + new_box
        + r"\end{minipage}"
    )
    stacked = (
        r"{\color{red}\bfseries OLD}\par\vspace{2pt}"
        + old_box
        + r"\par\vspace{8pt}{\color{blue}\bfseries NEW}\par\vspace{2pt}"
        + new_box
    )
    if layout == "columns":
        return columns
    if layout == "stacked":
        return stacked
    return (
        r"\sbox0{\includegraphics[width=.44\linewidth,height=.38\textheight,keepaspectratio]{"
        + old.output_path
        + r"}}\sbox2{\includegraphics[width=.44\linewidth,height=.38\textheight,keepaspectratio]{"
        + new.output_path
        + r"}}\ifdim\ht0>.22\textheight\ifdim\ht2>.22\textheight "
        + columns
        + r"\else "
        + stacked
        + r"\fi\else "
        + stacked
        + r"\fi"
    )


def generate_appendix(matches: Sequence[FigureMatch], config: FigureConfig) -> str:
    visible = [match for match in matches if match.status != "unchanged"]
    if not visible:
        return ""
    entries: list[str] = []
    for match in visible:
        heading = r"{\large\bfseries " + _heading(match, config) + r"}\par\vspace{4pt}"
        if match.old and match.new:
            pairs, removed, added = _pair_graphics(match.old, match.new)
            for old_graphic, new_graphic in pairs:
                if old_graphic.digest != new_graphic.digest:
                    entries.append(
                        heading
                        + _paired(old_graphic, new_graphic, match.layout or config.layout)
                        + r"\par\clearpage"
                    )
            entries.extend(heading + _single("REMOVED", item) + r"\clearpage" for item in removed)
            entries.extend(heading + _single("ADDED", item) + r"\clearpage" for item in added)
        elif match.new:
            entries.extend(
                heading + _single("ADDED", item) + r"\clearpage" for item in match.new.graphics
            )
        elif match.old:
            entries.extend(
                heading + _single("REMOVED", item) + r"\clearpage" for item in match.old.graphics
            )
    template = resources.files("texdelta").joinpath("templates/figure_appendix.tex").read_text()
    return template.replace("% TEXDELTA_ENTRIES", "\n".join(entries))


def inject_appendix(diff_text: str, appendix: str) -> str:
    if not appendix:
        return diff_text
    position = diff_text.rfind(r"\end{document}")
    if position < 0:
        raise ValueError("Generated diff has no \\end{document}")
    return diff_text[:position] + appendix + "\n" + diff_text[position:]
