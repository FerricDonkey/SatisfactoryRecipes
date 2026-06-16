"""Main GUI window."""

import fractions as fr
import pathlib

from PySide6 import QtGui, QtWidgets

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes import production_chain as pc
from satisfactory_recipes.gui import dialogs


class MainWindow(QtWidgets.QMainWindow):
    """Top-level GUI window for a production chain."""

    def __init__(
        self,
        *,
        game_data: ic.GameData,
        production_chain: pc.ProductionChain | None = None,
        filename: pathlib.Path | None = None,
    ) -> None:
        super().__init__()
        self.game_data = game_data
        self.production_chain = production_chain
        self.filename = filename

        self.setWindowTitle("Satisfactory Recipes")
        self.resize(1100, 760)

        self.goal_label = QtWidgets.QLabel()
        self.recipes_table = QtWidgets.QTableWidget()
        self.inputs_table = QtWidgets.QTableWidget()
        self.outputs_table = QtWidgets.QTableWidget()
        self.status_label = QtWidgets.QLabel()

        self._setup_actions()
        self._setup_layout()
        self.refresh()

    def _setup_actions(self) -> None:
        self.new_action = QtGui.QAction("New", self)
        self.open_action = QtGui.QAction("Open...", self)
        self.save_action = QtGui.QAction("Save", self)
        self.save_as_action = QtGui.QAction("Save As...", self)
        self.exit_action = QtGui.QAction("Exit", self)
        self.add_goal_recipe_action = QtGui.QAction("Add Goal Recipe...", self)
        self.add_shortage_recipe_action = QtGui.QAction("Add Shortage Recipe...", self)

        self.new_action.triggered.connect(self.new_chain)
        self.open_action.triggered.connect(self.open_chain)
        self.save_action.triggered.connect(self.save_chain)
        self.save_as_action.triggered.connect(self.save_chain_as)
        self.exit_action.triggered.connect(self.close)
        self.add_goal_recipe_action.triggered.connect(self.add_goal_recipe_from_ui)
        self.add_shortage_recipe_action.triggered.connect(self.add_shortage_recipe)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        recipe_menu = self.menuBar().addMenu("Recipes")
        recipe_menu.addAction(self.add_goal_recipe_action)
        recipe_menu.addAction(self.add_shortage_recipe_action)

    def _setup_layout(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        central.setLayout(layout)

        self.goal_label.setObjectName("goalLabel")
        layout.addWidget(self.goal_label)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self._make_recipes_panel())
        splitter.addWidget(self._make_net_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        self.setCentralWidget(central)

    def _make_recipes_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        panel.setLayout(layout)

        layout.addWidget(QtWidgets.QLabel("Recipes"))
        action_layout = QtWidgets.QHBoxLayout()
        self.add_goal_recipe_button = QtWidgets.QPushButton("Add Goal Recipe...")
        self.add_shortage_recipe_button = QtWidgets.QPushButton("Add Shortage Recipe...")
        self.add_goal_recipe_button.clicked.connect(self.add_goal_recipe_from_ui)
        self.add_shortage_recipe_button.clicked.connect(self.add_shortage_recipe)
        action_layout.addWidget(self.add_goal_recipe_button)
        action_layout.addWidget(self.add_shortage_recipe_button)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.recipes_table.setColumnCount(4)
        self.recipes_table.setHorizontalHeaderLabels(
            ["Recipe", "Count", "Building", "Mean Power"]
        )
        self.recipes_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.recipes_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.recipes_table)

        return panel

    def _make_net_panel(self) -> QtWidgets.QWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.inputs_table, "Inputs")
        tabs.addTab(self.outputs_table, "Outputs")

        for table in (self.inputs_table, self.outputs_table):
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Item", "Per Minute"])
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.horizontalHeader().setStretchLastSection(True)

        return tabs

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
            self.refresh()
            self.add_goal_recipe(amount_per_min=choice.amount_per_min)

    def new_chain(self) -> None:
        goal = dialogs.choose_goal_item(game_data=self.game_data, parent=self)
        if goal is None:
            return

        self.production_chain = pc.ProductionChain(goal=goal)
        self.filename = None
        self.refresh()
        self.add_goal_recipe()

    def add_goal_recipe(self, amount_per_min: fr.Fraction | None = None) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        chain = self.production_chain
        recipes = self.game_data.get_recipes_producing(chain.goal)
        recipe = dialogs.choose_recipe(
            recipes=recipes,
            title=f"Choose Recipe for {chain.goal.name}",
            parent=self,
        )
        if recipe is None:
            return

        amount = amount_per_min
        if amount is None:
            amount = dialogs.get_positive_fraction(
                title="Goal Output Rate",
                label=f"How many {chain.goal.name} per minute with this recipe?",
                parent=self,
            )
            if amount is None:
                return

        chain.recipes[recipe] = amount / recipe.products_per_min[chain.goal]
        self.refresh()

    def add_goal_recipe_from_ui(self) -> None:
        self.add_goal_recipe()

    def add_shortage_recipe(self) -> None:
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
            self.production_chain = pc.ProductionChain.load(filename, self.game_data)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Open Failed", str(exc))
            return False

        self.filename = filename
        self.refresh()
        return True

    def save_chain(self) -> None:
        if self.production_chain is None:
            self.prompt_for_goal_if_needed()
            if self.production_chain is None:
                return

        if self.filename is None:
            self.save_chain_as()
            return

        self.production_chain.save(self.filename, scale=self.game_data.scale)
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
        chain = self.production_chain
        if chain is None:
            self.goal_label.setText("No production chain loaded")
            self.status_label.setText("Choose File > New to select a goal item.")
            self._fill_recipes_table(None)
            self._fill_net_table(self.inputs_table, {})
            self._fill_net_table(self.outputs_table, {})
            self._update_recipe_actions()
            return

        self.goal_label.setText(f"Goal: {chain.goal.name}")
        filename = self.filename if self.filename is not None else "Unsaved"
        self.status_label.setText(f"File: {filename}")
        self._fill_recipes_table(chain)

        net = chain.get_net_per_min()
        inputs = {item: -amount for item, amount in net.items() if amount < 0}
        outputs = {item: amount for item, amount in net.items() if amount > 0}
        self._fill_net_table(self.inputs_table, inputs)
        self._fill_net_table(self.outputs_table, outputs)
        self._update_recipe_actions()

    def _update_recipe_actions(self) -> None:
        has_chain = self.production_chain is not None
        has_producible_shortages = False
        if self.production_chain is not None:
            has_producible_shortages = any(
                item in self.game_data.producible_items
                for item in self.production_chain.get_shortage_items()
            )

        self.add_goal_recipe_action.setEnabled(has_chain)
        self.add_shortage_recipe_action.setEnabled(has_chain and has_producible_shortages)
        self.add_goal_recipe_button.setEnabled(has_chain)
        self.add_shortage_recipe_button.setEnabled(has_chain and has_producible_shortages)

    def _fill_recipes_table(self, chain: pc.ProductionChain | None) -> None:
        self.recipes_table.setRowCount(0)
        if chain is None:
            return

        recipes = sorted(chain.recipes.items(), key=lambda pair: pair[0].name.lower())
        self.recipes_table.setRowCount(len(recipes))
        for row, (recipe, count) in enumerate(recipes):
            building = recipe.produced_in.name if recipe.produced_in else ""
            values = [
                recipe.name,
                f"{count:.3f}",
                building,
                f"{recipe.mean_power * count:.3f} MW",
            ]
            for col, value in enumerate(values):
                self.recipes_table.setItem(row, col, QtWidgets.QTableWidgetItem(value))

        self.recipes_table.resizeColumnsToContents()

    def _fill_net_table(
        self,
        table: QtWidgets.QTableWidget,
        values: dict[ic.Item, fr.Fraction],
    ) -> None:
        items = sorted(values.items(), key=lambda pair: pair[0].name.lower())
        table.setRowCount(len(items))
        for row, (item, amount) in enumerate(items):
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.name))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{amount:.3f}"))

        table.resizeColumnsToContents()
