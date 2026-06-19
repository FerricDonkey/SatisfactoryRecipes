"""Main GUI window."""

import fractions as fr
import pathlib
import typing as ty

from PySide6 import QtCore, QtGui, QtWidgets

from satisfactory_recipes import config as sr_config
from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes.gui import dialogs, widgets

type ThemeName = ty.Literal["system", "light", "dark"]
type StyleName = str


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
        self._default_palette = QtWidgets.QApplication.palette()
        self._default_style_name = QtWidgets.QApplication.style().objectName()
        self._default_font = QtWidgets.QApplication.font()
        self._zoom_steps = 0

        self.setWindowTitle("Satisfactory Recipes")
        self.resize(1100, 760)

        self.goal_header = widgets.GoalHeader()
        self.recipes_panel = widgets.RecipesPanel()
        self.chain_details = widgets.ChainDetailsTabs()
        self.status_label = QtWidgets.QLabel()

        # Compatibility aliases for callers and characterization tests that used
        # the original MainWindow-owned widgets.
        self.goal_label = self.goal_header.goal_label
        self.change_goal_button = self.goal_header.change_goal_button
        self.scale_combo = self.goal_header.scale_combo
        self.recipes_table = self.recipes_panel.table
        self.add_goal_recipe_button = self.recipes_panel.add_goal_recipe_button
        self.add_shortage_recipe_button = (
            self.recipes_panel.add_shortage_recipe_button
        )
        self.inputs_table = self.chain_details.inputs_table
        self.outputs_table = self.chain_details.outputs_table
        self.recipe_details_scroll = self.chain_details.recipe_details
        self.recipe_details_widget = self.chain_details.recipe_details.content_widget
        self.recipe_details_layout = self.chain_details.recipe_details.content_layout

        self._setup_actions()
        self._setup_theme_actions()
        self._setup_layout()
        self._sync_scale_combo()
        self._apply_saved_gui_preferences()
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
        self.zoom_in_action = QtGui.QAction("Zoom In", self)
        self.zoom_out_action = QtGui.QAction("Zoom Out", self)
        self.reset_zoom_action = QtGui.QAction("Reset Zoom", self)

        self.open_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.save_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.save_as_action.setShortcut(QtGui.QKeySequence.StandardKey.SaveAs)
        self.new_action.setShortcut(QtGui.QKeySequence.StandardKey.New)
        self.zoom_in_action.setShortcuts([
            QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.ZoomIn),
            QtGui.QKeySequence("Ctrl+="),
        ])
        self.zoom_out_action.setShortcut(QtGui.QKeySequence.StandardKey.ZoomOut)
        self.reset_zoom_action.setShortcut(QtGui.QKeySequence("Ctrl+0"))

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
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.reset_zoom_action.triggered.connect(self.reset_zoom)

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
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)

    def _setup_theme_actions(self) -> None:
        options_menu = self.menuBar().addMenu("Options")

        theme_menu = options_menu.addMenu("Theme")
        self.theme_action_group = QtGui.QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        for theme_name in ("System", "Light", "Dark"):
            action = QtGui.QAction(theme_name, self)
            action.setCheckable(True)
            action.setData(theme_name.lower())
            if theme_name == "System":
                action.setChecked(True)
            action.triggered.connect(self._handle_theme_action)
            self.theme_action_group.addAction(action)
            theme_menu.addAction(action)

        style_menu = options_menu.addMenu("Qt Style")
        self.style_action_group = QtGui.QActionGroup(self)
        self.style_action_group.setExclusive(True)
        current_style_name = self._default_style_name.lower()
        for style_name in QtWidgets.QStyleFactory.keys():
            action = QtGui.QAction(style_name, self)
            action.setCheckable(True)
            action.setData(style_name)
            if style_name.lower() == current_style_name:
                action.setChecked(True)
            action.triggered.connect(self._handle_style_action)
            self.style_action_group.addAction(action)
            style_menu.addAction(action)

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
        self.chain_details.amount_edit_requested.connect(
            self._handle_net_amount_changed
        )
        self.chain_details.shortage_recipe_requested.connect(
            self.add_shortage_recipe
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
                self.close()
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
            game_data = ic.GameData.from_json(self.docs_path)
            self.production_chain = pc.ProductionChain.load(filename, game_data)
            self.game_data = game_data
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open Failed", str(exc))
            return False

        self.filename = filename
        self.has_unsaved_changes = False
        self._sync_scale_combo()
        self.refresh()
        return True

    def select_docs_file(self) -> None:
        if not self._confirm_clear_chain(
            title="Select Game Data",
            message=(
                "Changing the game data file clears the current production "
                "chain and goal item. Continue?"
            ),
        ):
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
            game_data = ic.GameData.from_json(selection.docs_path)
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
        self._sync_scale_combo()
        self.refresh()

    def save_chain(self) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        if self.filename is None:
            self.save_chain_as()
            return

        self.production_chain.save(self.filename, scale=self.game_data.scale)
        self.has_unsaved_changes = False
        self.refresh()

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

        self.filename = pathlib.Path(filename_str)
        self.save_chain()

    def refresh(self) -> None:
        self._refresh_impl()

    def _refresh_impl(self) -> None:
        chain = self.production_chain
        if chain is None:
            self.goal_header.set_goal(None)
            self.status_label.setText(
                "Choose Set Goal or File > New to select a goal item."
            )
            self.recipes_panel.set_chain(None)
            self.chain_details.set_chain(None)
            self._update_recipe_actions()
            return

        self.goal_header.set_goal(chain.goal)
        filename = self.filename if self.filename is not None else "Unsaved"
        self.status_label.setText(f"File: {filename}{self._unsaved_marker()}")
        self.recipes_panel.set_chain(chain)
        self.chain_details.set_chain(chain)
        self._update_recipe_actions()
        self._resize_table_rows()

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
                self._sync_scale_combo()
                return

        self._set_recipe_scale(scale)

    def zoom_in(self) -> None:
        self._set_zoom_steps(self._zoom_steps + 1)

    def zoom_out(self) -> None:
        self._set_zoom_steps(self._zoom_steps - 1)

    def reset_zoom(self) -> None:
        self._set_zoom_steps(0)

    def _set_zoom_steps(self, steps: int) -> None:
        self._set_zoom_steps_impl(steps, persist=True)

    def _set_zoom_steps_impl(self, steps: int, *, persist: bool) -> None:
        steps = max(-5, min(steps, 8))
        if steps == self._zoom_steps:
            return

        self._zoom_steps = steps
        font = QtGui.QFont(self._default_font)
        base_size = self._default_font.pointSizeF()
        if base_size <= 0:
            base_size = 9
        font.setPointSizeF(base_size * (1.1**self._zoom_steps))

        app = QtWidgets.QApplication.instance()
        if isinstance(app, QtWidgets.QApplication):
            app.setFont(font)

        self._resize_table_rows()
        if persist:
            self.user_config.gui_zoom_steps = self._zoom_steps
            self._save_user_config()

    def _handle_theme_action(self) -> None:
        action = self.sender()
        if not isinstance(action, QtGui.QAction):
            return

        theme_name = action.data()
        if theme_name in ("system", "light", "dark"):
            self._set_theme(theme_name, persist=True)

    def _handle_style_action(self) -> None:
        action = self.sender()
        if not isinstance(action, QtGui.QAction):
            return

        style_name = action.data()
        if isinstance(style_name, str):
            self._set_style(style_name, persist=True)

    def _set_theme(self, theme_name: ThemeName, *, persist: bool) -> None:
        app = QtWidgets.QApplication.instance()
        if not isinstance(app, QtWidgets.QApplication):
            return

        if theme_name == "system":
            app.setPalette(self._default_palette)
            app.setStyleSheet("")
        elif theme_name == "light":
            app.setPalette(self._make_light_palette())
            app.setStyleSheet(self._make_light_stylesheet())
        elif theme_name == "dark":
            app.setPalette(self._make_dark_palette())
            app.setStyleSheet(self._make_dark_stylesheet())
        else:
            return

        self._check_action_by_data(self.theme_action_group, theme_name)
        if persist:
            self.user_config.gui_theme = theme_name
            self._save_user_config()

    def _set_style(self, style_name: StyleName, *, persist: bool) -> None:
        available_styles = {
            style.lower(): style for style in QtWidgets.QStyleFactory.keys()
        }
        actual_style_name = available_styles.get(style_name.lower())
        if actual_style_name is None:
            return

        QtWidgets.QApplication.setStyle(actual_style_name)
        self._check_action_by_data(self.style_action_group, actual_style_name)
        if persist:
            self.user_config.gui_style = actual_style_name
            self._save_user_config()

    def _apply_saved_gui_preferences(self) -> None:
        saved_style = self.user_config.gui_style
        if saved_style is not None:
            available_styles = {
                style.lower(): style for style in QtWidgets.QStyleFactory.keys()
            }
            if saved_style.lower() in available_styles:
                self._set_style(saved_style, persist=False)
            else:
                self.user_config.gui_style = None
                self._save_user_config()

        self._set_theme(self.user_config.gui_theme, persist=False)
        self._set_zoom_steps_impl(self.user_config.gui_zoom_steps, persist=False)

    @staticmethod
    def _check_action_by_data(
        action_group: QtGui.QActionGroup,
        data: str,
    ) -> None:
        for action in action_group.actions():
            action_data = action.data()
            if isinstance(action_data, str) and action_data.lower() == data.lower():
                action.setChecked(True)
                return

    def _save_user_config(self) -> None:
        sr_config.save_config(self.user_config)

    def _set_recipe_scale(self, scale: fr.Fraction) -> None:
        goal_class_name = (
            self.production_chain.goal.class_name
            if self.production_chain is not None
            else None
        )

        game_data = ic.GameData.from_json(self.docs_path)
        if scale != 1:
            game_data.scale_recipes(scale)

        self.game_data = game_data
        if goal_class_name is not None:
            self.production_chain = pc.ProductionChain(
                goal=self.game_data.items_d[goal_class_name],
            )
            self.filename = None
            self._mark_unsaved()

        self._sync_scale_combo()
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

    def _mark_unsaved(self) -> None:
        self.has_unsaved_changes = True

    def _unsaved_marker(self) -> str:
        if self.has_unsaved_changes:
            return " *"
        return ""

    @staticmethod
    def _make_light_palette() -> QtGui.QPalette:
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(245, 245, 245))
        palette.setColor(
            QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.black
        )
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 255, 255))
        palette.setColor(
            QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(240, 240, 240)
        )
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.black)
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(245, 245, 245))
        palette.setColor(
            QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.black
        )
        palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(0, 120, 215))
        palette.setColor(
            QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.white
        )
        return palette

    @staticmethod
    def _make_dark_palette() -> QtGui.QPalette:
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(45, 45, 48))
        palette.setColor(
            QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white
        )
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(30, 30, 30))
        palette.setColor(
            QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(45, 45, 48)
        )
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(45, 45, 48))
        palette.setColor(
            QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white
        )
        palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
        palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(0, 120, 215))
        palette.setColor(
            QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.white
        )
        return palette

    @staticmethod
    def _make_light_stylesheet() -> str:
        return """
            QWidget {
                background-color: #f5f5f5;
                color: #000000;
            }
            QMenuBar {
                background-color: #f5f5f5;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #dbeafe;
                color: #000000;
            }
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #b8b8b8;
            }
            QMenu::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
            QPushButton {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #9ca3af;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #e5f1fb;
                border-color: #0078d7;
            }
            QPushButton:pressed {
                background-color: #cce4f7;
            }
            QPushButton:disabled {
                background-color: #eeeeee;
                color: #777777;
                border-color: #c8c8c8;
            }
            QTabWidget::pane {
                border: 1px solid #b8b8b8;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e5e7eb;
                color: #000000;
                border: 1px solid #b8b8b8;
                padding: 5px 12px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                border-bottom-color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #dbeafe;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget, QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #b8b8b8;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
            QScrollArea {
                background-color: #f5f5f5;
                border: 1px solid #b8b8b8;
            }
            QGroupBox {
                background-color: #ffffff;
                color: #000000;
                border: 2px solid #9ca3af;
                margin-top: 14px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                background-color: #ffffff;
                font-size: 125%;
                font-weight: 700;
            }
            QHeaderView::section {
                background-color: #e5e7eb;
                color: #000000;
                border: 1px solid #b8b8b8;
                padding: 3px;
            }
            QTableCornerButton::section {
                background-color: #e5e7eb;
                border: 1px solid #b8b8b8;
            }
        """

    @staticmethod
    def _make_dark_stylesheet() -> str:
        return """
            QWidget {
                background-color: #2d2d30;
                color: #ffffff;
            }
            QMenuBar {
                background-color: #2d2d30;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #3e3e42;
                color: #ffffff;
            }
            QMenu {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #5a5a5a;
            }
            QMenu::item:selected {
                background-color: #0078d7;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #6b7280;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #4b5563;
                border-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
            QPushButton:disabled {
                background-color: #303033;
                color: #8a8a8a;
                border-color: #555555;
            }
            QTabWidget::pane {
                border: 1px solid #5a5a5a;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                padding: 5px 12px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom-color: #1e1e1e;
            }
            QTabBar::tab:hover {
                background-color: #4b5563;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget, QComboBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                selection-background-color: #0078d7;
                selection-color: #ffffff;
            }
            QScrollArea {
                background-color: #2d2d30;
                border: 1px solid #5a5a5a;
            }
            QGroupBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #777777;
                margin-top: 14px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                background-color: #1e1e1e;
                font-size: 125%;
                font-weight: 700;
            }
            QHeaderView::section {
                background-color: #3e3e42;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                padding: 3px;
            }
            QTableCornerButton::section {
                background-color: #3e3e42;
                border: 1px solid #5a5a5a;
            }
        """

    def _sync_scale_combo(self) -> None:
        self.goal_header.set_recipe_scale(self.game_data.scale)

    def _update_recipe_actions(self) -> None:
        has_chain = self.production_chain is not None
        has_producible_shortages = False
        if self.production_chain is not None:
            has_producible_shortages = any(
                item in self.game_data.producible_items
                for item in self.production_chain.get_shortage_items()
            )

        self.add_goal_recipe_action.setEnabled(has_chain)
        self.add_shortage_recipe_action.setEnabled(
            has_chain and has_producible_shortages
        )
        self.recipes_panel.set_actions_enabled(
            has_chain=has_chain,
            has_producible_shortages=has_producible_shortages,
        )
        self.change_goal_button.setEnabled(True)

    def _resize_table_rows(self) -> None:
        for table in (self.recipes_table, self.inputs_table, self.outputs_table):
            table.resizeRowsToContents()
