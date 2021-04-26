from ..doc_parsing import doc_parser as dp
from . import recipe_classes as rc

BUILDINGS = dp.get_buildings()
EQUIPMENT = dp.get_equipment()
RECIPES = tuple(
    rc.Recipe(**kwargs)
    for kwargs in dp.get_all_recipe_kwargs()
    if kwargs['ingredients_d'] != kwargs['products_d']
)
NAME_TO_RECIPE_D = {r.recipe_name: r for r in RECIPES}
GOOD_ITEMS = frozenset(
    thing
    for thing in dp.get_item_translation_d().values()
    if thing not in EQUIPMENT
    or any(
        thing in r.ingredients_d
        for r in RECIPES
        if any(thing not in EQUIPMENT for thing in  r.products_d)
    )
    or 'filter' in thing
)

ITEM_TO_CONSUMING_RECIPE_D = {
    item: tuple(r.recipe_name for r in RECIPES if item in r.ingredients_d)
    for item in GOOD_ITEMS
}

ITEM_TO_PRODUCING_RECIPE_D = {
    item: tuple(r.recipe_name for r in RECIPES if item in r.products_d)
    for item in GOOD_ITEMS
}

# Good items that are ingredients but not products
RAW_RESOURCES = frozenset(
    item
    for item in GOOD_ITEMS
    if len(ITEM_TO_PRODUCING_RECIPE_D.get(item, tuple())) == 0
)
PRODUCIBLE_ITEMS = frozenset(
    item
    for item in GOOD_ITEMS
    if len(ITEM_TO_PRODUCING_RECIPE_D.get(item, tuple())) != 0
)


