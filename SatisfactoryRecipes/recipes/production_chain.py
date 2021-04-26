"""
This file contains classes that can scale recipes and track stuff
"""
from typing import Optional, Dict, Union, Collection

from . import recipe_classes as rc
from . import constants as cons
import math

class ProductionChain:
    """
    The whole chain.
    """
    def __init__(self, desired_products_per_min_d:Optional[Dict[str, Union[int, float]]] = None):
        # self.item = item
        # self._goal_amount_per_min = goal_amount_per_min # do not change this directly, or scaling will not work
        if desired_products_per_min_d is None:
            self._desired_products_per_min_d = {}
        else:
            self._desired_products_per_min_d = desired_products_per_min_d
        self.active_name_to_recipes_d: Dict[str, rc.ScalableRecipe] = {}

    def get_desired_products(self):
        return tuple(self._desired_products_per_min_d)

    def get_desired_per_minute(self, product):
        return self._desired_products_per_min_d.get(product, 0)

    def get_products_per_minute_d(self):
        """
        what all is currently being produced.

        These are really badly written

        I should really cache this and keep it updated rather than call every time I care

        INCLUDES LOOP BACK CALCULATIONS (eg, products that consume what they produce)

        :return: dictionary {item: output per minute}
        """
        to_return:dict = {}
        # Get all of the output
        for scalable_recipe in self.active_name_to_recipes_d.values():
            for product, quantity in scalable_recipe.get_products_per_minute_d().items():
                to_return[product] = to_return.get(product, 0) + quantity

        # now handle any loopback
        for scalable_recipe in self.active_name_to_recipes_d.values():
            for ingredient, quantity in scalable_recipe.get_ingredients_per_minute_d().items():
                if ingredient in to_return:
                    to_return[ingredient] -= quantity

        for item, quantity in self._desired_products_per_min_d.items():
            to_return[item] = to_return.get(item, 0) - quantity

        # only negative values that count as products are those in the _desired_products_per_min
        return {
            item: quantity
            for item, quantity in to_return.items()
            if (quantity > 0 and item not in self._desired_products_per_min_d)
            or (item in self._desired_products_per_min_d
                and (quantity< 0 or quantity > self._desired_products_per_min_d[item])
                )
        }


    def get_ingredients_per_minute_d(self, ignored_recipe_names: Collection[str] = frozenset()):
        """
        what all is currently being consumed.

        These are really badly written

        I should really cache this and keep it updated rather than call every time I care

        INCLUDES LOOP BACK CALCULATIONS (eg, products that consume what they produce)

        :return: dictionary {item: output per minute}
        """
        to_return:dict = {}
        # Get all of the output
        for scalable_recipe in self.active_name_to_recipes_d.values():
            if scalable_recipe.recipe_name not in ignored_recipe_names:
                for ingredient, quantity in scalable_recipe.get_ingredients_per_minute_d().items():
                    to_return[ingredient] = to_return.get(ingredient, 0) + quantity

        # now handle any loopback
        for scalable_recipe in self.active_name_to_recipes_d.values():
            if scalable_recipe.recipe_name not in ignored_recipe_names:
                for product, quantity in scalable_recipe.get_products_per_minute_d().items():
                    if product in to_return:
                        to_return[product] -= quantity

        # handle desired_products. This is really, really bad, I'm doing well over 2 to 4 times as
        # much work as I need to
        if self._desired_products_per_min_d:
            prod_d = self.get_products_per_minute_d()
            # Note: prod_d has the desired amount subtracted so that it will be at 0 when
            #       we're making enough
            for item, _ in self._desired_products_per_min_d.items():
                to_return[item] = to_return.get(item, 0) - prod_d.get(item, 0)

        return {item: quantity for item, quantity in to_return.items() if not math.isclose(quantity, 0)}

    def add_recipe(self, recipe_name:str, auto_scale = True):
        if recipe_name in self.active_name_to_recipes_d:
            return
        new_recipe =rc.ScalableRecipe(parent_recipe = cons.NAME_TO_RECIPE_D[recipe_name])
        if auto_scale:
            new_recipe.scale_to_ingredients_per_min_d(self.get_ingredients_per_minute_d())
        self.active_name_to_recipes_d[new_recipe.recipe_name] = new_recipe


    def remove_recipe(self, recipe_name: str):
        """
        remove a recipe from active recipes

        :param recipe_name:
        :return:
        """

        if recipe_name in self.active_name_to_recipes_d:
            del self.active_name_to_recipes_d[recipe_name]

    def multiply_full_chain(self, factor: Union[int, float]):
        """
        multiply all recipes in the chain by factor

        :param factor:
        :return:
        """

        for scalable_recipe in self.active_name_to_recipes_d.values():
            scalable_recipe.scale *= factor

    def multiply_desired_amounts(self, factor: Union[int, float]):
        self._desired_products_per_min_d = {
            key: value * factor
            for key, value in self._desired_products_per_min_d.items()
        }

    def rescale_single_recipe(self, recipe_name: str, new_scale: Union[None, int, float] = None):
        """
        set the scale for a particular recipe (do nothing if that recipe is not in use

        :param recipe_name:
        :param new_scale:
        :return:
        """

        if new_scale is not None:
            self.active_name_to_recipes_d[recipe_name].scale = new_scale
        else:
            self.active_name_to_recipes_d[recipe_name].scale_to_ingredients_per_min_d(
                ingredients_per_min_d = self.get_ingredients_per_minute_d(
                    ignored_recipe_names = {recipe_name}
                )
            )

