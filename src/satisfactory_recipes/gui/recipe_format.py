"""Shared rich recipe formatting for GUI views."""

import fractions as fr

from satisfactory_recipes import info_classes as ic


def recipe_details_html(recipe: ic.Recipe, count: fr.Fraction) -> str:
    title = f"{recipe.name} x {count:.3f}"
    return (
        '<div class="recipe-card">'
        f'<div class="recipe-title">{title}</div>'
        f"{recipe_body_html(recipe, count)}"
        "</div>"
    )


def recipe_body_html(recipe: ic.Recipe, count: fr.Fraction) -> str:
    produce_items = "".join(
        "<li>"
        f"<b>{item.name}</b> x {recipe.products[item]:.1f} "
        f"({per_min * count:.3f}/min)"
        "</li>"
        for item, per_min in recipe.products_per_min.items()
    )
    consume_items = "".join(
        "<li>"
        f"<b>{item.name}</b> x {recipe.inputs[item]:.1f} "
        f"({per_min * count:.3f}/min)"
        "</li>"
        for item, per_min in recipe.inputs_per_min.items()
    )

    produced_in = ""
    if recipe.produced_in is not None:
        produced_in = (
            '<div class="power">'
            f"Produced in <b>{recipe.produced_in.name}</b> "
            f"({recipe.mean_power} MW each: {recipe.mean_power * count:.3f} MW)"
            "</div>"
        )

    return (
        '<div class="section-title">Produce</div>'
        f"<ul>{produce_items}</ul>"
        '<div class="section-title">Consume</div>'
        f"<ul>{consume_items}</ul>"
        f"{produced_in}"
    )


def recipe_details_document_html(recipe_blocks: list[str]) -> str:
    return (
        """
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
        """
        + "\n".join(recipe_blocks)
    )
