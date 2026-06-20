"""Reusable components for searchable selections and exact rate entry."""

from __future__ import annotations

import collections.abc as cabc
import dataclasses
import fractions as fr
import typing as ty

from PySide6 import QtCore, QtWidgets

from satisfactory_recipes import search


@dataclasses.dataclass(frozen=True, slots=True)
class SelectionOption[T]:
    """One searchable row with display text kept separate from object identity."""

    label: str
    value: T
    subtitle: str = ""


class SearchableSelectionList[T](QtWidgets.QWidget):
    """A searchable single-selection list carrying arbitrary Python objects."""

    selection_changed = QtCore.Signal(object)
    selection_activated = QtCore.Signal(object)

    def __init__(
        self,
        *,
        options: cabc.Iterable[SelectionOption[T]],
        search_placeholder: str,
        unfiltered_sort_key: cabc.Callable[[SelectionOption[T]], tuple[bool, str]]
        | None = None,
        detail_widget: QtWidgets.QWidget | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._options = tuple(options)
        self._unfiltered_sort_key = unfiltered_sort_key or (
            lambda option: (False, option.label.casefold())
        )

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText(search_placeholder)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_edit)
        if detail_widget is None:
            layout.addWidget(self.list_widget)
        else:
            splitter = QtWidgets.QSplitter()
            splitter.addWidget(self.list_widget)
            splitter.addWidget(detail_widget)
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 3)
            layout.addWidget(splitter)
        self.setLayout(layout)

        self.search_edit.textChanged.connect(self.refresh)
        self.list_widget.itemSelectionChanged.connect(self._emit_selection)
        self.list_widget.itemDoubleClicked.connect(self._emit_activation)
        self.refresh("")

    @property
    def selected_object(self) -> T | None:
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return None
        return self._object_from_item(selected_items[0])

    def refresh(self, text: str) -> None:
        options = (
            search.sort_objects(self._options, text, label=lambda option: option.label)
            if text
            else sorted(self._options, key=self._unfiltered_sort_key)
        )

        self.list_widget.clear()
        for option in options:
            item = QtWidgets.QListWidgetItem(option.label)
            if option.subtitle:
                item.setToolTip(option.subtitle)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, option.value)
            self.list_widget.addItem(item)

        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_object)

    def _emit_activation(self, item: QtWidgets.QListWidgetItem) -> None:
        self.selection_activated.emit(self._object_from_item(item))

    @staticmethod
    def _object_from_item(item: QtWidgets.QListWidgetItem) -> T:
        return ty.cast("T", item.data(QtCore.Qt.ItemDataRole.UserRole))


class PositiveFractionInput(QtWidgets.QWidget):
    """A labeled input that parses and validates a positive exact fraction."""

    validation_title = "Invalid Amount"
    validation_message = "Enter a positive number or fraction."

    def __init__(
        self,
        *,
        label: str,
        initial_text: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.label = QtWidgets.QLabel(label)
        self.line_edit = QtWidgets.QLineEdit(initial_text)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        self.setLayout(layout)

    @property
    def value(self) -> fr.Fraction:
        try:
            amount = fr.Fraction(self.line_edit.text())
        except (ValueError, ZeroDivisionError) as error:
            raise ValueError(self.validation_message) from error
        if amount <= 0:
            raise ValueError(self.validation_message)
        return amount

    def value_or_warn(
        self,
        *,
        parent: QtWidgets.QWidget | None = None,
    ) -> fr.Fraction | None:
        try:
            return self.value
        except ValueError:
            QtWidgets.QMessageBox.warning(
                parent or self,
                self.validation_title,
                self.validation_message,
            )
            return None
