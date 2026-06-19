"""
Contains basic classes for things like recipes, items, buildings
"""

import copy
import dataclasses
import enum
import fractions as fr
import sys
import typing as ty

from satisfactory_recipes import stupid_classes as sc


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class _BaseInfo:
    class_name: str  # Used as key in dictionaries
    source_native_class: str


class BuildingKind(enum.StrEnum):
    MANUFACTURER = enum.auto()


class BuildingPowerMode(enum.StrEnum):
    CONSTANT = enum.auto()
    RECIPE_DEFINED = enum.auto()


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Building(_BaseInfo):
    """An automated producer with power behavior defined by its source class."""

    name: str
    kind: BuildingKind
    power_mode: BuildingPowerMode
    power_draw: fr.Fraction
    estimated_minimum_power_draw: fr.Fraction | None = None
    estimated_maximum_power_draw: fr.Fraction | None = None


class MatterState(enum.StrEnum):
    INVALID = enum.auto()
    SOLID = enum.auto()
    GAS = enum.auto()
    LIQUID = enum.auto()

    @staticmethod
    def from_doc_form(doc_form: str) -> MatterState:
        return {
            "RF_INVALID": MatterState.INVALID,
            "RF_SOLID": MatterState.SOLID,
            "RF_GAS": MatterState.GAS,
            "RF_LIQUID": MatterState.LIQUID,
        }[doc_form]


class ItemKind(enum.StrEnum):
    STANDARD = enum.auto()
    RESOURCE = enum.auto()
    BIOMASS = enum.auto()
    NUCLEAR_FUEL = enum.auto()
    POWER_SHARD = enum.auto()
    POWER_BOOSTER_FUEL = enum.auto()
    CONSUMABLE = enum.auto()
    AMMUNITION = enum.auto()
    EQUIPMENT = enum.auto()
    VEHICLE = enum.auto()


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Item(_BaseInfo):
    name: str
    kind: ItemKind
    matter_state: MatterState
    stack_size: int
    resource_sink_points: int

    @property
    def is_resource(self) -> bool:
        return self.kind is ItemKind.RESOURCE

    @property
    def is_liquid(self) -> bool:
        return self.matter_state == MatterState.LIQUID

    @property
    def is_gas(self) -> bool:
        return self.matter_state == MatterState.GAS

    @property
    def is_fluid(self) -> bool:
        return self.is_gas or self.is_liquid


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class VariablePowerParameters:
    """Raw recipe power parameters: minimum is constant, maximum adds factor."""

    constant: fr.Fraction
    factor: fr.Fraction

    @property
    def minimum(self) -> fr.Fraction:
        return self.constant

    @property
    def maximum(self) -> fr.Fraction:
        return self.constant + self.factor

    @property
    def mean(self) -> fr.Fraction:
        return self.constant + self.factor / 2


class RecipePowerSource(enum.StrEnum):
    NONE = enum.auto()
    BUILDING = enum.auto()
    RECIPE = enum.auto()


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class PowerProfile:
    """Resolved power range and the authoritative source of that range."""

    source: RecipePowerSource
    minimum_draw: fr.Fraction
    maximum_draw: fr.Fraction

    @property
    def mean_draw(self) -> fr.Fraction:
        return (self.minimum_draw + self.maximum_draw) / 2

    @classmethod
    def none(cls) -> ty.Self:
        return cls(
            source=RecipePowerSource.NONE,
            minimum_draw=fr.Fraction(0),
            maximum_draw=fr.Fraction(0),
        )

    @classmethod
    def from_building(cls, power_draw: fr.Fraction) -> ty.Self:
        return cls(
            source=RecipePowerSource.BUILDING,
            minimum_draw=power_draw,
            maximum_draw=power_draw,
        )

    @classmethod
    def from_recipe(cls, parameters: VariablePowerParameters) -> ty.Self:
        return cls(
            source=RecipePowerSource.RECIPE,
            minimum_draw=parameters.minimum,
            maximum_draw=parameters.maximum,
        )


