import argparse
import collections.abc as cabc
import dataclasses
import fractions as fr
import functools
import pathlib
import sys
import traceback
import typing as ty

from . import info_classes as ic
from . import production_chain as pc

MAX_DISPLAY_OPTIONS = 10
QUIT_COMMANDS = ("exit", "quit")
CANCEL_COMMANDS = ("cancel",)


class _SupportsName(ty.Protocol):
    @property
    def name(self) -> str: ...


class _WeDoneException(Exception):
    """
    Raised to end interaction session from anywhere via exceptional_input.

    (entire thing should be wrapped in a try except that grabs this)
    """


class _CancelException(Exception):
    """
    Raised to cancel particular function calls via exceptional_input.

    Cancelable portions of a command should be wrapped in a try except that
    handles this. If an input cannot be canceled, suggest using exceptional_input
    with can_cancel=False
    """


def exceptional_input(
    prompt: str,
    can_cancel: bool = True,
) -> str:
    value = input(prompt)
    if value in QUIT_COMMANDS:
        raise _WeDoneException()
    if value in CANCEL_COMMANDS:
        if can_cancel:
            raise _CancelException()
        else:
            print("Cannot Cancel.")
            return exceptional_input(prompt, can_cancel=can_cancel)

    return value


def get_path_no_exists(prompt: str) -> pathlib.Path:
    while True:
        path = pathlib.Path(exceptional_input(f"{prompt}:"))
        if path.exists():
            print(f"Can't use {path}, that exists and we don't overwrite things")
            continue
        return path


def get_path_exists(prompt: str) -> pathlib.Path:
    while True:
        path = pathlib.Path(exceptional_input(f"{prompt}:"))
        if not path.exists():
            print(f"{path} does not exist")
            continue
        return path


def get_positive_float(prompt: str) -> fr.Fraction:
    while True:
        try:
            value = fr.Fraction(exceptional_input(f"{prompt}: "))
        except ValueError:
            continue
        if value > 0:
            return value


def _cancelable_decorator[**P](func: ty.Callable[P, None]) -> ty.Callable[P, None]:
    """
    Decorator to capture CancelException and return None if it is raised.

    ONLY USE IF CancelException WILL ONLY BE RAISED AT TIMES WHEN THIS IS OK.
    """

    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            return func(*args, **kwargs)
        except _CancelException:
            return None

    return wrapped


def choose_bounded_int(
    prompt: str,
    lower: int,
    upper: int,
) -> int:
    """
    Prompt for an integer such that lower <= integer < upper.

    Works like range, under the assumption that it will usually be used to
    select an index from a list of known length
    """
    while True:
        try:
            index = int(exceptional_input(f"{prompt}: "))
        except ValueError:
            continue
        if lower <= index < upper:
            return index


def choose_named[T: _SupportsName](
    items: cabc.Sequence[T],
    prompt: str = "Choose an option",
) -> T:
    print(f"{prompt}:")
    index_len = len(f"{len(items) - 1}")
    for index, item in enumerate(items):
        print(f"    {index:>{index_len}} - {item.name}")

    chosen_index = choose_bounded_int("Select index", 0, len(items))
    return items[chosen_index]


def _match_score(target: str, key: str) -> int:
    """
    How much key matches target. Higher is better
    """

    def mini_score(targ: str, k: str) -> int:
        score = 0
        for c1, c2 in zip(targ, k):
            if c1.lower() != c2.lower():
                break
            score += 1
        return score

    scores: list[int] = []
    while target:
        scores.append(mini_score(target, key))
        target = " ".join(target.split()[1:])
    return max(scores)


def _sort_options(options: ty.Iterable[str], entry: str) -> list[str]:
    # NOTE: better matches first
    def key_func(option: str):
        return (
            -(option.lower() == entry.lower()),
            -(option.lower().startswith(entry.lower())),
            -_match_score(option, entry),
            option,
        )

    return [opt for opt in sorted(options, key=key_func) if _match_score(opt, entry)]


def get_arbitrary_item(
    game_data: ic.GameData,
    must_be_producible: bool,
    prompt: str = "Enter an item",
) -> ic.Item:
    if must_be_producible:
        item_name_d = game_data.producible_item_name_d
    else:
        item_name_d = game_data.item_name_d

    options: list[str] = []
    while True:
        item_name = exceptional_input(f"{prompt}: ")
        if not item_name:
            continue
        if item_name.isdigit():
            item_index = int(item_name)
            if 0 <= item_index < min(MAX_DISPLAY_OPTIONS, len(options)):
                return game_data.item_name_d[options[item_index]]
            continue

        item = item_name_d.get(item_name)
        if item is not None:
            return item

        options = _sort_options(item_name_d.keys(), item_name)
        if options:
            print("Did you mean:")
            for index, option in enumerate(options[:MAX_DISPLAY_OPTIONS]):
                print(f"{index} - {option}")
            print()

    assert False, "unreachable code reached"


