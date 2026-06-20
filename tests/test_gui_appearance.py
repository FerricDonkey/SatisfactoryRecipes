from PySide6 import QtCore, QtGui, QtWidgets
import pytestqt.qtbot

from satisfactory_recipes import config as sr_config
from satisfactory_recipes.gui import appearance


def test_appearance_manager_owns_actions_and_persists_user_changes(
    qtbot: pytestqt.qtbot.QtBot,
    qapp: QtWidgets.QApplication,
) -> None:
    original_palette = QtGui.QPalette(qapp.palette())
    original_font = QtGui.QFont(qapp.font())
    original_stylesheet = qapp.styleSheet()
    configuration = sr_config.Configuration()
    save_count = 0
    change_count = 0

    def record_save() -> None:
        nonlocal save_count
        save_count += 1

    manager = appearance.AppearanceManager(
        configuration=configuration,
        save_callback=record_save,
    )

    def record_change() -> None:
        nonlocal change_count
        change_count += 1

    manager.appearance_changed.connect(record_change)
    menu = QtWidgets.QMenu()
    view_menu = QtWidgets.QMenu()
    qtbot.addWidget(menu)
    qtbot.addWidget(view_menu)
    manager.populate_options_menu(menu)
    manager.populate_view_menu(view_menu)

    try:
        manager.set_theme("dark")
        manager.set_zoom_steps(99)
        selected_font = QtGui.QFontDatabase.families()[0]
        manager.set_font_family(selected_font)

        assert configuration.gui_theme == "dark"
        assert configuration.gui_zoom_steps == 8
        assert configuration.gui_font_family == selected_font
        assert manager.zoom_steps == 8
        assert manager.font_family == selected_font
        assert qapp.font().family() == selected_font
        assert qapp.styleSheet()
        assert save_count == 3
        assert change_count == 3
        assert len(menu.actions()) == 2
        assert len(view_menu.actions()) == 1
        font_menu = view_menu.actions()[0].menu()
        assert isinstance(font_menu, QtWidgets.QMenu)
        assert len(font_menu.actions()) > 1
        assert manager.zoom_in_action.shortcut().toString()
        assert manager.zoom_out_action.shortcut().toString()
        assert manager.reset_zoom_action.shortcut().toString() == "Ctrl+0"

        manager.set_zoom_steps(-99)
        assert configuration.gui_zoom_steps == -5
        assert manager.zoom_steps == -5
        assert qapp.font().family() == selected_font
        assert save_count == 4
        assert change_count == 4
    finally:
        qapp.setPalette(original_palette)
        qapp.setFont(original_font)
        qapp.setStyleSheet(original_stylesheet)


def test_saved_preferences_apply_without_rewriting_valid_config(
    qapp: QtWidgets.QApplication,
) -> None:
    original_palette = QtGui.QPalette(qapp.palette())
    original_font = QtGui.QFont(qapp.font())
    original_stylesheet = qapp.styleSheet()
    original_style = qapp.style().objectName()
    saved_font = QtGui.QFontDatabase.families()[0]
    configuration = sr_config.Configuration(
        gui_theme="light",
        gui_style=original_style,
        gui_font_family=saved_font,
        gui_zoom_steps=-3,
    )
    save_count = 0

    def record_save() -> None:
        nonlocal save_count
        save_count += 1

    manager = appearance.AppearanceManager(
        configuration=configuration,
        save_callback=record_save,
    )

    try:
        manager.apply_saved_preferences()

        assert manager.zoom_steps == -3
        assert manager.font_family == saved_font
        assert qapp.font().family() == saved_font
        assert qapp.styleSheet()
        assert save_count == 0
        theme_action = manager.theme_action_group.checkedAction()
        assert theme_action is not None
        assert theme_action.data() == "light"
        style_action = manager.style_action_group.checkedAction()
        assert style_action is not None
        assert str(style_action.data()).lower() == original_style.lower()
    finally:
        qapp.setPalette(original_palette)
        qapp.setFont(original_font)
        qapp.setStyleSheet(original_stylesheet)
        QtWidgets.QApplication.setStyle(original_style)


def test_invalid_saved_style_is_cleared_and_saved() -> None:
    configuration = sr_config.Configuration(gui_style="Definitely Not A Qt Style")
    save_count = 0

    def record_save() -> None:
        nonlocal save_count
        save_count += 1

    manager = appearance.AppearanceManager(
        configuration=configuration,
        save_callback=record_save,
    )

    manager.apply_saved_preferences()

    assert configuration.gui_style is None
    assert save_count == 1


