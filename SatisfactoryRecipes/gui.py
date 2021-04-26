import sys

from typing import Union, Dict, Optional

from PyQt5 import QtGui as qgui
from PyQt5 import QtCore as qcore
from PyQt5.QtCore import Qt as qt
from PyQt5 import QtWidgets as qwid

from .recipes import constants as cons
from .recipes import production_chain as pc

BIG_FONT = qgui.QFont('Times New Roman', 16)
BIG_FONT.setBold(True)
MEDIUM_FONT = qgui.QFont('Times New Roman', 14)
MEDIUM_FONT.setBold(True)
NORMAL_FONT = qgui.QFont('Times New Roman', 12)

NO_SELECTION = '--None--'
NO_RECIPE = 'Pre-Made'

DEFAULT_AMOUNT_PER_MINUTE = 780  # one mk5 belt

class DaGui(qwid.QWidget):
    def __init__(self, main_window):
        qwid.QWidget.__init__(self, main_window)
        self.production_chain:Optional[pc.ProductionChain] = None

        self.master_h_layout = qwid.QHBoxLayout(self)

        self.product_chooser = ProductSelectionPane(parent = self)
        self.production_results_display = ProductionResultsPane(parent = self)
        production_vlayout = qwid.QVBoxLayout()
        production_vlayout.addLayout(self.product_chooser)
        production_vlayout.addLayout(self.production_results_display)

        self.recipe_display = ActiveRecipePanes(parent = self)
        self.required_ingredients_display = RequiredIngredientsPane(parent = self)

        self.master_h_layout.addLayout(production_vlayout)
        self.master_h_layout.addLayout(self.recipe_display)
        self.master_h_layout.addLayout(self.required_ingredients_display)


    def refresh(self):
        self.production_results_display.refresh()
        self.recipe_display.refresh()
        self.required_ingredients_display.refresh()

    def initialize_production_chain(self):
        """

        :return:
        """
        #self.clear_production_chain_gui()
        self.production_chain = pc.ProductionChain(
            desired_products_per_min_d = {
                self.product_chooser.product(): self.production_results_display.per_minute_entry.get_val()
            }
        )
        self.refresh()

class ProductSelectionPane(qwid.QVBoxLayout):
    def __init__(self, parent:DaGui):
        qwid.QVBoxLayout.__init__(self)

        self.parent = parent
        self.search_box = qwid.QLineEdit(font = NORMAL_FONT)
        self.product_drop_down = qwid.QComboBox(font = NORMAL_FONT)
        self.start_button = qwid.QPushButton('Start', font = NORMAL_FONT)

        self.addWidget(FLabel('Select Product:', font = MEDIUM_FONT))

        grid = qwid.QGridLayout()
        grid.addWidget(FLabel("Search: "), 0,0)
        grid.addWidget(self.search_box, 0, 1)
        grid.addWidget(FLabel("Product: "), 1, 0)
        grid.addWidget(self.product_drop_down, 1,1)

        self.addLayout(grid)
        self.addWidget(self.start_button, alignment = qt.AlignRight)

        self.search_box.textChanged.connect(self.filter_items)
        self.filter_items()
        self.start_button.clicked.connect(self.start_button_func)

    def product(self):
        return self.product_drop_down.currentText()

    def filter_items(self):
        self.product_drop_down.clear()
        self.product_drop_down.addItems(
            (NO_SELECTION,)+tuple(
                item
                for item in sorted(cons.PRODUCIBLE_ITEMS)
                if item.lower().startswith(self.search_box.text().strip().lower())
            )
        )

    def start_button_func(self):
        if self.product() != NO_SELECTION:
            self.parent.initialize_production_chain()
            self.product_drop_down.setCurrentIndex(0)


