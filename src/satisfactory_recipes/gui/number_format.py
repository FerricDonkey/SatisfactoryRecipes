"""Consistent readable and exact formatting for GUI fraction values."""

from __future__ import annotations

import fractions as fr


def decimal(value: fr.Fraction, *, precision: int = 3, unit: str = "") -> str:
    """Format an exact fraction as a grouped, rounded decimal for display."""
    display = f"{value:_.{precision}f}"
    return f"{display} {unit}" if unit else display


def mixed_number(value: fr.Fraction) -> str:
    """Format an exact fraction as an integer, fraction, or mixed number."""
    numerator = abs(value.numerator)
    whole, remainder = divmod(numerator, value.denominator)
    sign = "-" if value < 0 else ""
    if remainder == 0:
        return f"{sign}{whole:_}"
    fraction = f"{remainder}/{value.denominator}"
    if whole == 0:
        return f"{sign}{fraction}"
    separator = " - " if value < 0 else " + "
    return f"{sign}{whole:_}{separator}{fraction}"


def exact_tooltip(
    value: fr.Fraction,
    *,
    unit: str = "",
    hint: str = "",
) -> str:
    """Build tooltip text containing an exact mixed-number value and optional hint."""
    exact = mixed_number(value)
    lines = [f"Exact: {exact} {unit}".rstrip()]
    if hint:
        lines.append(hint)
    return "\n".join(lines)
