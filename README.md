# Satisfactory Recipes

Satisfactory Recipes is a bookkeeping tool for planning production chains in the game [Satisfactory](https://www.satisfactorygame.com/).

## What It Does

You choose an item you want to make. You add a recipe to produce some number of that item. You add recipes to produce any ingredients you need for that recipe. You add recipes to produce ingredients needed to produce those ingredients. Lather, rinse, repeat.

The program remembers what you tell it, and scales recipes to make the required number of each ingredient automatically, as well as providing recipes that can make the item. It also allows you scale the whole kit and kaboodle up or down to produce or consume any amount of any item involved.

The program DOES tell you how many of each input you need, and how many of each machine making each recipe you need. It will give an estimated mean power consumption, ignoring sloops, clock speed, games settings etc.

The program DOES NOT tell you which machines hook to which means or which outputs go to which inputs. But it DOES give you a list of all recipes with their scaled inputs and outputs. Figuring out how to hook them up is up to you.

**NOTE:** This uses fractions for math, to avoid float rounding. This does mean that if you mean 1/3, you should enter 1/3, not 0.333. And  if you mean 5/3, you should enter 5/3, not 1.6666.

Recipes etc are read from game files that YOU must provide, but the program tries to make that easy on you (see below). Hopefully, if you have Satisfactory installed, you don't have to worry about it much.

## Installation

### "Sweaty nerds, where exe" Installation

Download and use the exe. Windows will yell at you and tell you it's unsafe. It's not, unless I got supply-chained, but it's up to you if you trust that. If you don't like that, follow the below step. It's not any safer, but it might feel like it is.

This works on windows because that's all I did. Find some other sweaty nerd to convert it to executables for your OS, if you want.

### "I am the sweaty nerd" Installation

Get python 3.14 somehow. Install this package into it. You will need uv build. If you install uv and git for your os first (see their docs), then:

```bash
git clone https://github.com/FerricDonkey/SatisfactoryRecipes.git
cd SatisfactoryRecipes
uv python install 3.14
uv run sat-rec  # launches, if run from this directory
```

Make whatever scripts/aliases make you happy to `uv run sat-rec` from wherever you want.

### "I am the sweaty nerd, but I still want an exe for some reason" Installation

```bash
git clone https://github.com/FerricDonkey/SatisfactoryRecipes.git
cd SatisfactoryRecipes
uv python install 3.14
uv sync --frozen --no-default-groups --group deploy
mkdir dist
uv run --no-sync pyside6-deploy -c pysidedeploy.spec -f --name SatisfactoryRecipes
./dist/SatisfactoryRecipes.exe  # Launches
```

## Usage

There is a gui and a cli. Why both? Because I made the cli first. Then I made an AI make the gui, because I still didn't want to. And I haven't deleted the cli because reasons, I dunno.

If you downloaded the exe, double click it. If you want, use it from the command line with some of the following arguments, in place of the `uv run sat-rec` part, but be aware that this is the first step to becoming a sweaty nerd.

```bash
uv run sat-rec  # launches gui
uv run sat-rec gui  # still launches gui, but you got to type 3 extra characters
uv run sat-rec cli  # launches the cli. I dunno why you'd want this.

### The below all work with gui replaced with cli or omitted
# load a file from the start
uv run sat-rec gui --infile saved_file.json

# specify where the docs are
uv run sat-rec gui --docs-path "path/to/CommunityResources/Docs/en-us.json"

# specify where the game is and make us find the docs within it
uv run sat-rec gui --game-path "path/to/Satisfactory"

# Initialize with recipe inputs scaled down to 1/4, as added in satisfactory 1.2
uv run sat-rec gui --scale 1/4
```

### How the gui works

You like click on things and stuff. There's a bunch of buttons, but you can sometimes double click entries in tables to make stuff happen.

It'll remember some of your preferences by putting them in some directory that the internet told me was an ok place on your computer to dump crap. You're welcome.

## Satisfactory Docs Discovery

This program needs the satisfactory information stored in there `en-US.json` (will other localizations work? I dunno, never tried. Knock yourself out, see what happens).

That file isn't mine, so I'm not giving it to you. But if you own satisfactory and have it installed, then you have that file, and you can use it. The program will search some places that I thought it might be on windows, plus some places that an AI thought it might be for people who use weird operating systems. If we didn't guess where yours is, you can enter a path. It should be in `your_satisfactory_installdir/CommunityResources/Docs/en-us.json`

## License

This project is licensed under the
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/).

Noncommercial personal, hobby, educational, and similar use is allowed under
that license. Commercial use requires separate permission from the author.

Copyright Jacob Suggs.

## Warranty

There isn't one. Insofar as I'm aware, it probably won't light your computer on fire, but if it does, that's what you get for running random software off the internet.
