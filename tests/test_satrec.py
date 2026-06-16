"""Basic Tests."""

import collections.abc as cabc
import fractions as fr
import json
import pathlib

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


def make_fake_item(
    name: str,
    matter_state: ic.MatterState = ic.MatterState.SOLID,
) -> ic.Item:
    return ic.Item(
        class_name=name,
        name=name,
        matter_state=matter_state,
        stack_size=1,
        resource_sink_points=1,
        is_resource=True,
    )


def make_fake_recipe(
    *,
    class_name: str = "Recipe_Fake_C",
    name: str | None = None,
    inputs: dict[ic.Item, fr.Fraction],
    products: dict[ic.Item, fr.Fraction] | None = None,
    craft_time: fr.Fraction = fr.Fraction(60),
) -> ic.Recipe:
    if products is None:
        products = {}

    if name is None:
        name = class_name

    return ic.Recipe(
        class_name=class_name,
        name=name,
        inputs=sc.ScalableCounter[ic.Item](inputs, frozen=True),
        inputs_per_min=sc.ScalableCounter[ic.Item](
            {
                item: amount * fr.Fraction(60) / craft_time
                for item, amount in inputs.items()
            },
            frozen=True,
        ),
        products=sc.ScalableCounter[ic.Item](products, frozen=True),
        products_per_min=sc.ScalableCounter[ic.Item](
            {
                item: amount * fr.Fraction(60) / craft_time
                for item, amount in products.items()
            },
            frozen=True,
        ),
        produced_in=None,
        craft_time=craft_time,
        _variable_part_mean_power_draw=fr.Fraction(0),
    )


def make_fake_game_data(
    *,
    items: list[ic.Item],
    recipes: list[ic.Recipe],
    scale: fr.Fraction = fr.Fraction(1),
) -> ic.GameData:
    return ic.GameData(
        buildings_d={},
        items_d={item.class_name: item for item in items},
        recipes_d={recipe.class_name: recipe for recipe in recipes},
        scale=scale,
    )


def write_chain_json(
    filename: pathlib.Path,
    *,
    goal_class_name: str = "Desc_Ingot_C",
    recipes: dict[str, str] | None = None,
    recipe_input_scale: str = "1/4",
    save_file_version: int = 1,
    extra: dict[str, object] | None = None,
) -> None:
    if recipes is None:
        recipes = {"Recipe_Ingot_C": "1"}

    data: dict[str, object] = {
        "goal_class_name": goal_class_name,
        "recipes": recipes,
        "recipe_input_scale": recipe_input_scale,
        "save_file_version": save_file_version,
    }

    if extra:
        data.update(extra)

    filename.write_text(json.dumps(data))


@pytest.mark.parametrize(
    ("amount", "factor", "is_fluid", "expected"),
    [
        # Solids at 0.25x:
        # 1 -> 0.25 -> min 1
        (fr.Fraction(1), fr.Fraction(1, 4), False, fr.Fraction(1)),
        # 2 -> 0.5 -> round half up to 1
        (fr.Fraction(2), fr.Fraction(1, 4), False, fr.Fraction(1)),
        # 3 -> 0.75 -> round to 1
        (fr.Fraction(3), fr.Fraction(1, 4), False, fr.Fraction(1)),
        # 4 -> 1
        (fr.Fraction(4), fr.Fraction(1, 4), False, fr.Fraction(1)),
        # 5 -> 1.25 -> round to 1
        (fr.Fraction(5), fr.Fraction(1, 4), False, fr.Fraction(1)),
        # 6 -> 1.5 -> round half up to 2
        (fr.Fraction(6), fr.Fraction(1, 4), False, fr.Fraction(2)),
        # Fluids/gases round in raw units, where 1 displayed unit == 1000 raw.
        # 0.001 -> 1 raw unit; cannot go below 1 raw unit.
        (fr.Fraction(1, 1000), fr.Fraction(1, 4), True, fr.Fraction(1, 1000)),
        # 0.002 -> 2 raw; 2 * 1/4 = 0.5 -> 1 raw.
        (fr.Fraction(2, 1000), fr.Fraction(1, 4), True, fr.Fraction(1, 1000)),
        # 0.006 -> 6 raw; 6 * 1/4 = 1.5 -> 2 raw.
        (fr.Fraction(6, 1000), fr.Fraction(1, 4), True, fr.Fraction(2, 1000)),
        # 30 m³ -> 30000 raw; quarter is 7500 raw -> 7.5 m³.
        (fr.Fraction(30), fr.Fraction(1, 4), True, fr.Fraction(15, 2)),
    ],
)
def test_scale_one_input_edge_cases(
    amount: fr.Fraction,
    factor: fr.Fraction,
    is_fluid: bool,
    expected: fr.Fraction,
) -> None:
    assert ic.Recipe.scale_one_input(amount, factor, is_fluid) == expected


