import fractions as fr
import json
import pathlib

import pytest

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import config as sr_config
from tests import support


def test_get_recipes_producing() -> None:
    """Make sure all recipes that say they produce something do."""
    docs_path = sr_config.find_docs_path()
    if docs_path is None:
        pytest.skip("Satisfactory docs file not found")

    game_data = ic.GameData.from_json(docs_path)
    for item in game_data.producible_items:
        for recipe in game_data.get_recipes_producing(item):
            assert item in recipe.products
            assert recipe.products_per_min[item] > 0


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
    solid_1 = support.make_fake_item("solid_1", ic.MatterState.SOLID)
    solid_6 = support.make_fake_item("solid_6", ic.MatterState.SOLID)
    liquid_30 = support.make_fake_item("liquid_30", ic.MatterState.LIQUID)
    gas_006 = support.make_fake_item("gas_006", ic.MatterState.GAS)

    recipe = support.make_fake_recipe(
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
    input_item = support.make_fake_item("input_item", ic.MatterState.SOLID)
    product_item = support.make_fake_item("product_item", ic.MatterState.SOLID)

    recipe = support.make_fake_recipe(
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
    item = support.make_fake_item("item", ic.MatterState.SOLID)
    recipe = support.make_fake_recipe(inputs={item: fr.Fraction(8)})

    scaled = recipe.create_scaled(fr.Fraction(1, 4))

    assert scaled.inputs.frozen
    assert scaled.inputs_per_min.frozen

    with pytest.raises(TypeError):
        scaled.inputs[item] = fr.Fraction(999)

    with pytest.raises(TypeError):
        scaled.inputs_per_min[item] = fr.Fraction(999)


def test_game_data_scale_recipes_replaces_recipes_and_updates_scale() -> None:
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")

    recipe = support.make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(8)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = support.make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    old_recipe = game_data.recipes_d["Recipe_Ingot_C"]

    game_data.scale_recipes(fr.Fraction(1, 4))

    new_recipe = game_data.recipes_d["Recipe_Ingot_C"]

    assert game_data.scale == fr.Fraction(1, 4)
    assert new_recipe is not old_recipe
    assert new_recipe.inputs[ore] == fr.Fraction(2)


def test_game_data_reports_recipes_skipped_for_missing_items(
    tmp_path: pathlib.Path,
) -> None:
    item_native_class = (
        "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'"
    )
    recipe_native_class = "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'"
    known_item_class = "Desc_Known_C"
    missing_item_class = "Desc_Missing_C"

    def recipe_source(class_name: str, product_class: str) -> dict[str, str]:
        return {
            "ClassName": class_name,
            "mDisplayName": class_name,
            "mIngredients": "()",
            "mProduct": (
                f'((ItemClass="/Game/Test/{product_class}.{product_class}",Amount=1))'
            ),
            "mProducedIn": "()",
            "mManufactoringDuration": "1",
        }

    docs = [
        {
            "NativeClass": item_native_class,
            "Classes": [
                {
                    "ClassName": known_item_class,
                    "mDisplayName": "Known Item",
                    "mForm": "RF_SOLID",
                    "mCachedStackSize": "100",
                }
            ],
        },
        {
            "NativeClass": recipe_native_class,
            "Classes": [
                recipe_source("Recipe_Loaded_C", known_item_class),
                recipe_source("Recipe_Skipped_C", missing_item_class),
            ],
        },
    ]
    docs_path = tmp_path / "en-us.json"
    docs_path.write_text(json.dumps(docs))

    game_data = ic.GameData.from_json(docs_path)

    assert set(game_data.recipes_d) == {"Recipe_Loaded_C"}
    assert game_data.parse_report == ic.ParseReport(
        raw_recipe_count=2,
        loaded_recipe_count=1,
        skipped_recipe_count=1,
        missing_item_classes_by_recipe={
            "Recipe_Skipped_C": frozenset({missing_item_class})
        },
    )
