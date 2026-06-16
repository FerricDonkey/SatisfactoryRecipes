"""
Contains basic classes for things like recipes, items, buildings
"""

import abc
import copy
import dataclasses
import enum
import fractions as fr
import json
import pathlib
import sys
import typing as ty

from satisfactory_recipes import stupid_classes as sc

@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class _BaseInfo(abc.ABC):
    class_name: str  # Used as key in dictionaries

    @classmethod
    def from_dict(cls, in_dict: dict[str, str]) -> ty.Self:
        """Load from a dictionary."""
        try:
            return cls._from_dict_impl(in_dict)
        except Exception as exc:
            raise RuntimeError(
                f"Error processings:\n{json.dumps(in_dict, indent=2)}"
            ) from exc

    @classmethod
    @abc.abstractmethod
    def _from_dict_impl(cls, in_dict: dict[str, str]) -> ty.Self:
        """Load from a dictionary."""
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Building(_BaseInfo):
    """
    Information about buildings.

    Note that Particle Accelerators and similar variable length power buildings have a power
    draw of 0, and the recipes come with power draw.
    """

    name: str
    category: str
    power_draw: (
        fr.Fraction
    )  # NOTE: If the power is 0 (eg Particle Accelerator), Power comes from the recipe

    @classmethod
    def _from_dict_impl(cls, in_dict: dict[str, str]) -> ty.Self:
        return cls(
            class_name=in_dict["ClassName"],
            name=in_dict["mDisplayName"],
            category="<<PLACEHOLDER-FIX-THIS>>",
            power_draw=fr.Fraction(in_dict["mPowerConsumption"]),
        )

    @property
    def is_workstation(self) -> bool:
        return self.category == "workstation"

    @property
    def is_extractor(self) -> bool:
        return self.category == "extraction"


