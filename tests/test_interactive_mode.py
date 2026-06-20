import fractions as fr
import pathlib

import pytest

from satisfactory_recipes import interactive_mode as im
from satisfactory_recipes import production_chain as pc
from tests import support


def test_interactive_save_passes_current_game_data_scale(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goal = support.make_fake_item("Desc_Goal_C")

    game_data = support.make_fake_game_data(
        items=[goal],
        recipes=[],
        scale=fr.Fraction(1, 4),
    )

    production_chain = pc.ProductionChain(goal=goal)
    runner = im.InteractiveRunner(
        game_data=game_data,
        production_chain=production_chain,
    )

    save_path = tmp_path / "chain.json"

    def fake_get_path_no_exists(prompt: str) -> pathlib.Path:
        return save_path

    monkeypatch.setattr(
        im,
        "get_path_no_exists",
        fake_get_path_no_exists,
    )

    calls: list[tuple[pc.ProductionChain, pathlib.Path, fr.Fraction]] = []

    def fake_save(
        self: pc.ProductionChain,
        filename: pathlib.Path,
        scale: fr.Fraction,
    ) -> None:
        calls.append((self, filename, scale))

    monkeypatch.setattr(pc.ProductionChain, "save", fake_save)

    runner.save()

    assert calls == [(production_chain, save_path, fr.Fraction(1, 4))]


def test_interactive_save_cancel_does_not_save(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goal = support.make_fake_item("Desc_Goal_C")
    game_data = support.make_fake_game_data(items=[goal], recipes=[])
    production_chain = pc.ProductionChain(goal=goal)

    runner = im.InteractiveRunner(
        game_data=game_data,
        production_chain=production_chain,
    )

    def fake_get_path_no_exists(prompt: str) -> pathlib.Path:
        raise im.CancelException()

    monkeypatch.setattr(
        im,
        "get_path_no_exists",
        fake_get_path_no_exists,
    )

    called = False

    def fake_save(
        self: pc.ProductionChain,
        filename: pathlib.Path,
        scale: fr.Fraction,
    ) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(pc.ProductionChain, "save", fake_save)

    runner.save()

    assert not called
