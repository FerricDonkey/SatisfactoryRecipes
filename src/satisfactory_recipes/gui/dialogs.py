"""Application dialogs composed from reusable selection and input widgets."""

from __future__ import annotations

import dataclasses
import enum
import fractions as fr
import pathlib
import typing as ty

from PySide6 import QtWidgets

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes.gui import dialog_components, recipe_format


class GoalDialogAction(enum.Enum):
    LOAD_FILE = enum.auto()


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class InitialGoalSelection:
    item: ic.Item
    amount_per_min: fr.Fraction


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class RecipeSelection:
    recipe: ic.Recipe
    amount_per_min: fr.Fraction


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class DocsPathSelection:
    docs_path: pathlib.Path
    game_path: pathlib.Path | None = None


class DocsPathDialog(QtWidgets.QDialog):
    """Dialog for locating the Satisfactory docs file."""

    def __init__(
        self,
        *,
        message: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Find Satisfactory Game Data")
        self.resize(640, 260)

        self.selected_docs_path: pathlib.Path | None = None
        self.selected_game_path: pathlib.Path | None = None

        intro_label = QtWidgets.QLabel(
            "Satisfactory Recipes needs the game docs file before it can load "
            "items and recipes."
        )
        intro_label.setWordWrap(True)

        detail_label = QtWidgets.QLabel(message)
        detail_label.setWordWrap(True)

        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText(
            "CommunityResources/Docs/en-us.json has not been selected"
        )

        choose_docs_button = QtWidgets.QPushButton("Choose Docs File...")
        choose_game_button = QtWidgets.QPushButton("Choose Game Folder...")
        choose_docs_button.clicked.connect(self._choose_docs_file)
        choose_game_button.clicked.connect(self._choose_game_folder)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        chooser_layout = QtWidgets.QHBoxLayout()
        chooser_layout.addWidget(choose_docs_button)
        chooser_layout.addWidget(choose_game_button)
        chooser_layout.addStretch()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(intro_label)
        layout.addWidget(detail_label)
        layout.addWidget(self.path_edit)
        layout.addLayout(chooser_layout)
        layout.addStretch()
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _choose_docs_file(self) -> None:
        filename, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose Satisfactory Docs File",
            "",
            "Satisfactory Docs (en-us.json);;JSON Files (*.json);;All Files (*)",
        )
        if not filename:
            return

        docs_path = pathlib.Path(filename)
        if not sr_config.is_valid_docs_path(docs_path):
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Docs File",
                "Choose the Satisfactory CommunityResources/Docs/en-us.json file.",
            )
            return

        self._set_selection(docs_path=docs_path, game_path=None)

    def _choose_game_folder(self) -> None:
        dirname = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose Satisfactory Install Folder",
            "",
        )
        if not dirname:
            return

        game_path = pathlib.Path(dirname)
        if not sr_config.is_valid_game_path(game_path):
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Game Folder",
                "Choose the Satisfactory install folder containing "
                "CommunityResources/Docs/en-us.json.",
            )
            return

        self._set_selection(
            docs_path=sr_config.docs_path_from_game_path(game_path),
            game_path=game_path,
        )

    def _set_selection(
        self,
        *,
        docs_path: pathlib.Path,
        game_path: pathlib.Path | None,
    ) -> None:
        self.selected_docs_path = docs_path
        self.selected_game_path = game_path
        self.path_edit.setText(str(docs_path))
        self.ok_button.setEnabled(True)


def choose_docs_path(
    *,
    message: str,
    parent: QtWidgets.QWidget | None = None,
) -> DocsPathSelection | None:
    dialog = DocsPathDialog(message=message, parent=parent)
    result = dialog.exec()
    if result != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    if dialog.selected_docs_path is None:
        return None

    return DocsPathSelection(
        docs_path=dialog.selected_docs_path,
        game_path=dialog.selected_game_path,
    )


class _SearchDialog[T](QtWidgets.QDialog):
    """Shared composition and acceptance behavior for search dialogs."""

    def __init__(
        self,
        *,
        options: ty.Iterable[dialog_components.SelectionOption[T]],
        title: str,
        search_placeholder: str,
        size: tuple[int, int],
        show_amount: bool,
        unfiltered_sort_key: ty.Callable[
            [dialog_components.SelectionOption[T]], tuple[bool, str]
        ]
        | None = None,
        detail_widget: QtWidgets.QWidget | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(*size)

        self.selected_object: T | None = None
        self.selected_amount_per_min: fr.Fraction | None = None
        self.selection_widget = dialog_components.SearchableSelectionList(
            options=options,
            search_placeholder=search_placeholder,
            unfiltered_sort_key=unfiltered_sort_key,
            detail_widget=detail_widget,
        )
        self.search_edit = self.selection_widget.search_edit

        self.amount_input: dialog_components.PositiveFractionInput | None = None
        self.amount_edit: QtWidgets.QLineEdit | None = None
        if show_amount:
            self.amount_input = dialog_components.PositiveFractionInput(
                label="Per minute",
                initial_text="100",
            )
            self.amount_edit = self.amount_input.line_edit

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        self.ok_button.setEnabled(False)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.selection_widget)
        if self.amount_input is not None:
            layout.addWidget(self.amount_input)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.selection_widget.selection_changed.connect(self._update_ok_button)
        self.selection_widget.selection_activated.connect(self._accept_object)
        self.button_box.accepted.connect(self._accept_selected_object)
        self.button_box.rejected.connect(self.reject)
        self._update_ok_button(self.selection_widget.selected_object)

    def _update_ok_button(self, selection: object | None = None) -> None:
        self.ok_button.setEnabled(selection is not None)

    def _accept_object(self, selected_object: object) -> None:
        amount = self._get_amount_if_needed()
        if amount is None and self.amount_input is not None:
            return

        selected = ty.cast("T", selected_object)
        self.selected_object = selected
        self.selected_amount_per_min = amount
        self._store_selected_object(selected)
        self.accept()

    def _accept_selected_object(self) -> None:
        selected_object = self.selection_widget.selected_object
        if selected_object is not None:
            self._accept_object(selected_object)

    def _get_amount_if_needed(self) -> fr.Fraction | None:
        if self.amount_input is None:
            return None
        return self.amount_input.value_or_warn(parent=self)

    def _store_selected_object(self, selected_object: T) -> None:
        raise NotImplementedError


