from PySide6 import QtGui, QtWidgets
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
    qtbot.addWidget(menu)
    manager.populate_options_menu(menu)

    try:
        manager.set_theme("dark")
        manager.set_zoom_steps(99)

        assert configuration.gui_theme == "dark"
        assert configuration.gui_zoom_steps == 8
        assert manager.zoom_steps == 8
        assert qapp.styleSheet()
        assert save_count == 2
        assert change_count == 2
        assert len(menu.actions()) == 2
        assert manager.zoom_in_action.shortcut().toString()
        assert manager.zoom_out_action.shortcut().toString()
        assert manager.reset_zoom_action.shortcut().toString() == "Ctrl+0"

        manager.set_zoom_steps(-99)
        assert configuration.gui_zoom_steps == -5
        assert manager.zoom_steps == -5
        assert save_count == 3
        assert change_count == 3
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
    configuration = sr_config.Configuration(
        gui_theme="light",
        gui_style=original_style,
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
