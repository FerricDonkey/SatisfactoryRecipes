"""Parse Satisfactory documentation JSON into provenance-aware domain objects."""

from __future__ import annotations

import dataclasses
import fractions as fr
import json
import pathlib
import typing as ty

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import stupid_classes as sc

RECIPE_NATIVE_CLASS = "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'"
FIXED_MANUFACTURER_NATIVE_CLASS = (
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturer'"
)
VARIABLE_MANUFACTURER_NATIVE_CLASS = (
    "/Script/CoreUObject.Class'/Script/FactoryGame."
    "FGBuildableManufacturerVariablePower'"
)

ITEM_KINDS_BY_NATIVE_CLASS: dict[str, ic.ItemKind] = {
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'": (
        ic.ItemKind.STANDARD
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGResourceDescriptor'": (
        ic.ItemKind.RESOURCE
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptorBiomass'": (
        ic.ItemKind.BIOMASS
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptorNuclearFuel'": (
        ic.ItemKind.NUCLEAR_FUEL
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGPowerShardDescriptor'": (
        ic.ItemKind.POWER_SHARD
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame."
    "FGItemDescriptorPowerBoosterFuel'": ic.ItemKind.POWER_BOOSTER_FUEL,
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGConsumableDescriptor'": (
        ic.ItemKind.CONSUMABLE
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGAmmoTypeProjectile'": (
        ic.ItemKind.AMMUNITION
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGAmmoTypeSpreadshot'": (
        ic.ItemKind.AMMUNITION
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGAmmoTypeInstantHit'": (
        ic.ItemKind.AMMUNITION
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGEquipmentDescriptor'": (
        ic.ItemKind.EQUIPMENT
    ),
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGVehicleDescriptor'": (
        ic.ItemKind.VEHICLE
    ),
}

BUILDING_POWER_MODES_BY_NATIVE_CLASS: dict[str, ic.BuildingPowerMode] = {
    FIXED_MANUFACTURER_NATIVE_CLASS: ic.BuildingPowerMode.CONSTANT,
    VARIABLE_MANUFACTURER_NATIVE_CLASS: ic.BuildingPowerMode.RECIPE_DEFINED,
}

DOCS_DEFAULT_VARIABLE_POWER = ic.VariablePowerParameters(
    constant=fr.Fraction(0),
    factor=fr.Fraction(1),
)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ParseReport:
    """Structured diagnostics from loading a Satisfactory docs file."""

    raw_recipe_count: int
    automated_recipe_count: int
    loaded_recipe_count: int
    ignored_recipe_count: int
    skipped_recipe_count: int
    missing_item_classes_by_recipe: dict[str, frozenset[str]]
    fixed_power_recipes_with_nondefault_parameters: dict[
        str, ic.VariablePowerParameters
    ]
    recipe_power_recipes_with_default_parameters: frozenset[str]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class ParseResult:
    """Game data and diagnostics produced by parsing a documentation file."""

    game_data: ic.GameData
    report: ParseReport


@dataclasses.dataclass(frozen=True, slots=True)
class _DocsSection:
    native_class: str
    records: tuple[dict[str, object], ...]


@dataclasses.dataclass(frozen=True, slots=True)
class _RawRecipe:
    class_name: str
    source_native_class: str
    name: str
    ingredients: dict[str, fr.Fraction]
    products: dict[str, fr.Fraction]
    produced_in: tuple[str, ...]
    craft_time: fr.Fraction
    variable_power: ic.VariablePowerParameters


def _validated_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected docs class record to be an object, got {value!r}")
    record: dict[str, object] = {}
    for key, field_value in ty.cast(dict[object, object], value).items():
        if not isinstance(key, str):
            raise TypeError("Expected docs class record keys to be strings")
        record[key] = field_value
    return record


def _string_record(record: dict[str, object]) -> dict[str, str]:
    string_record: dict[str, str] = {}
    for key, value in record.items():
        if not isinstance(value, str):
            raise TypeError(f"Expected string field {key}, got {value!r}")
        string_record[key] = value
    return string_record


def _load_sections(docs_json: pathlib.Path) -> tuple[_DocsSection, ...]:
    with open(docs_json, "rb") as source:
        raw_data = ty.cast(object, json.load(source))
    if not isinstance(raw_data, list):
        raise TypeError("Expected Satisfactory docs root to be a list")

    sections: list[_DocsSection] = []
    for raw_section in ty.cast(list[object], raw_data):
        if not isinstance(raw_section, dict):
            raise TypeError("Expected each Satisfactory docs section to be an object")
        raw_section = ty.cast(dict[object, object], raw_section)
        native_class = raw_section.get("NativeClass")
        raw_records = raw_section.get("Classes")
        if not isinstance(native_class, str) or not isinstance(raw_records, list):
            raise TypeError("Docs section requires string NativeClass and list Classes")
        sections.append(
            _DocsSection(
                native_class=native_class,
                records=tuple(
                    _validated_record(record)
                    for record in ty.cast(list[object], raw_records)
                ),
            )
        )
    return tuple(sections)


