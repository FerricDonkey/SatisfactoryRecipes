import dataclasses
import fractions as fr

import pytest
from PySide6 import QtWidgets
import pytestqt.qtbot

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes.gui import dialogs
from tests import support


def test_item_search_filters_and_returns_exact_amount(
    qtbot: pytestqt.qtbot.QtBot,
) -> None:
    iron_plate = support.make_fake_item("Iron Plate")
    iron_rod = support.make_fake_item("Iron Rod")
    copper_sheet = support.make_fake_item("Copper Sheet")
    dialog = dialogs.ItemSearchDialog(
        items=[iron_plate, iron_rod, copper_sheet],
        title="Choose Item",
        show_amount=True,
    )
    qtbot.addWidget(dialog)

    dialog.search_edit.setText("plate")

    assert dialog.item_list.count() == 1
    assert dialog.item_list.item(0).text() == "Iron Plate"
    assert dialog.amount_edit is not None
    dialog.amount_edit.setText("1/3")
    buttons = dialog.findChild(QtWidgets.QDialogButtonBox)
    assert buttons is not None
    ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    assert ok_button is not None
    ok_button.click()

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.selected_item == iron_plate
    assert dialog.selected_amount_per_min == fr.Fraction(1, 3)


def test_recipe_search_updates_preview_and_returns_selection(
    qtbot: pytestqt.qtbot.QtBot,
) -> None:
    ore = support.make_fake_item("Iron Ore")
    ingot = support.make_fake_item("Iron Ingot")
    smelter = ic.Building(
        class_name="Build_Smelter_C",
        name="Smelter",
        category="manufacturing",
        power_draw=fr.Fraction(4),
    )
    recipe = dataclasses.replace(
        support.make_fake_recipe(
            class_name="Recipe_Ingot_C",
            name="Iron Ingot",
            inputs={ore: fr.Fraction(1)},
            products={ingot: fr.Fraction(1)},
        ),
        produced_in=smelter,
    )
    dialog = dialogs.RecipeSearchDialog(
        recipes=[recipe],
        title="Choose Recipe",
        show_amount=True,
    )
    qtbot.addWidget(dialog)

    assert "Iron Ingot" in dialog.details.toPlainText()
    assert "Smelter" in dialog.details.toPlainText()
    assert dialog.amount_edit is not None
    dialog.amount_edit.setText("7/3")
    buttons = dialog.findChild(QtWidgets.QDialogButtonBox)
    assert buttons is not None
    ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    assert ok_button is not None
    ok_button.click()

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.selected_recipe == recipe
    assert dialog.selected_amount_per_min == fr.Fraction(7, 3)


def test_item_search_double_click_accepts_current_item(
    qtbot: pytestqt.qtbot.QtBot,
) -> None:
    iron_plate = support.make_fake_item("Iron Plate")
    dialog = dialogs.ItemSearchDialog(items=[iron_plate], title="Choose Item")
    qtbot.addWidget(dialog)

    dialog.item_list.itemDoubleClicked.emit(dialog.item_list.item(0))

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.selected_item is iron_plate


def test_invalid_amount_keeps_search_dialog_open(
    qtbot: pytestqt.qtbot.QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    iron_plate = support.make_fake_item("Iron Plate")
    dialog = dialogs.ItemSearchDialog(
        items=[iron_plate],
        title="Choose Item",
        show_amount=True,
    )
    qtbot.addWidget(dialog)
    assert dialog.amount_edit is not None
    dialog.amount_edit.setText("0")
    warnings: list[tuple[str, str]] = []

    def record_warning(
        _parent: QtWidgets.QWidget,
        title: str,
        message: str,
    ) -> QtWidgets.QMessageBox.StandardButton:
        warnings.append((title, message))
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", record_warning)
    dialog.ok_button.click()

    assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.selected_item is None
    assert warnings == [("Invalid Amount", "Enter a positive number or fraction.")]


def test_positive_fraction_dialog_accepts_exact_fraction(
    qtbot: pytestqt.qtbot.QtBot,
) -> None:
    dialog = dialogs.PositiveFractionDialog(title="Scale Chain", label="Per minute")
    qtbot.addWidget(dialog)
    dialog.fraction_input.line_edit.setText("11/7")
    buttons = dialog.findChild(QtWidgets.QDialogButtonBox)
    assert buttons is not None
    ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    assert ok_button is not None

    ok_button.click()

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.selected_fraction == fr.Fraction(11, 7)