class ItemSearchDialog(_SearchDialog[ic.Item]):
    """Dialog for selecting an item from a searchable list."""

    def __init__(
        self,
        *,
        items: ty.Iterable[ic.Item],
        title: str,
        allow_load_file: bool = False,
        show_amount: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        self.selected_item: ic.Item | None = None
        self.goal_dialog_action: GoalDialogAction | None = None
        super().__init__(
            options=(
                dialog_components.SelectionOption(label=item.name, value=item)
                for item in items
            ),
            title=title,
            search_placeholder="Search items",
            size=(520, 640),
            show_amount=show_amount,
            parent=parent,
        )
        self.item_list = self.selection_widget.list_widget
        if allow_load_file:
            load_button = self.button_box.addButton(
                "Load File...",
                QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
            )
            load_button.clicked.connect(self._request_load_file)

    def _store_selected_object(self, selected_object: ic.Item) -> None:
        self.selected_item = selected_object

    def _request_load_file(self) -> None:
        self.goal_dialog_action = GoalDialogAction.LOAD_FILE
        self.accept()


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


def choose_initial_goal_item(
    *,
    game_data: ic.GameData,
    parent: QtWidgets.QWidget | None = None,
) -> InitialGoalSelection | GoalDialogAction | None:
    dialog = ItemSearchDialog(
        items=game_data.producible_items,
        title="Choose Goal Item",
        allow_load_file=True,
        show_amount=True,
        parent=parent,
    )
    result = dialog.exec()
    if result != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    if dialog.goal_dialog_action is not None:
        return dialog.goal_dialog_action
    if dialog.selected_item is None or dialog.selected_amount_per_min is None:
        return None
    return InitialGoalSelection(
        item=dialog.selected_item,
        amount_per_min=dialog.selected_amount_per_min,
    )


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


def _recipe_selection_sort_key(
    option: dialog_components.SelectionOption[ic.Recipe],
) -> tuple[bool, str]:
    normalized_name = option.label.casefold()
    return normalized_name.startswith("alternate:"), normalized_name


class RecipeSearchDialog(_SearchDialog[ic.Recipe]):
    """Dialog for selecting a recipe from a searchable list."""

    def __init__(
        self,
        *,
        recipes: ty.Iterable[ic.Recipe],
        title: str,
        show_amount: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        self.selected_recipe: ic.Recipe | None = None
        self.details = QtWidgets.QTextEdit()
        self.details.setReadOnly(True)
        super().__init__(
            options=(
                dialog_components.SelectionOption(label=recipe.name, value=recipe)
                for recipe in recipes
            ),
            title=title,
            search_placeholder="Search recipes",
            size=(760, 640),
            show_amount=show_amount,
            unfiltered_sort_key=_recipe_selection_sort_key,
            detail_widget=self.details,
            parent=parent,
        )
        self.recipe_list = self.selection_widget.list_widget
        self.selection_widget.selection_changed.connect(self._update_recipe_preview)
        self._update_recipe_preview(self.selection_widget.selected_object)

    def _update_recipe_preview(self, selected_object: object | None) -> None:
        if selected_object is None:
            self.details.clear()
            self.details.setToolTip("")
            return

        recipe = ty.cast(ic.Recipe, selected_object)
        self.details.setToolTip(
            recipe_format.recipe_exact_tooltip(recipe, fr.Fraction(1))
        )
        self.details.setHtml(
            recipe_format.recipe_details_document_html(
                [recipe_format.recipe_details_html(recipe, fr.Fraction(1))]
            )
        )

    def _store_selected_object(self, selected_object: ic.Recipe) -> None:
        self.selected_recipe = selected_object


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


def choose_recipe_with_amount(
    *,
    recipes: ty.Iterable[ic.Recipe],
    title: str,
    parent: QtWidgets.QWidget | None = None,
) -> RecipeSelection | None:
    dialog = RecipeSearchDialog(
        recipes=recipes,
        title=title,
        show_amount=True,
        parent=parent,
    )
    result = dialog.exec()
    if result != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    if dialog.selected_recipe is None or dialog.selected_amount_per_min is None:
        return None
    return RecipeSelection(
        recipe=dialog.selected_recipe,
        amount_per_min=dialog.selected_amount_per_min,
    )


class PositiveFractionDialog(QtWidgets.QDialog):
    """Dialog wrapper for the reusable positive-fraction input."""

    def __init__(
        self,
        *,
        title: str,
        label: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selected_fraction: fr.Fraction | None = None
        self.fraction_input = dialog_components.PositiveFractionInput(label=label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_fraction)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.fraction_input)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _accept_fraction(self) -> None:
        amount = self.fraction_input.value_or_warn(parent=self)
        if amount is None:
            return
        self.selected_fraction = amount
        self.accept()


def get_positive_fraction(
    *,
    title: str,
    label: str,
    parent: QtWidgets.QWidget | None = None,
) -> fr.Fraction | None:
    dialog = PositiveFractionDialog(title=title, label=label, parent=parent)
    result = dialog.exec()
    if result == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.selected_fraction
    return None
