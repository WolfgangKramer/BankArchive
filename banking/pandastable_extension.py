"""
Created on 12.04.2021
__updated__ = "2023-10-10"
@author: Wolfg

    Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education. Journal of Open
    Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
    and
    https://readthedocs.org/projects/pandastable/downloads/pdf/latest/
"""

from tkinter.ttk import Frame
from pandastable import Table, addButton, images

from banking.declarations import MESSAGE_TITLE

BUTTON_NEW = 'NEW'
BUTTON_DELETE = 'DELETE'
BUTTON_RESTORE = 'RESTORE'
BUTTON_UPDATE = 'UPDATE'


class ToolBarRows(Frame):
    """Uses the parent instance to provide the functions"""

    def __init__(self, parent, root):

        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.root = root
        img = images.add_row()
        addButton(self, 'New', root.new_row, img, 'Insert New Table Row')
        img = images.refresh()
        addButton(self, 'Change', root.change_row, img, 'Change Table Row')
        img = images.del_row()
        addButton(self, 'Delete', root.del_row, img, 'Delete Table Row')


class Table(Table):
    """
    Parameter:
        ...
        Special ToolBarRows if edit_rows True
    """

    def __init__(self, parent=None, model=None, dataframe=None,
                 width=None, height=None,
                 rows=20, cols=5, showtoolbar=False, showstatusbar=False,
                 editable=True, enable_menus=True,
                 edit_rows=False, title=MESSAGE_TITLE, root=None):
        self.title = title
        super().__init__(parent=parent, model=model, dataframe=dataframe,
                         width=width, height=height,
                         rows=rows, cols=cols, showtoolbar=showtoolbar, showstatusbar=showstatusbar,
                         editable=editable, enable_menus=enable_menus)
        if edit_rows:
            self.toolbar = ToolBarRows(
                self.parentframe, root)  # Special Toolbar
            self.toolbar.grid(row=0, column=3, rowspan=2, sticky='news')
            self.showtoolbar = False  # deactivate standard toolbar of Table
        if hasattr(self, 'pf'):
            self.pf.updateData()

    def plotSelected(self):

        super().plotSelected()
        self.pf.setOption(
            'title', self.title)  # Plot title
        self.pf.replot()
        return
