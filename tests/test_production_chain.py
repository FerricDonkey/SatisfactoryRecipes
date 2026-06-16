import fractions as fr
import json
import pathlib

import pytest

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes import stupid_classes as sc
from tests import support


def test_production_chain_save_load_round_trips(tmp_path: pathlib.Path) -> None:
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")
    plate = support.make_fake_item("Desc_Plate_C")

    ingot_recipe = support.make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )
    plate_recipe = support.make_fake_recipe(
        class_name="Recipe_Plate_C",
        inputs={ingot: fr.Fraction(4)},
        products={plate: fr.Fraction(1)},
    )

    game_data = support.make_fake_game_data(
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
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")

    recipe = support.make_fake_recipe(
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
        scale=fr.Fraction(1),
    )

    filename = tmp_path / "chain.json"
    support.write_chain_json(
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
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")
    recipe = support.make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = support.make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    filename = tmp_path / "chain.json"
    support.write_chain_json(filename, save_file_version=999)

    with pytest.raises(ValueError, match="Unsupported production chain save version"):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(4)


def test_load_rejects_missing_goal_item_without_scaling(
    tmp_path: pathlib.Path,
) -> None:
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")
    recipe = support.make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = support.make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    filename = tmp_path / "chain.json"
    support.write_chain_json(filename, goal_class_name="Desc_Missing_C")

    with pytest.raises(ValueError, match="goal item not found"):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(4)


def test_load_rejects_missing_recipe_without_scaling(
    tmp_path: pathlib.Path,
) -> None:
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")

    game_data = support.make_fake_game_data(
        items=[ore, ingot],
        recipes=[],
    )

    filename = tmp_path / "chain.json"
    support.write_chain_json(
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
    ore = support.make_fake_item("Desc_Ore_C")
    ingot = support.make_fake_item("Desc_Ingot_C")
    recipe = support.make_fake_recipe(
        class_name="Recipe_Ingot_C",
        inputs={ore: fr.Fraction(4)},
        products={ingot: fr.Fraction(1)},
    )

    game_data = support.make_fake_game_data(
        items=[ore, ingot],
        recipes=[recipe],
    )

    filename = tmp_path / "chain.json"
    support.write_chain_json(filename, extra={"surprise": "nope"})

    with pytest.raises(Exception, match="surprise"):
        pc.ProductionChain.load(filename, game_data)

    assert game_data.scale == fr.Fraction(1)
    assert game_data.recipes_d["Recipe_Ingot_C"].inputs[ore] == fr.Fraction(4)


def test_scale_item_rejects_item_not_in_chain() -> None:
    item = support.make_fake_item("Desc_Item_C")
    other = support.make_fake_item("Desc_Other_C")

    chain = pc.ProductionChain(goal=item)

    with pytest.raises(ValueError, match="current amount is 0"):
        chain.scale_item(other, fr.Fraction(10))


def test_scale_item_rejects_zero_current_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = support.make_fake_item("Desc_Item_C")
    chain = pc.ProductionChain(goal=item)

    def fake_get_net_per_min(self: pc.ProductionChain) -> sc.ScalableCounter[ic.Item]:
        return sc.ScalableCounter[ic.Item]({item: fr.Fraction(0)})

    monkeypatch.setattr(pc.ProductionChain, "get_net_per_min", fake_get_net_per_min)

    with pytest.raises(ValueError, match="current amount is 0"):
        chain.scale_item(item, fr.Fraction(10))
