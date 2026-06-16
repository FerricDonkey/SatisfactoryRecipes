import collections.abc as cabc
import fractions as fr

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc


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