class ProductionResultsPane(qwid.QVBoxLayout):
    def __init__(self, parent:DaGui):
        qwid.QVBoxLayout.__init__(self)
        self.parent = parent
        self.setAlignment(qcore.Qt.AlignTop)
        self.addWidget(FLabel('Goal (per minute)           ', font = MEDIUM_FONT))
        goal_hlayout = qwid.QHBoxLayout()

        self.product_flabel = FLabel('None')
        self.per_minute_entry = NumberEntry(default = DEFAULT_AMOUNT_PER_MINUTE)
        self.per_minute_entry.setText(format_num(DEFAULT_AMOUNT_PER_MINUTE))
        self.per_minute_entry.editingFinished.connect(self.per_minute_change_function)

        goal_hlayout.addWidget(FLabel('  '))
        goal_hlayout.addWidget(self.product_flabel)
        goal_hlayout.addWidget(self.per_minute_entry)
        self.addLayout(goal_hlayout)

        self.addWidget(FLabel(' '))  # spacer
        self.addWidget(FLabel('Excess/Short Products per minute', font = MEDIUM_FONT))
        
        # I'm still not really sure how much of this is necessary, but it works
        self.excess_container_widget = qwid.QWidget()
        self.excess_container_layout = qwid.QGridLayout(self.excess_container_widget)
        self.excess_container_layout.setAlignment(qcore.Qt.AlignTop)

        self.scrolling_excess_area = qwid.QScrollArea()
        self.scrolling_excess_area.setVerticalScrollBarPolicy(qcore.Qt.ScrollBarAlwaysOn)
        self.scrolling_excess_area.setWidget(self.excess_container_widget)
        self.addWidget(self.scrolling_excess_area)

    def per_minute_change_function(self):
        prod_chain = self.parent.production_chain
        new_consumption = self.per_minute_entry.get_val()
        prev_consumption = prod_chain.get_desired_per_minute(prod_chain.get_desired_products()[0])
        self.parent.production_chain.multiply_full_chain(new_consumption/prev_consumption)
        self.parent.refresh()

    def clear_scroll(self):
        try:
            self.excess_container_widget.deleteLater()
        except:
            pass

    def refresh(self):
        # todo currently supports one product, change maybe
        if self.parent.production_chain is not None:
            prod_name = self.parent.production_chain.get_desired_products()[0]
            amount = format_num(self.parent.production_chain.get_desired_per_minute(prod_name))
        else:
            prod_name = 'None'
            amount = format_num(DEFAULT_AMOUNT_PER_MINUTE)
        self.product_flabel.setText(prod_name)
        self.per_minute_entry.setText(amount)

        # still not really sure what's going on here
        self.clear_scroll()
        self.excess_container_widget = qwid.QWidget()
        self.excess_container_layout = qwid.QGridLayout(self.excess_container_widget)
        self.excess_container_layout.setAlignment(qcore.Qt.AlignTop)

        if self.parent.production_chain:
            for index, (product, per_min) in enumerate(self.parent.production_chain.get_products_per_minute_d().items()):
                self.excess_container_layout.addWidget(FLabel(product+':'), index, 0)
                self.excess_container_layout.addWidget(FLabel(format_num(per_min)), index, 1)

        self.scrolling_excess_area.setWidget(self.excess_container_widget)


class RequiredIngredientsPane(qwid.QVBoxLayout):
    """
    Show all ingredients that are not being made by active recipes
    """
    def __init__(self, parent:DaGui):
        """
        Initialize
        """
        qwid.QVBoxLayout.__init__(self)
        self.parent = parent
        self.addWidget(FLabel('Input Ingredients (per minute)        ', font = MEDIUM_FONT))

        self.ingredient_container_widget = qwid.QWidget()

        self.ingredient_container_layout = qwid.QVBoxLayout(self.ingredient_container_widget)
        self.ingredient_container_layout.setAlignment(qcore.Qt.AlignTop)

        self.scrolling_ingredient_area = qwid.QScrollArea()
        self.scrolling_ingredient_area.setVerticalScrollBarPolicy(qcore.Qt.ScrollBarAlwaysOn)
        self.scrolling_ingredient_area.setWidget(self.ingredient_container_widget)
        self.addWidget(self.scrolling_ingredient_area)

    def clear(self):
        """
        Remove all ingredient widgets from the ingredient area
        """
        try:
            self.ingredient_container_widget.deleteLater()
        except:
            pass

    def refresh(self):
        self.clear()
        self.ingredient_container_widget = qwid.QWidget()
        self.ingredient_container_layout = qwid.QVBoxLayout(self.ingredient_container_widget)
        self.ingredient_container_layout.setAlignment(qcore.Qt.AlignTop)

        if self.parent.production_chain:
            # recall this is a property, so best to snapshot (at least until I get around to caching the property)
            ingredients_per_minute = self.parent.production_chain.get_ingredients_per_minute_d().items()
            for index, (ingredient, per_minute) in enumerate(ingredients_per_minute):
                NewPaneClass = RawResourcePane if ingredient in cons.RAW_RESOURCES else CompositeResourcePane
                self.ingredient_container_layout.addLayout(
                    NewPaneClass(parent = self.parent, item = ingredient, per_minute = per_minute)
                )
                if index +1 < len(ingredients_per_minute):
                    self.ingredient_container_layout.addWidget(HorizontalLineWidget())

        self.scrolling_ingredient_area.setWidget(self.ingredient_container_widget)

