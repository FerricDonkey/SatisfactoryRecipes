import fractions as fr

import pytest
from PySide6 import QtWidgets
from pytestqt.qtbot import QtBot

from satisfactory_recipes.gui import dialog_components


def test_searchable_selection_filters_selects_and_emits_activation(
    qtbot: QtBot,
) -> None:
    iron_plate = object()
    iron_rod = object()
    copper_sheet = object()
    selector = dialog_components.SearchableSelectionList(
        options=[
            ("Iron Plate", iron_plate),
            ("Iron Rod", iron_rod),
            ("Copper Sheet", copper_sheet),
        ],
        search_placeholder="Search items",
    )
    qtbot.addWidget(selector)

    assert selector.search_edit.placeholderText() == "Search items"
    assert selector.selected_object is copper_sheet

    selections: list[object | None] = []
    selector.selection_changed.connect(selections.append)
    selector.search_edit.setText("rod")

    assert selector.list_widget.count() == 1
    assert selector.list_widget.item(0).text() == "Iron Rod"
    assert selector.selected_object is iron_rod
    assert selections[-1] is iron_rod

    activated: list[object] = []
    selector.selection_activated.connect(activated.append)
    selector.list_widget.itemDoubleClicked.emit(selector.list_widget.item(0))
    assert activated == [iron_rod]


def test_positive_fraction_input_returns_an_exact_value(qtbot: QtBot) -> None:
    fraction_input = dialog_components.PositiveFractionInput(
        label="Per minute",
        initial_text="7/3",
    )
    qtbot.addWidget(fraction_input)

    assert fraction_input.value == fr.Fraction(7, 3)


@pytest.mark.parametrize("text", ["", "nonsense", "0", "-2", "1/0"])
def test_positive_fraction_input_rejects_invalid_values(
    qtbot: QtBot,
    text: str,
) -> None:
    fraction_input = dialog_components.PositiveFractionInput(
        label="Per minute",
        initial_text=text,
    )
    qtbot.addWidget(fraction_input)

    with pytest.raises(ValueError, match="positive number or fraction"):
        _value = fraction_input.value


def test_positive_fraction_input_uses_one_validation_message(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fraction_input = dialog_components.PositiveFractionInput(
        label="Per minute",
        initial_text="bad",
    )
    qtbot.addWidget(fraction_input)
    warnings: list[tuple[str, str]] = []

    def record_warning(
        _parent: QtWidgets.QWidget,
        title: str,
        message: str,
    ) -> QtWidgets.QMessageBox.StandardButton:
        warnings.append((title, message))
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", record_warning)

    assert fraction_input.value_or_warn() is None
    assert warnings == [
        (
            dialog_components.PositiveFractionInput.validation_title,
            dialog_components.PositiveFractionInput.validation_message,
        )
    ]
