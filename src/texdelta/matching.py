"""Deterministic, explainable matching of logical figures."""

import re
from collections.abc import Iterable, Sequence
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Optional

from .models import Figure, FigureConfig, FigureMatch


def _words(value: str) -> str:
    value = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


def _caption_score(old: Figure, new: Figure) -> float:
    return SequenceMatcher(None, _words(old.caption), _words(new.caption)).ratio()


def _caption_jaccard(old: Figure, new: Figure) -> float:
    old_words = set(_words(old.caption).split())
    new_words = set(_words(new.caption).split())
    union = old_words | new_words
    return len(old_words & new_words) / len(union) if union else 0.0


def _basename_stems(figure: Figure) -> set[str]:
    return {Path(graphic.original).stem.lower() for graphic in figure.graphics}


def _selector(figure: Figure, selector: str) -> bool:
    if selector == figure.identifier or selector == f"label:{figure.label}":
        return True
    return any(
        selector in {graphic.original, Path(graphic.original).name} for graphic in figure.graphics
    )


def _unique_pair(
    old_pool: Sequence[Figure],
    new_pool: Sequence[Figure],
    predicate: Callable[[Figure, Figure], bool],
) -> list[tuple[Figure, Figure]]:
    candidates: dict[str, list[Figure]] = {
        old.identifier: [new for new in new_pool if predicate(old, new)] for old in old_pool
    }
    reverse: dict[str, list[Figure]] = {
        new.identifier: [old for old in old_pool if predicate(old, new)] for new in new_pool
    }
    return [
        (old, choices[0])
        for old in old_pool
        if len(choices := candidates[old.identifier]) == 1
        and len(reverse[choices[0].identifier]) == 1
    ]


def _figure_changed(old: Figure, new: Figure) -> bool:
    return sorted(g.digest for g in old.graphics) != sorted(g.digest for g in new.graphics)


def match_figures(
    old: Sequence[Figure], new: Sequence[Figure], config: FigureConfig
) -> list[FigureMatch]:
    old_pool = [f for f in old if not any(_selector(f, item) for item in config.exclude_old)]
    new_pool = [f for f in new if not any(_selector(f, item) for item in config.exclude_new)]
    used_old: set[str] = set()
    used_new: set[str] = set()
    matches: list[FigureMatch] = []

    def add(
        o: Figure,
        n: Figure,
        confidence: str,
        signals: Iterable[str],
        heading: Optional[str] = None,
        layout: Optional[str] = None,
    ) -> None:
        if o.identifier in used_old or n.identifier in used_new:
            return
        used_old.add(o.identifier)
        used_new.add(n.identifier)
        matches.append(
            FigureMatch(
                old=o,
                new=n,
                status="changed" if _figure_changed(o, n) else "unchanged",
                confidence=confidence,
                signals=list(signals),
                heading=heading,
                layout=layout,
            )
        )

    for override in config.pairs:
        old_hits = [f for f in old_pool if _selector(f, override.old)]
        new_hits = [f for f in new_pool if _selector(f, override.new)]
        if len(old_hits) == len(new_hits) == 1:
            add(
                old_hits[0],
                new_hits[0],
                "high",
                ["configuration override"],
                override.heading,
                override.layout,
            )

    def remaining() -> tuple[list[Figure], list[Figure]]:
        return (
            [f for f in old_pool if f.identifier not in used_old],
            [f for f in new_pool if f.identifier not in used_new],
        )

    old_left, new_left = remaining()
    for o, n in _unique_pair(
        old_left,
        new_left,
        lambda a, b: bool({g.digest for g in a.graphics} & {g.digest for g in b.graphics}),
    ):
        add(o, n, "high", ["unique referenced asset content hash"])

    old_left, new_left = remaining()
    for o, n in _unique_pair(old_left, new_left, lambda a, b: bool(a.label and a.label == b.label)):
        add(o, n, "high", ["unique LaTeX label"])

    old_left, new_left = remaining()
    for o, n in _unique_pair(
        old_left,
        new_left,
        lambda a, b: (
            bool(_basename_stems(a) & _basename_stems(b))
            and abs(a.ordinal - b.ordinal) <= 2
            and _caption_score(a, b) >= 0.10
        ),
    ):
        add(o, n, "medium", ["unique asset basename", "caption/order evidence"])

    old_left, new_left = remaining()
    for o, n in _unique_pair(
        old_left,
        new_left,
        lambda a, b: abs(a.ordinal - b.ordinal) <= 2 and _caption_jaccard(a, b) >= 0.65,
    ):
        add(o, n, "medium", ["mutual caption similarity", "nearby document order"])

    old_left, new_left = remaining()
    matches.extend(
        FigureMatch(f, None, "removed", "ambiguous", ["no confident match"]) for f in old_left
    )
    matches.extend(
        FigureMatch(None, f, "added", "ambiguous", ["no confident match"]) for f in new_left
    )

    rank = {"changed": 0, "added": 1, "removed": 2, "unchanged": 3}
    matches.sort(
        key=lambda item: (
            rank[item.status],
            (item.new.ordinal if item.new else item.old.ordinal if item.old else 0),
        )
    )
    return matches
