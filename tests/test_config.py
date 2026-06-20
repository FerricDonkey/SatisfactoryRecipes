import collections.abc as cabc
import json
import pathlib

import pytest

from satisfactory_recipes import config as sr_config


def make_docs_file(base_path: pathlib.Path) -> pathlib.Path:
    docs_path = base_path / sr_config.DOCS_RELATIVE_PATH
    docs_path.parent.mkdir(parents=True)
    docs_path.write_text("[]")
    return docs_path


def test_load_malformed_config_returns_default_without_overwriting(
    tmp_path: pathlib.Path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{not json")
    warnings: list[str] = []

    loaded = sr_config.load_config(config_path=config_path, warn=warnings.append)

    assert loaded == sr_config.Configuration()
    assert "Ignoring malformed configuration file" in warnings[0]
    assert config_path.read_text() == "{not json"


def test_resolve_docs_path_uses_configured_docs_path(
    tmp_path: pathlib.Path,
) -> None:
    docs_path = tmp_path / "en-us.json"
    docs_path.write_text("[]")

    resolved = sr_config.resolve_docs_path(
        configuration=sr_config.Configuration(docs_path=docs_path),
        save=False,
    )

    assert resolved == docs_path


def test_resolve_docs_path_uses_configured_game_path(
    tmp_path: pathlib.Path,
) -> None:
    docs_path = make_docs_file(tmp_path)

    resolved = sr_config.resolve_docs_path(
        configuration=sr_config.Configuration(game_path=tmp_path),
        save=False,
    )

    assert resolved == docs_path


@pytest.mark.parametrize("filename", sr_config.DOCS_FILENAMES)
def test_docs_path_from_game_path_accepts_filename_case_variants(
    tmp_path: pathlib.Path,
    filename: str,
) -> None:
    docs_path = tmp_path / sr_config.DOCS_DIRECTORY / filename
    docs_path.parent.mkdir(parents=True)
    docs_path.write_text("[]")

    assert sr_config.docs_path_from_game_path(tmp_path) == docs_path
    assert sr_config.is_valid_docs_path(docs_path)


def test_get_common_docs_paths_generates_cross_platform_candidates() -> None:
    paths = set(sr_config.get_common_docs_paths())

    expected_game_paths = {
        pathlib.Path("C:/SteamLibrary/steamapps/common/Satisfactory"),
        pathlib.Path("/c/Program Files/Epic Games/SatisfactoryEarlyAccess"),
        pathlib.Path("/mnt/c/Program Files/Epic Games/SatisfactoryExperimental"),
        pathlib.Path.home()
        / ".local"
        / "share"
        / "Steam"
        / "steamapps"
        / "common"
        / "Satisfactory",
        pathlib.Path.home()
        / "Library"
        / "Application Support"
        / "Steam"
        / "steamapps"
        / "common"
        / "Satisfactory",
        pathlib.Path("/Users/Shared/Epic Games/Satisfactory"),
    }
    for game_path in expected_game_paths:
        for filename in sr_config.DOCS_FILENAMES:
            assert game_path / sr_config.DOCS_DIRECTORY / filename in paths


def test_resolve_docs_path_discards_stale_paths_and_saves_clean_config(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    stale_docs_path = tmp_path / "missing-en-us.json"
    stale_game_path = tmp_path / "missing-game"
    sr_config.save_config(
        sr_config.Configuration(
            docs_path=stale_docs_path,
            game_path=stale_game_path,
        ),
        config_path=config_path,
    )
    warnings: list[str] = []

    def fake_find_docs_path() -> pathlib.Path | None:
        return None

    monkeypatch.setattr(sr_config, "find_docs_path", fake_find_docs_path)

    with pytest.raises(sr_config.DocsPathNotFoundError):
        sr_config.resolve_docs_path(config_path=config_path, warn=warnings.append)

    saved = json.loads(config_path.read_text())
    assert saved == {
        "docs_path": None,
        "game_path": None,
        "gui_theme": "system",
        "gui_style": None,
        "gui_font_family": None,
        "gui_zoom_steps": 0,
    }
    assert any("Configured docs_path" in warning for warning in warnings)
    assert any("Configured game_path" in warning for warning in warnings)


def test_resolve_docs_path_finds_and_saves_discovered_path(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    docs_path = make_docs_file(tmp_path / "game")

    def fake_get_common_docs_paths() -> cabc.Iterator[pathlib.Path]:
        yield docs_path

    monkeypatch.setattr(
        sr_config,
        "get_common_docs_paths",
        fake_get_common_docs_paths,
    )

    resolved = sr_config.resolve_docs_path(config_path=config_path)

    saved = sr_config.load_config(config_path=config_path)
    assert resolved == docs_path
    assert saved.docs_path == docs_path
