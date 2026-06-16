"""Application entry point and top-level command line parsing."""

import argparse
import fractions as fr
import pathlib
import sys
import typing as ty

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import interactive_mode as im


def add_docs_args(
    parser: argparse.ArgumentParser,
    *,
    default: object = None,
) -> None:
    parser.add_argument(
        "--docs-path",
        help="Path to CommunityResources/Docs/en-us.json",
        default=default,
        type=pathlib.Path,
    )
    parser.add_argument(
        "--game-path",
        help="Path to the Satisfactory install directory",
        default=default,
        type=pathlib.Path,
    )


def add_cli_args(
    parser: argparse.ArgumentParser,
    *,
    filename_default: object = None,
    scale_default: object = fr.Fraction(1, 1),
) -> None:
    parser.add_argument(
        "--infile",
        dest="filename",
        help="Existing production chain file to load",
        default=filename_default,
        type=pathlib.Path,
    )
    parser.add_argument(
        "--scale",
        dest="scale",
        help="Input recipe scale",
        default=scale_default,
        type=fr.Fraction,
    )


def add_gui_args(
    parser: argparse.ArgumentParser,
    *,
    filename_default: object = None,
    scale_default: object = fr.Fraction(1, 1),
) -> None:
    parser.add_argument(
        "--infile",
        dest="filename",
        help="Existing production chain file to load",
        default=filename_default,
        type=pathlib.Path,
    )
    parser.add_argument(
        "--scale",
        dest="scale",
        help="Input recipe scale",
        default=scale_default,
        type=fr.Fraction,
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Satisfactory recipe bookkeeping")
    add_docs_args(parser)
    add_cli_args(parser)

    subparsers = parser.add_subparsers(dest="command")
    cli_parser = subparsers.add_parser("cli", help="Launch the interactive CLI")
    add_docs_args(cli_parser, default=argparse.SUPPRESS)
    add_cli_args(
        cli_parser,
        filename_default=argparse.SUPPRESS,
        scale_default=argparse.SUPPRESS,
    )
    cli_parser.set_defaults(command="cli")

    gui_parser = subparsers.add_parser("gui", help="Launch the GUI")
    add_docs_args(gui_parser, default=argparse.SUPPRESS)
    add_gui_args(
        gui_parser,
        filename_default=argparse.SUPPRESS,
        scale_default=argparse.SUPPRESS,
    )
    gui_parser.set_defaults(command="gui")

    parser.set_defaults(command="cli")

    return parser


def resolve_docs_path(args: argparse.Namespace) -> pathlib.Path:
    docs_path_arg = getattr(args, "docs_path", None)
    game_path_arg = getattr(args, "game_path", None)

    if docs_path_arg is None and game_path_arg is None:
        return sr_config.resolve_docs_path()

    configuration = sr_config.load_config()
    if docs_path_arg is not None:
        configuration.docs_path = docs_path_arg
    if game_path_arg is not None:
        configuration.game_path = game_path_arg

    return sr_config.resolve_docs_path(configuration=configuration)


def run_cli(args: argparse.Namespace) -> None:
    docs_path = resolve_docs_path(args)

    game_data = ic.GameData.from_json(docs_path)
    scale = getattr(args, "scale", fr.Fraction(1, 1))
    if scale != 1:
        game_data.scale_recipes(scale)

    try:
        filename = getattr(args, "filename", None)
        if filename is None:
            runner = im.InteractiveRunner.from_goal_prompt(game_data)
        else:
            runner = im.InteractiveRunner.from_production_chain_file(
                filename=filename,
                game_data=game_data,
            )
        runner.mainloop()
    except im.ExitInteractiveException:
        pass


def run_gui(args: argparse.Namespace) -> None:
    docs_path = resolve_docs_path(args)
    scale = getattr(args, "scale", fr.Fraction(1, 1))

    from satisfactory_recipes.gui import app as gui_app

    gui_app.main(
        docs_path=docs_path,
        filename=getattr(args, "filename", None),
        initial_scale=scale,
    )


def dispatch(args: argparse.Namespace) -> None:
    if args.command == "cli":
        run_cli(args)
        return
    if args.command == "gui":
        run_gui(args)
        return

    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: ty.Sequence[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    parser = make_parser()
    args = parser.parse_args(argv)

    try:
        dispatch(args)
    except sr_config.DocsPathNotFoundError as exc:
        parser.exit(status=1, message=f"{exc}\n")
