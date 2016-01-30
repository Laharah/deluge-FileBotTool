"""
Contains some common functions for manipulating gtk UIs
"""
__author__ = 'Lunchbox'

# noinspection PyUnresolvedReferences
import gtk


def inflate_list_store_combo(model_data, combo_widget):
    """inflates an individual combo box
    Args:
      model_data: data to be loaded into a list store (list)
      combo_widget: the widget to load data into.
    """
    empty = True
    if combo_widget.get_model():
        empty = False
    list_store = gtk.ListStore(str)
    for datum in model_data:
        list_store.append([datum])

    combo_widget.set_model(list_store)

    if empty:
        renderer = gtk.CellRendererText()
        combo_widget.pack_start(renderer, expand=True)
        combo_widget.add_attribute(renderer, "text", 0)
