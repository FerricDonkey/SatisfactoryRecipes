import dataclasses
import fractions as fr

from satisfactory_recipes import info_classes as ic
from satisfactory_recipes.gui import recipe_format
from tests import support


def test_recipe_html_escapes_domain_names() -> None:
    input_item = support.make_fake_item("Ore <Raw>")
    output_item = support.make_fake_item("Ingot & Plate")
    building = ic.Building(
        class_name="Build_Test_C",
        name="Maker > Constructor",
        category="manufacturing",
        power_draw=fr.Fraction(4),
    )
    recipe = dataclasses.replace(
        support.make_fake_recipe(
            class_name="Recipe_Test_C",
            name="Make <This> & That",
            inputs={input_item: fr.Fraction(1)},
            products={output_item: fr.Fraction(1)},
        ),
        produced_in=building,
    )

    details = recipe_format.recipe_details_html(recipe, fr.Fraction(1))

    assert "Make &lt;This&gt; &amp; That" in details
    assert "Ore &lt;Raw&gt;" in details
    assert "Ingot &amp; Plate" in details
    assert "Maker &gt; Constructor" in details