class MatterState(enum.StrEnum):
    SOLID = enum.auto()
    GAS = enum.auto()
    LIQUID = enum.auto()

    @staticmethod
    def from_doc_form(doc_form: str) -> MatterState:
        return {
            "RF_SOLID": MatterState.SOLID,
            "RF_GAS": MatterState.GAS,
            "RF_LIQUID": MatterState.LIQUID,
        }[doc_form]


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Item(_BaseInfo):
    name: str
    matter_state: MatterState
    stack_size: int
    resource_sink_points: int
    is_resource: bool

    @property
    def is_liquid(self) -> bool:
        return self.matter_state == MatterState.LIQUID

    @property
    def is_gas(self) -> bool:
        return self.matter_state == MatterState.GAS

    @property
    def is_fluid(self) -> bool:
        return self.is_gas or self.is_liquid

    @classmethod
    def _from_dict_impl(cls, in_dict: dict[str, str]) -> ty.Self:
        """Load from a dictionary."""
        matter_state = MatterState.from_doc_form(in_dict["mForm"])
        stack_size = int(in_dict["mCachedStackSize"])

        return cls(
            class_name=in_dict["ClassName"],
            name=in_dict["mDisplayName"],
            matter_state=matter_state,
            stack_size=stack_size,
            resource_sink_points=int(in_dict.get("mResourceSinkPoints", 0)),
            is_resource=("mManualMiningAudioName" in in_dict),
        )


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class RecipeRaw(_BaseInfo):
    """
    Intermediate class for Recipe as read from data.

    NOTE: mean_power_draw will be 0 for most recipes, and non-zero for
          things made in the particle accelerator, etc. For best results,
          add power draw from building and recipe.
    """

    name: str
    ingredients: dict[str, fr.Fraction]
    products: dict[str, fr.Fraction]
    produced_in: list[str]
    craft_time: fr.Fraction
    mean_power_draw: fr.Fraction

    @staticmethod
    def parse_item_counts(items_str: str) -> dict[str, fr.Fraction]:
        """
        Take the mIngredients/mProducts string (or similar), convert to dictionary.

        Example str: "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'/Game/FactoryGame/Resource/Parts/IronIngot/Desc_IronIngot.Desc_IronIngot_C'\",Amount=3))"
        """
        items_str = items_str[1:-1]
        item_strs = [val.strip("()") for val in items_str.split("),(")]
        out_d: dict[str, fr.Fraction] = {}
        for item_str in item_strs:
            if not item_str:
                continue
            try:
                key_part, amount_part = item_str.split(",")
            except Exception:
                raise RuntimeError(f"Parse Error:\n    {items_str=}\n    {item_str=}\n")
            amount = fr.Fraction(amount_part.split("=")[1])

            key_part = key_part.split("=")[1]
            key = key_part.split(".")[-1].rstrip("\"'")
            out_d[key] = amount

        return out_d

    @staticmethod
    def parse_produced_in(produced_in_str: str) -> list[str]:
        """
        Take the mProducedIn string (or similar), convert to list of building keys.

        Example str: "(\"/Game/FactoryGame/Buildable/Factory/ConstructorMk1/Build_ConstructorMk1.Build_ConstructorMk1_C\",\"/Game/FactoryGame/Buildable/-Shared/WorkBench/BP_WorkBenchComponent.BP_WorkBenchComponent_C\",\"/Script/FactoryGame.FGBuildableAutomatedWorkBench\")"
        """
        pieces = produced_in_str.split(",")
        return [piece.split(".")[-1].strip("()\"'") for piece in pieces]

    @classmethod
    def _from_dict_impl(cls, in_dict: dict[str, str]) -> ty.Self:
        """Load from a dictionary."""
        # I think mean_power_draw is correct - the names make no sense, but they match
        # what I see for recipes.
        mean_power_draw = (
            2 * fr.Fraction(in_dict.get("mVariablePowerConsumptionConstant", "0"))
            + fr.Fraction(in_dict.get("mVariablePowerConsumptionFactor", "0"))
        ) / 2
        return cls(
            class_name=in_dict["ClassName"],
            name=in_dict["mDisplayName"],
            ingredients=cls.parse_item_counts(in_dict["mIngredients"]),
            products=cls.parse_item_counts(in_dict["mProduct"]),
            produced_in=cls.parse_produced_in(in_dict["mProducedIn"]),
            craft_time=fr.Fraction(in_dict["mManufactoringDuration"]),
            mean_power_draw=mean_power_draw,
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
    _variable_part_mean_power_draw: (
        fr.Fraction
    )  # From raw recipe, for variable things only

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

    def create_scaled(self, factor: fr.Fraction) -> ty.Self:
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
        # Certain fixmas items are weird
        if self.produced_in is None:
            return fr.Fraction(0, 1)

        # TODO: Make more idiomatic. Basically, buildings set their power to 0
        #       if they should use the recipe power.
        if self.produced_in.power_draw > 0:
            return self.produced_in.power_draw

        return self._variable_part_mean_power_draw

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

    @classmethod
    def from_base_recipe(
        cls,
        base_recipe: RecipeRaw,
        class_name_to_item_d: dict[str, Item],
        class_name_to_building_d: dict[str, Building],
    ) -> ty.Self:
        """
        Create from _baseRecipe object (replace string names of things with
        the related things, etc)

        Args:
            base_recipe: recipe in base form
            class_name_to_item_d: dictionary to look up items
            class_name_to_building_d: dictionary to look up buildings

        Returns:
            Recipe in more useful form

        """

        def convert_item_d(
            item_d: dict[str, fr.Fraction],
        ) -> sc.ScalableCounter[Item]:
            """Given dictionary of item keys to counts, make dictionary from Item objects to counts."""
            new_d = sc.ScalableCounter[Item]()
            for class_name, amount in item_d.items():
                item = class_name_to_item_d[class_name]
                if item.is_fluid:
                    amount = fr.Fraction(amount, 1000)
                new_d[item] = amount
            new_d.freeze()
            return new_d

        buildings = [
            building
            for class_name in base_recipe.produced_in
            if (
                (building := class_name_to_building_d.get(class_name)) is not None
                and not (building.is_workstation or building.is_extractor)
            )
        ]

        if len(buildings) > 1:
            raise RuntimeError(
                "BUG: Expected at most one building after excluding manual "
                f"stations, but got {buildings=}"
            )

        products = convert_item_d(base_recipe.products)
        consume = convert_item_d(base_recipe.ingredients)
        consume_per_min = consume * (60 / base_recipe.craft_time)
        products_per_min = products * (60 / base_recipe.craft_time)
        consume_per_min.freeze()
        products_per_min.freeze()

        return cls(
            class_name=base_recipe.class_name,
            name=base_recipe.name,
            inputs=consume,
            inputs_per_min=consume_per_min,
            products=products,
            products_per_min=products_per_min,
            produced_in=buildings[0] if buildings else None,
            craft_time=base_recipe.craft_time,
            _variable_part_mean_power_draw=base_recipe.mean_power_draw,
        )

    @classmethod
    def _from_dict_impl(cls, in_dict: dict[str, str]) -> ty.Self:
        raise RuntimeError(
            "Do not construct Recipe from dictionary - instead construct "
            "RecipeRaw, and build recipes from that"
        )


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

    @classmethod
    def from_json(cls, docs_json: pathlib.Path) -> ty.Self:
        """
        Load from docs.json file
        """
        with open(docs_json, "rb") as fin:
            all_data = json.load(fin)

        buildings_src: list[dict[str, str]] = []
        recipe_src: list[dict[str, str]] = []
        item_src: list[dict[str, str]] = []

        native_class_to_srcs = {
            "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'": item_src,
            "/Script/CoreUObject.Class'/Script/FactoryGame.FGResourceDescriptor'": item_src,
            "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptorNuclearFuel'": item_src,
            "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'": recipe_src,
            "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturerVariablePower'": buildings_src,
            "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturer'": buildings_src,
        }

        for junk_d in all_data:
            dest_l = native_class_to_srcs.get(junk_d["NativeClass"])
            if dest_l is None:
                continue
            dest_l.extend(junk_d["Classes"])

        buildings_d = {
            src_d["ClassName"]: Building.from_dict(
                in_dict=src_d,
            )
            for src_d in buildings_src
        }

        items_d = {
            src_d["ClassName"]: Item.from_dict(
                in_dict=src_d,
            )
            for src_d in item_src
        }

        recipes_base = {
            src_d["ClassName"]: RecipeRaw.from_dict(
                in_dict=src_d,
            )
            for src_d in recipe_src
        }

        class_name_to_item_d = {item.class_name: item for item in items_d.values()}
        class_name_to_building_d = {
            building.class_name: building for building in buildings_d.values()
        }

        recipes_d = {
            key_name: Recipe.from_base_recipe(
                base_recipe=base_recipe,
                class_name_to_item_d=class_name_to_item_d,
                class_name_to_building_d=class_name_to_building_d,
            )
            for key_name, base_recipe in recipes_base.items()
            if all(
                item_cn in class_name_to_item_d
                for source in (base_recipe.products, base_recipe.ingredients)
                for item_cn in source
            )
        }

        return cls(
            buildings_d=buildings_d,
            items_d=items_d,
            recipes_d=recipes_d,
        )

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
