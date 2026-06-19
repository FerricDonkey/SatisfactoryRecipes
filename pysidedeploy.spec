[app]

# display/output name for the deployed application.
title = SatisfactoryRecipes

# paths are relative to this configuration file unless otherwise noted.
project_dir = src/satisfactory_recipes
input_file = src\satisfactory_recipes\__main__.py
exec_directory = dist
project_file = 

# add assets/satisfactory-recipes.ico here when the application icon is ready.
icon = .venv\Lib\site-packages\PySide6\scripts\deploy_lib\pyside_icon.ico

[python]

# pyside6-deploy replaces this with the active environment at build time.
python_path = C:\Users\Suggs\source\repos\SatisfactoryRecipes\.venv\Scripts\python.exe
packages = Nuitka==4
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]
qml_files = 
excluded_qml_plugins = 
modules = Core,Gui,Widgets

# leave blank so the native build discovers plugins for its own platform.
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,platforminputcontexts,platforms,platforms/darwin,platformthemes,styles,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

# accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,platforminputcontexts,platforms,platforms/darwin,platformthemes,styles,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

[android]
wheel_pyside = 
wheel_shiboken = 
plugins = 

[nuitka]
macos.permissions = 
mode = onefile
extra_args = --noinclude-qt-translations --windows-console-mode=force

# --quiet --noinclude-qt-translations --windows-console-mode = disable

[buildozer]
mode = debug
recipe_dir = 
jars_dir = 
ndk_path = 
sdk_path = 
local_libs = 
arch = 