def test_recipe_scaling_scales_inputs_and_recomputes_inputs_per_min() -> None:
    solid_1 = make_fake_item("solid_1", ic.MatterState.SOLID)
    solid_6 = make_fake_item("solid_6", ic.MatterState.SOLID)
    liquid_30 = make_fake_item("liquid_30", ic.MatterState.LIQUID)
    gas_006 = make_fake_item("gas_006", ic.MatterState.GAS)

    recipe = make_fake_recipe(
        inputs={
            solid_1: fr.Fraction(1),
            solid_6: fr.Fraction(6),
            liquid_30: fr.Fraction(30),
            gas_006: fr.Fraction(6, 1000),
        },
        craft_time=fr.Fraction(30),
    )

    scaled = recipe.create_scaled(fr.Fraction(1, 4))

    assert scaled.inputs[solid_1] == fr.Fraction(1)
    assert scaled.inputs[solid_6] == fr.Fraction(2)
    assert scaled.inputs[liquid_30] == fr.Fraction(15, 2)
    assert scaled.inputs[gas_006] == fr.Fraction(2, 1000)

    # craft_time is 30 seconds, so each machine does 2 cycles/min.
    assert scaled.inputs_per_min[solid_1] == fr.Fraction(2)
    assert scaled.inputs_per_min[solid_6] == fr.Fraction(4)
    assert scaled.inputs_per_min[liquid_30] == fr.Fraction(15)
    assert scaled.inputs_per_min[gas_006] == fr.Fraction(4, 1000)

    hash(scaled)


def test_recipe_scaling_does_not_scale_products() -> None:
    input_item = make_fake_item("input_item", ic.MatterState.SOLID)
    product_item = make_fake_item("product_item", ic.MatterState.SOLID)

    recipe = make_fake_recipe(
        inputs={input_item: fr.Fraction(8)},
        products={product_item: fr.Fraction(3)},
        craft_time=fr.Fraction(15),
    )

    scaled = recipe.create_scaled(fr.Fraction(1, 4))

    assert scaled.inputs[input_item] == fr.Fraction(2)
    assert scaled.inputs_per_min[input_item] == fr.Fraction(8)

    # Products should be unchanged by recipe input scaling.
    assert scaled.products[product_item] == fr.Fraction(3)
    assert scaled.products_per_min[product_item] == fr.Fraction(12)


def test_recipe_scaling_freezes_new_input_counters() -> None:
    item = make_fake_item("item", ic.MatterState.SOLID)
    recipe = make_fake_recipe(inputs={item: fr.Fraction(8)})

    scaled = recipe.create_scaled(fr.Fraction(1, 4))

    assert scaled.inputs.frozen
    assert scaled.inputs_per_min.frozen

    with pytest.raises(TypeError):
        scaled.inputs[item] = fr.Fraction(999)

    with pytest.raises(TypeError):
        scaled.inputs_per_min[item] = fr.Fraction(999)


