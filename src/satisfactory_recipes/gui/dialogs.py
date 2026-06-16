"""Reusable GUI dialogs."""

import fractions as fr
import typing as ty

from PySide6 import QtCore, QtWidgets

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import search


class ItemSearchDialog(QtWidgets.QDialog):
    """Dialog for selecting an item from a searchable list."""

    def __init__(
        self,
        *,
        items: ty.Iterable[ic.Item],
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 640)

        self._items_by_name = {item.name: item for item in items}
        self._all_names = sorted(self._items_by_name)
        self.selected_item: ic.Item | None = None

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search items")
        self.item_list = QtWidgets.QListWidget()
        self.item_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.search_edit)
        layout.addWidget(self.item_list)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.search_edit.textChanged.connect(self._refresh_items)
        self.item_list.itemSelectionChanged.connect(self._update_ok_button)
        self.item_list.itemDoubleClicked.connect(self._accept_item)
        buttons.accepted.connect(self._accept_selected_item)
        buttons.rejected.connect(self.reject)

        self._refresh_items("")

    def _refresh_items(self, text: str) -> None:
        if text:
            names = search.sort_options(self._all_names, text)
        else:
            names = self._all_names

        self.item_list.clear()
        for name in names:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, self._items_by_name[name])
            self.item_list.addItem(item)

        if self.item_list.count():
            self.item_list.setCurrentRow(0)

    def _update_ok_button(self) -> None:
        self.ok_button.setEnabled(bool(self.item_list.selectedItems()))

    def _accept_item(self, item: QtWidgets.QListWidgetItem) -> None:
        self.selected_item = ty.cast(
            ic.Item,
            item.data(QtCore.Qt.ItemDataRole.UserRole),
        )
        self.accept()

    def _accept_selected_item(self) -> None:
        selected_items = self.item_list.selectedItems()
        if selected_items:
            self._accept_item(selected_items[0])


def choose_goal_item(
    *,
    game_data: ic.GameData,
    parent: QtWidgets.QWidget | None = None,
) -> ic.Item | None:
    dialog = ItemSearchDialog(
        items=game_data.producible_items,
        title="Choose Goal Item",
        parent=parent,
    )
    result = dialog.exec()
    if result == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.selected_item
    return None


def choose_item_from_items(
    *,
    items: ty.Iterable[ic.Item],
    title: str,
    parent: QtWidgets.QWidget | None = None,
) -> ic.Item | None:
    dialog = ItemSearchDialog(
        items=items,
        title=title,
        parent=parent,
    )
    result = dialog.exec()
    if result == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.selected_item
    return None


class RecipeSearchDialog(QtWidgets.QDialog):
    """Dialog for selecting a recipe from a searchable list."""

    def __init__(
        self,
        *,
        recipes: ty.Iterable[ic.Recipe],
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 640)

        self._recipes_by_name = {recipe.name: recipe for recipe in recipes}
        self._all_names = sorted(self._recipes_by_name)
        self.selected_recipe: ic.Recipe | None = None

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search recipes")
        self.recipe_list = QtWidgets.QListWidget()
        self.recipe_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.details = QtWidgets.QPlainTextEdit()
        self.details.setReadOnly(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.recipe_list)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.search_edit)
        layout.addWidget(splitter)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.search_edit.textChanged.connect(self._refresh_recipes)
        self.recipe_list.itemSelectionChanged.connect(self._update_selection)
        self.recipe_list.itemDoubleClicked.connect(self._accept_recipe)
        buttons.accepted.connect(self._accept_selected_recipe)
        buttons.rejected.connect(self.reject)

        self._refresh_recipes("")

    def _refresh_recipes(self, text: str) -> None:
        if text:
            names = search.sort_options(self._all_names, text)
        else:
            names = self._all_names

        self.recipe_list.clear()
        for name in names:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, self._recipes_by_name[name])
            self.recipe_list.addItem(item)

        if self.recipe_list.count():
            self.recipe_list.setCurrentRow(0)

    def _update_selection(self) -> None:
        selected_items = self.recipe_list.selectedItems()
        self.ok_button.setEnabled(bool(selected_items))
        if not selected_items:
            self.details.clear()
            return

        recipe = ty.cast(
            ic.Recipe,
            selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole),
        )
        self.details.setPlainText(recipe.make_pretty_str())

    def _accept_recipe(self, item: QtWidgets.QListWidgetItem) -> None:
        self.selected_recipe = ty.cast(
            ic.Recipe,
            item.data(QtCore.Qt.ItemDataRole.UserRole),
        )
        self.accept()

    def _accept_selected_recipe(self) -> None:
        selected_items = self.recipe_list.selectedItems()
        if selected_items:
            self._accept_recipe(selected_items[0])


def choose_recipe(
    *,
    recipes: ty.Iterable[ic.Recipe],
    title: str,
    parent: QtWidgets.QWidget | None = None,
) -> ic.Recipe | None:
    dialog = RecipeSearchDialog(
        recipes=recipes,
        title=title,
        parent=parent,
    )
    result = dialog.exec()
    if result == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.selected_recipe
    return None


def get_positive_fraction(
    *,
    title: str,
    label: str,
    parent: QtWidgets.QWidget | None = None,
) -> fr.Fraction | None:
    while True:
        value, ok = QtWidgets.QInputDialog.getText(parent, title, label)
        if not ok:
            return None

        try:
            amount = fr.Fraction(value)
        except ValueError:
            QtWidgets.QMessageBox.warning(
                parent,
                "Invalid Amount",
                "Enter a positive number or fraction.",
            )
            continue

        if amount > 0:
            return amount

        QtWidgets.QMessageBox.warning(
            parent,
            "Invalid Amount",
            "Enter a positive number or fraction.",
        )
