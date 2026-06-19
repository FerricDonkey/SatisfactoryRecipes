import dataclasses
import fractions as fr

from PySide6 import QtWidgets
from pytestqt.qtbot import QtBot

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes.gui.dialogs import ItemSearchDialog, RecipeSearchDialog
from tests import support


def test_item_search_filters_and_returns_exact_amount(qtbot: QtBot) -> None:
    iron_plate = support.make_fake_item("Iron Plate")
    iron_rod = support.make_fake_item("Iron Rod")
    copper_sheet = support.make_fake_item("Copper Sheet")
    dialog = ItemSearchDialog(
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


def test_recipe_search_updates_preview_and_returns_selection(qtbot: QtBot) -> None:
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
    dialog = RecipeSearchDialog(
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
