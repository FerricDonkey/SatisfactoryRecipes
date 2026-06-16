"""User configuration and Satisfactory docs discovery."""

import collections.abc as cabc
import pathlib
import string
import sys

import platformdirs as pfd
import pydantic

APP_NAME = "satisfactory-recipes"
CONFIG_FILENAME = "config.json"
DOCS_RELATIVE_PATH = pathlib.Path("CommunityResources") / "Docs" / "en-us.json"

type WarnFunc = cabc.Callable[[str], None]


class DocsPathNotFoundError(FileNotFoundError):
    """Raised when the Satisfactory docs file cannot be found."""


class Configuration(pydantic.BaseModel):
    """Persisted user preferences."""

    model_config = pydantic.ConfigDict(extra="forbid")

    docs_path: pathlib.Path | None = None
    game_path: pathlib.Path | None = None


def _default_warn(message: str) -> None:
    print(message, file=sys.stderr)


def _emit_warning(warn: WarnFunc | None, message: str) -> None:
    (warn or _default_warn)(message)


def get_config_path() -> pathlib.Path:
    return pfd.user_config_path(APP_NAME, ensure_exists=True) / CONFIG_FILENAME


def _load_config_with_save_permission(
    config_path: pathlib.Path,
    warn: WarnFunc | None = None,
) -> tuple[Configuration, bool]:
    if not config_path.exists():
        return Configuration(), True

    try:
        return Configuration.model_validate_json(config_path.read_text()), True
    except pydantic.ValidationError as exc:
        _emit_warning(
            warn,
            f"Ignoring malformed configuration file {config_path}:\n{exc}",
        )
    except OSError as exc:
        _emit_warning(
            warn,
            f"Could not read configuration file {config_path}: {exc}",
        )

    return Configuration(), False


def load_config(
    config_path: pathlib.Path | None = None,
    warn: WarnFunc | None = None,
) -> Configuration:
    """Load saved configuration, returning defaults if the file cannot be used."""
    if config_path is None:
        config_path = get_config_path()

    config, _can_save = _load_config_with_save_permission(config_path, warn=warn)
    return config


def save_config(
    config: Configuration,
    config_path: pathlib.Path | None = None,
    warn: WarnFunc | None = None,
) -> None:
    if config_path is None:
        config_path = get_config_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config.model_dump_json(indent=2))
    except OSError as exc:
        _emit_warning(
            warn,
            f"Could not save configuration file {config_path}: {exc}",
        )


def docs_path_from_game_path(game_path: pathlib.Path) -> pathlib.Path:
    return game_path / DOCS_RELATIVE_PATH


def is_valid_docs_path(docs_path: pathlib.Path) -> bool:
    return docs_path.expanduser().is_file() and docs_path.name == "en-us.json"


def is_valid_game_path(game_path: pathlib.Path) -> bool:
    return is_valid_docs_path(docs_path_from_game_path(game_path.expanduser()))


def discard_invalid_paths(
    config: Configuration,
    warn: WarnFunc | None = None,
) -> tuple[Configuration, bool]:
    """Remove stale paths while keeping schema validation separate."""
    changed = False
    docs_path = config.docs_path
    game_path = config.game_path

    if docs_path is not None and not is_valid_docs_path(docs_path):
        _emit_warning(
            warn,
            "Configured docs_path does not point to "
            f"CommunityResources/Docs/en-us.json and will be ignored: {docs_path}",
        )
        docs_path = None
        changed = True

    if game_path is not None and not is_valid_game_path(game_path):
        _emit_warning(
            warn,
            "Configured game_path does not contain "
            f"{DOCS_RELATIVE_PATH} and will be ignored: {game_path}",
        )
        game_path = None
        changed = True

    return config.model_copy(
        update={
            "docs_path": docs_path,
            "game_path": game_path,
        }
    ), changed


def get_common_docs_paths() -> list[pathlib.Path]:
    paths: list[pathlib.Path] = []
    for drive in string.ascii_uppercase:
        root = pathlib.Path(f"{drive}:/")
        candidates = [
            root / "SteamLibrary" / "steamapps" / "common" / "Satisfactory",
            root
            / "Program Files (x86)"
            / "Steam"
            / "steamapps"
            / "common"
            / "Satisfactory",
            root
            / "Program Files"
            / "Steam"
            / "steamapps"
            / "common"
            / "Satisfactory",
        ]
        paths.extend(docs_path_from_game_path(path) for path in candidates)

    return paths


def find_docs_path() -> pathlib.Path | None:
    for docs_path in get_common_docs_paths():
        if is_valid_docs_path(docs_path):
            return docs_path
    return None


def resolve_docs_path(
    *,
    config_path: pathlib.Path | None = None,
    configuration: Configuration | None = None,
    warn: WarnFunc | None = None,
    save: bool = True,
) -> pathlib.Path:
    if config_path is None:
        config_path = get_config_path()

    if configuration is None:
        config, can_save = _load_config_with_save_permission(config_path, warn=warn)
    else:
        config = configuration
        can_save = save

    config, changed = discard_invalid_paths(config, warn=warn)

    if config.docs_path is not None:
        if changed and can_save and save:
            save_config(config, config_path=config_path, warn=warn)
        return config.docs_path.expanduser()

    if config.game_path is not None:
        if changed and can_save and save:
            save_config(config, config_path=config_path, warn=warn)
        return docs_path_from_game_path(config.game_path.expanduser())

    found_docs_path = find_docs_path()
    if found_docs_path is not None:
        config = config.model_copy(update={"docs_path": found_docs_path})
        if can_save and save:
            save_config(config, config_path=config_path, warn=warn)
        return found_docs_path

    if changed and can_save and save:
        save_config(config, config_path=config_path, warn=warn)

    raise DocsPathNotFoundError(
        "Could not find Satisfactory docs file. Configure docs_path to point "
        "to CommunityResources/Docs/en-us.json, or configure game_path to "
        "point to the Satisfactory install directory."
    )