class SingleIngredientPane(qwid.QVBoxLayout):
    """
    For as yet unsatisfied ingredients. Used as a base class for RawResourcePane or
    CompositeResourcePane only
    """
    def __init__(self, parent: DaGui, item:str, per_minute: Union[int, float]):
        qwid.QVBoxLayout.__init__(self)
        self.parent = parent
        self.item = item
        self.addWidget(FLabel(f'{self.item}'))
        self.per_minute_entry = NumberEntry(default = DEFAULT_AMOUNT_PER_MINUTE)
        self.per_minute_entry.setFixedWidth(100)
        self.per_minute_entry.setText(format_num(per_minute))
        self.per_minute_entry.editingFinished.connect(self.per_minute_change_function)

    def per_minute_change_function(self):
        new_consumption = self.per_minute_entry.get_val()
        prev_consumption = self.parent.production_chain.get_ingredients_per_minute_d()[self.item]
        self.parent.production_chain.multiply_full_chain(new_consumption/prev_consumption)
        self.parent.production_chain.multiply_desired_amounts(new_consumption/prev_consumption)
        self.parent.refresh()

class RawResourcePane(SingleIngredientPane):
    """
    For as yet unsatisfied ingredients that cannot be produced from other ingredients
    """
    def __init__(self, parent:DaGui, item:str, per_minute: Union[int, float]):
        SingleIngredientPane.__init__(
            self,
            parent = parent,
            item = item,
            per_minute = per_minute
        )

        hlayout = qwid.QHBoxLayout()
        hlayout.addWidget(FLabel("       Per min:"))
        hlayout.addWidget(self.per_minute_entry)
        self.addLayout(hlayout)

class CompositeResourcePane(SingleIngredientPane):
    """
    For as yet unsatisfied ingredients that can be produced from other ingredients
    """
    def __init__(self, parent: DaGui, item: str, per_minute: Union[int, float]):
        SingleIngredientPane.__init__(
            self,
            parent = parent,
            item = item,
            per_minute = per_minute
        )
        self.recipe_drop_down = qwid.QComboBox(font = NORMAL_FONT)
        self.recipe_drop_down.addItems(
            (NO_RECIPE,)+
            tuple(
                name
                for name, recipe in sorted(cons.NAME_TO_RECIPE_D.items())
                if self.item in recipe.get_products_per_minute_d()
            )
        )
        self.recipe_drop_down.currentTextChanged.connect(self.recipe_selection_function)
        self.addWidget(self.recipe_drop_down)

        hlayout = qwid.QHBoxLayout()
        hlayout.addWidget(FLabel("       Per min:"))
        hlayout.addWidget(self.per_minute_entry)
        self.addLayout(hlayout)

    def recipe_selection_function(self):
        self.parent.production_chain.add_recipe(self.recipe_drop_down.currentText())
        self.parent.refresh()

class ActiveRecipePanes(qwid.QVBoxLayout):
    """
    For showing and modifying recipes that are in use by the production line
    """
    def __init__(self, parent:DaGui):
        """
        Initialize
        """
        qwid.QVBoxLayout.__init__(self)
        self.parent = parent

        self.setAlignment(qt.AlignTop)
        self.addWidget(FLabel('Active Recipes' + ' '*40, font = MEDIUM_FONT))

        self.recipe_container_widget = qwid.QWidget()

        self.recipe_container_layout = qwid.QVBoxLayout(self.recipe_container_widget)
        self.recipe_container_layout.setAlignment(qcore.Qt.AlignTop)

        self.scrolling_recipe_area = qwid.QScrollArea()
        self.scrolling_recipe_area.setVerticalScrollBarPolicy(qcore.Qt.ScrollBarAlwaysOn)
        self.scrolling_recipe_area.setWidget(self.recipe_container_widget)
        self.addWidget(self.scrolling_recipe_area)

    def clear(self):
        """
        Remove all ingredient widgets from the ingredient area
        """
        try:
            self.recipe_container_widget.deleteLater()
        except:
            pass

    def refresh(self):
        print("sup")
        self.clear()
        self.recipe_container_widget = qwid.QWidget()
        self.recipe_container_layout = qwid.QVBoxLayout(self.recipe_container_widget)
        self.recipe_container_layout.setAlignment(qcore.Qt.AlignTop)

        if self.parent.production_chain:
            for index, recipe_name in enumerate(self.parent.production_chain.active_name_to_recipes_d):
                self.recipe_container_layout.addLayout(
                    RecipePane(parent = self.parent, recipe_name = recipe_name)
                )
                if index + 1 < len(self.parent.production_chain.active_name_to_recipes_d):
                    self.recipe_container_layout.addWidget(HorizontalLineWidget())

        self.scrolling_recipe_area.setWidget(self.recipe_container_widget)