def test_production_chain_save_load_round_trips(tmp_path: pathlib.Path) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")
    plate = make_fake_item("Desc_Plate_C")

    ingot_recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )
    plate_recipe = make_fake_recipe(
        class_name="Recipe_Plate_C",
        inputs={ingot: fr.Fraction(4)},
        products={plate: fr.Fraction(1)},
    )

    game_data = make_fake_game_data(
        items=[ore, ingot, plate],
        recipes=[ingot_recipe, plate_recipe],
    )

    chain = pc.ProductionChain(
        goal=plate,
        recipes=sc.ScalableCounter[ic.Recipe]({
            ingot_recipe: fr.Fraction(3, 2),
            plate_recipe: fr.Fraction(4),
        }),
    )

    filename = tmp_path / "chain.json"
    chain.save(filename, scale=fr.Fraction(1, 4))

    loaded = pc.ProductionChain.load(filename, game_data)

    assert loaded.goal == plate
    assert game_data.scale == fr.Fraction(1, 4)

    loaded_recipe_counts = {
        recipe.class_name: count for recipe, count in loaded.recipes.items()
    }

    assert loaded_recipe_counts == {
        "Recipe_Ingot_C": fr.Fraction(3, 2),
        "Recipe_Plate_C": fr.Fraction(4),
    }


def test_production_chain_save_file_shape(tmp_path: pathlib.Path) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")

    recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    chain = pc.ProductionChain(
        goal=ingot,
        recipes=sc.ScalableCounter[ic.Recipe]({recipe: fr.Fraction(7, 3)}),
    )

    filename = tmp_path / "chain.json"
    chain.save(filename, scale=fr.Fraction(1, 4))

    raw = json.loads(filename.read_text())

    assert raw == {
        "goal_class_name": "Desc_Ingot_C",
        "recipes": {
            "Recipe_Ingot_C": "7/3",
        },
        "recipe_input_scale": "1/4",
        "save_file_version": 1,
    }


def test_load_uses_scaled_recipe_objects(tmp_path: pathlib.Path) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")

    recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(8)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
        scale=fr.Fraction(1),
    )

    filename = tmp_path / "chain.json"
    write_chain_json(
        filename,
        goal_class_name="Desc_Ingot_C",
        recipes={"Recipe_Ingot_C": "2"},
        recipe_input_scale="1/4",
    )

    loaded = pc.ProductionChain.load(filename, game_data)

    loaded_recipe = next(iter(loaded.recipes))

    assert loaded_recipe.class_name == "Recipe_Ingot_C"
    assert loaded_recipe.inputs[ore] == fr.Fraction(2)
    assert loaded.recipes[loaded_recipe] == fr.Fraction(2)

    assert game_data.scale == fr.Fraction(1, 4)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(2)


def test_load_rejects_unsupported_save_version_without_scaling(
    tmp_path: pathlib.Path,
) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")
    recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    filename = tmp_path / "chain.json"
    write_chain_json(filename, save_file_version=999)

    with pytest.raises(ValueError, match="Unsupported production chain save version"):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(4)


def test_load_rejects_missing_goal_item_without_scaling(
    tmp_path: pathlib.Path,
) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")
    recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    filename = tmp_path / "chain.json"
    write_chain_json(filename, goal_class_name="Desc_Missing_C")

    with pytest.raises(ValueError, match="goal item not found"):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(4)


def test_load_rejects_missing_recipe_without_scaling(
    tmp_path: pathlib.Path,
) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")

    game_data = make_fake_game_data(
        items=[ore, ingot],
        recipes=[],
    )

    filename = tmp_path / "chain.json"
    write_chain_json(
        filename,
        recipes={"Recipe_Missing_C": "1"},
    )

    with pytest.raises(
        ValueError, match="Save file recipe not found in current game data"
    ):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)


def test_load_rejects_extra_save_fields_without_scaling(
    tmp_path: pathlib.Path,
) -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")
    recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    filename = tmp_path / "chain.json"
    write_chain_json(filename, extra={"surprise": "nope"})

    with pytest.raises(Exception, match="surprise"):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(4)


def test_game_data_scale_recipes_replaces_recipes_and_updates_scale() -> None:
    ore = make_fake_item("Desc_Ore_C")
    ingot = make_fake_item("Desc_Ingot_C")

    recipe = make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(8)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    old_recipe = game_data.recipes_d["Recipe_Ingot_C"]

    game_data.scale_recipes(fr.Fraction(1, 4))

    new_recipe = game_data.recipes_d["Recipe_Ingot_C"]

    assert game_data.scale == fr.Fraction(1, 4)
    assert new_recipe is not old_recipe
    assert new_recipe.inputs[ore] == fr.Fraction(2)
