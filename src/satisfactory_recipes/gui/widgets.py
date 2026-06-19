"""Data-driven widgets that display chain state and emit user intent."""

import collections.abc as cabc
import fractions as fr
import functools

from PySide6 import QtCore, QtGui, QtWidgets

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes.gui import number_format, recipe_format

type ItemRates = cabc.Sequence[tuple[ic.Item, fr.Fraction]]
type RecipeCounts = cabc.Sequence[tuple[ic.Recipe, fr.Fraction]]


class GoalHeader(QtWidgets.QWidget):
    """Goal display and recipe input-scale controls."""

    change_goal_requested = QtCore.Signal()
    scale_changed = QtCore.Signal(object)

    SCALE_OPTIONS: tuple[fr.Fraction, ...] = (
        fr.Fraction(1, 4),
        fr.Fraction(1, 2),
        fr.Fraction(3, 4),
        fr.Fraction(1, 1),
        fr.Fraction(5, 4),
        fr.Fraction(3, 2),
        fr.Fraction(7, 4),
        fr.Fraction(2, 1),
    )

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.goal_label = QtWidgets.QLabel()
        self.goal_label.setObjectName("goalLabel")
        self.change_goal_button = QtWidgets.QPushButton("Set Goal")
        self.scale_combo = QtWidgets.QComboBox()
        for scale in self.SCALE_OPTIONS:
            self.scale_combo.addItem(self._scale_display_text(scale), scale)
            self.scale_combo.setItemData(
                self.scale_combo.count() - 1,
                number_format.exact_tooltip(scale),
                QtCore.Qt.ItemDataRole.ToolTipRole,
            )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.goal_label)
        layout.addWidget(self.change_goal_button)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel("Recipe scale"))
        layout.addWidget(self.scale_combo)

        self.change_goal_button.clicked.connect(self.change_goal_requested)
        self.scale_combo.currentIndexChanged.connect(self._emit_selected_scale)

    def set_view(self, *, goal: ic.Item | None, recipe_scale: fr.Fraction) -> None:
        if goal is None:
            self.goal_label.setText("No production chain loaded")
        else:
            self.goal_label.setText(f"Goal: {goal.name}")
        self._set_recipe_scale(recipe_scale)

    def _set_recipe_scale(self, scale: fr.Fraction) -> None:
        blocker = QtCore.QSignalBlocker(self.scale_combo)
        try:
            for index, option in enumerate(self.SCALE_OPTIONS):
                if option == scale:
                    self.scale_combo.setCurrentIndex(index)
                    return
            self.scale_combo.setCurrentIndex(-1)
        finally:
            del blocker

    def _emit_selected_scale(self, _index: int) -> None:
        scale = self.scale_combo.currentData()
        if isinstance(scale, fr.Fraction):
            self.scale_changed.emit(scale)

    @staticmethod
    def _scale_display_text(scale: fr.Fraction) -> str:
        display = number_format.decimal(scale, precision=2).rstrip("0")
        if display.endswith("."):
            display += "0"
        return display


