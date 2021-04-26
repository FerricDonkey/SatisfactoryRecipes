"""
Get stuff out of Docs.json
"""

import typing
import pathlib
import json

DOC_FILE = pathlib.Path(__file__).parent / 'Docs.json'
if not DOC_FILE.exists():
    DOC_FILE = pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Satisfactory\CommunityResources\Docs') / 'Docs.json'
if not DOC_FILE.exists():
    DOC_FILE = pathlib.Path(r'D:\Program Files (x86)\Steam\steamapps\common\Satisfactory\CommunityResources\Docs')  / 'Docs.json'
if not DOC_FILE.exists():
    raise RuntimeError(
        f"Could not find docs file, please place a copy in {pathlib.Path(__file__).parent.absolute()}, "
        "or teach the code where yours lives."
    )

THING_FINDER_KEY = "NativeClass"
class FINDER:
    Recipe = "Class'/Script/FactoryGame.FGRecipe'"
    Item = "Class'/Script/FactoryGame.FGItemDescriptor'"
    Resource = "Class'/Script/FactoryGame.FGResourceDescriptor'"
    BioCrap = "Class'/Script/FactoryGame.FGItemDescriptorBiomass'"
    Equipement = "Class'/Script/FactoryGame.FGEquipmentDescriptor'"
    Consumable = "Class'/Script/FactoryGame.FGConsumableDescriptor'"
    Building = "Class'/Script/FactoryGame.FGBuildingDescriptor'"

ALL_NAMED = (
    FINDER.Item,
    FINDER.Resource,
    FINDER.BioCrap,
    FINDER.Equipement,
    FINDER.Consumable,
    #FINDER.Building,
)

ACTUAL_VALUES_KEY = 'Classes'

CLASS_NAME_KEY = 'ClassName'
PRINTABLE_NAME_KEY = 'mDisplayName'

INGREDIENTS_KEY = 'mIngredients'
PRODUCES_KEY = 'mProduct'
TIME_KEY = 'mManufactoringDuration'
BUILD_IN_KEY = 'mProducedIn'

def parse_ingredients_product_str(data:str, rename_d:dict) -> typing.Optional[typing.Dict[str, int]]:
    data = data.split(r'"')[1:]
    # key error will happen for building recipes, which I don't care about
    try:
        parsed_d = dict((
            (thing.split('.')[-1], int(amount.split('=')[1].split(')')[0]) )
            for thing, amount in zip(data[:-1:2], data[1::2])
        ))
        parsed_d = {rename_d.get(key, key): val for key, val in parsed_d.items()}
        return parsed_d
    except KeyError:
        return None



def get_all_recipe_kwargs() -> typing.Tuple[dict,...]:
    with open(DOC_FILE, encoding = 'utf16') as fin:
        data = json.load(fin)

    raw_recipes_l = (
        r
        for r in get_raw_data_section(data, FINDER.Recipe)
        if 'buildgun' not in r.get(BUILD_IN_KEY).lower()
    )
    item_name_translation_d = get_item_translation_d(data)
    all_recipe_kwargs = (
        {
            'ingredients_d': parse_ingredients_product_str(raw_d[INGREDIENTS_KEY], item_name_translation_d),
            'products_d': parse_ingredients_product_str(raw_d[PRODUCES_KEY], item_name_translation_d),
            'time': float(raw_d[TIME_KEY]),
            'recipe_name': raw_d[PRINTABLE_NAME_KEY],
        }
        for raw_d in raw_recipes_l
    )

    return tuple(r for r in all_recipe_kwargs if r['products_d'] is not None)  # filter out bad recipes (buildings)


def get_raw_data_section(all_data:typing.Sequence[dict], search_val:str) -> typing.Optional[typing.List[dict]]:

    for sub_d in all_data:
        if sub_d.get(THING_FINDER_KEY, None) == search_val:
            raw_data = sub_d[ACTUAL_VALUES_KEY]
            break
    else:
        print(f"Error finding {search_val}.")
        return None

    return raw_data

def get_item_translation_d(data:typing.Optional[typing.Sequence] = None) -> typing.Dict[str, str]:
    if data is None:
        with open(DOC_FILE, encoding = 'utf16') as fin:
            data = json.load(fin)

    raw_items_dl = (
        thing
        for finder in ALL_NAMED
        for thing in get_raw_data_section(data, finder)
    )

    return {
        item_d[CLASS_NAME_KEY]: item_d[PRINTABLE_NAME_KEY]
        for item_d in raw_items_dl
    }

def get_buildings(data:typing.Optional[typing.Sequence] = None) -> typing.FrozenSet[str]:
    if data is None:
        with open(DOC_FILE, encoding = 'utf16') as fin:
            data = json.load(fin)

    return frozenset(
        item_d[CLASS_NAME_KEY]
        for item_d in get_raw_data_section(data, FINDER.Building)
    )

def get_equipment(data:typing.Optional[typing.Sequence] = None) -> typing.FrozenSet[str]:
    if data is None:
        with open(DOC_FILE, encoding = 'utf16') as fin:
            data = json.load(fin)

    return frozenset(
        item_d[PRINTABLE_NAME_KEY]
        for item_d in get_raw_data_section(data, FINDER.Equipement)
        if item_d[PRINTABLE_NAME_KEY]
    )