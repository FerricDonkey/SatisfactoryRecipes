"""Application entry point and top-level command line parsing."""

import argparse
import fractions as fr
import pathlib
import sys
import typing as ty

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import interactive_mode as im


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive production planner")
    parser.add_argument(
        "--infile",
        dest="filename",
        help="Existing production chain file to load",
        default=None,
        type=pathlib.Path,
    )
    parser.add_argument(
        "--scale",
        dest="scale",
        help="Input recipe scale",
        default=fr.Fraction(1, 1),
        type=fr.Fraction,
    )
    parser.add_argument(
        "--docs-path",
        help="Path to CommunityResources/Docs/en-us.json",
        default=None,
        type=pathlib.Path,
    )
    parser.add_argument(
        "--game-path",
        help="Path to the Satisfactory install directory",
        default=None,
        type=pathlib.Path,
    )

    return parser


def main(argv: ty.Sequence[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    parser = make_parser()
    args = parser.parse_args(argv)

    try:
        if args.docs_path is None and args.game_path is None:
            docs_path = sr_config.resolve_docs_path()
        else:
            configuration = sr_config.load_config()
            if args.docs_path is not None:
                configuration.docs_path = args.docs_path
            if args.game_path is not None:
                configuration.game_path = args.game_path

            docs_path = sr_config.resolve_docs_path(configuration=configuration)
    except sr_config.DocsPathNotFoundError as exc:
        parser.exit(status=1, message=f"{exc}\n")

    game_data = ic.GameData.from_json(docs_path)
    if args.scale != 1:
        game_data.scale_recipes(args.scale)

    try:
        if args.filename is None:
            runner = im.InteractiveRunner.from_goal_prompt(game_data)
        else:
            runner = im.InteractiveRunner.from_production_chain_file(
                filename=args.filename,
                game_data=game_data,
            )
        runner.mainloop()
    except im.ExitInteractiveException:
        pass
