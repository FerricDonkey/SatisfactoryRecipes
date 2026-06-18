import argparse
import fractions as fr
import pathlib

import pytest

from satisfactory_recipes.gui import app as gui_app
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


def test_parser_supports_gui_subcommand() -> None:
    args = main.make_parser().parse_args(
        [
            "gui",
            "--infile",
            "chain.json",
            "--scale",
            "1/4",
            "--docs-path",
            "en-us.json",
        ]
    )

    assert args.command == "gui"
    assert args.filename == pathlib.Path("chain.json")
    assert args.scale == fr.Fraction(1, 4)
    assert args.docs_path == pathlib.Path("en-us.json")


def test_dispatch_runs_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    args = main.make_parser().parse_args(["cli"])
    calls: list[argparse.Namespace] = []

    def fake_run_cli(parsed_args: argparse.Namespace) -> None:
        calls.append(parsed_args)

    monkeypatch.setattr(main, "run_cli", fake_run_cli)

    main.dispatch(args)

    assert calls == [args]


def test_dispatch_runs_gui(monkeypatch: pytest.MonkeyPatch) -> None:
    args = main.make_parser().parse_args(["gui"])
    calls: list[argparse.Namespace] = []

    def fake_run_gui(parsed_args: argparse.Namespace) -> None:
        calls.append(parsed_args)

    monkeypatch.setattr(main, "run_gui", fake_run_gui)

    main.dispatch(args)

    assert calls == [args]


def test_run_gui_defers_docs_resolution_to_gui_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = main.make_parser().parse_args(
        [
            "gui",
            "--docs-path",
            "en-us.json",
            "--game-path",
            "Satisfactory",
            "--infile",
            "chain.json",
            "--scale",
            "1/2",
        ]
    )
    calls: list[tuple[pathlib.Path | None, pathlib.Path | None, pathlib.Path | None]] = []

    def fake_gui_main(
        *,
        docs_path: pathlib.Path | None = None,
        game_path: pathlib.Path | None = None,
        filename: pathlib.Path | None = None,
        initial_scale: fr.Fraction = fr.Fraction(1, 1),
    ) -> int:
        assert initial_scale == fr.Fraction(1, 2)
        calls.append((docs_path, game_path, filename))
        return 0

    def fail_resolve_docs_path(_args: argparse.Namespace) -> pathlib.Path:
        raise AssertionError("GUI docs resolution should happen inside gui.app")

    monkeypatch.setattr(gui_app, "main", fake_gui_main)
    monkeypatch.setattr(main, "resolve_docs_path", fail_resolve_docs_path)

    main.run_gui(args)

    assert calls == [
        (
            pathlib.Path("en-us.json"),
            pathlib.Path("Satisfactory"),
            pathlib.Path("chain.json"),
        )
    ]