def _parse_item(
    raw_record: dict[str, object],
    *,
    source_native_class: str,
    kind: ic.ItemKind,
) -> ic.Item:
    record = _string_record(raw_record)
    return ic.Item(
        class_name=record["ClassName"],
        source_native_class=source_native_class,
        name=record["mDisplayName"],
        kind=kind,
        matter_state=ic.MatterState.from_doc_form(record["mForm"]),
        stack_size=int(record["mCachedStackSize"]),
        resource_sink_points=int(record.get("mResourceSinkPoints", "0")),
    )


def _parse_building(
    raw_record: dict[str, object],
    *,
    source_native_class: str,
    power_mode: ic.BuildingPowerMode,
) -> ic.Building:
    record = _string_record(raw_record)
    estimated_minimum: fr.Fraction | None = None
    estimated_maximum: fr.Fraction | None = None
    if power_mode is ic.BuildingPowerMode.RECIPE_DEFINED:
        estimated_minimum = fr.Fraction(record["mEstimatedMininumPowerConsumption"])
        estimated_maximum = fr.Fraction(record["mEstimatedMaximumPowerConsumption"])
    return ic.Building(
        class_name=record["ClassName"],
        source_native_class=source_native_class,
        name=record["mDisplayName"],
        kind=ic.BuildingKind.MANUFACTURER,
        power_mode=power_mode,
        power_draw=fr.Fraction(record["mPowerConsumption"]),
        estimated_minimum_power_draw=estimated_minimum,
        estimated_maximum_power_draw=estimated_maximum,
    )


def _parse_item_counts(items_str: str) -> dict[str, fr.Fraction]:
    """Parse an mIngredients/mProduct tuple string into class-name amounts."""
    items_str = items_str[1:-1]
    item_strings = [value.strip("()") for value in items_str.split("),(")]
    counts: dict[str, fr.Fraction] = {}
    for item_string in item_strings:
        if not item_string:
            continue
        key_part, amount_part = item_string.split(",")
        amount = fr.Fraction(amount_part.split("=")[1])
        key_part = key_part.split("=")[1]
        class_name = key_part.split(".")[-1].rstrip("\"'")
        counts[class_name] = amount
    return counts


def _parse_class_references(references: str) -> tuple[str, ...]:
    pieces = references.split(",")
    return tuple(
        class_name
        for piece in pieces
        if (class_name := piece.split(".")[-1].strip("()\"'"))
    )


def _parse_recipe(
    raw_record: dict[str, object],
    *,
    source_native_class: str,
) -> _RawRecipe:
    record = _string_record(raw_record)
    return _RawRecipe(
        class_name=record["ClassName"],
        source_native_class=source_native_class,
        name=record["mDisplayName"],
        ingredients=_parse_item_counts(record["mIngredients"]),
        products=_parse_item_counts(record["mProduct"]),
        produced_in=_parse_class_references(record["mProducedIn"]),
        craft_time=fr.Fraction(record["mManufactoringDuration"]),
        variable_power=ic.VariablePowerParameters(
            constant=fr.Fraction(record["mVariablePowerConsumptionConstant"]),
            factor=fr.Fraction(record["mVariablePowerConsumptionFactor"]),
        ),
    )


def _convert_item_counts(
    counts: dict[str, fr.Fraction],
    items: dict[str, ic.Item],
) -> sc.ScalableCounter[ic.Item]:
    converted = sc.ScalableCounter[ic.Item]()
    for class_name, amount in counts.items():
        item = items[class_name]
        if item.is_fluid:
            amount /= 1000
        converted[item] = amount
    converted.freeze()
    return converted


def _resolve_power_profile(
    building: ic.Building,
    parameters: ic.VariablePowerParameters,
) -> ic.PowerProfile:
    if building.power_mode is ic.BuildingPowerMode.CONSTANT:
        return ic.PowerProfile.from_building(building.power_draw)
    return ic.PowerProfile.from_recipe(parameters)


def _resolve_recipe(
    raw_recipe: _RawRecipe,
    *,
    items: dict[str, ic.Item],
    building: ic.Building,
) -> ic.Recipe:
    products = _convert_item_counts(raw_recipe.products, items)
    inputs = _convert_item_counts(raw_recipe.ingredients, items)
    inputs_per_min = inputs * (60 / raw_recipe.craft_time)
    products_per_min = products * (60 / raw_recipe.craft_time)
    inputs_per_min.freeze()
    products_per_min.freeze()
    return ic.Recipe(
        class_name=raw_recipe.class_name,
        source_native_class=raw_recipe.source_native_class,
        name=raw_recipe.name,
        inputs=inputs,
        inputs_per_min=inputs_per_min,
        products=products,
        products_per_min=products_per_min,
        produced_in=building,
        craft_time=raw_recipe.craft_time,
        power_profile=_resolve_power_profile(building, raw_recipe.variable_power),
    )


