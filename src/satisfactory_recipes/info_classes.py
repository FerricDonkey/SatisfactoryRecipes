"""
Contains basic classes for things like recipes, items, buildings
"""

import collections.abc as cabc
import dataclasses
import json
import numbers
import pathlib
import statistics
import sys
import typing as ty
from functools import cached_property

DOCS_PATH = pathlib.Path(__file__).parent / "docs.json"


class StupidFrozenDict[K, V](dict[K, V]):
    def __init__(
        self,
        mapping: cabc.Mapping[K, V] | cabc.Iterable[tuple[K, V]] = (),
        /,
        **kwargs: V,
    ) -> None:
        self._frozen = False
        super().__init__(mapping, **kwargs)

        for key, value in tuple(self.items()):
            self[key] = self._freeze_value(value)

        self._frozen = True

    @classmethod
    def _freeze_value(cls, value: ty.Any) -> ty.Any:
        if isinstance(value, list):
            return tuple(value)  # type: ignore
        if isinstance(value, set):
            return frozenset(value)  # type: ignore
        if isinstance(value, dict):
            return cls(value)  # type: ignore
        return value

    def __setitem__(self, key: K, value: V) -> None:
        if self._frozen:
            raise TypeError("NOOOO. Not allowed. That's the whole point")
        super().__setitem__(key, value)

    def __hash__(self) -> int:  # type: ignore
        return hash(tuple(sorted(self.items())))


class ScalableCounter[T](dict[T, float]):
    """
    Dictionary-like counter whose missing values default to 0.0.

    Supports addition/subtraction with mappings and multiplication/division
    by real numbers. Can be frozen for hashability.
    """

    def __init__(
        self,
        mapping: cabc.Mapping[T, float] | cabc.Iterable[tuple[T, float]] = (),
        /,
        *,
        frozen: bool = False,
        **kwargs: float,
    ) -> None:
        super().__init__(mapping, **kwargs)
        self._frozen: bool = frozen
        self._hash: int | None = None

    def __missing__(self, key: T) -> float:
        if self._frozen:
            # Do not mutate a frozen counter just because someone read a missing key.
            return 0.0

        self[key] = 0.0
        return 0.0

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> ty.Self:
        self._frozen = True
        self._hash = None
        return self

    def unfrozen_copy(self) -> ty.Self:
        return type(self)(self.items())

    def frozen_copy(self) -> ty.Self:
        return type(self)(self.items(), frozen=True)

    def __setitem__(self, key: T, value: float) -> None:
        if self._frozen:
            raise TypeError(f"Called __setitem__ from frozen {type(self).__name__}")
        self._hash = None
        super().__setitem__(key, value)

    def __delitem__(self, key: T) -> None:
        if self._frozen:
            raise TypeError(f"Called __delitem__ from frozen {type(self).__name__}")
        self._hash = None
        super().__delitem__(key)

    def clear(self) -> None:
        if self._frozen:
            raise TypeError(f"Called clear from frozen {type(self).__name__}")
        self._hash = None
        super().clear()

    def pop(self, key: T, default: object = ty.cast(object, ...)) -> float:
        if self._frozen:
            raise TypeError(f"Called pop from frozen {type(self).__name__}")
        self._hash = None

        if default is ...:
            return super().pop(key)

        return super().pop(key, ty.cast(float, default))

    def popitem(self) -> tuple[T, float]:
        if self._frozen:
            raise TypeError(f"Called popitem from frozen {type(self).__name__}")
        self._hash = None
        return super().popitem()

    def update(self, *args: object, **kwargs: float) -> None:
        if self._frozen:
            raise TypeError(f"Called update from frozen {type(self).__name__}")
        self._hash = None
        super().update(*args, **kwargs)  # type: ignore[arg-type]

    def setdefault(self, key: T, default: float = 0.0) -> float:
        if self._frozen:
            raise TypeError(f"Called setdefault from frozen {type(self).__name__}")
        self._hash = None
        return super().setdefault(key, default)

    def __hash__(self) -> int:
        if not self._frozen:
            raise TypeError(
                f"Called __hash__ from non-frozen {type(self).__name__} {self}. "
                "You can freeze first with thing.freeze()."
            )

        if self._hash is None:
            self._hash = hash(tuple(sorted(self.items())))

        return self._hash

    def __add__(self, other: cabc.Mapping[T, float]) -> ty.Self:
        summed = self.unfrozen_copy()
        summed += other
        return summed

    def __iadd__(self, other: cabc.Mapping[T, float]) -> ty.Self:
        self._check_mutable_for_inplace()

        for key, val in other.items():
            self[key] += val

        return self

    def __sub__(self, other: cabc.Mapping[T, float]) -> ty.Self:
        subbed = self.unfrozen_copy()
        subbed -= other
        return subbed

    def __isub__(self, other: cabc.Mapping[T, float]) -> ty.Self:
        self._check_mutable_for_inplace()

        for key, val in other.items():
            self[key] -= val

        return self

    def __mul__(self, scale: numbers.Real) -> ty.Self:
        scaled = self.unfrozen_copy()
        scaled *= scale
        return scaled

    def __rmul__(self, scale: numbers.Real) -> ty.Self:
        return self * scale

    def __imul__(self, scale: numbers.Real) -> ty.Self:
        self._check_mutable_for_inplace()
        self._check_scale(scale, "*")

        for key in tuple(self):
            self[key] *= float(scale)

        return self

    def __truediv__(self, scale: numbers.Real) -> ty.Self:
        scaled = self.unfrozen_copy()
        scaled /= scale
        return scaled

    def __itruediv__(self, scale: numbers.Real) -> ty.Self:
        self._check_mutable_for_inplace()
        self._check_scale(scale, "/")

        for key in tuple(self):
            self[key] /= float(scale)

        return self

    def _check_mutable_for_inplace(self) -> None:
        if self._frozen:
            raise TypeError(
                f"inplace operations not supported for frozen {type(self).__name__}"
            )

    @staticmethod
    def _check_scale(scale: object, op: str) -> None:
        if not isinstance(scale, numbers.Real):
            raise TypeError(
                f"Unsupported operation {op} with scale of type {type(scale).__name__}"
            )


