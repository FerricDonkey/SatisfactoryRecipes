import dataclasses
import fractions as fr

from PySide6 import QtWidgets
from pytestqt.qtbot import QtBot

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes import stupid_classes as sc
from satisfactory_recipes.gui import widgets
from tests import support


def make_widget_scenario() -> tuple[
    ic.Item,
    ic.Item,
    ic.Recipe,
    pc.ProductionChain,
]:
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
            inputs={ore: fr.Fraction(2)},
            products={ingot: fr.Fraction(1)},
        ),
        produced_in=smelter,
    )
    chain = pc.ProductionChain(
        goal=ingot,
        recipes=sc.ScalableCounter[ic.Recipe]({recipe: fr.Fraction(3)}),
    )
    return ore, ingot, recipe, chain


def test_goal_header_displays_state_and_emits_user_intent(qtbot: QtBot) -> None:
    _ore, ingot, _recipe, _chain = make_widget_scenario()
    header = widgets.GoalHeader()
    qtbot.addWidget(header)
    requested_scales: list[fr.Fraction] = []
    goal_requests = 0

    def record_scale(value: object) -> None:
        assert isinstance(value, fr.Fraction)
        requested_scales.append(value)

    def record_goal_request() -> None:
        nonlocal goal_requests
        goal_requests += 1

    header.scale_changed.connect(record_scale)
    header.change_goal_requested.connect(record_goal_request)

    header.set_view(goal=ingot, recipe_scale=fr.Fraction(1, 2))

    assert header.goal_label.text() == "Goal: Iron Ingot"
    assert header.scale_combo.currentData() == fr.Fraction(1, 2)
    assert requested_scales == []

    header.change_goal_button.click()
    header.scale_combo.setCurrentIndex(0)

    assert goal_requests == 1
    assert requested_scales == [fr.Fraction(1, 4)]


def test_recipes_panel_renders_and_emits_recipe_actions(qtbot: QtBot) -> None:
    _ore, _ingot, recipe, chain = make_widget_scenario()
    panel = widgets.RecipesPanel()
    qtbot.addWidget(panel)
    removed: list[ic.Recipe] = []
    goal_requests = 0
    shortage_requests = 0

    def record_removal(value: object) -> None:
        assert isinstance(value, ic.Recipe)
        removed.append(value)

    def record_goal_request() -> None:
        nonlocal goal_requests
        goal_requests += 1

    def record_shortage_request() -> None:
        nonlocal shortage_requests
        shortage_requests += 1

    panel.remove_recipe_requested.connect(record_removal)
    panel.add_goal_recipe_requested.connect(record_goal_request)
    panel.add_shortage_recipe_requested.connect(record_shortage_request)
    panel.set_view(
        recipes=tuple(chain.recipes.items()),
        can_add_goal_recipe=True,
        can_add_shortage_recipe=True,
    )

    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 1).text() == "Iron Ingot"  # type: ignore[union-attr]
    assert panel.table.item(0, 4).text() == "12.000 MW"  # type: ignore[union-attr]

    panel.add_goal_recipe_button.click()
    panel.add_shortage_recipe_button.click()
    wrapper = panel.table.cellWidget(0, 0)
    assert wrapper is not None
    remove_button = wrapper.findChild(QtWidgets.QToolButton)
    assert remove_button is not None
    remove_button.click()

    assert goal_requests == 1
    assert shortage_requests == 1
    assert removed == [recipe]
    assert recipe in chain.recipes


def test_net_items_table_renders_without_edit_signal_and_emits_exact_amount(
    qtbot: QtBot,
) -> None:
    ore, _ingot, _recipe, _chain = make_widget_scenario()
    table = widgets.NetItemsTable()
    qtbot.addWidget(table)
    edits: list[tuple[ic.Item, fr.Fraction]] = []
    activations: list[ic.Item] = []

    def record_edit(item_value: object, amount_value: object) -> None:
        assert isinstance(item_value, ic.Item)
        assert isinstance(amount_value, fr.Fraction)
        edits.append((item_value, amount_value))

    def record_activation(item_value: object) -> None:
        assert isinstance(item_value, ic.Item)
        activations.append(item_value)

    table.amount_edit_requested.connect(record_edit)
    table.item_activated.connect(record_activation)
    table.set_view(((ore, fr.Fraction(5, 3)),))

    assert edits == []
    name_item = table.item(0, 0)
    amount_item = table.item(0, 1)
    assert name_item is not None
    assert amount_item is not None
    assert amount_item.text() == "1.667"
    assert "Double-click" in amount_item.toolTip()

    amount_item.setText("7/3")
    table.itemDoubleClicked.emit(name_item)

    assert edits == [(ore, fr.Fraction(7, 3))]
    assert activations == [ore]


def test_chain_details_tabs_renders_all_views_and_forwards_shortage_request(
    qtbot: QtBot,
) -> None:
    ore, ingot, _recipe, chain = make_widget_scenario()
    tabs = widgets.ChainDetailsTabs()
    qtbot.addWidget(tabs)
    shortages: list[ic.Item] = []

    def record_shortage(item_value: object) -> None:
        assert isinstance(item_value, ic.Item)
        shortages.append(item_value)

    tabs.shortage_recipe_requested.connect(record_shortage)
    net = chain.get_net_per_min()
    tabs.set_view(
        inputs=tuple((item, -amount) for item, amount in net.items() if amount < 0),
        outputs=tuple((item, amount) for item, amount in net.items() if amount > 0),
        recipes=tuple(chain.recipes.items()),
    )

    assert tabs.inputs_table.rowCount() == 1
    assert tabs.outputs_table.rowCount() == 1
    input_name = tabs.inputs_table.item(0, 0)
    output_name = tabs.outputs_table.item(0, 0)
    assert input_name is not None
    assert output_name is not None
    assert input_name.text() == ore.name
    assert output_name.text() == ingot.name
    assert "add a recipe" in input_name.toolTip()
    assert "Double-click" in tabs.tabToolTip(0)
    assert tabs.recipe_details.content_layout.count() == 2

    tabs.inputs_table.itemDoubleClicked.emit(input_name)

    assert shortages == [ore]
