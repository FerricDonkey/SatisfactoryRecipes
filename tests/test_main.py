import argparse
import fractions as fr
import pathlib

import pytest

from satisfactory_recipes import main


def test_parser_defaults_to_cli() -> None:
    args = main.make_parser().parse_args([])

    assert args.command == "cli"
    assert args.filename is None
    assert args.scale == fr.Fraction(1, 1)
    assert args.docs_path is None
    assert args.game_path is None


def test_parser_supports_legacy_cli_options_without_subcommand() -> None:
    args = main.make_parser().parse_args(
        [
            "--infile",
            "chain.json",
            "--scale",
            "1/4",
            "--docs-path",
            "en-us.json",
        ]
    )

    assert args.command == "cli"
    assert args.filename == pathlib.Path("chain.json")
    assert args.scale == fr.Fraction(1, 4)
    assert args.docs_path == pathlib.Path("en-us.json")


def test_parser_supports_cli_subcommand() -> None:
    args = main.make_parser().parse_args(
        [
            "cli",
            "--infile",
            "chain.json",
            "--scale",
            "1/4",
            "--game-path",
            "Satisfactory",
        ]
    )

    assert args.command == "cli"
    assert args.filename == pathlib.Path("chain.json")
    assert args.scale == fr.Fraction(1, 4)
    assert args.game_path == pathlib.Path("Satisfactory")


def test_dispatch_runs_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    args = main.make_parser().parse_args(["cli"])
    calls: list[argparse.Namespace] = []

    def fake_run_cli(parsed_args: argparse.Namespace) -> None:
        calls.append(parsed_args)

    monkeypatch.setattr(main, "run_cli", fake_run_cli)

    main.dispatch(args)

    assert calls == [args]