def _un_camel(camel_str: str) -> str:
    chars = []
    for c in camel_str:
        if c == c.lower():
            chars.append(c)
        else:
            chars.append(f"_{c.lower()}")
    return "".join(chars)


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class _BaseInfo:
    key_name: str
    class_name: str

    _FIELD_NAME_TRANSLATION_D: ty.ClassVar[dict[str, str]] = {}
    _FIELD_VALUE_TRANSLATION_D: ty.ClassVar[dict[str, ty.Callable]] = {}

    @classmethod
    def from_dict(cls, key_name: str, in_dict: dict[str, ty.Any]) -> ty.Self:
        existent_fields = set(field.name for field in dataclasses.fields(cls))
        kwargs = {}
        for key, value in in_dict.items():
            field_name = cls._FIELD_NAME_TRANSLATION_D.get(
                key
            )  # TODO: ERROR CHECKING HERE
            if field_name is None:
                field_name = _un_camel(key)
            if field_name in existent_fields:
                value_translator = cls._FIELD_VALUE_TRANSLATION_D.get(
                    field_name, lambda x: x
                )
                kwargs[field_name] = value_translator(value)

        try:
            info = cls(
                key_name=key_name,
                **kwargs,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not load {cls.__name__} from:\n{json.dumps(in_dict, indent=2)}"
            ) from exc

        return info


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Building(_BaseInfo):
    _FIELD_NAME_TRANSLATION_D: ty.ClassVar[dict[str, str]] = {
        "powerUsedRecipes": "power_used_data",
        "powerUsed": "power_used_data",
    }
    _FIELD_VALUE_TRANSLATION_D: ty.ClassVar[dict[str, ty.Callable]] = {
        "power_used_data": lambda power_data: (
            power_data
            if not isinstance(power_data, dict)
            else StupidFrozenDict(power_data)
        )
    }

    name: str
    category: str
    power_used_data: int | dict[str, tuple[int]] | None = None

    def get_mean_power(self, recipe_key_name: str) -> int:
        """
        Mean power used by a recipe, specified by "key_name
        """
        if self.power_used_data is None:
            raise TypeError(
                f"Building {self.name} ({self.key_name}, {self.category=}) does not use power"
            )

        if isinstance(self.power_used_data, int):
            return self.power_used_data
        else:
            return statistics.mean(self.power_used_data[recipe_key_name])

    @property
    def is_workstation(self) -> bool:
        return self.category == "workstation"

    @property
    def is_extractor(self) -> bool:
        return self.category == "extraction"


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Item(_BaseInfo):
    name: str
    category: str
    stack: int | None = None  # fluids don't have stack
    resource_sink_points: int = 0

    @property
    def is_liquid(self) -> bool:
        return self.category == "liquid"

    @property
    def is_gas(self) -> bool:
        return self.category == "gas"

    @property
    def is_fluid(self) -> bool:
        return self.is_gas or self.is_liquid


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class _RecipeBase(_BaseInfo):
    """
    Intermediate class for Recipe as read from
    """

    _FIELD_NAME_TRANSLATION_D: ty.ClassVar[dict[str, str]] = {
        "mManufactoringDuration": "craft_time",
        "mProducedIn": "produced_in",
    }

    name: str
    ingredients: dict[str, float]
    produce: dict[str, float]
    produced_in: list[str] = dataclasses.field(default_factory=list)
    craft_time: float


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Recipe(_BaseInfo):
    _FLUID_REDUCTION_FACTOR: ty.ClassVar[int] = 1000

    name: str
    consume: ScalableCounter[Item]
    consume_per_min: ScalableCounter[Item]
    produce: ScalableCounter[Item]
    produce_per_min: ScalableCounter[Item]
    produced_in: Building | None
    craft_time: float

    @property
    def mean_power(self) -> float:
        if self.produced_in is None:
            return 0
        try:
            return self.produced_in.get_mean_power(self.key_name)
        except Exception as exc:
            raise TypeError(f'Power error in recipe: "{self.name}"') from exc

    def make_pretty_str(self, indent: int = 0, scale: float | None = None) -> str:
        if scale is not None:
            postfix = f" x {scale:.3f}"
        else:
            postfix = ""
        desc = f"{self.name}{postfix}:\n    Produce:"
        for item, per_min in self.produce_per_min.items():
            if scale is not None:
                per_min *= scale
            per_craft = self.produce[item]
            desc += f"\n      - {item.name} x {per_craft:.1f} ({per_min:.3f}/min)"

        desc += "\n    Consume:"
        for item, per_min in self.consume_per_min.items():
            if scale is not None:
                per_min *= scale
            per_craft = self.consume[item]
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
        scale: float | None = None,
        file: ty.TextIO = sys.stdout,
    ) -> None:
        file.write(f"{self.make_pretty_str(indent=indent, scale=scale)}\n")

    @classmethod
    def from_base_recipe(
        cls,
        base_recipe: _RecipeBase,
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

        def convert_item_d(item_d: dict[Item, float]) -> ScalableCounter[Item]:
            new_d = ScalableCounter()
            for class_name, amount in item_d.items():
                item = class_name_to_item_d[class_name]
                if item.is_fluid:
                    amount /= cls._FLUID_REDUCTION_FACTOR
                new_d[item] = amount
            new_d.frozen = True
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

        produce = convert_item_d(base_recipe.produce)
        consume = convert_item_d(base_recipe.ingredients)
        consume_per_min = consume * (60 / base_recipe.craft_time)
        produce_per_min = produce * (60 / base_recipe.craft_time)
        consume_per_min.frozen = True
        produce_per_min.frozen = True

        return cls(
            key_name=base_recipe.key_name,
            class_name=base_recipe.class_name,
            name=base_recipe.name,
            consume=consume,
            consume_per_min=consume_per_min,
            produce=produce,
            produce_per_min=produce_per_min,
            produced_in=buildings[0] if buildings else None,
            craft_time=base_recipe.craft_time,
        )


@dataclasses.dataclass(kw_only=True)
class GameData:
    buildings_d: dict[str, Building]
    items_d: dict[str, Item]
    recipes_d: dict[str, Recipe]

    @classmethod
    def from_json(cls, docs_json: pathlib.Path) -> ty.Self:
        """
        Load from docs.json file
        """

        with open(docs_json) as fin:
            all_data = json.load(fin)

        buildings_d = {
            key_name: Building.from_dict(
                key_name=key_name,
                in_dict=building_d,
            )
            for key_name, building_d in all_data["buildingsData"].items()
        }

        items_d = {
            key_name: Item.from_dict(
                key_name=key_name,
                in_dict=building_d,
            )
            for source in (all_data["itemsData"], all_data["toolsData"])
            for key_name, building_d in source.items()
        }

        recipes_base = {
            key_name: _RecipeBase.from_dict(
                key_name=key_name,
                in_dict=building_d,
            )
            for key_name, building_d in all_data["recipesData"].items()
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
                for source in (base_recipe.produce, base_recipe.ingredients)
                for item_cn in source
            )
        }

        return cls(
            buildings_d=buildings_d,
            items_d=items_d,
            recipes_d=recipes_d,
        )

    @cached_property
    def producible_items(self) -> frozenset[Item]:
        return frozenset(
            item
            for recipe in self.recipes_d.values()
            for item in recipe.produce
            if recipe.produced_in
        )

    @cached_property
    def item_name_d(self) -> dict[str, Item]:
        item_name_d = {item.name: item for item in self.items_d.values()}
        assert len(item_name_d) == len(self.items_d)
        return item_name_d

    @cached_property
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
            if (item in recipe.produce and recipe.produced_in)
        ]
