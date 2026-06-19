"""Shared rich recipe formatting for GUI views."""

from __future__ import annotations

import fractions as fr
import html

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes.gui import number_format


def recipe_details_html(recipe: ic.Recipe, count: fr.Fraction) -> str:
    title = f"{html.escape(recipe.name)} x {number_format.decimal(count)}"
    return (
        '<div class="recipe-card">'
        f'<div class="recipe-title">{title}</div>'
        f"{recipe_body_html(recipe, count)}"
        "</div>"
    )


def recipe_body_html(recipe: ic.Recipe, count: fr.Fraction) -> str:
    produce_items = "".join(
        "<li>"
        f"<b>{html.escape(item.name)}</b> x "
        f"{number_format.decimal(recipe.products[item], precision=1)} "
        f"({number_format.decimal(per_min * count)}/min)"
        "</li>"
        for item, per_min in recipe.products_per_min.items()
    )
    consume_items = "".join(
        "<li>"
        f"<b>{html.escape(item.name)}</b> x "
        f"{number_format.decimal(recipe.inputs[item], precision=1)} "
        f"({number_format.decimal(per_min * count)}/min)"
        "</li>"
        for item, per_min in recipe.inputs_per_min.items()
    )

    produced_in = ""
    if recipe.produced_in is not None:
        produced_in = (
            '<div class="power">'
            f"Produced in <b>{html.escape(recipe.produced_in.name)}</b> "
            f"({number_format.decimal(recipe.mean_power, unit='MW')} each: "
            f"{number_format.decimal(recipe.mean_power * count, unit='MW')})"
            "</div>"
        )

    return (
        '<div class="section-title">Produce</div>'
        f"<ul>{produce_items}</ul>"
        '<div class="section-title">Consume</div>'
        f"<ul>{consume_items}</ul>"
        f"{produced_in}"
    )


def recipe_exact_tooltip(recipe: ic.Recipe, count: fr.Fraction) -> str:
    """Return a rich tooltip listing the exact values displayed for a recipe."""
    lines = [f"Recipe count: {number_format.mixed_number(count)}"]
    lines.extend(
        f"Product {item.name}: {number_format.mixed_number(recipe.products[item])} "
        f"per craft; {number_format.mixed_number(per_min * count)}/min"
        for item, per_min in recipe.products_per_min.items()
    )
    lines.extend(
        f"Input {item.name}: {number_format.mixed_number(recipe.inputs[item])} "
        f"per craft; {number_format.mixed_number(per_min * count)}/min"
        for item, per_min in recipe.inputs_per_min.items()
    )
    if recipe.produced_in is not None:
        lines.append(
            "Mean power: "
            f"{number_format.mixed_number(recipe.mean_power)} MW each; "
            f"{number_format.mixed_number(recipe.mean_power * count)} MW total"
        )
    return f"<pre>{html.escape(chr(10).join(lines))}</pre>"


def recipe_details_document_html(recipe_blocks: list[str]) -> str:
    return """
        <style>
          body {
            font-family: sans-serif;
          }
          .recipe-card {
            border: 2px solid currentColor;
            border-radius: 6px;
            padding: 14px 16px;
            margin: 0 4px 20px 4px;
          }
          .recipe-title {
            font-size: 155%;
            font-weight: 700;
            border-bottom: 1px solid currentColor;
            padding-bottom: 5px;
            margin-bottom: 12px;
          }
          .section-title {
            font-size: 110%;
            font-weight: 700;
            margin-top: 10px;
            margin-bottom: 5px;
          }
          ul {
            margin-top: 2px;
            margin-bottom: 8px;
          }
          li {
            margin-bottom: 2px;
          }
          .power {
            margin-top: 8px;
          }
        </style>
        """ + "\n".join(recipe_blocks)
