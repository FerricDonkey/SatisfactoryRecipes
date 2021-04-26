
# from typing import Tuple
#
# from . import recipe_classes as rc
# from . import constants as cons


# def get_recipes_that_produce(item: str) -> Tuple[rc.Recipe, ...]:
#     return tuple(r for r in cons.RECIPES if item in r.products_per_minute_d)
#
#
# def scale_recipe_to_other(
#     source_recipe: rc.ScalableRecipe,
#     recipe_to_scale: rc.ScalableRecipe,
#     consume_from_source: bool = False
# ) -> None:
#     """
#     Scale a recipe so that it's in/outputs (depending on consume) match another
#
#     :param source_recipe:
#     :param recipe_to_scale:
#     :param consume_from_source:
#     :return:
#     """
#     source_p_d = source_recipe.ingredients_d if not consume_from_source else source_recipe.produces_d
#     source_n_d = source_recipe.ingredients_d if consume_from_source else source_recipe.produces_d
#     to_scale_p_d = recipe_to_scale.ingredients_d if consume_from_source else recipe_to_scale.produces_d
#     to_scale_n_d = recipe_to_scale.ingredients_d if not consume_from_source else recipe_to_scale.produces_d
#
#     items = set(source_p_d).intersection(to_scale_p_d)
#     assert len(items) > 0, "No items in common, bug in scaling"
#
#     # mostly there will be one product
#     scale_factor = max(
#         (source_p_d[item] - source_n_d.get(item, 0)) / (to_scale_p_d[item] - to_scale_n_d.get(item, 0))
#         for item in items
#     )
#     recipe_to_scale.scale *= scale_factor