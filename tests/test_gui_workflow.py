import dataclasses
import fractions as fr
import pathlib

import pytest
from PySide6 import QtWidgets
import pytestqt.qtbot

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import interactive_mode as im
from satisfactory_recipes.gui import dialogs
from satisfactory_recipes.gui import main_window
from tests import support


def test_create_scale_save_and_reopen_complete_chain(
    qtbot: pytestqt.qtbot.QtBot,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    ore = support.make_fake_item("Ore")
    ingot = support.make_fake_item("Iron Ingot")
    plate = support.make_fake_item("Iron Plate")
    constructor = ic.Building(
        class_name="Build_Constructor_C",
        name="Constructor",
        category="manufacturing",
        power_draw=fr.Fraction(4),
    )
    ingot_recipe = dataclasses.replace(
        support.make_fake_recipe(
            class_name="Recipe_Ingot_C",
            name="Iron Ingot",
            inputs={ore: fr.Fraction(2)},
            products={ingot: fr.Fraction(1)},
        ),
        produced_in=constructor,
    )
    plate_recipe = dataclasses.replace(
        support.make_fake_recipe(
            class_name="Recipe_Plate_C",
            name="Iron Plate",
            inputs={ingot: fr.Fraction(2)},
            products={plate: fr.Fraction(1)},
        ),
        produced_in=constructor,
    )

    def fresh_game_data() -> ic.GameData:
        return support.make_fake_game_data(
            items=[ore, ingot, plate],
            recipes=[ingot_recipe, plate_recipe],
        )

    game_data = fresh_game_data()
    game_data.scale_recipes(fr.Fraction(1, 2))
    scaled_ingot_recipe = game_data.recipes_d[ingot_recipe.class_name]
    scaled_plate_recipe = game_data.recipes_d[plate_recipe.class_name]
    window = main_window.MainWindow(
        docs_path=pathlib.Path("fake-en-us.json"),
        game_data=game_data,
        user_config=sr_config.Configuration(),
    )

    def prepare_for_test_cleanup(widget: QtWidgets.QWidget) -> None:
        assert isinstance(widget, main_window.MainWindow)
        widget.has_unsaved_changes = False

    qtbot.addWidget(window, before_close_func=prepare_for_test_cleanup)
    window.show()

    def choose_goal(*_args: object, **_kwargs: object) -> ic.Item:
        return plate

    def choose_goal_recipe(
        *_args: object,
        **_kwargs: object,
    ) -> dialogs.RecipeSelection:
        return dialogs.RecipeSelection(
            recipe=scaled_plate_recipe,
            amount_per_min=fr.Fraction(3),
        )

    def choose_shortage_recipe(
        *_args: object,
        **_kwargs: object,
    ) -> ic.Recipe:
        return scaled_ingot_recipe

    monkeypatch.setattr(dialogs, "choose_goal_item", choose_goal)
    monkeypatch.setattr(
        dialogs,
        "choose_recipe_with_amount",
        choose_goal_recipe,
    )
    monkeypatch.setattr(dialogs, "choose_recipe", choose_shortage_recipe)

    window.new_chain()
    window.add_shortage_recipe(ingot)

    output_rate = window.chain_details.outputs_table.item(0, 1)
    assert output_rate is not None
    output_rate.setText("7/2")

    assert window.production_chain is not None
    counts_before_save = {
        recipe.class_name: count
        for recipe, count in window.production_chain.recipes.items()
    }
    assert counts_before_save == {
        plate_recipe.class_name: fr.Fraction(7, 2),
        ingot_recipe.class_name: fr.Fraction(7, 2),
    }

    save_path = tmp_path / "complete-chain.json"

    def choose_save_path(*_args: object, **_kwargs: object) -> tuple[str, str]:
        return str(save_path), "Production Chain (*.json)"

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", choose_save_path)
    window.save_chain_as()

    assert save_path.exists()
    assert not window.has_unsaved_changes

    def choose_open_path(*_args: object, **_kwargs: object) -> tuple[str, str]:
        return str(save_path), "Production Chain (*.json)"

    def load_fresh_game_data(
        _game_data_type: type[ic.GameData],
        _docs_path: pathlib.Path,
    ) -> ic.GameData:
        return fresh_game_data()

    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", choose_open_path)
    monkeypatch.setattr(
        ic.GameData,
        "from_json",
        classmethod(load_fresh_game_data),
    )

    assert window.open_chain()
    assert window.production_chain is not None
    assert window.production_chain.goal.class_name == plate.class_name
    assert window.game_data.scale == fr.Fraction(1, 2)
    assert {
        recipe.class_name: count
        for recipe, count in window.production_chain.recipes.items()
    } == counts_before_save
    assert window.goal_header.scale_combo.currentData() == fr.Fraction(1, 2)

    cli_runner = im.InteractiveRunner.from_production_chain_file(
        filename=save_path,
        game_data=fresh_game_data(),
    )
    assert cli_runner.game_data.scale == fr.Fraction(1, 2)
    assert {
        recipe.class_name: count
        for recipe, count in cli_runner.production_chain.recipes.items()
    } == counts_before_save