def round_half_up(value: fr.Fraction) -> fr.Fraction:
    """
    Round positive Fraction to nearest int, with .5 rounded up.
    """
    quotient, remainder = divmod(value.numerator, value.denominator)

    if remainder * 2 >= value.denominator:
        return fr.Fraction(quotient + 1, 1)

    return fr.Fraction(quotient, 1)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Recipe(_BaseInfo):
    name: str
    inputs: sc.ScalableCounter[Item]
    inputs_per_min: sc.ScalableCounter[Item]
    products: sc.ScalableCounter[Item]
    products_per_min: sc.ScalableCounter[Item]
    produced_in: Building | None
    craft_time: fr.Fraction
    power_profile: PowerProfile

    @staticmethod
    def scale_one_input(
        amount: fr.Fraction,
        factor: fr.Fraction,
        is_fluid: bool,
    ) -> fr.Fraction:
        # fluid is internally tracked and rounds at 1000x display value
        if is_fluid:
            amount *= 1000
        amount *= factor
        amount = max(round_half_up(amount), fr.Fraction(1, 1))

        # Undo the fluid scaling
        if is_fluid:
            amount /= 1000
        return amount

    def create_scaled(self, factor: fr.Fraction) -> Recipe:
        """Return a new recipes, scaling inputs by factor, handling rounding as done in 1.2."""
        new_inputs = sc.ScalableCounter[Item](
            {
                item: self.scale_one_input(amount, factor, item.is_fluid)
                for item, amount in self.inputs.items()
            },
            frozen=True,
        )
        new_inputs_per_min = sc.ScalableCounter[Item](
            {
                item: amount / fr.Fraction(self.craft_time, 60)
                for item, amount in new_inputs.items()
            },
            frozen=True,
        )

        return copy.replace(
            self,
            inputs=new_inputs,
            inputs_per_min=new_inputs_per_min,
        )

    @property
    def mean_power(self) -> fr.Fraction:
        return self.power_profile.mean_draw

    def make_pretty_str(self, indent: int = 0, scale: fr.Fraction | None = None) -> str:
        if scale is not None:
            postfix = f" x {scale:.3f}"
        else:
            postfix = ""
        desc = f"{self.name}{postfix}:\n    Produce:"
        for item, per_min in self.products_per_min.items():
            if scale is not None:
                per_min *= scale
            per_craft = self.products[item]
            desc += f"\n      - {item.name} x {per_craft:.1f} ({per_min:.3f}/min)"

        desc += "\n    Consume:"
        for item, per_min in self.inputs_per_min.items():
            if scale is not None:
                per_min *= scale
            per_craft = self.inputs[item]
            desc += f"\n      - {item.name} x {per_craft:.1f} ({per_min:.3f}/min)"

        if self.produced_in:
            desc += f"\n    Produced in {self.produced_in.name} "
            if scale is not None:
                desc += f"({self.mean_power} MW each: {self.mean_power * scale:.3f} MW)"
            else:
                desc += f"({self.mean_power} MW)"

        if indent > 0:
            desc = " " * indent + f"\n{' ' * indent}".join(desc.splitlines())
        return desc

    def print(
        self,
        indent: int = 0,
        scale: fr.Fraction | None = None,
        file: ty.TextIO = sys.stdout,
    ) -> None:
        file.write(f"{self.make_pretty_str(indent=indent, scale=scale)}\n")


@dataclasses.dataclass(kw_only=True)
class GameData:
    buildings_d: dict[str, Building]
    items_d: dict[str, Item]
    recipes_d: dict[str, Recipe]
    scale: fr.Fraction = fr.Fraction(1)

    def scale_recipes(self, factor: fr.Fraction) -> None:
        """Replace recipes with scaled version."""
        self.scale *= factor
        self.recipes_d |= {
            key: value.create_scaled(factor) for key, value in self.recipes_d.items()
        }

    @property
    def producible_items(self) -> frozenset[Item]:
        return frozenset(
            item
            for recipe in self.recipes_d.values()
            for item in recipe.products
            if recipe.produced_in
        )

    @property
    def item_name_d(self) -> dict[str, Item]:
        item_name_d = {item.name: item for item in self.items_d.values()}
        assert len(item_name_d) == len(self.items_d)
        return item_name_d

    @property
    def producible_item_name_d(self) -> dict[str, Item]:
        return {
            name: item
            for name, item in self.item_name_d.items()
            if item in self.producible_items
        }

    def get_recipes_producing(self, item: Item) -> list[Recipe]:
        return [
            recipe
            for recipe in self.recipes_d.values()
            if (item in recipe.products and recipe.produced_in)
        ]
