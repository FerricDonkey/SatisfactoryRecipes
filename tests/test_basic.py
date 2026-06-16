"""Basic Tests."""

import collections.abc as cabc
import fractions as fr

import pytest

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes import stupid_classes as sc


def choose_recipe(recipes: cabc.Collection[ic.Recipe], item: ic.Item) -> ic.Recipe:
    recipes = sorted(
        recipes,
        key=lambda recipe: (
            len(recipe.products),
            len(recipe.inputs),
            -recipe.products_per_min[item],
        ),
    )
    recipe = recipes[0]
    assert item in recipe.products
    return recipe


def test_frozen_dict() -> None:
    """Test the frozen dict."""
    fd = sc.StupidFrozenDict({3: ["hello"]})
    print(fd)
    with pytest.raises(TypeError):
        fd[3] = ["goodbye"]

    assert 7 not in fd


def test_get_recipes_producing() -> None:
    """Make sure all recipes that say they produce something do."""
    game_data = ic.GameData.from_json(ic.DOCS_PATH)
    for item in game_data.producible_items:
        for recipe in game_data.get_recipes_producing(item):
            assert item in recipe.products
            assert recipe.products_per_min[item] > 0


def test_production_chain_no_crash() -> None:
    """This is a bad test, because it doesn't make sure anything is correct."""
    game_data = ic.GameData.from_json(ic.DOCS_PATH)
    # raise ValueError(f"{game_data.producible_item_name_d}")
    goal_item = game_data.producible_item_name_d["Plutonium Fuel Rod"]
    production_chain = pc.ProductionChain(goal=goal_item)
    recipe = choose_recipe(game_data.get_recipes_producing(goal_item), goal_item)
    production_chain.recipes[recipe] = fr.Fraction(1, 1)
    production_chain.scale_item(goal_item, fr.Fraction(100, 1))
    # production_chain.print()

    count = 0
    while True:
        print("===================================")
        # production_chain.print()
        net = production_chain.get_net_per_min()
        for item, value in net.items():
            print(f"    {item.name}: {value}")
        print()
        assert float("inf") not in net.values()

        shortage_items = production_chain.get_shortage_items()
        shortage_items = {
            item
            for item in shortage_items
            if item in game_data.producible_items
            and not item.is_resource
            and net[item] < -0.00001
        }
        if not shortage_items:
            break

        this_item = next(iter(shortage_items))
        assert net[this_item] < 0
        print(f"--- {this_item.name} {net[this_item]}")
        recipe = choose_recipe(game_data.get_recipes_producing(this_item), this_item)
        production_chain.add_scaled_recipe(recipe, this_item)
        print(f"--- {recipe.name} {production_chain.recipes[recipe]}")
        recipe.print(indent=6)
        count += 1
        if count > 1000:
            raise RuntimeError("Taking too long, something is up")

    print()
    production_chain.print()


def test_recipe_scaling() -> None:
    """Ensure recipe scaling works."""
    fake_solid1 = ic.Item(
        class_name="solid1",
        name="solid1",
        matter_state=ic.MatterState.SOLID,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )
    fake_solid2 = ic.Item(
        class_name="solid2",
        name="solid2",
        matter_state=ic.MatterState.SOLID,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )
    fake_gas1 = ic.Item(
        class_name="gas1",
        name="gas1",
        matter_state=ic.MatterState.GAS,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )
    fake_gas2 = ic.Item(
        class_name="gas2",
        name="gas2",
        matter_state=ic.MatterState.GAS,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )
    fake_liquid1 = ic.Item(
        class_name="liquid1",
        name="liquid1",
        matter_state=ic.MatterState.LIQUID,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )
    fake_liquid2 = ic.Item(
        class_name="liquid2",
        name="liquid2",
        matter_state=ic.MatterState.LIQUID,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )

    fake_recipe = ic.Recipe(
        class_name="fake",
        name="fake",
        inputs=sc.ScalableCounter[ic.Item]({
            fake_solid1: fr.Fraction(1, 1),
            fake_solid2: fr.Fraction(4, 1),
            fake_gas1: fr.Fraction(1, 1000),
            fake_gas2: fr.Fraction(4, 1000),
            fake_liquid1: fr.Fraction(1, 1000),
            fake_liquid2: fr.Fraction(4, 1000),
        }),
        inputs_per_min=sc.ScalableCounter[ic.Item]({
            fake_solid1: fr.Fraction(1, 1),
            fake_solid2: fr.Fraction(4, 1),
            fake_gas1: fr.Fraction(1, 1000),
            fake_gas2: fr.Fraction(4, 1000),
            fake_liquid1: fr.Fraction(1, 1000),
            fake_liquid2: fr.Fraction(4, 1000),
        }),
        products=sc.ScalableCounter[ic.Item]({
            fake_solid1: fr.Fraction(1, 1),
            fake_solid2: fr.Fraction(4, 1),
            fake_gas1: fr.Fraction(1, 1000),
            fake_gas2: fr.Fraction(4, 1000),
            fake_liquid1: fr.Fraction(1, 1000),
            fake_liquid2: fr.Fraction(4, 1000),
        }),
        products_per_min=sc.ScalableCounter[ic.Item]({
            fake_solid1: fr.Fraction(1, 1),
            fake_solid2: fr.Fraction(4, 1),
            fake_gas1: fr.Fraction(1, 1000),
            fake_gas2: fr.Fraction(4, 1000),
            fake_liquid1: fr.Fraction(1, 1000),
            fake_liquid2: fr.Fraction(4, 1000),
        }),
        produced_in=None,
        craft_time=fr.Fraction(1, 1),
        _variable_part_mean_power_draw=fr.Fraction(1, 1),
    )

    quarter_scale = fake_recipe.create_scaled(fr.Fraction(1, 4))
    for counter in (quarter_scale.inputs_per_min, quarter_scale.inputs):
        for item, amount in counter.items():
            if item.is_fluid:
                assert amount == fr.Fraction(1, 1000)
            else:
                assert amount == fr.Fraction(1, 1)
