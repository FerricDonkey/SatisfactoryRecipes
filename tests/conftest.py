import os


# Qt chooses its platform plugin when QApplication is created. Keep the GUI suite
# runnable in CI and other sessions without a display server.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