class RecipePane(qwid.QVBoxLayout):
    """
    For displaying a single parent
    """
    def __init__(self, parent:DaGui, recipe_name:str):
        """
        Initialize
        """
        qwid.QVBoxLayout.__init__(self)
        self.parent = parent
        self.recipe_name = recipe_name

        # RECIPE      [Remove]
        # This is dumb, but will right justify the delete and left justify the name
        outerhlayout = qwid.QHBoxLayout()
        innerhlayout1 = qwid.QHBoxLayout()
        innerhlayout2 = qwid.QHBoxLayout()
        innerhlayout2.setAlignment(qt.AlignRight)
        innerhlayout1.addWidget(FLabel(self.recipe_name))
        delbutton = qwid.QPushButton('Remove')
        delbutton.clicked.connect(self.remove_recipe_func)
        innerhlayout2.addWidget(delbutton)
        self.addLayout(outerhlayout)

        # Machine Count: <entry box> [Rescale]
        hlayout = qwid.QHBoxLayout()
        hlayout.addWidget(FLabel('Machine Count:'))
        self.scale_entry_box = NumberEntry()
        self.scale_entry_box.setText(format_num(
            self.parent.production_chain.active_name_to_recipes_d[self.recipe_name].scale
        ))
        self.scale_entry_box.editingFinished.connect(
            lambda: self.rescale_count_func(scale = self.scale_entry_box.get_val())
        )
        rescale_button = qwid.QPushButton('Rescale')
        rescale_button.clicked.connect(lambda: self.rescale_count_func(scale = None))

        grid = qwid.QGridLayout()
        grid.addWidget(FLabel('Produces'), 0, 0, 1, 3)
        # vertical line between these two
        grid.addWidget(FLabel('Consumes'), 0, 4, 1, 3)
        grid.addWidget(FLabel('  '), 1, 0) # spacing
        grid.addWidget(FLabel('  '), 1, 4)

        this_recipe = self.parent.production_chain.active_name_to_recipes_d[self.recipe_name]
        prod_per_minute = this_recipe.get_products_per_minute_d()
        consumed_per_minute = this_recipe.get_ingredients_per_minute_d()
        for base_col, source_d in zip((1, 5), (prod_per_minute, consumed_per_minute)):
            for row_offset, (product, quantity) in enumerate(source_d.items()):
                grid.addWidget(FLabel(product), 1 + row_offset, base_col)
                grid.addWidget(FLabel(format_num(quantity)), 1 + row_offset, base_col+1)

        grid.addWidget(VerticalLineWidget(), 0, 3, max(len(prod_per_minute), len(consumed_per_minute)), 1)

    def remove_recipe_func(self):
        self.parent.production_chain.remove_recipe(recipe_name = self.recipe_name)
        self.parent.refresh()

    def rescale_count_func(self, scale: Union[None, int, float]):
        self.parent.production_chain.rescale_single_recipe(
            recipe_name = self.recipe_name,
            new_scale = scale
        )
        self.parent.refresh()

class FLabel(qwid.QLabel):
    """
    QLabel augmented with a default font keyword argument, so that font can be set at creation time
    """
    def __init__(self, *args, font:qgui.QFont = NORMAL_FONT, right_justify = False, **kwargs):
        qwid.QLabel.__init__(self, *args, **kwargs)
        if right_justify:
            self.setAlignment(qcore.Qt.AlignRight)

        if font is not None:
            self.setFont(font)

class NumberEntry(qwid.QLineEdit):
    def __init__(self, *args, font = NORMAL_FONT, default:Union[None, int, float] = 1, **kwargs):
        qwid.QLineEdit.__init__(self, *args, font = font, **kwargs)
        self._validator = qgui.QDoubleValidator()  # this is stupid, but the internet tells me I have to do this stupid thing
        self.setValidator(self._validator)
        self.default = default

    def get_val(self):
        if '.' not in self.text():
            return int(self.text()) if self.text() else self.default
        elif self.text() != '.':
            return float(self.text())
        return self.default


def launch():
    gui_executor_loop_thing = qwid.QApplication(sys.argv)  # inherit command line args for qt nonsense
    #screen_dims = gui_executor_loop_thing.primaryScreen().size()

    # apparently if you don't keep a reference to the gui, it gets killed.
    main_window = qwid.QMainWindow()
    da_gui = DaGui(main_window = main_window)
    main_window.setCentralWidget(da_gui)
    main_window.setWindowTitle('Planner')
    main_window.show()

    gui_executor_loop_thing.exec_()

class HorizontalLineWidget(qwid.QFrame):
    def __init__(self):
        qwid.QFrame.__init__(self)
        self.setFrameShape(qwid.QFrame.HLine)
        self.setFrameShadow(qwid.QFrame.Sunken)

class VerticalLineWidget(qwid.QFrame):
    def __init__(self):
        qwid.QFrame.__init__(self)
        self.setFrameShape(qwid.QFrame.VLine)
        self.setFrameShadow(qwid.QFrame.Sunken)

def format_num(num: Union[int, float]) -> str:
    if isinstance(num, int):
        return str(num)
    return f'{num:0.2f}'