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

class EditableList(object):
    """ controler for a liststore and treeview"""
    def __init__(self, view, model):
        """
        Args:
            view: gtk.treeview widget
            model: gtk.liststore

        Returns:
            EditableList controler object
        """
        self.view = view
        self.model = model
        self.view.set_model(self.model)

    def get_selected(self):
        """ Returns: the iterator of the selected row """
        return self.view.get_selection().get_selected()[1]

    def get_row(self):
        """retruns the model data for selected row"""
        return self.model[self.get_selected()]

    def move_down(self):
        """moves the selected row down"""
        iter = self.get_selected()
        next = self.model.iter_next(iter)
        if not next:
            return
        self.model.swap(iter, next)

    def move_up(self):
        """Moves selected row down"""
        iter = self.get_selected()
        selection_path = self.model.get_path(iter)
        try:
            prev = self.model.get_iter((selection_path[0] - 1))
        except ValueError:
            return
        self.model.swap(iter, prev)

    def remove(self):
        """deletes a row"""
        iter = self.get_selected()
        if iter:
            self.model.remove(iter)

    def add(self, data):
        """
        Adds Data to row
        Args:
            data: iterable containing the new row data
        """
        self.model.append(data)

    def set(self, *args):
        """See gtk.liststore.set"""
        self.model.set(*args)

    def set_value(self, iter, column, value):
        """See gtk.ListStore.set_value"""
        self.model.set_value(iter, column, value)

    def get_data(self):
        """Returns: list containing 1 tuple per row of the model data"""
        return [row for row in self.model]

    def clear(self):
        """clear the ListStore"""
        self.model.clear()

    def replace_model(self, new_model):
        """
        replace the model with new_model
        Args:
            new_model: gtk.ListStore
        """

        self.model = new_model
        self.view.set_model(self.model)