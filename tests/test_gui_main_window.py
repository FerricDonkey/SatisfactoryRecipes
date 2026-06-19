import collections.abc as cabc
import dataclasses
import fractions as fr
import pathlib

import pytest
from PySide6 import QtGui, QtWidgets
from pytestqt.qtbot import QtBot

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes import stupid_classes as sc
from satisfactory_recipes.gui import dialogs
from satisfactory_recipes.gui.main_window import MainWindow
from tests import support


@dataclasses.dataclass(frozen=True, slots=True)
class GuiScenario:
    ore: ic.Item
    ingot: ic.Item
    plate: ic.Item
    ingot_recipe: ic.Recipe
    plate_recipe: ic.Recipe
    game_data: ic.GameData
    chain: pc.ProductionChain


@pytest.fixture
def gui_scenario() -> GuiScenario:
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
    game_data = support.make_fake_game_data(
        items=[ore, ingot, plate],
        recipes=[ingot_recipe, plate_recipe],
    )
    chain = pc.ProductionChain(
        goal=plate,
        recipes=sc.ScalableCounter[ic.Recipe](
            {
                plate_recipe: fr.Fraction(3),
            }
        ),
    )
    return GuiScenario(
        ore=ore,
        ingot=ingot,
        plate=plate,
        ingot_recipe=ingot_recipe,
        plate_recipe=plate_recipe,
        game_data=game_data,
        chain=chain,
    )


def make_window(
    qtbot: QtBot,
    scenario: GuiScenario,
    *,
    chain: pc.ProductionChain | None,
    configuration: sr_config.Configuration | None = None,
    filename: pathlib.Path | None = None,
) -> MainWindow:
    window = MainWindow(
        docs_path=pathlib.Path("fake-en-us.json"),
        game_data=scenario.game_data,
        user_config=configuration or sr_config.Configuration(),
        production_chain=chain,
        filename=filename,
    )
    qtbot.addWidget(window)
    window.show()
    return window


def get_table_item(
    table: QtWidgets.QTableWidget,
    row: int,
    column: int,
) -> QtWidgets.QTableWidgetItem:
    item = table.item(row, column)
    assert item is not None
    return item


def test_window_renders_empty_state(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
) -> None:
    window = make_window(qtbot, gui_scenario, chain=None)

    assert window.goal_label.text() == "No production chain loaded"
    assert window.recipes_table.rowCount() == 0
    assert window.inputs_table.rowCount() == 0
    assert window.outputs_table.rowCount() == 0
    assert not window.add_goal_recipe_action.isEnabled()
    assert not window.add_shortage_recipe_action.isEnabled()


def test_window_renders_representative_chain(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
) -> None:
    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)

    assert window.goal_label.text() == "Goal: Iron Plate"
    assert window.status_label.text() == "File: Unsaved"
    assert window.recipes_table.rowCount() == 1
    assert get_table_item(window.recipes_table, 0, 1).text() == "Iron Plate"
    assert get_table_item(window.recipes_table, 0, 2).text() == "3.000"
    assert get_table_item(window.recipes_table, 0, 3).text() == "Constructor"
    assert get_table_item(window.recipes_table, 0, 4).text() == "12.000 MW"

    assert window.inputs_table.rowCount() == 1
    assert get_table_item(window.inputs_table, 0, 0).text() == "Iron Ingot"
    assert get_table_item(window.inputs_table, 0, 1).text() == "6.000"
    assert window.outputs_table.rowCount() == 1
    assert get_table_item(window.outputs_table, 0, 0).text() == "Iron Plate"
    assert get_table_item(window.outputs_table, 0, 1).text() == "3.000"

    detail_text = " ".join(
        label.text()
        for label in window.recipe_details_widget.findChildren(QtWidgets.QLabel)
    )
    assert "Iron Plate" in detail_text
    assert "Produced in <b>Constructor</b>" in detail_text


def test_recipe_actions_follow_available_shortages(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
) -> None:
    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)

    assert window.add_goal_recipe_action.isEnabled()
    assert window.add_shortage_recipe_action.isEnabled()
    assert window.add_goal_recipe_button.isEnabled()
    assert window.add_shortage_recipe_button.isEnabled()

    gui_scenario.chain.recipes[gui_scenario.ingot_recipe] = fr.Fraction(6)
    window.refresh()

    assert not window.add_shortage_recipe_action.isEnabled()
    assert not window.add_shortage_recipe_button.isEnabled()


