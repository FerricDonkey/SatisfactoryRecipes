"""Application-wide GUI theme, style, and zoom management."""

import collections.abc as cabc
from typing import Literal

from PySide6 import QtCore, QtGui, QtWidgets

from satisfactory_recipes import config as sr_config

type ThemeName = Literal["system", "light", "dark"]
type SaveCallback = cabc.Callable[[], None]


class AppearanceManager(QtCore.QObject):
    """Apply and persist application-wide appearance preferences."""

    appearance_changed = QtCore.Signal()

    def __init__(
        self,
        *,
        configuration: sr_config.Configuration,
        save_callback: SaveCallback,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.configuration = configuration
        self._save_callback = save_callback
        self._default_palette = QtWidgets.QApplication.palette()
        self._default_style_name = QtWidgets.QApplication.style().objectName()
        self._default_font = QtWidgets.QApplication.font()
        self._zoom_steps = 0

        self.zoom_in_action = QtGui.QAction("Zoom In", self)
        self.zoom_out_action = QtGui.QAction("Zoom Out", self)
        self.reset_zoom_action = QtGui.QAction("Reset Zoom", self)
        self.zoom_in_action.setShortcuts(
            [
                QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.ZoomIn),
                QtGui.QKeySequence("Ctrl+="),
            ]
        )
        self.zoom_out_action.setShortcut(QtGui.QKeySequence.StandardKey.ZoomOut)
        self.reset_zoom_action.setShortcut(QtGui.QKeySequence("Ctrl+0"))
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.reset_zoom_action.triggered.connect(self.reset_zoom)

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

    @property
    def zoom_steps(self) -> int:
        return self._zoom_steps

    def populate_options_menu(self, options_menu: QtWidgets.QMenu) -> None:
        theme_menu = options_menu.addMenu("Theme")
        theme_menu.addActions(self.theme_action_group.actions())
        style_menu = options_menu.addMenu("Qt Style")
        style_menu.addActions(self.style_action_group.actions())

    def apply_saved_preferences(self) -> None:
        saved_style = self.configuration.gui_style
        if saved_style is not None:
            available_styles = {
                style.lower(): style for style in QtWidgets.QStyleFactory.keys()
            }
            if saved_style.lower() in available_styles:
                self.set_style(saved_style, persist=False)
            else:
                self.configuration.gui_style = None
                self._save_callback()

        self.set_theme(self.configuration.gui_theme, persist=False)
        self._set_zoom_steps(self.configuration.gui_zoom_steps, persist=False)

    def zoom_in(self) -> None:
        self.set_zoom_steps(self._zoom_steps + 1)

    def zoom_out(self) -> None:
        self.set_zoom_steps(self._zoom_steps - 1)

    def reset_zoom(self) -> None:
        self.set_zoom_steps(0)

    def set_zoom_steps(self, steps: int) -> None:
        self._set_zoom_steps(steps, persist=True)

    def _set_zoom_steps(self, steps: int, *, persist: bool) -> None:
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

        if persist:
            self.configuration.gui_zoom_steps = self._zoom_steps
            self._save_callback()
        self.appearance_changed.emit()

    def set_theme(self, theme_name: ThemeName, *, persist: bool = True) -> None:
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
            self.configuration.gui_theme = theme_name
            self._save_callback()
        self.appearance_changed.emit()

    def set_style(self, style_name: str, *, persist: bool = True) -> None:
        available_styles = {
            style.lower(): style for style in QtWidgets.QStyleFactory.keys()
        }
        actual_style_name = available_styles.get(style_name.lower())
        if actual_style_name is None:
            return

        QtWidgets.QApplication.setStyle(actual_style_name)
        self._check_action_by_data(self.style_action_group, actual_style_name)
        if persist:
            self.configuration.gui_style = actual_style_name
            self._save_callback()
        self.appearance_changed.emit()

    def _handle_theme_action(self) -> None:
        action = self.sender()
        if not isinstance(action, QtGui.QAction):
            return
        theme_name = action.data()
        if theme_name in ("system", "light", "dark"):
            self.set_theme(theme_name)

    def _handle_style_action(self) -> None:
        action = self.sender()
        if not isinstance(action, QtGui.QAction):
            return
        style_name = action.data()
        if isinstance(style_name, str):
            self.set_style(style_name)

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
