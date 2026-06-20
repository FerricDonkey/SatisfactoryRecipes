"""Top-level coordination for GUI session state and user workflows."""

from __future__ import annotations

import fractions as fr
import pathlib

from PySide6 import QtCore, QtGui, QtWidgets

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import docs_parser
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes.gui import appearance, dialogs, view_state, widgets


class MainWindow(QtWidgets.QMainWindow):
    """Top-level GUI window for a production chain."""

    def __init__(
        self,
        *,
        docs_path: pathlib.Path,
        game_data: ic.GameData,
        user_config: sr_config.Configuration,
        production_chain: pc.ProductionChain | None = None,
        filename: pathlib.Path | None = None,
    ) -> None:
        super().__init__()
        self.docs_path = docs_path
        self.user_config = user_config
        self.game_data = game_data
        self.production_chain = production_chain
        self.filename = filename
        self.has_unsaved_changes = False
        self.selected_recipe: ic.Recipe | None = None
        self.appearance_manager = appearance.AppearanceManager(
            configuration=self.user_config,
            save_callback=self._save_user_config,
            parent=self,
        )

        self.setWindowTitle("Satisfactory Recipes")
        self.resize(1100, 760)

        self.goal_header = widgets.GoalHeader()
        self.recipes_panel = widgets.RecipesPanel()
        self.chain_details = widgets.ChainDetailsTabs()
        self.status_label = QtWidgets.QLabel()

        self._setup_actions()
        self._setup_theme_actions()
        self._setup_layout()
        self.appearance_manager.apply_saved_preferences()
        self.refresh()

    def _setup_actions(self) -> None:
        self.new_action = QtGui.QAction("New", self)
        self.open_action = QtGui.QAction("Open...", self)
        self.select_docs_action = QtGui.QAction("Select Game Data...", self)
        self.save_action = QtGui.QAction("Save", self)
        self.save_as_action = QtGui.QAction("Save As...", self)
        self.exit_action = QtGui.QAction("Exit", self)
        self.add_goal_recipe_action = QtGui.QAction("Add Goal Recipe...", self)
        self.add_shortage_recipe_action = QtGui.QAction("Add Shortage Recipe...", self)
        self.open_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.save_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.save_as_action.setShortcut(QtGui.QKeySequence.StandardKey.SaveAs)
        self.new_action.setShortcut(QtGui.QKeySequence.StandardKey.New)

        self.new_action.triggered.connect(self.new_chain)
        self.open_action.triggered.connect(self.open_chain)
        self.select_docs_action.triggered.connect(self.select_docs_file)
        self.save_action.triggered.connect(self.save_chain)
        self.save_as_action.triggered.connect(self.save_chain_as)
        self.exit_action.triggered.connect(self.close)
        self.add_goal_recipe_action.triggered.connect(self.add_goal_recipe_from_ui)
        self.add_shortage_recipe_action.triggered.connect(
            self.add_shortage_recipe_from_ui
        )

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.select_docs_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        recipe_menu = self.menuBar().addMenu("Recipes")
        recipe_menu.addAction(self.add_goal_recipe_action)
        recipe_menu.addAction(self.add_shortage_recipe_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.appearance_manager.zoom_in_action)
        view_menu.addAction(self.appearance_manager.zoom_out_action)
        view_menu.addAction(self.appearance_manager.reset_zoom_action)
        view_menu.addSeparator()
        self.appearance_manager.populate_view_menu(view_menu)

    def _setup_theme_actions(self) -> None:
        options_menu = self.menuBar().addMenu("Options")
        self.appearance_manager.populate_options_menu(options_menu)

    def _setup_layout(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        central.setLayout(layout)

        self.goal_header.change_goal_requested.connect(self.change_goal)
        self.goal_header.scale_changed.connect(self._handle_scale_changed)
        self.recipes_panel.add_goal_recipe_requested.connect(
            self.add_goal_recipe_from_ui
        )
        self.recipes_panel.add_shortage_recipe_requested.connect(
            self.add_shortage_recipe_from_ui
        )
        self.recipes_panel.remove_recipe_requested.connect(self.remove_recipe)
        self.recipes_panel.recipe_selected.connect(self._handle_recipe_selected)
        self.recipes_panel.recipe_count_edit_requested.connect(
            self._handle_recipe_count_changed,
            QtCore.Qt.ConnectionType.QueuedConnection,
        )
        self.chain_details.amount_edit_requested.connect(
            self._handle_net_amount_changed
        )
        self.chain_details.shortage_recipe_requested.connect(self.add_shortage_recipe)
        self.appearance_manager.appearance_changed.connect(
            self._handle_appearance_changed
        )

        layout.addWidget(self.goal_header)

        splitter = QtWidgets.QSplitter()
        splitter.setOpaqueResize(True)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.recipes_panel)
        splitter.addWidget(self.chain_details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([660, 440])
        layout.addWidget(splitter, stretch=1)

        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)

    def prompt_for_goal_if_needed(self) -> None:
        if self.production_chain is not None:
            return

        while self.production_chain is None:
            choice = dialogs.choose_initial_goal_item(
                game_data=self.game_data,
                parent=self,
            )
            if choice is None:
                return
            if choice is dialogs.GoalDialogAction.LOAD_FILE:
                if self.open_chain():
                    return
                continue

            self.production_chain = pc.ProductionChain(goal=choice.item)
            self.filename = None
            self._mark_unsaved()
            self.refresh()
            self.add_goal_recipe(amount_per_min=choice.amount_per_min)

    def new_chain(self) -> None:
        if not self._confirm_discard_unsaved_changes("Creating a new chain"):
            return

        goal = dialogs.choose_goal_item(game_data=self.game_data, parent=self)
        if goal is None:
            return

        self._set_goal_and_clear_recipes(goal)
        self.add_goal_recipe()

    def change_goal(self) -> None:
        if self.production_chain is not None and not self._confirm_clear_chain(
            title="Change Goal",
            message=(
                "Changing the goal item clears all recipes in the current "
                "production chain. Continue?"
            ),
        ):
            return

        goal = dialogs.choose_goal_item(game_data=self.game_data, parent=self)
        if goal is None:
            return

        self._set_goal_and_clear_recipes(goal)

    def add_goal_recipe(self, amount_per_min: fr.Fraction | None = None) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        chain = self.production_chain
        recipes = self.game_data.get_recipes_producing(chain.goal)
        if amount_per_min is None:
            selection = dialogs.choose_recipe_with_amount(
                recipes=recipes,
                title=f"Choose Recipe for {chain.goal.name}",
                parent=self,
            )
            if selection is None:
                return
            recipe = selection.recipe
            amount = selection.amount_per_min
        else:
            chosen_recipe = dialogs.choose_recipe(
                recipes=recipes,
                title=f"Choose Recipe for {chain.goal.name}",
                parent=self,
            )
            if chosen_recipe is None:
                return
            recipe = chosen_recipe
            amount = amount_per_min

        chain.recipes[recipe] = amount / recipe.products_per_min[chain.goal]
        self._mark_unsaved()
        self.refresh()

    def add_goal_recipe_from_ui(self) -> None:
        self.add_goal_recipe()

    def add_shortage_recipe(self, shortage_item: ic.Item | None = None) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        chain = self.production_chain
        shortage_items = sorted(
            (
                item
                for item in chain.get_shortage_items()
                if item in self.game_data.producible_items
            ),
            key=lambda item: item.name.lower(),
        )
        if not shortage_items:
            QtWidgets.QMessageBox.information(
                self,
                "No Shortages",
                "There are no producible shortage items.",
            )
            return

        item = shortage_item
        if item is not None and item not in shortage_items:
            QtWidgets.QMessageBox.information(
                self,
                "No Shortage",
                f"{item.name} is not currently a producible shortage item.",
            )
            return
        if item is None:
            item = dialogs.choose_item_from_items(
                items=shortage_items,
                title="Choose Shortage Item",
                parent=self,
            )
        if item is None:
            return

        recipe = dialogs.choose_recipe(
            recipes=self.game_data.get_recipes_producing(item),
            title=f"Choose Recipe for {item.name}",
            parent=self,
        )
        if recipe is None:
            return

        try:
            chain.add_scaled_recipe(recipe, item)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Could Not Add Recipe", str(exc))
            return

        self._mark_unsaved()
        self.refresh()

    def add_shortage_recipe_from_ui(self) -> None:
        self.add_shortage_recipe()

    def remove_recipe(self, recipe: ic.Recipe, _checked: bool = False) -> None:
        if self.production_chain is None or recipe not in self.production_chain.recipes:
            return

        del self.production_chain.recipes[recipe]
        self._mark_unsaved()
        self.refresh()

    def open_chain(self) -> bool:
        if not self._confirm_discard_unsaved_changes("Opening another chain"):
            return False

        filename_str, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Production Chain",
            "",
            "Production Chain (*.json);;All Files (*)",
        )
        if not filename_str:
            return False

        filename = pathlib.Path(filename_str)
        try:
            game_data = docs_parser.load_game_data(self.docs_path)
            self.production_chain = pc.ProductionChain.load(filename, game_data)
            self.game_data = game_data
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open Failed", str(exc))
            return False

        self.filename = filename
        self.has_unsaved_changes = False
        self.refresh()
        return True

    def select_docs_file(self) -> None:
        if not self._confirm_discard_unsaved_changes("Changing the game data file"):
            return

        selection = dialogs.choose_docs_path(
            message=(
                "Choose the Satisfactory CommunityResources/Docs/en-us.json "
                "file, or choose the Satisfactory install folder that contains it."
            ),
            parent=self,
        )
        if selection is None:
            return

        scale = self.game_data.scale
        try:
            game_data = docs_parser.load_game_data(selection.docs_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Game Data Load Failed", str(exc))
            return

        if scale != 1:
            game_data.scale_recipes(scale)

        self.docs_path = selection.docs_path
        self.game_data = game_data
        self.production_chain = None
        self.filename = None
        self.has_unsaved_changes = False
        self.user_config.docs_path = selection.docs_path
        self.user_config.game_path = selection.game_path
        self._save_user_config()
        self.refresh()

    def save_chain(self) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        if self.filename is None:
            self.save_chain_as()
            return

        self._save_chain_to(self.filename)

    def save_chain_as(self) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        filename_str, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Production Chain",
            "",
            "Production Chain (*.json);;All Files (*)",
        )
        if not filename_str:
            return

        self._save_chain_to(pathlib.Path(filename_str))

    def _save_chain_to(self, filename: pathlib.Path) -> bool:
        chain = self.production_chain
        if chain is None:
            return False

        try:
            chain.save(filename, scale=self.game_data.scale)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save Failed", str(exc))
            return False

        self.filename = filename
        self.has_unsaved_changes = False
        self.refresh()
        return True

    def refresh(self) -> None:
        state = view_state.build_main_window_view_state(
            chain=self.production_chain,
            game_data=self.game_data,
            filename=self.filename,
            has_unsaved_changes=self.has_unsaved_changes,
        )
        displayed_recipes = {recipe for recipe, _count in state.recipes}
        if self.selected_recipe not in displayed_recipes:
            self.selected_recipe = None
        self.goal_header.set_view(
            goal=state.goal,
            recipe_scale=state.recipe_scale,
        )
        self.status_label.setText(state.status_text)
        self.recipes_panel.set_view(
            recipes=state.recipes,
            can_add_goal_recipe=state.can_add_goal_recipe,
            can_add_shortage_recipe=state.can_add_shortage_recipe,
            selected_recipe=self.selected_recipe,
        )
        self.chain_details.set_view(
            inputs=state.inputs,
            outputs=state.outputs,
            recipes=state.recipes,
            selected_recipe=self.selected_recipe,
        )
        self.add_goal_recipe_action.setEnabled(state.can_add_goal_recipe)
        self.add_shortage_recipe_action.setEnabled(state.can_add_shortage_recipe)

    def _handle_recipe_selected(self, selected: object) -> None:
        recipe = selected if isinstance(selected, ic.Recipe) else None
        self.selected_recipe = recipe
        self.chain_details.focus_recipe(recipe)

    def _handle_recipe_count_changed(
        self,
        selected: object,
        value: object,
    ) -> None:
        if (
            self.production_chain is None
            or not isinstance(selected, ic.Recipe)
            or not isinstance(value, fr.Fraction)
            or selected not in self.production_chain.recipes
        ):
            return

        try:
            self.production_chain.scale_recipe_count(selected, value)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Could Not Scale", str(exc))
            self.refresh()
            return

        self.selected_recipe = selected
        self._mark_unsaved()
        self.refresh()

    def _handle_net_amount_changed(
        self,
        item: ic.Item,
        amount: fr.Fraction,
    ) -> None:
        if self.production_chain is None:
            return

        try:
            self.production_chain.scale_item(item, amount)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Could Not Scale", str(exc))
            self.refresh()
            return

        self._mark_unsaved()
        self.refresh()

    def _handle_scale_changed(self, scale: fr.Fraction) -> None:
        if scale == self.game_data.scale:
            return

        if self.production_chain is not None and self.production_chain.recipes:
            result = QtWidgets.QMessageBox.question(
                self,
                "Change Recipe Scale",
                "Changing recipe scale reloads game data and clears all recipes "
                "in the current production chain. Continue?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if result != QtWidgets.QMessageBox.StandardButton.Yes:
                self.refresh()
                return

        self._set_recipe_scale(scale)

    def _handle_appearance_changed(self) -> None:
        self.recipes_panel.refresh_appearance()
        self.chain_details.refresh_appearance()

    def _save_user_config(self) -> None:
        sr_config.save_config(self.user_config)

    def _set_recipe_scale(self, scale: fr.Fraction) -> None:
        goal_class_name = (
            self.production_chain.goal.class_name
            if self.production_chain is not None
            else None
        )

        game_data = docs_parser.load_game_data(self.docs_path)
        if scale != 1:
            game_data.scale_recipes(scale)

        self.game_data = game_data
        if goal_class_name is not None:
            self.production_chain = pc.ProductionChain(
                goal=self.game_data.items_d[goal_class_name],
            )
            self.filename = None
            self._mark_unsaved()

        self.refresh()

    def _set_goal_and_clear_recipes(self, goal: ic.Item) -> None:
        self.production_chain = pc.ProductionChain(goal=goal)
        self.filename = None
        self._mark_unsaved()
        self.refresh()

    def _confirm_clear_chain(self, *, title: str, message: str) -> bool:
        if self.production_chain is None:
            return True

        result = QtWidgets.QMessageBox.question(
            self,
            title,
            message,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        return result == QtWidgets.QMessageBox.StandardButton.Yes

    def _confirm_discard_unsaved_changes(self, action: str) -> bool:
        if not self.has_unsaved_changes:
            return True

        result = QtWidgets.QMessageBox.question(
            self,
            "Discard Unsaved Changes?",
            f"{action} will discard unsaved changes. Continue?",
            QtWidgets.QMessageBox.StandardButton.Discard
            | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        return result == QtWidgets.QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        if self._confirm_discard_unsaved_changes("Closing the window"):
            event.accept()
        else:
            event.ignore()

    def _mark_unsaved(self) -> None:
        self.has_unsaved_changes = True