class RecipesPanel(QtWidgets.QWidget):
    """Recipe actions and the summarized recipe table."""

    add_goal_recipe_requested = QtCore.Signal()
    add_shortage_recipe_requested = QtCore.Signal()
    remove_recipe_requested = QtCore.Signal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.add_goal_recipe_button = QtWidgets.QPushButton("Add Goal Recipe...")
        self.add_shortage_recipe_button = QtWidgets.QPushButton(
            "Add Shortage Recipe..."
        )
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                "Recipe",
                "Count",
                "Building",
                "Mean Power",
            ]
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 24)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

        action_layout = QtWidgets.QHBoxLayout()
        action_layout.addWidget(self.add_goal_recipe_button)
        action_layout.addWidget(self.add_shortage_recipe_button)
        action_layout.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Recipes"))
        layout.addLayout(action_layout)
        layout.addWidget(self.table)

        self.add_goal_recipe_button.clicked.connect(self.add_goal_recipe_requested)
        self.add_shortage_recipe_button.clicked.connect(
            self.add_shortage_recipe_requested
        )

    def set_view(
        self,
        *,
        recipes: RecipeCounts,
        can_add_goal_recipe: bool,
        can_add_shortage_recipe: bool,
    ) -> None:
        self.table.setRowCount(0)
        self.table.setRowCount(len(recipes))
        for row, (recipe, count) in enumerate(recipes):
            self.table.setCellWidget(row, 0, self._make_remove_button(recipe))
            building = recipe.produced_in.name if recipe.produced_in else ""
            power = recipe.mean_power * count
            values = (
                (recipe.name, ""),
                (
                    number_format.decimal(count),
                    number_format.exact_tooltip(count),
                ),
                (building, ""),
                (
                    number_format.decimal(power, unit="MW"),
                    number_format.exact_tooltip(power, unit="MW"),
                ),
            )
            for column, (value, tooltip) in enumerate(values, start=1):
                table_item = QtWidgets.QTableWidgetItem(value)
                if tooltip:
                    table_item.setToolTip(tooltip)
                self.table.setItem(row, column, table_item)

        self.table.resizeRowsToContents()
        self.add_goal_recipe_button.setEnabled(can_add_goal_recipe)
        self.add_shortage_recipe_button.setEnabled(can_add_shortage_recipe)

    def refresh_appearance(self) -> None:
        """Refresh palette-dependent icons and font-dependent row sizes."""
        for row in range(self.table.rowCount()):
            wrapper = self.table.cellWidget(row, 0)
            button = wrapper.findChild(QtWidgets.QToolButton)
            if button is not None:
                button.setIcon(self._make_remove_icon())
        self.table.resizeRowsToContents()

    def _make_remove_button(self, recipe: ic.Recipe) -> QtWidgets.QWidget:
        remove_button = QtWidgets.QToolButton()
        remove_button.setIcon(self._make_remove_icon())
        remove_button.setIconSize(QtCore.QSize(12, 12))
        remove_button.setAutoRaise(True)
        remove_button.setFixedSize(16, 16)
        remove_button.setToolTip("Remove recipe")
        remove_button.setAccessibleName("Remove recipe")
        remove_button.clicked.connect(
            functools.partial(self._request_recipe_removal, recipe)
        )

        wrapper = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()
        layout.addWidget(remove_button)
        layout.addStretch()
        return wrapper

    def _request_recipe_removal(
        self,
        recipe: ic.Recipe,
        _checked: bool = False,
    ) -> None:
        self.remove_recipe_requested.emit(recipe)

    def _make_remove_icon(self) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        color = self.palette().color(QtGui.QPalette.ColorRole.ButtonText)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(color, 1.8)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(3, 3, 9, 9)
        painter.drawLine(9, 3, 3, 9)
        painter.end()
        return QtGui.QIcon(pixmap)


class NetItemsTable(QtWidgets.QTableWidget):
    """Reusable editable table of item rates."""

    RATE_EDIT_HINT = "Double-click a Per Minute cell to edit the chain rate."

    amount_edit_requested = QtCore.Signal(object, object)
    item_activated = QtCore.Signal(object)

    def __init__(
        self,
        *,
        activation_hint: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rendering = False
        self._values: dict[ic.Item, fr.Fraction] = {}
        self._activation_hint = activation_hint

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Item", "Per Minute"])
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        rate_header = self.horizontalHeaderItem(1)
        if rate_header is not None:
            rate_header.setToolTip(self.RATE_EDIT_HINT)
        table_hints = [self.RATE_EDIT_HINT]
        if activation_hint is not None:
            table_hints.append(activation_hint)
        self.setToolTip(" ".join(table_hints))

        self.itemChanged.connect(self._handle_item_changed)
        self.itemDoubleClicked.connect(self._handle_item_double_clicked)

    def set_view(self, values: ItemRates) -> None:
        self._values = dict(values)
        self._rendering = True
        try:
            self.setRowCount(len(values))
            for row, (item, amount) in enumerate(values):
                name_item = QtWidgets.QTableWidgetItem(item.name)
                name_item.setFlags(
                    name_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable
                )
                name_item.setData(QtCore.Qt.ItemDataRole.UserRole, item)
                if self._activation_hint is not None:
                    name_item.setToolTip(self._activation_hint)

                amount_item = QtWidgets.QTableWidgetItem(number_format.decimal(amount))
                amount_item.setData(QtCore.Qt.ItemDataRole.UserRole, item)
                amount_item.setToolTip(
                    number_format.exact_tooltip(amount, hint=self.RATE_EDIT_HINT)
                )
                self.setItem(row, 0, name_item)
                self.setItem(row, 1, amount_item)
        finally:
            self._rendering = False
        self.resizeRowsToContents()

    def _handle_item_changed(self, table_item: QtWidgets.QTableWidgetItem) -> None:
        if self._rendering or table_item.column() != 1:
            return
        item = table_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(item, ic.Item):
            return

        try:
            amount = fr.Fraction(table_item.text())
        except ValueError:
            amount = fr.Fraction(0)
        if amount <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Amount",
                "Enter a positive number or fraction.",
            )
            self.set_view(tuple(self._values.items()))
            return

        self.amount_edit_requested.emit(item, amount)

    def _handle_item_double_clicked(
        self,
        table_item: QtWidgets.QTableWidgetItem,
    ) -> None:
        if table_item.column() != 0:
            return
        item = table_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(item, ic.Item):
            self.item_activated.emit(item)


