"""
Created on 12.04.2021
__updated__ = "2024-07-10"
@author: Wolfg

    Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education. Journal of Open
    Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
    and
    https://readthedocs.org/projects/pandastable/downloads/pdf/latest/
"""
from tkinter import PhotoImage
from tkinter.ttk import Frame
from pandastable import Table, addButton, images, util
from banking.declarations import ToolbarSwitch

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


class ToolBarBanking(Frame):
    """
    Modification of class ToolBar
    Uses the parent instance to provide the functions"""

    def __init__(self, parent=None, parentapp=None):

        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        img = self.currency_sign()
        addButton(self, 'CurrenySign', self.toolbar_switch, img, 'ToolBar')
        if not ToolbarSwitch.toolbar_switch:
            img = images.save_proj()
            addButton(self, 'Save', self.parentapp.save, img, 'save')
            img = images.copy()
            addButton(self, 'Copy', self.parentapp.copyTable,
                      img, 'copy table to clipboard')
            img = images.paste()
            addButton(self, 'Paste', self.parentapp.paste, img, 'paste table')
            img = images.plot()
            addButton(self, 'Plot', self.parentapp.plotSelected,
                      img, 'plot selected')
            img = images.transpose()
            addButton(self, 'Transpose',
                      self.parentapp.transpose, img, 'transpose')
            img = images.aggregate()
            addButton(self, 'Aggregate',
                      self.parentapp.aggregate, img, 'aggregate')
            img = images.pivot()
            addButton(self, 'Pivot', self.parentapp.pivot, img, 'pivot')
            img = images.melt()
            addButton(self, 'Melt', self.parentapp.melt, img, 'melt')
            img = images.merge()
            addButton(self, 'Merge', self.parentapp.doCombine,
                      img, 'merge, concat or join')
            img = images.table_multiple()
            addButton(self, 'Table from selection', self.parentapp.tableFromSelection,
                      img, 'sub-table from selection')
            img = images.filtering()
            addButton(self, 'Query', self.parentapp.queryBar,
                      img, 'filter table')
            img = images.calculate()
            addButton(self, 'Evaluate function',
                      self.parentapp.evalBar, img, 'calculate')

            img = images.table_delete()
            addButton(self, 'Clear', self.parentapp.clearTable,
                      img, 'clear table')
        return

    def toolbar_switch(self):

        if ToolbarSwitch.toolbar_switch:
            ToolbarSwitch.toolbar_switch = False
        else:
            ToolbarSwitch.toolbar_switch = True
        self.master.quit()  # quits BuiltPandasBox: next call shows reformatted  decimal columns

    def currency_sign(self):
        '''
        Button activate/deactivate Toolbar
        Switch off/on currency_sign in columns of type decimal
        '''
        img = PhotoImage(format='gif', data=(
            'R0lGODlhIAAXAPcAAAAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwArZgArmQArzAAr/wBVAABVMwBVZgBV'
            + 'mQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCqmQCqzACq/wDVAADVMwDVZgDVmQDVzADV'
            + '/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMAMzMAZjMAmTMAzDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNV'
            + 'MzNVZjNVmTNVzDNV/zOAADOAMzOAZjOAmTOAzDOA/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPV'
            + 'mTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YAAGYAM2YAZmYAmWYAzGYA/2YrAGYrM2YrZmYrmWYrzGYr'
            + '/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaAM2aAZmaAmWaAzGaA/2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbV'
            + 'M2bVZmbVmWbVzGbV/2b/AGb/M2b/Zmb/mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkr'
            + 'mZkrzJkr/5lVAJlVM5lVZplVmZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq'
            + '/5nVAJnVM5nVZpnVmZnVzJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswAmcwAzMwA/8wrAMwr'
            + 'M8wrZswrmcwrzMwr/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyAM8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyq'
            + 'mcyqzMyq/8zVAMzVM8zVZszVmczVzMzV/8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A'
            + '//8rAP8rM/8rZv8rmf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+q'
            + 'M/+qZv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP///wAAAAAAAAAAAAAA'
            + 'ACH5BAEAAPwALAAAAAAgABcAAAhLAPcJHEiwoMGDCBMqXMiwocOHECNKnEixokWJYgAAmHSR4KRMHQtO'
            + '0gjAQMiBN056JLlC5b4b9VwKzCRGpsCMG23q3Mmzp8+fBgMCADs=')
        )
        return img


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
        self.toolbar_switch = ToolbarSwitch.toolbar_switch
        super().__init__(parent=parent, model=model, dataframe=dataframe,
                         width=width, height=height,
                         rows=rows, cols=cols, showtoolbar=showtoolbar, showstatusbar=showstatusbar,
                         editable=editable, enable_menus=enable_menus)
        if showtoolbar:
            if edit_rows:
                self.toolbar = ToolBarRows(
                    parent, root)  # Special Toolbar
                self.toolbar.grid(row=0, column=3, rowspan=2, sticky='news')
                self.showtoolbar = False  # deactivate standard toolbar of Table
            else:
                self.toolbar = ToolBarBanking(parent, self)
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
