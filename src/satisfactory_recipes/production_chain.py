"""
Actual production chain logic
"""

import dataclasses
import fractions as fr
import pathlib
import sys
import typing as ty

import pydantic

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import stupid_classes as sc


@dataclasses.dataclass(kw_only=True, slots=True)
class ProductionChain:
    goal: ic.Item
    recipes: sc.ScalableCounter[ic.Recipe] = dataclasses.field(
        default_factory=sc.ScalableCounter[ic.Recipe]
    )

    def make_pretty_str(self) -> str:
        desc = (
            "============================================\n"
            f"Production Chain for {self.goal.name}:\n"
            "--------------------------------------------\n"
        )
        if not self.recipes:
            return desc + "No recipes chosen"

        desc += "Recipes:"
        for recipe, count in self.recipes.items():
            desc += f"\n{recipe.make_pretty_str(indent=4, scale=count)}\n"

        net = self.get_net_per_min()
        inputs = sorted(
            (item for item, val in net.items() if val < 0),
            key=lambda item: item.name.lower(),
        )
        desc += "\nInputs per minute:"
        for item in inputs:
            desc += f"\n    {item.name}: {-net[item]:.3f}"

        outputs = sorted(
            (item for item, val in net.items() if val > 0),
            key=lambda item: item.name.lower(),
        )
        desc += "\n\nOutputs per minute:"
        for item in outputs:
            desc += f"\n    {item.name}: {net[item]:.3f}"

        total_power = sum(
            recipe.mean_power * count for recipe, count in self.recipes.items()
        )
        desc += f"\n\nTotal Mean Power: {total_power:.3f} MW"

        return desc

    def print(
        self,
        file: ty.TextIO = sys.stdout,
    ) -> None:
        file.write(f"{self.make_pretty_str()}\n")

    def get_shortage_items(self) -> set[ic.Item]:
        return set(
            item for item, amount in self.get_net_per_min().items() if amount < 0
        )

    def get_involved_items(self) -> set[ic.Item]:
        return set(
            item for item, amount in self.get_net_per_min().items() if amount != 0
        )

    def get_net_per_min(self) -> sc.ScalableCounter[ic.Item]:
        net = sc.ScalableCounter[ic.Item]()
        for recipe, count in self.recipes.items():
            net += recipe.products_per_min * count
            net -= recipe.inputs_per_min * count

        to_del = [item for item, amount in net.items() if amount == 0]
        for item in to_del:
            del net[item]

        return net

    def get_produced_per_min(
        self, consume_byproducts: bool
    ) -> sc.ScalableCounter[ic.Item]:
        produced = sum(
            (
                recipe.products_per_min * recipe_count
                for recipe, recipe_count in self.recipes.items()
            ),
            start=sc.ScalableCounter[ic.Item](),
        )

        if consume_byproducts:
            consumed = self.get_consumed_per_min(consume_byproducts=False)
            for item in produced:
                produced[item] -= consumed[item]

        return produced

    def get_consumed_per_min(
        self, consume_byproducts: bool
    ) -> sc.ScalableCounter[ic.Item]:
        consumed = sum(
            (
                recipe.inputs_per_min * recipe_count
                for recipe, recipe_count in self.recipes.items()
            ),
            start=sc.ScalableCounter[ic.Item](),
        )
        if consume_byproducts:
            produced = self.get_produced_per_min(consume_byproducts=False)
            for item in consumed:
                consumed[item] -= produced[item]

        return consumed

    def add_scaled_recipe(self, recipe: ic.Recipe, item: ic.Item) -> None:
        """
        Add enough or recipe to meet the need of item
        """
        if item not in recipe.products:
            raise RuntimeError(
                f"Cannot use {recipe} to produce {item} - not a product."
            )
        net = self.get_net_per_min()
        if item not in net:
            raise RuntimeError("Tried to scaled add a recipe that was not needed")

        amount_needed = -net[item]
        if amount_needed < 0:
            raise RuntimeError(
                f"Tried to add a {recipe} to satisfy {item} that was already satisfied."
            )

        try:
            self.recipes[recipe] += fr.Fraction(
                amount_needed,
                recipe.products_per_min[item],
            )
        except Exception as exc:
            raise RuntimeError(
                f"problem with Recipe:\n{recipe.make_pretty_str(indent=4)}\n"
                f"Wanted to use it to make {item}"
            ) from exc

    def scale_item(self, item: ic.Item, amount: fr.Fraction) -> None:
        """
        Scale to match input/output of items.
        """
        if amount == 0:
            raise ValueError("Not allowed to scale to 0")

        net = self.get_net_per_min()
        current_amount = abs(net[item])
        if current_amount == 0:
            raise ValueError(f"Cannot scale {item.name}; current amount is 0")

        amount = abs(amount)
        self.recipes *= fr.Fraction(amount, current_amount)

    def to_saveable(self, scale: fr.Fraction) -> _ProductionChainSavable:
        """Convert to a saveable format. It is the caller's responsibility to ensure scale is correct."""
        return _ProductionChainSavable(
            goal_class_name=self.goal.class_name,
            recipes={item.class_name: amount for item, amount in self.recipes.items()},
            recipe_input_scale=scale,
        )

    @classmethod
    def from_saveable(
        cls,
        saveable: _ProductionChainSavable,
        game_data: ic.GameData,
    ) -> ty.Self:
        """Load from saved state. MUTATES game_data TO CORRECT SCALE"""
        if saveable.save_file_version != 1:
            raise ValueError(
                f"Unsupported production chain save version: "
                f"{saveable.save_file_version}"
            )

        if saveable.goal_class_name not in game_data.items_d:
            raise ValueError(
                f"Save file goal item not found in current game data: "
                f"{saveable.goal_class_name}"
            )
        for recipe_class_name in saveable.recipes:
            if recipe_class_name not in game_data.recipes_d:
                raise ValueError(
                    f"Save file recipe not found in current game data: "
                    f"{recipe_class_name}"
                )

        # DO THIS BEFORE converting dictionaries, so that the recipes are correct.
        game_data.scale_recipes(saveable.recipe_input_scale / game_data.scale)

        return cls(
            goal=game_data.items_d[saveable.goal_class_name],
            recipes=sc.ScalableCounter({
                game_data.recipes_d[recipe]: count
                for recipe, count in saveable.recipes.items()
            }),
        )

    def save(self, filename: pathlib.Path, scale: fr.Fraction) -> None:
        saveable = self.to_saveable(scale=scale)
        filename.write_text(saveable.model_dump_json(indent=2))

    @classmethod
    def load(cls, filename: pathlib.Path, game_data: ic.GameData) -> ty.Self:
        """Load from saved file. MUTATES game_data TO CORRECT SCALE"""
        saveable = _ProductionChainSavable.model_validate_json(filename.read_text())
        return cls.from_saveable(saveable, game_data)


class _ProductionChainSavable(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    goal_class_name: str
    recipes: dict[str, fr.Fraction]
    recipe_input_scale: fr.Fraction
    save_file_version: int = 1