@dataclasses.dataclass(kw_only=True, slots=True)
class InteractiveRunner:
    game_data: ic.GameData
    production_chain: pc.ProductionChain

    @_cancelable_decorator
    def add_recipe_for_shortage_item(self) -> None:
        items = self.production_chain.get_shortage_items()
        if not items:
            print("No shortage items to add")
            return

        item = choose_named(
            sorted(items, key=lambda it: it.name.lower()),
            "Choose item to add recipe",
        )
        recipes = self.game_data.get_recipes_producing(item)
        recipes.sort(key=lambda r: (r.name.startswith("Alternate"), r.name.lower()))

        print("Available Recipes\n===========================================")
        for recipe in recipes:
            recipe.print(indent=4)
            print()

        recipe = choose_named(recipes)
        self.production_chain.add_scaled_recipe(recipe, item)
        print("New Recipe:")
        recipe.print(indent=4, scale=self.production_chain.recipes[recipe])

    @_cancelable_decorator
    def add_goal_recipe(self) -> None:
        recipes = self.game_data.get_recipes_producing(self.production_chain.goal)
        recipes.sort(key=lambda r: (r.name.startswith("Alternate"), r.name.lower()))

        print("Available Recipes\n===========================")
        for recipe in recipes:
            recipe.print(indent=4)
            print()

        recipe = choose_named(recipes)
        per_min = get_positive_float(
            f"How many {self.production_chain.goal.name} per minute with this recipe"
        )
        count = per_min / recipe.products_per_min[self.production_chain.goal]
        self.production_chain.recipes[recipe] = count
        print("New Recipe:")
        recipe.print(indent=4, scale=self.production_chain.recipes[recipe])

    @_cancelable_decorator
    def scale_item(self) -> None:
        if not self.production_chain.recipes:
            print("Cannot scale before adding recipes")
            return

        item = choose_named(
            items=sorted(
                self.production_chain.get_involved_items(),
                key=lambda it: it.name.lower(),
            ),
            prompt="Chose item to scale",
        )
        amount = get_positive_float(
            f"Enter new amount of {item.name} to produce/consume"
        )
        self.production_chain.scale_item(item, amount)

    @_cancelable_decorator
    def clear_recipes(self) -> None:
        self.production_chain.recipes.clear()

    @_cancelable_decorator
    def remove_recipe(self) -> None:
        recipe = choose_named(
            sorted(
                self.production_chain.recipes.keys(),
                key=lambda it: it.name.lower(),
            )
        )
        del self.production_chain.recipes[recipe]

    def print_state(self) -> None:
        print("\n")
        self.production_chain.print()

    @_cancelable_decorator
    def save(self) -> None:
        path = get_path_no_exists("Enter path to save data")
        try:
            self.production_chain.save(path)
            print(f"Saved to {path.resolve()}\n")
        except Exception:
            traceback.print_exc()
            print(f"\nCould not save to {path}. See above traceback for details")

    @_cancelable_decorator
    def load(self) -> None:
        path = get_path_exists("Enter path to load data")
        try:
            new_chain = pc.ProductionChain.load(
                filename=path,
                game_data=self.game_data,
            )
            self.production_chain = new_chain
        except Exception:
            traceback.print_exc()
            print(f"\nCould not load {path}. See above traceback for details")

    @classmethod
    def from_production_chain_file(
        cls,
        filename: pathlib.Path,
        game_data: ic.GameData,
    ) -> ty.Self:
        return cls(
            game_data=game_data,
            production_chain=pc.ProductionChain.load(
                filename=filename,
                game_data=game_data,
            ),
        )

    @classmethod
    def from_goal_prompt(cls, game_data: ic.GameData) -> ty.Self:
        goal = get_arbitrary_item(
            game_data=game_data,
            must_be_producible=True,
            prompt="Choose Item to Produce",
        )
        return cls.from_starting_item(
            game_data=game_data,
            item=goal,
        )

    @classmethod
    def from_starting_item(cls, game_data: ic.GameData, item: ic.Item) -> ty.Self:
        """Create with a specified goal."""
        assert item in game_data.producible_items
        return cls(
            game_data=game_data,
            production_chain=pc.ProductionChain(
                goal=item,
            ),
        )

    def print_help(self) -> None:
        print("OPTIONS:")
        for option in self._DISPATCH_TABLE:
            print(f"    {option}")
        print('\nType "quit" to quit. Type "cancel" during any command to cancel.\n')

    def mainloop(self) -> None:
        print(
            '\nType "help" to see commands. For any command, type "cancel" to '
            'cancel. Type "quit" to quit.'
        )
        try:
            while True:
                command_str = exceptional_input('\nEnter command (eg "help"): ').strip()
                command = self._DISPATCH_TABLE.get(command_str)
                if command is None:
                    print(f"Invalid command {command_str}")
                else:
                    command(self)
        except _WeDoneException:
            pass

    _DISPATCH_TABLE: ty.ClassVar[dict[str, ty.Callable[[InteractiveRunner], None]]] = {
        "add-recipe-shortage": add_recipe_for_shortage_item,
        "add-recipe-goal": add_goal_recipe,
        "scale-item": scale_item,
        "remove-recipe": remove_recipe,
        "clear-recipes": clear_recipes,
        "print": print_state,
        "help": print_help,
        "save": save,
        "load": load,
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive production planner")
    parser.add_argument(
        "--infile",
        dest="filename",
        help="- Existing file to load, if any",
        default=None,
    )

    return parser


def main(argv: ty.Sequence[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]

    parser = make_parser()
    args = parser.parse_args(argv)

    game_data = ic.GameData.from_json(ic.DOCS_PATH)
    try:
        if args.filename is None:
            runner = InteractiveRunner.from_goal_prompt(game_data)
        else:
            runner = InteractiveRunner.from_production_chain_file(
                filename=args.filename,
                game_data=game_data,
            )
        runner.mainloop()
    except _WeDoneException:
        pass


if __name__ == "__main__":
    main()
