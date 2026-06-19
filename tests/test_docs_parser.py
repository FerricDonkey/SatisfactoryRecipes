import fractions as fr
import json
import pathlib

from satisfactory_recipes import docs_parser
from satisfactory_recipes import info_classes as ic


def _write_docs(
    tmp_path: pathlib.Path,
    sections: list[dict[str, object]],
) -> pathlib.Path:
    docs_path = tmp_path / "en-us.json"
    docs_path.write_text(json.dumps(sections))
    return docs_path


def _item_record(class_name: str) -> dict[str, str]:
    return {
        "ClassName": class_name,
        "mDisplayName": class_name,
        "mForm": "RF_SOLID",
        "mCachedStackSize": "100",
        "mResourceSinkPoints": "1",
    }


def _building_record(
    class_name: str,
    *,
    power_draw: str,
    estimated_minimum: str | None = None,
    estimated_maximum: str | None = None,
) -> dict[str, str]:
    record = {
        "ClassName": class_name,
        "mDisplayName": class_name,
        "mPowerConsumption": power_draw,
    }
    if estimated_minimum is not None:
        record["mEstimatedMininumPowerConsumption"] = estimated_minimum
    if estimated_maximum is not None:
        record["mEstimatedMaximumPowerConsumption"] = estimated_maximum
    return record


def _recipe_record(
    class_name: str,
    *,
    product_class: str,
    producer_class: str,
    power_constant: str = "0",
    power_factor: str = "1",
) -> dict[str, str]:
    return {
        "ClassName": class_name,
        "mDisplayName": class_name,
        "mIngredients": "()",
        "mProduct": (
            f'((ItemClass="/Game/Test/{product_class}.{product_class}",Amount=1))'
        ),
        "mProducedIn": (f'("/Game/Test/{producer_class}.{producer_class}")'),
        "mManufactoringDuration": "1",
        "mVariablePowerConsumptionConstant": power_constant,
        "mVariablePowerConsumptionFactor": power_factor,
    }


def test_all_supported_item_categories_retain_source_provenance(
    tmp_path: pathlib.Path,
) -> None:
    expected: dict[str, tuple[str, ic.ItemKind]] = {}
    sections: list[dict[str, object]] = []
    for index, (source_native_class, item_kind) in enumerate(
        docs_parser.ITEM_KINDS_BY_NATIVE_CLASS.items()
    ):
        class_name = f"Desc_Test_{index}_C"
        expected[class_name] = (source_native_class, item_kind)
        sections.append(
            {
                "NativeClass": source_native_class,
                "Classes": [_item_record(class_name)],
            }
        )

    game_data = docs_parser.load_game_data(_write_docs(tmp_path, sections))

    assert len(game_data.items_d) == len(docs_parser.ITEM_KINDS_BY_NATIVE_CLASS)
    for class_name, (source_native_class, item_kind) in expected.items():
        item = game_data.items_d[class_name]
        assert item.source_native_class == source_native_class
        assert item.kind is item_kind
        assert item.is_resource is (item_kind is ic.ItemKind.RESOURCE)


def test_power_source_comes_from_building_provenance_not_recipe_defaults(
    tmp_path: pathlib.Path,
) -> None:
    item_class = "Desc_Product_C"
    missing_item_class = "Desc_Missing_C"
    fixed_building_class = "Build_Fixed_C"
    variable_building_class = "Build_Variable_C"
    sections: list[dict[str, object]] = [
        {
            "NativeClass": next(
                source
                for source, kind in docs_parser.ITEM_KINDS_BY_NATIVE_CLASS.items()
                if kind is ic.ItemKind.STANDARD
            ),
            "Classes": [_item_record(item_class)],
        },
        {
            "NativeClass": docs_parser.FIXED_MANUFACTURER_NATIVE_CLASS,
            "Classes": [_building_record(fixed_building_class, power_draw="4")],
        },
        {
            "NativeClass": docs_parser.VARIABLE_MANUFACTURER_NATIVE_CLASS,
            "Classes": [
                _building_record(
                    variable_building_class,
                    power_draw="0",
                    estimated_minimum="0",
                    estimated_maximum="400",
                )
            ],
        },
        {
            "NativeClass": docs_parser.RECIPE_NATIVE_CLASS,
            "Classes": [
                _recipe_record(
                    "Recipe_Fixed_C",
                    product_class=item_class,
                    producer_class=fixed_building_class,
                    power_constant="500",
                    power_factor="1000",
                ),
                _recipe_record(
                    "Recipe_Variable_C",
                    product_class=item_class,
                    producer_class=variable_building_class,
                    power_constant="100",
                    power_factor="300",
                ),
                _recipe_record(
                    "Recipe_VariableDefault_C",
                    product_class=item_class,
                    producer_class=variable_building_class,
                ),
                _recipe_record(
                    "Recipe_MissingItem_C",
                    product_class=missing_item_class,
                    producer_class=fixed_building_class,
                ),
                _recipe_record(
                    "Recipe_Ignored_C",
                    product_class=item_class,
                    producer_class="BP_WorkBench_C",
                ),
            ],
        },
    ]

    parse_result = docs_parser.parse_game_data(_write_docs(tmp_path, sections))
    game_data = parse_result.game_data

    fixed = game_data.recipes_d["Recipe_Fixed_C"]
    assert fixed.source_native_class == docs_parser.RECIPE_NATIVE_CLASS
    assert fixed.produced_in is not None
    assert fixed.produced_in.source_native_class == (
        docs_parser.FIXED_MANUFACTURER_NATIVE_CLASS
    )
    assert fixed.power_profile == ic.PowerProfile.from_building(fr.Fraction(4))

    variable = game_data.recipes_d["Recipe_Variable_C"]
    assert variable.power_profile == ic.PowerProfile(
        source=ic.RecipePowerSource.RECIPE,
        minimum_draw=fr.Fraction(100),
        maximum_draw=fr.Fraction(400),
    )
    assert variable.mean_power == fr.Fraction(250)

    variable_default = game_data.recipes_d["Recipe_VariableDefault_C"]
    assert variable_default.power_profile.source is ic.RecipePowerSource.RECIPE
    assert variable_default.mean_power == fr.Fraction(1, 2)

    assert parse_result.report == docs_parser.ParseReport(
        raw_recipe_count=5,
        automated_recipe_count=4,
        loaded_recipe_count=3,
        ignored_recipe_count=1,
        skipped_recipe_count=1,
        missing_item_classes_by_recipe={
            "Recipe_MissingItem_C": frozenset({missing_item_class})
        },
        fixed_power_recipes_with_nondefault_parameters={
            "Recipe_Fixed_C": ic.VariablePowerParameters(
                constant=fr.Fraction(500),
                factor=fr.Fraction(1000),
            )
        },
        recipe_power_recipes_with_default_parameters=frozenset(
            {"Recipe_VariableDefault_C"}
        ),
    )
