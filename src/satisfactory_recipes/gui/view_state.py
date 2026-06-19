"""Presentation data derived from the current production-chain session."""

import dataclasses
import fractions as fr
import pathlib

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc

type ItemRates = tuple[tuple[ic.Item, fr.Fraction], ...]
type RecipeCounts = tuple[tuple[ic.Recipe, fr.Fraction], ...]


@dataclasses.dataclass(frozen=True, slots=True)
class MainWindowViewState:
    """Immutable display data for one main-window refresh."""

    goal: ic.Item | None
    recipe_scale: fr.Fraction
    status_text: str
    recipes: RecipeCounts
    inputs: ItemRates
    outputs: ItemRates
    can_add_goal_recipe: bool
    can_add_shortage_recipe: bool


def build_main_window_view_state(
    *,
    chain: pc.ProductionChain | None,
    game_data: ic.GameData,
    filename: pathlib.Path | None,
    has_unsaved_changes: bool,
) -> MainWindowViewState:
    """Compute all display data with a single production-chain net calculation."""
    if chain is None:
        return MainWindowViewState(
            goal=None,
            recipe_scale=game_data.scale,
            status_text="Choose Set Goal or File > New to select a goal item.",
            recipes=(),
            inputs=(),
            outputs=(),
            can_add_goal_recipe=False,
            can_add_shortage_recipe=False,
        )

    recipes = tuple(
        sorted(chain.recipes.items(), key=lambda pair: pair[0].name.lower())
    )
    net_rates = chain.get_net_per_min()
    inputs = tuple(
        sorted(
            ((item, -amount) for item, amount in net_rates.items() if amount < 0),
            key=lambda pair: pair[0].name.lower(),
        )
    )
    outputs = tuple(
        sorted(
            ((item, amount) for item, amount in net_rates.items() if amount > 0),
            key=lambda pair: pair[0].name.lower(),
        )
    )
    producible_items = set(game_data.producible_items)
    displayed_filename = filename if filename is not None else "Unsaved"
    unsaved_marker = " *" if has_unsaved_changes else ""
    return MainWindowViewState(
        goal=chain.goal,
        recipe_scale=game_data.scale,
        status_text=f"File: {displayed_filename}{unsaved_marker}",
        recipes=recipes,
        inputs=inputs,
        outputs=outputs,
        can_add_goal_recipe=True,
        can_add_shortage_recipe=any(
            item in producible_items for item, _amount in inputs
        ),
    )
