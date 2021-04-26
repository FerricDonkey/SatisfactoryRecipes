"""
Contains basic classes for recipes
"""

from typing import Union, Dict

class Recipe:
    def __init__(self, ingredients_d:dict, products_d:dict, time:float, recipe_name:str):
        """
        set up the recipe

        :param ingredients_d: {item: input PER CRAFT}
        :param products_d: {item: output PER CRAFT}
        :param time: time to craft in seconds
        :param recipe_name: name of recipe
        """
        self.ingredients_d = ingredients_d
        self.products_d = products_d
        self.time = time
        self.recipe_name = recipe_name

    def __str__(self):
        val = f"{self.recipe_name}\n  Requires:\n"
        for item, count in self.ingredients_d.items():
            val += f"    {item}: {count}\n"
        val += "  Produces:\n"
        for item, count in self.products_d.items():
            val += f"    {item}: {count}\n"
        return val

    def __repr__(self):
        val = f'<Recipe {self.recipe_name} ({self.time}s):'
        if self.products_d is None:
            val += ' INVALID '
        else:
            for item, count in self.products_d.items():
                val += f" {item}-{count},"
        val = val[:-1] + ' FROM'
        if self.ingredients_d is None:
            val += ' INVALID '
        else:
            for item, count in self.ingredients_d.items():
                val += f" {item}-{count},"
        return val[:-1] + '>'

    def get_products_per_minute_d(self) -> Dict[str, Union[int, float]]:
        """
        How much of everything is produced per minute

        I should really cache this and keep it updated rather than call every time I care

        :return:
        """
        return {item: amount / (self.time / 60) for item, amount in self.products_d.items()}

    def get_ingredients_per_minute_d(self) -> Dict[str, Union[int, float]]:
        """
        How much of everything is consumed per minute

        I should really cache this and keep it updated rather than call every time I care

        :return:
        """
        return {item: amount / (self.time / 60) for item, amount in self.ingredients_d.items()}

class NonRecipe(Recipe):
    """
    For items that are treated as pre-made (necessity or desire)
    """
    def __init__(self, item_name: str):
        Recipe.__init__(self,
            products_d = {item_name:1},
            ingredients_d = {item_name:1},
            time = 1,  # dummy val
            recipe_name = f'Pre-Made {item_name}'
        )

class ScalableRecipe(Recipe):
    """
    Recipe with scalable inputs and outputs for ease of chaining.
    """

    def __init__(self, parent_recipe: Recipe, scale: Union[float, int] = 1):
        """
        Initialize from a fixed recipe.

        :param parent_recipe:
        :param scale:
        """
        Recipe.__init__(self,
            ingredients_d = parent_recipe.ingredients_d,
            products_d = parent_recipe.products_d,
            time = parent_recipe.time,
            recipe_name = parent_recipe.recipe_name
        )
        self._base_products_d = self.products_d.copy()
        self._base_ingredients_d = self.ingredients_d.copy()
        self._scale: Union[int, float]
        self.scale = scale

    def normalize_for_item(self, item: str, per_minute: Union[float, int] = 1, consume: bool = False) -> None:
        """
        Set scale such that per_minute items are produced/consumed per minute

        :param item: what item to normalize with respect to
        :param per_minute: how many per minute
        :param consume: Whether we're normalizing for an ingredient (if not then product)
        :return: None
        """
        positive_d = self._base_products_d if not consume else self._base_ingredients_d
        negative_d = self._base_products_d if consume else self._base_ingredients_d

        # we allow a default for negative d because most recipes don't consume_from_source what they produce or the other way
        # around, but not for the positive d because if we're normalizing to produce/consume_from_source something we can't, that's
        # a problem
        default_per_minute = (positive_d[item] - negative_d.get(item, 0)) * 60 / self.time
        self.scale = per_minute / default_per_minute

    def scale_to_ingredients_per_min_d(self, ingredients_per_min_d: Dict[str, Union[float, int]]) -> None:
        """
        scale recipe to satisfy all

        :param ingredients_per_min_d: {item: number required per minute
        :return:
        """
        prod_per_min_d = self.get_products_per_minute_d()  # property, so reduce calls
        items = set(ingredients_per_min_d).intersection(prod_per_min_d)
        if len(items) == 0:
            return
        self.scale = max(ingredients_per_min_d[item]/prod_per_min_d[item] for item in items)

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, new_scale):
        self._scale = new_scale
        self.products_d = {i: n * self._scale for i, n in self._base_products_d.items()}
        self.ingredients_d = {i: n * self._scale for i, n in self._base_ingredients_d.items()}

    def __repr__(self):
        val = f'<Recipe {format_num(self.scale)}x{self.recipe_name} ({self.time}s):'
        if self._base_products_d is None:
            val += ' INVALID '
        else:
            for item, count in self._base_products_d.items():
                val += f" {item}-{count},"
        val = val[:-1] + ' FROM'
        if self._base_ingredients_d is None:
            val += ' INVALID '
        else:
            for item, count in self._base_ingredients_d.items():
                val += f" {item}-{count},"
        return val[:-1] + '>'

    def __str__(self):
        val = f"{self.recipe_name}x{format_num(self.scale)} ({self.time}s)\n  Requires (per craft):\n"
        for item, count in self._base_ingredients_d.items():
            val += f"    {item}: {count}\n"
        val += "  Produces (per craft):\n"
        for item, count in self._base_products_d.items():
            val += f"    {item}: {count}\n"
        return val

def format_num(num: Union[int, float]) -> str:
    if isinstance(num, int):
        return str(num)
    return f'{num:0.2f}'