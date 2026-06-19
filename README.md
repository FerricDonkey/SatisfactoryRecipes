# Satisfactory Recipes

Satisfactory Recipes is a bookkeeping tool for planning production chains in the game [Satisfactory](https://www.satisfactorygame.com/).

## What It Does

The program will allow you to chose an item to produce, choose recipes to produce it, chose recipes to produce the ingredients it needs, choose recipes to produce those ingredients, and so on.

It will track how many machines (not accounting for over/under clocking) you need for each recipe, and what the total inputs/outputs are. It will NOT suggest flow from machine to machine, plan layouts, etc. That's still for you.


The app works with the `en-us.json` documentation file installed with Satisfactory. It does not include or redistribute game data. It will attempt to locate this file automatically, but if it fails it will prompt you to point you at the location where you have installed the game or placed your copy of the file.

**NOTE:** This uses fractions for math, so floating point errors should be avoided. This does mean that if you mean 1/3, you should enter 1/3, not 0.333.

## Installation

### "You Don't Know or Care What Python Packages Are" Installation

Download the project, unzip it to a folder, then run the installer script for your
operating system:

- Windows: double-click `install.ps1`, or run it from PowerShell.
- Linux/mac: run `./install.sh` from a terminal.

The installer downloads `uv` if needed, uses `uv` to install Python 3.14 if needed,
installs the project dependencies, and creates a launcher script in the project
folder. After installation, start the GUI by double clicking the new `.ps1` file for windows, or `.sh` file for linux/mac`.

### "You Know What You're Doing" Installation

If you already know your way around Python packaging, install Python 3.14 or newer
and then install the project with `uv` or `pip`. If using pip and if you have not used uv before, you may need to first `pip install "uv_build>=0.9.17,<0.10.0"` (or you can install uv directly).

```sh
uv sync
uv run sat-rec gui
```

With `pip`, create and activate a Python 3.14+ virtual environment, then install
the project:

```sh
python -m pip install .
sat-rec gui
```


## Interfaces

The project currently has both a GUI and an interactive CLI. The author was too lazy to make the gui himself, so had an AI do it.

### GUI

```sh
uv run sat-rec gui
```

Useful options:

```sh
uv run sat-rec gui --infile saved_file.json
uv run sat-rec gui --docs-path "path/to/CommunityResources/Docs/en-us.json"
uv run sat-rec gui --game-path "path/to/Satisfactory"
uv run sat-rec gui --scale 1/4
```

The GUI supports:

- searchable goal and recipe selection
- save/load
- recipe input scaling
- light/dark/system themes
- Qt style selection
- zoom with `Ctrl++`, `Ctrl+-`, and `Ctrl+0`
- editable input/output rates for chain scaling
- detailed recipe cards

### CLI

```sh
uv run sat-rec cli
```

For now, running without a subcommand also launches the CLI:

```sh
uv run sat-rec
```

Useful options:

```sh
uv run sat-rec cli --infile uranium.json
uv run sat-rec cli --docs-path "path/to/CommunityResources/Docs/en-us.json"
uv run sat-rec cli --game-path "path/to/Satisfactory"
uv run sat-rec cli --scale 1/4
```

## Satisfactory Docs Discovery

On startup, the app tries to find Satisfactory's docs file in this order:

1. a configured `docs_path`
2. a configured `game_path`
3. common Steam install locations across drive letters

If a valid path is found or supplied, it is remembered in the user config file
using `platformdirs`.

Stale configured paths are ignored with a warning. Malformed config files are
also ignored without preventing the program from starting.

## Development

This project uses Python 3.14+ and `uv`.

Install/sync dependencies:

```sh
uv sync
```

Run tests:

```sh
uv run pytest
```

Run type and lint checks:

```sh
uv run pyright
uv run mypy src tests
uv run ruff check
```

## License

This project is licensed under the
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

Noncommercial personal, hobby, educational, and similar use is allowed under
that license. Commercial use requires separate permission from the author.

Copyright Jacob Suggs.
