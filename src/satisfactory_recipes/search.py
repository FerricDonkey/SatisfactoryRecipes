"""Search and ranking helpers shared by CLI and GUI selection flows."""

import collections.abc as cabc


def match_score(target: str, key: str) -> int:
    """Score how much key matches target. Higher is better."""

    def mini_score(targ: str, k: str) -> int:
        score = 0
        for c1, c2 in zip(targ, k):
            if c1.lower() != c2.lower():
                break
            score += 1
        return score

    scores: list[int] = []
    while target:
        scores.append(mini_score(target, key))
        target = " ".join(target.split()[1:])
    return max(scores)


def _sort_key(option: str, entry: str) -> tuple[bool, bool, int, str]:
    return (
        not (option.lower() == entry.lower()),
        not option.lower().startswith(entry.lower()),
        -match_score(option, entry),
        option,
    )


def sort_options(options: cabc.Iterable[str], entry: str) -> list[str]:
    """Sort options by how well they match entry."""
    return [
        option
        for option in sorted(options, key=lambda option: _sort_key(option, entry))
        if match_score(option, entry)
    ]


def sort_objects[T](
    options: cabc.Iterable[T],
    entry: str,
    *,
    label: cabc.Callable[[T], str],
) -> list[T]:
    """Sort arbitrary objects using their display labels without losing identity."""
    return [
        option
        for option in sorted(
            options,
            key=lambda option: _sort_key(label(option), entry),
        )
        if match_score(label(option), entry)
    ]
