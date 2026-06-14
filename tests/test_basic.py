"""Basic Tests."""

import json

import pytest

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes import stupid_classes as sc


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
            assert recipe.produce_per_min[item] > 0


def test_production_chain_no_crash() -> None:
    """This is a bad test, because it doesn't make sure anything is correct."""
    game_data = ic.GameData.from_json(ic.DOCS_PATH)
    # raise ValueError(f"{game_data.producible_item_name_d}")
    goal_item = game_data.producible_item_name_d["Plutonium Fuel Rod"]
    production_chain = pc.ProductionChain(goal=goal_item)
    recipe = game_data.get_recipes_producing(goal_item)[0]
    production_chain.recipes[recipe] = 1
    production_chain.scale_item(goal_item, 100)
    production_chain.print()

    while True:
        net = production_chain.get_net_per_min()
        jsonable = {item.name: value for item, value in net.items()}
        print(json.dumps(jsonable, indent=2))
        print()
        assert float("inf") not in net.values()

        shortage_items = production_chain.get_shortage_items()
        shortage_items = {
            item
            for item in shortage_items
            if item in game_data.producible_items and item.name != "Water"
        }
        if not shortage_items:
            break

        this_item = next(iter(shortage_items))
        recipe = game_data.get_recipes_producing(this_item)[0]
        production_chain.add_scaled_recipe(recipe, this_item)

    print()
    production_chain.print()
