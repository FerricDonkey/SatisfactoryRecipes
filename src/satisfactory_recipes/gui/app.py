"""GUI application bootstrap."""

import fractions as fr
import pathlib
import sys

from PySide6 import QtCore, QtWidgets

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes.gui import main_window


def main(
    *,
    docs_path: pathlib.Path,
    filename: pathlib.Path | None = None,
    initial_scale: fr.Fraction = fr.Fraction(1, 1),
) -> int:
    app = QtWidgets.QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])

    game_data = ic.GameData.from_json(docs_path)
    production_chain = None
    if filename is not None:
        production_chain = pc.ProductionChain.load(filename, game_data)
    elif initial_scale != 1:
        game_data.scale_recipes(initial_scale)

    window = main_window.MainWindow(
        docs_path=docs_path,
        game_data=game_data,
        production_chain=production_chain,
        filename=filename,
    )
    window.show()

    if production_chain is None:
        QtCore.QTimer.singleShot(0, window.prompt_for_goal_if_needed)

    if owns_app:
        return app.exec()

    return 0
