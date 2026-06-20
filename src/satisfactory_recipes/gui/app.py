"""GUI application bootstrap."""

from __future__ import annotations

import fractions as fr
import pathlib
import sys

from PySide6 import QtCore, QtWidgets

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import docs_parser
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes.gui import dialogs
from satisfactory_recipes.gui import main_window


QtCore.QLoggingCategory.setFilterRules("qt.qpa.fonts.warning=false")


def deployment_smoke_test() -> None:
    """Construct and briefly show the real main window without external data."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(["satisfactory-recipes-smoke-test"])

    window = main_window.MainWindow(
        docs_path=pathlib.Path("deployment-smoke-test-en-US.json"),
        game_data=ic.GameData(buildings_d={}, items_d={}, recipes_d={}),
        user_config=sr_config.Configuration(),
    )
    window.show()
    app.processEvents()
    if not window.isVisible():
        raise RuntimeError("Deployment smoke-test window did not become visible")
    window.close()
    app.processEvents()


def _resolve_docs_path_for_gui(
    *,
    docs_path: pathlib.Path | None,
    game_path: pathlib.Path | None,
    user_config: sr_config.Configuration,
) -> tuple[pathlib.Path, sr_config.Configuration] | None:
    warnings: list[str] = []
    user_config, changed = sr_config.discard_invalid_paths(
        user_config,
        warn=warnings.append,
    )

    if docs_path is not None:
        user_config.docs_path = docs_path
    if game_path is not None:
        user_config.game_path = game_path

    try:
        resolved_docs_path = sr_config.resolve_docs_path(
            configuration=user_config,
            warn=warnings.append,
        )
    except sr_config.DocsPathNotFoundError as exc:
        message = str(exc)
        if warnings:
            message = "\n\n".join([*warnings, message])

        selection = dialogs.choose_docs_path(message=message)
        if selection is None:
            return None

        user_config.docs_path = selection.docs_path
        user_config.game_path = selection.game_path
        sr_config.save_config(user_config)
        return selection.docs_path, user_config

    user_config.docs_path = resolved_docs_path
    if game_path is not None:
        user_config.game_path = game_path
    if changed or docs_path is not None or game_path is not None:
        sr_config.save_config(user_config)

    return resolved_docs_path, user_config


def main(
    *,
    docs_path: pathlib.Path | None = None,
    game_path: pathlib.Path | None = None,
    filename: pathlib.Path | None = None,
    initial_scale: fr.Fraction = fr.Fraction(1, 1),
) -> int:
    app = QtWidgets.QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])

    user_config = sr_config.load_config()
    docs_resolution = _resolve_docs_path_for_gui(
        docs_path=docs_path,
        game_path=game_path,
        user_config=user_config,
    )
    if docs_resolution is None:
        return 1

    docs_path, user_config = docs_resolution
    game_data = docs_parser.load_game_data(docs_path)
    production_chain = None
    if filename is not None:
        production_chain = pc.ProductionChain.load(filename, game_data)
    elif initial_scale != 1:
        game_data.scale_recipes(initial_scale)

    window = main_window.MainWindow(
        docs_path=docs_path,
        game_data=game_data,
        user_config=user_config,
        production_chain=production_chain,
        filename=filename,
    )
    window.show()

    if production_chain is None:
        QtCore.QTimer.singleShot(0, window.prompt_for_goal_if_needed)

    if owns_app:
        return app.exec()

    return 0
