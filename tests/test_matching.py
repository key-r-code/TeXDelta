from pathlib import Path

from texdelta.matching import match_figures
from texdelta.models import Figure, FigureConfig, Graphic, PairOverride


def graphic(name: str, digest: str) -> Graphic:
    return Graphic(Path(name), name, digest, f"support/{name}")


def figure(side: str, ordinal: int, label: str, caption: str, name: str, digest: str) -> Figure:
    return Figure(side, ordinal, "figure", label, caption, [graphic(name, digest)])


def test_matching_priority_and_one_sided() -> None:
    old = [
        figure("old", 1, "old-label", "Same graphic", "before.png", "same"),
        figure("old", 2, "fig:changed", "Changed chart", "chart.png", "old"),
        figure("old", 3, "fig:removed", "Removed result", "removed.png", "gone"),
    ]
    new = [
        figure("new", 1, "new-label", "Renamed graphic", "after.png", "same"),
        figure("new", 2, "fig:changed", "Changed chart revised", "chart.png", "new"),
        figure("new", 3, "fig:added", "Added result", "added.png", "added"),
    ]
    matches = match_figures(old, new, FigureConfig())
    assert [item.status for item in matches] == ["changed", "added", "removed", "unchanged"]
    assert matches[-1].signals == ["unique referenced asset content hash"]


def test_override_and_exclusion() -> None:
    old = [figure("old", 1, "a", "Alpha", "a.png", "1")]
    new = [figure("new", 9, "b", "Beta", "b.png", "2")]
    config = FigureConfig(pairs=[PairOverride("a", "b", "Manual", "columns")])
    match = match_figures(old, new, config)[0]
    assert match.heading == "Manual"
    assert match.layout == "columns"
    assert match.confidence == "high"
    config.exclude_old = ["a"]
    assert match_figures(old, new, config)[0].status == "added"
