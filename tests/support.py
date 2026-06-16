import fractions as fr
import json
import pathlib

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import stupid_classes as sc


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