def parse_game_data(docs_json: pathlib.Path) -> ParseResult:
    """Load supported production data and report why other recipes were excluded."""
    sections = _load_sections(docs_json)
    items: dict[str, ic.Item] = {}
    buildings: dict[str, ic.Building] = {}
    raw_recipes: dict[str, _RawRecipe] = {}

    for section in sections:
        if (
            item_kind := ITEM_KINDS_BY_NATIVE_CLASS.get(section.native_class)
        ) is not None:
            for record in section.records:
                item = _parse_item(
                    record,
                    source_native_class=section.native_class,
                    kind=item_kind,
                )
                if item.class_name in items:
                    raise RuntimeError(f"Duplicate item class {item.class_name}")
                items[item.class_name] = item
            continue

        if (
            power_mode := BUILDING_POWER_MODES_BY_NATIVE_CLASS.get(section.native_class)
        ) is not None:
            for record in section.records:
                building = _parse_building(
                    record,
                    source_native_class=section.native_class,
                    power_mode=power_mode,
                )
                if building.class_name in buildings:
                    raise RuntimeError(
                        f"Duplicate building class {building.class_name}"
                    )
                buildings[building.class_name] = building
            continue

        if section.native_class == RECIPE_NATIVE_CLASS:
            for record in section.records:
                recipe = _parse_recipe(
                    record,
                    source_native_class=section.native_class,
                )
                if recipe.class_name in raw_recipes:
                    raise RuntimeError(f"Duplicate recipe class {recipe.class_name}")
                raw_recipes[recipe.class_name] = recipe

    automated_recipes: dict[str, tuple[_RawRecipe, ic.Building]] = {}
    ignored_recipe_count = 0
    for class_name, raw_recipe in raw_recipes.items():
        producers = [
            buildings[producer_class]
            for producer_class in raw_recipe.produced_in
            if producer_class in buildings
        ]
        if not producers:
            ignored_recipe_count += 1
            continue
        if len(producers) > 1:
            raise RuntimeError(
                f"Recipe {class_name} resolved to multiple automated producers: "
                f"{producers}"
            )
        automated_recipes[class_name] = (raw_recipe, producers[0])

    missing_item_classes_by_recipe = {
        class_name: frozenset(
            item_class
            for counts in (raw_recipe.ingredients, raw_recipe.products)
            for item_class in counts
            if item_class not in items
        )
        for class_name, (raw_recipe, _building) in automated_recipes.items()
    }
    missing_item_classes_by_recipe = {
        class_name: missing_items
        for class_name, missing_items in missing_item_classes_by_recipe.items()
        if missing_items
    }

    fixed_power_recipes_with_nondefault_parameters = {
        class_name: raw_recipe.variable_power
        for class_name, (raw_recipe, building) in automated_recipes.items()
        if building.power_mode is ic.BuildingPowerMode.CONSTANT
        and raw_recipe.variable_power != DOCS_DEFAULT_VARIABLE_POWER
    }
    recipe_power_recipes_with_default_parameters = frozenset(
        class_name
        for class_name, (raw_recipe, building) in automated_recipes.items()
        if building.power_mode is ic.BuildingPowerMode.RECIPE_DEFINED
        and raw_recipe.variable_power == DOCS_DEFAULT_VARIABLE_POWER
    )

    recipes = {
        class_name: _resolve_recipe(
            raw_recipe,
            items=items,
            building=building,
        )
        for class_name, (raw_recipe, building) in automated_recipes.items()
        if class_name not in missing_item_classes_by_recipe
    }
    report = ParseReport(
        raw_recipe_count=len(raw_recipes),
        automated_recipe_count=len(automated_recipes),
        loaded_recipe_count=len(recipes),
        ignored_recipe_count=ignored_recipe_count,
        skipped_recipe_count=len(missing_item_classes_by_recipe),
        missing_item_classes_by_recipe=missing_item_classes_by_recipe,
        fixed_power_recipes_with_nondefault_parameters=(
            fixed_power_recipes_with_nondefault_parameters
        ),
        recipe_power_recipes_with_default_parameters=(
            recipe_power_recipes_with_default_parameters
        ),
    )
    return ParseResult(
        game_data=ic.GameData(
            buildings_d=buildings,
            items_d=items,
            recipes_d=recipes,
        ),
        report=report,
    )


def load_game_data(docs_json: pathlib.Path) -> ic.GameData:
    """Load domain data without retaining parser diagnostics."""
    return parse_game_data(docs_json).game_data