def test_refresh_computes_chain_view_state_once(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_get_net_per_min = pc.ProductionChain.get_net_per_min
    net_calculations = 0

    def count_net_calculation(
        chain: pc.ProductionChain,
    ) -> sc.ScalableCounter[ic.Item]:
        nonlocal net_calculations
        net_calculations += 1
        return original_get_net_per_min(chain)

    monkeypatch.setattr(
        pc.ProductionChain,
        "get_net_per_min",
        count_net_calculation,
    )

    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)
    assert net_calculations == 1

    window.refresh()
    assert net_calculations == 2


def test_remove_recipe_button_updates_chain_and_dirty_state(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
) -> None:
    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)
    button_wrapper = window.recipes_table.cellWidget(0, 0)
    assert button_wrapper is not None
    remove_button = button_wrapper.findChild(QtWidgets.QToolButton)
    assert remove_button is not None

    remove_button.click()

    assert gui_scenario.plate_recipe not in gui_scenario.chain.recipes
    assert window.recipes_table.rowCount() == 0
    assert window.has_unsaved_changes
    assert window.status_label.text() == "File: Unsaved *"


def test_editing_net_rate_scales_chain_exactly(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
) -> None:
    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)
    amount_item = get_table_item(window.outputs_table, 0, 1)

    amount_item.setText("7/2")

    assert gui_scenario.chain.recipes[gui_scenario.plate_recipe] == fr.Fraction(7, 2)
    assert get_table_item(window.outputs_table, 0, 1).text() == "3.500"
    assert get_table_item(window.inputs_table, 0, 1).text() == "7.000"
    assert window.has_unsaved_changes


def test_double_clicking_input_adds_recipe_for_that_shortage(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)

    def choose_ingot_recipe(
        *,
        recipes: cabc.Iterable[ic.Recipe],
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> ic.Recipe:
        del recipes, title, parent
        return gui_scenario.ingot_recipe

    monkeypatch.setattr(
        dialogs,
        "choose_recipe",
        choose_ingot_recipe,
    )

    input_name_item = get_table_item(window.inputs_table, 0, 0)
    window.inputs_table.itemDoubleClicked.emit(input_name_item)

    assert gui_scenario.chain.recipes[gui_scenario.ingot_recipe] == fr.Fraction(6)
    assert get_table_item(window.inputs_table, 0, 0).text() == "Ore"
    assert get_table_item(window.inputs_table, 0, 1).text() == "12.000"
    assert not window.add_shortage_recipe_action.isEnabled()


def test_scale_combo_reflects_current_game_data_scale(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
) -> None:
    gui_scenario.game_data.scale = fr.Fraction(1, 2)
    window = make_window(qtbot, gui_scenario, chain=gui_scenario.chain)

    assert window.scale_combo.currentData() == fr.Fraction(1, 2)
    assert window.scale_combo.currentText() == "0.5"


def test_saved_theme_style_and_zoom_are_applied(
    qtbot: QtBot,
    gui_scenario: GuiScenario,
    qapp: QtWidgets.QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_palette = QtGui.QPalette(qapp.palette())
    original_font = QtGui.QFont(qapp.font())
    original_stylesheet = qapp.styleSheet()
    original_style = qapp.style().objectName()
    configuration = sr_config.Configuration(
        gui_theme="dark",
        gui_style=original_style,
        gui_zoom_steps=2,
    )

    def ignore_save_config(
        config: sr_config.Configuration,
        config_path: pathlib.Path | None = None,
        warn: sr_config.WarnFunc | None = None,
    ) -> None:
        del config, config_path, warn

    monkeypatch.setattr(sr_config, "save_config", ignore_save_config)

    try:
        window = make_window(
            qtbot,
            gui_scenario,
            chain=gui_scenario.chain,
            configuration=configuration,
        )

        assert qapp.font().pointSizeF() == pytest.approx(
            original_font.pointSizeF() * 1.1**2
        )
        assert window.appearance_manager.zoom_steps == 2
        assert qapp.styleSheet()
        checked_theme = window.theme_action_group.checkedAction()
        assert checked_theme is not None
        assert checked_theme.data() == "dark"
        checked_style = window.style_action_group.checkedAction()
        assert checked_style is not None
        assert str(checked_style.data()).lower() == original_style.lower()

        wrapper = window.recipes_table.cellWidget(0, 0)
        assert wrapper is not None
        remove_button = wrapper.findChild(QtWidgets.QToolButton)
        assert remove_button is not None
        dark_icon_key = remove_button.icon().cacheKey()
        window.appearance_manager.set_theme("light", persist=False)
        assert remove_button.icon().cacheKey() != dark_icon_key
    finally:
        qapp.setPalette(original_palette)
        qapp.setFont(original_font)
        qapp.setStyleSheet(original_stylesheet)
        QtWidgets.QApplication.setStyle(original_style)
