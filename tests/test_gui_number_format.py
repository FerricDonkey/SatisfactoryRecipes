import fractions as fr

from satisfactory_recipes.gui import number_format


def test_decimal_groups_thousands_without_converting_to_float() -> None:
    assert number_format.decimal(fr.Fraction(3_700_000, 3)) == "1_233_333.333"


def test_mixed_number_preserves_exact_positive_and_negative_values() -> None:
    assert number_format.mixed_number(fr.Fraction(67, 3)) == "22 + 1/3"
    assert number_format.mixed_number(fr.Fraction(-67, 3)) == "-22 - 1/3"
    assert number_format.mixed_number(fr.Fraction(1, 3)) == "1/3"
    assert number_format.mixed_number(fr.Fraction(6, 3)) == "2"


def test_exact_tooltip_includes_units_and_action_hint() -> None:
    assert (
        number_format.exact_tooltip(
            fr.Fraction(67, 3),
            unit="MW",
            hint="Helpful action",
        )
        == "Exact: 22 + 1/3 MW\nHelpful action"
    )
