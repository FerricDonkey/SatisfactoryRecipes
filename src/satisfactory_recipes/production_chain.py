"""
Actual production chain logic
"""
import dataclasses
import json
import math
import sys
import typing as ty

from . import info_classes as ic


@dataclasses.dataclass(kw_only=True, slots=True)
class ProductionChain:
    goal: ic.Item
    recipes: ic.ScalableCounter[ic.Recipe] = dataclasses.field(default_factory=ic.ScalableCounter)

    def make_pretty_str(self) -> str:
        desc=(
            '============================================\n'
            f'Production Chain for {self.goal.name}:\n'
            '--------------------------------------------\n'
        )
        if not self.recipes:
            return desc + 'No recipes chosen'

        desc += 'Recipes:'
        for recipe, count in self.recipes.items():
            desc += f'\n{recipe.make_pretty_str(indent=4, scale=count)}\n'

        net = self.get_net_per_min()
        inputs = sorted(
            (item for item, val in net.items() if val < 0),
            key = lambda item: item.name.lower()
        )
        desc += '\nInputs per minute:'
        for item in inputs:
            desc +=f'\n    {item.name}: {-net[item]:.3f}'

        outputs = sorted(
            (item for item, val in net.items() if val > 0),
            key=lambda item: item.name.lower()
        )
        desc += '\n\nOutputs per minute:'
        for item in outputs:
            desc += f'\n    {item.name}: {net[item]:.3f}'

        total_power = sum(
            recipe.mean_power * count
            for recipe, count in self.recipes.items()
        )
        desc += f'\n\nTotal Mean Power: {total_power:.3f} MW'

        return desc

    def print(
        self,
        file: ty.TextIO = sys.stdout,
    ) -> None:
        file.write(f'{self.make_pretty_str()}\n')

    def get_shortage_items(self) -> set[ic.Item]:
        return set(
            item
            for item, amount in self.get_net_per_min().items()
            if amount < 0
        )

    def get_inolved_items(self) -> set[ic.Item]:
        return set(
            item
            for item, amount in self.get_net_per_min().items()
            if not math.isclose(amount, 0)
        )

    def get_net_per_min(self) -> ic.ScalableCounter[ic.Item]:
        net = ic.ScalableCounter()
        for recipe, count in self.recipes.items():
            net += recipe.produce_per_min * count
            net -= recipe.consume_per_min * count

        to_del = [
            item
            for item, amount in net.items()
            if math.isclose(amount, 0)
        ]
        for item in to_del:
            del net[item]

        return net

    def get_produced_per_min(self, consume_byproducts: bool) -> ic.ScalableCounter[ic.Item]:
        produced = sum(
            (
                recipe.produce_per_min * recipe_count
                for recipe, recipe_count in self.recipes.items()
            ),
            start=ic.ScalableCounter()
        )

        if consume_byproducts:
            consumed = self.get_consumed_per_min(consume_byproducts=False)
            for item in produced:
                produced[item] -= consumed[item]

        return produced

    def get_consumed_per_min(self, consume_byproducts: bool) -> ic.ScalableCounter[ic.Item]:
        consumed = sum(
            (
                recipe.consume_per_min * recipe_count
                for recipe, recipe_count in self.recipes.items()
            ),
            start=ic.ScalableCounter()
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
        net = self.get_net_per_min()
        amount_needed = abs(net.get(item))
        if amount_needed is None:
            raise RuntimeError(
                'Tried to scaled add a recipe that was not needed'
            )
        try:
            self.recipes[recipe] += amount_needed / recipe.produce_per_min[item]
        except Exception as exc:
            raise RuntimeError(
                f'problem with Recipe:\n{recipe.make_pretty_str(indent=4)}\n'
            ) from exc

    def scale_item(self, item: ic.Item, amount: float) -> None:
        """
        Scale to match input/output of items.
        """
        if amount == 0:
            raise ValueError('Not allowed to scale to 0')

        net = self.get_net_per_min()
        current_amount = abs(net[item])
        amount = abs(amount)
        self.recipes *= amount / current_amount

    def to_dict(self) -> dict:
        return {
            'goal': self.goal.key_name,
            'recipes': {
                recipe.key_name: count
                for recipe, count in self.recipes.items()
            }
        }

    @classmethod
    def from_dict(cls, in_dict: dict, game_data: ic.GameData) -> ty.Self:
        return cls(
            goal=game_data.items_d[in_dict['goal']],
            recipes=ic.ScalableCounter({
                game_data.recipes_d[recipe]: count
                for recipe, count in in_dict['recipes'].items()
            })
        )

    def save(self, filename: ic.PathStr) -> None:
        with open(filename, 'w') as fout:
            json.dump(self.to_dict(), fout, indent=2)

    @classmethod
    def load(cls, filename: ic.PathStr, game_data: ic.GameData) -> ty.Self:
        with open(filename) as fin:
            return cls.from_dict(json.load(fin), game_data=game_data)