class RecipeDetailsView(QtWidgets.QScrollArea):
    """Scrollable collection of rich recipe detail cards."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.setWidget(self.content_widget)
        self.setWidgetResizable(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def set_view(self, recipes: RecipeCounts) -> None:
        self.clear()
        for recipe, count in recipes:
            self.content_layout.addWidget(self._make_card(recipe, count))
        self.content_layout.addStretch()

    def clear(self) -> None:
        while self.content_layout.count():
            layout_item = self.content_layout.takeAt(0)
            if layout_item is None:
                continue
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _make_card(
        recipe: ic.Recipe,
        count: fr.Fraction,
    ) -> QtWidgets.QGroupBox:
        card = QtWidgets.QGroupBox(f"{recipe.name} x {number_format.decimal(count)}")
        card.setToolTip(recipe_format.recipe_exact_tooltip(recipe, count))
        card_layout = QtWidgets.QVBoxLayout(card)

        body = QtWidgets.QLabel()
        body.setTextFormat(QtCore.Qt.TextFormat.RichText)
        body.setText(recipe_format.recipe_body_html(recipe, count))
        body.setToolTip(recipe_format.recipe_exact_tooltip(recipe, count))
        body.setWordWrap(True)
        body.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card_layout.addWidget(body)
        return card


class ChainDetailsTabs(QtWidgets.QTabWidget):
    """Net input/output tables and recipe detail cards."""

    amount_edit_requested = QtCore.Signal(object, object)
    shortage_recipe_requested = QtCore.Signal(object)

    SHORTAGE_RECIPE_HINT = (
        "Double-click an input item to add a recipe for that shortage."
    )

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.inputs_table = NetItemsTable(activation_hint=self.SHORTAGE_RECIPE_HINT)
        self.outputs_table = NetItemsTable()
        self.recipe_details = RecipeDetailsView()
        self.addTab(self.inputs_table, "Inputs")
        self.addTab(self.outputs_table, "Outputs")
        self.addTab(self.recipe_details, "Recipe Details")
        self.setTabToolTip(0, self.SHORTAGE_RECIPE_HINT)
        self.setTabToolTip(1, NetItemsTable.RATE_EDIT_HINT)

        self.inputs_table.amount_edit_requested.connect(self.amount_edit_requested)
        self.outputs_table.amount_edit_requested.connect(self.amount_edit_requested)
        self.inputs_table.item_activated.connect(self.shortage_recipe_requested)

    def set_view(
        self,
        *,
        inputs: ItemRates,
        outputs: ItemRates,
        recipes: RecipeCounts,
    ) -> None:
        self.inputs_table.set_view(inputs)
        self.outputs_table.set_view(outputs)
        self.recipe_details.set_view(recipes)

    def refresh_appearance(self) -> None:
        self.inputs_table.resizeRowsToContents()
        self.outputs_table.resizeRowsToContents()