def test_unavailable_saved_font_uses_qt_default_without_losing_preference(
    qapp: QtWidgets.QApplication,
) -> None:
    original_font = QtGui.QFont(qapp.font())
    unavailable_font = "Definitely Not An Installed Font"
    configuration = sr_config.Configuration(gui_font_family=unavailable_font)
    save_count = 0

    def record_save() -> None:
        nonlocal save_count
        save_count += 1

    manager = appearance.AppearanceManager(
        configuration=configuration,
        save_callback=record_save,
    )

    try:
        manager.apply_saved_preferences()

        assert manager.font_family == original_font.family()
        assert qapp.font().family() == original_font.family()
        assert configuration.gui_font_family == unavailable_font
        assert save_count == 0
    finally:
        qapp.setFont(original_font)


def test_font_picker_accepts_cancels_and_restores_automatic_font(
    qapp: QtWidgets.QApplication,
) -> None:
    original_font = QtGui.QFont(qapp.font())
    configuration = sr_config.Configuration()
    save_count = 0

    def record_save() -> None:
        nonlocal save_count
        save_count += 1

    manager = appearance.AppearanceManager(
        configuration=configuration,
        save_callback=record_save,
    )
    selected_font = next(
        family
        for family in QtGui.QFontDatabase.families()
        if QtGui.QFontDatabase.isSmoothlyScalable(family)
    )

    def cancel_picker() -> None:
        dialog = qapp.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QDialog)
        font_box = dialog.findChild(QtWidgets.QFontComboBox)
        assert font_box is not None
        assert font_box.fontFilters() & QtWidgets.QFontComboBox.FontFilter.ScalableFonts
        dialog.reject()

    def accept_picker() -> None:
        dialog = qapp.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QDialog)
        font_box = dialog.findChild(QtWidgets.QFontComboBox)
        assert font_box is not None
        font_box.setCurrentFont(QtGui.QFont(selected_font))
        dialog.accept()

    try:
        QtCore.QTimer.singleShot(0, cancel_picker)
        manager.choose_font_action.trigger()

        assert configuration.gui_font_family is None
        assert save_count == 0

        QtCore.QTimer.singleShot(0, accept_picker)
        manager.choose_font_action.trigger()

        assert configuration.gui_font_family == selected_font
        assert manager.font_family == selected_font
        assert manager.current_font_action.text() == f"Current: {selected_font}"
        assert save_count == 1

        manager.use_automatic_font_action.trigger()

        assert configuration.gui_font_family is None
        assert manager.font_family == manager.automatic_font_family
        assert manager.current_font_action.text().endswith("(automatic)")
        assert save_count == 2
    finally:
        qapp.setFont(original_font)


def test_every_available_qt_style_supports_each_theme(
    qtbot: pytestqt.qtbot.QtBot,
    qapp: QtWidgets.QApplication,
) -> None:
    original_palette = QtGui.QPalette(qapp.palette())
    original_font = QtGui.QFont(qapp.font())
    original_stylesheet = qapp.styleSheet()
    original_style = qapp.style().objectName()
    manager = appearance.AppearanceManager(
        configuration=sr_config.Configuration(),
        save_callback=lambda: None,
    )
    probe = QtWidgets.QTableWidget(1, 1)
    probe.setItem(0, 0, QtWidgets.QTableWidgetItem("Theme probe"))
    qtbot.addWidget(probe)
    probe.show()
    themes: tuple[appearance.ThemeName, ...] = ("system", "light", "dark")

    try:
        for style_name in QtWidgets.QStyleFactory.keys():
            manager.set_style(style_name, persist=False)
            checked_style = manager.style_action_group.checkedAction()
            assert checked_style is not None
            assert str(checked_style.data()).lower() == style_name.lower()
            for theme_name in themes:
                manager.set_theme(theme_name, persist=False)
                qapp.processEvents()
                checked_theme = manager.theme_action_group.checkedAction()
                assert checked_theme is not None
                assert checked_theme.data() == theme_name
                assert probe.isVisible()
    finally:
        qapp.setPalette(original_palette)
        qapp.setFont(original_font)
        qapp.setStyleSheet(original_stylesheet)
        QtWidgets.QApplication.setStyle(original_style)
