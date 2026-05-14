"""
Created on 12.04.2021
__updated__ = "2026-03-22"
@author: Wolfgang Kramer

    Modified code of:
    Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education. Journal of Open
    Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
    and
    https://readthedocs.org/projects/pandastable/downloads/pdf/latest/
"""
import webbrowser

from collections import OrderedDict
from tkinter import (
    PhotoImage, Menu, HORIZONTAL, VERTICAL, BOTH, TOP, BOTTOM, LEFT, BooleanVar,
    IntVar, X, RIGHT
    )
from tkinter.ttk import Frame, Checkbutton, Label, Entry
from pandastable import (
    Table, addButton, images, util, PlotViewer, handlers,
    ColumnHeader, RowHeader, IndexHeader, AutoScrollbar, ToolBar, statusBar
)
from pandastable.plotting import addFigure
from pandastable.headers import createSubMenu
from pandastable.dialogs import applyStyle
from banking.declarations import (
    ToolbarSwitch, POPUP_MENU_TEXT,
    EDIT_ROW, CURRENCY_SIGN, NUMERIC, NO_CURRENCY_SIGN, TechnicalIndicatorData,
    WM_DELETE_WINDOW,
)
from banking.declarations_mariadb import (
    DB_close,
    )
from banking.message_handler import MESSAGE_TITLE

BUTTON_NEW = 'NEW'
BUTTON_DELETE = 'DELETE'
BUTTON_RESTORE = 'RESTORE'
BUTTON_UPDATE = 'UPDATE'


class MyPlotViewer(PlotViewer):
    """
    Copy of pandastable, plotting.py
    Label Info added
    """
    WINDOW = []  # opened instant plotting Windows

    def __init__(self, table, parent=None, showoptions=True):

        self.button_state = ''
        self.parent = parent
        super().__init__(table, parent, showoptions)
        pass

    def close(self):

        for window in MyPlotViewer.WINDOW:
            window.destroy()
        MyPlotViewer.WINDOW = []
        self.button_state = WM_DELETE_WINDOW
        PlotViewer.close(self)

    def setupGUI(self):
        """Add GUI elements"""

        # import tkinter as tk
        # self.m = PanedWindow(self.main, orient=self.orient)
        self.m = Frame(self.main)
        self.m.pack(fill=BOTH, expand=1)
        # frame for figure
        self.plotfr = Frame(self.m)
        # add it to the panedwindow
        self.fig, self.canvas = addFigure(self.plotfr)
        self.ax = self.fig.add_subplot(111)

        # self.m.add(self.plotfr, weight=12)
        self.plotfr.pack(side=TOP, fill=BOTH, expand=1)

        # frame for controls
        self.ctrlfr = Frame(self.main)
        # self.m.add(self.ctrlfr, weight=4)
        self.ctrlfr.pack(side=BOTTOM, fill=BOTH)

        # button frame
        bf = Frame(self.ctrlfr, padding=2)
        bf.pack(side=TOP, fill=BOTH)

        side = LEFT
        # add button toolbar
        addButton(bf, 'Plot', self.replot, images.plot(),
                  'plot current data', side=side, compound="left", width=16)
        addButton(bf, 'Apply Options', self.updatePlot, images.refresh(),
                  'refresh plot with current options', side=side,
                  width=20)
        addButton(bf, 'Zoom Out', lambda: self.zoom(False), images.zoom_out(),
                  'zoom out', side=side)
        addButton(bf, 'Zoom In', self.zoom, images.zoom_in(),
                  'zoom in', side=side)
        addButton(bf, 'Clear', self.clear, images.plot_clear(),
                  'clear plot', side=side)
        addButton(bf, 'Save', self.savePlot, images.save(),
                  'save plot', side=side)

        # dicts to store global options, can be saved with projects
        self.globalvars = {}
        self.globalopts = OrderedDict({'dpi': 80, 'grid layout': False, '3D plot': False})
        from functools import partial
        for n in self.globalopts:
            val = self.globalopts[n]
            if type(val) is bool:
                v = self.globalvars[n] = BooleanVar()
                v.set(val)
                b = Checkbutton(bf, text=n, variable=v, command=partial(self.setGlobalOption, n))
            else:
                v = self.globalvars[n] = IntVar()
                v.set(val)
                Label(bf, text=n).pack(side=LEFT, fill=X, padx=2)
                b = Entry(bf, textvariable=v, width=5)
                v.trace("w", partial(self.setGlobalOption, n))
            b.pack(side=LEFT, padx=2)
        addButton(bf, 'Hide', self.toggle_options, images.prefs(),
                  'show/hide plot options', side=RIGHT)
        addButton(bf, 'Info', self.info_website, None,
                  'Info WebSite', side=RIGHT)
        addButton(bf, 'Add Close', self.add_close, None,
                  'Add Close', side=RIGHT)
        self.addWidgets()

        # def onpick(event):
        #     print(event)
        # self.fig.canvas.mpl_connect(k)'pick_event', onpick)
        # self.fig.canvas.mpl_connect('button_release_event', onpic
        dr = handlers.DragHandler(self)
        dr.connect()
        return

    def info_website(self):

        indicator = self.table.title.split(" ", 1)[0]
        url = ''.join(["https://www.google.com/search?q=", indicator])
        webbrowser.open(url)

    def add_close(self):

        TechnicalIndicatorData.TA_CLOSE.append(DB_close)

        for window in MyPlotViewer.WINDOW:
            window.quit()

        MyPlotViewer.WINDOW = []


class ToolBarBanking(Frame):
    """
    Modification of class ToolBar
    Uses the parent instance to provide the functions"""

    def __init__(self, parent, parentapp, root, mode=NUMERIC):

        Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        self.root = root
        if mode == NUMERIC:
            img = self.currency_sign()
            addButton(self, 'CurrenySign', self.toolbar_switch, img, 'ToolBar')
        if mode == NUMERIC and ToolbarSwitch.toolbar_switch:
            img = images.excel()
            addButton(self, 'Export excel', self.root.excel_writer,
                      img, 'export to excel file')
            """
            img = images.save_proj()
            addButton(self, 'Save', self.parentapp.save, img, 'save')
            """
            img = images.copy()
            addButton(self, 'Copy', self.parentapp.copyTable,
                      img, 'copy table to clipboard')
            """
            img = images.paste()
            addButton(self, 'Paste', self.parentapp.paste, img, 'paste table')
            """
            img = images.plot()
            addButton(self, 'Plot', self.parentapp.plotSelected,
                      img, 'plot selected')
            """
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
            """
            img = images.filtering()
            addButton(self, 'Query', self.parentapp.queryBar,
                      img, 'filter table')
            """
            img = images.calculate()
            addButton(self, 'Evaluate function',
                      self.parentapp.evalBar, img, 'calculate')

            img = images.table_delete()
            addButton(self, 'Clear', self.parentapp.clearTable,
                      img, 'clear table')
            """
        return

    def toolbar_switch(self):

        if ToolbarSwitch.toolbar_switch:
            ToolbarSwitch.toolbar_switch = False
        else:
            ToolbarSwitch.toolbar_switch = True
        self.master.quit()  # quits Frame BuiltPandasBox: next shows reformatted  decimal columns
        # self.parentapp.root.quit() # quits pandas_table of BuiltPandaasBox

    def currency_sign(self):
        """
        Button activate/deactivate Toolbar
        Switch off/on currency_sign in columns of type decimal
        """
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

    def popupMenu(self, event):
        """Add left and right click behaviour for column header"""

        df = self.table.model.df
        if len(df.columns) == 0:
            return
        ismulti = util.check_multiindex(df.columns)
        """
        colname = str(df.columns[self.table.currentcol])
        currcol = self.table.currentcol
        """
        multicols = self.table.multiplecollist
        colnames = list(df.columns[multicols])[:4]
        colnames = [str(i)[:20] for i in colnames]
        if len(colnames) > 2:
            colnames = ','.join(colnames[:2]) + \
                '+%s others' % str(len(colnames)-2)
        else:
            colnames = ','.join(colnames)
        popupmenu = Menu(self, tearoff=0)

        def popupFocusOut(event):
            popupmenu.unpost()

        columncommands = {"Rename": self.renameColumn,
                          # "Add": self.table.addColumn,
                          # "Delete": self.table.deleteColumn,
                          "Copy": self.table.copyColumn,
                          "Move to Start": self.table.moveColumns,
                          "Move to End": lambda: self.table.moveColumns(pos='end')
                          }
        formatcommands = {'Set Color': self.table.setColumnColors,
                          'Color by Value': self.table.setColorbyValue,
                          # 'Alignment': self.table.setAlignment,
                          # 'Wrap Header': self.table.setWrap
                          }
        popupmenu.add_command(label="Sort by " + colnames + ' \u2193',
                              command=lambda: self.table.sortTable(ascending=[1 for i in multicols]))
        popupmenu.add_command(label="Sort by " + colnames + ' \u2191',
                              command=lambda: self.table.sortTable(ascending=[0 for i in multicols]))
        """
        popupmenu.add_command(label="Set %s as Index" %
                              colnames, command=self.table.setindex)
        popupmenu.add_command(label="Delete Column(s)",
                              command=self.table.deleteColumn)
        """
        if ismulti is True:
            popupmenu.add_command(label="Flatten Index",
                                  command=self.table.flattenIndex)
        """
        popupmenu.add_command(label="Fill With Data",
                              command=self.table.fillColumn)
        popupmenu.add_command(label="Create Categorical",
                              command=self.table.createCategorical)
        popupmenu.add_command(label="Apply Function",
                              command=self.table.applyColumnFunction)
        popupmenu.add_command(label="Resample/Transform",
                              command=self.table.applyTransformFunction)
        popupmenu.add_command(label="Value Counts",
                              command=self.table.valueCounts)
        popupmenu.add_command(label="String Operation",
                              command=self.table.applyStringMethod)
        popupmenu.add_command(label="Date/Time Conversion",
                              command=self.table.convertDates)
        """
        popupmenu.add_command(label="Set Data Type",
                              command=self.table.setColumnType)

        createSubMenu(popupmenu, 'Column', columncommands)
        createSubMenu(popupmenu, 'Format', formatcommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)
        return popupmenu


class ColumnHeaderCallForms(ColumnHeader):
    """Overrides PopUpMenu of pandastable Class ColumnHeader """

    def popupMenu(self, event):
        """Add left and right click behaviour for column header"""

        df = self.table.model.df
        if len(df.columns) == 0:
            return
        ismulti = util.check_multiindex(df.columns)
        """
        colname = str(df.columns[self.table.currentcol])
        currcol = self.table.currentcol
        """
        multicols = self.table.multiplecollist
        colnames = list(df.columns[multicols])[:4]
        colnames = [str(i)[:20] for i in colnames]
        if len(colnames) > 2:
            colnames = ','.join(colnames[:2]) + \
                '+%s others' % str(len(colnames)-2)
        else:
            colnames = ','.join(colnames)
        popupmenu = Menu(self, tearoff=0)

        def popupFocusOut(event):
            popupmenu.unpost()

        columncommands = {"Rename": self.renameColumn,
                          # "Add": self.table.addColumn,
                          # "Delete": self.table.deleteColumn,
                          "Copy": self.table.copyColumn,
                          "Move to Start": self.table.moveColumns,
                          "Move to End": lambda: self.table.moveColumns(pos='end')
                          }
        formatcommands = {'Set Color': self.table.setColumnColors,
                          'Color by Value': self.table.setColorbyValue,
                          # 'Alignment': self.table.setAlignment,
                          # 'Wrap Header' : self.table.setWrap
                          }
        popupmenu.add_command(label="Sort by " + colnames + ' \u2193',
                              command=lambda: self.table.sortTable(ascending=[1 for i in multicols]))
        popupmenu.add_command(label="Sort by " + colnames + ' \u2191',
                              command=lambda: self.table.sortTable(ascending=[0 for i in multicols]))
        """
        popupmenu.add_command(label="Delete Column(s)", command=self.table.deleteColumn)
        """
        if ismulti is True:
            popupmenu.add_command(label="Flatten Index",
                                  command=self.table.flattenIndex)
        """
        popupmenu.add_command(label="Fill With Data", command=self.table.fillColumn)
        popupmenu.add_command(label="Create Categorical", command=self.table.createCategorical)
        popupmenu.add_command(label="Apply Function", command=self.table.applyColumnFunction)
        popupmenu.add_command(label="Resample/Transform", command=self.table.applyTransformFunction)
        popupmenu.add_command(label="Value Counts", command=self.table.valueCounts)
        popupmenu.add_command(label="String Operation", command=self.table.applyStringMethod)
        popupmenu.add_command(label="Date/Time Conversion", command=self.table.convertDates)
        """
        popupmenu.add_command(label="Set Data Type",
                              command=self.table.setColumnType)

        createSubMenu(popupmenu, 'Column', columncommands)
        createSubMenu(popupmenu, 'Format', formatcommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)
        return popupmenu


class RowHeaderCallForms(RowHeader):
    """Overrides PopUpMenu of pandastable Class RowHeader """

    def __init__(self, parent=None, table=None, width=50, bg='gray75', root=None):
        self.root = root
        super().__init__(parent=parent, table=table, width=width, bgcolor=bg)

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """
        modfication of method popupMenu
        """
        defaultactions = {}
        if hasattr(self.root, 'show_row'):
            defaultactions.update(
                {POPUP_MENU_TEXT['Show selected Row']: lambda: self.root.show_row()})
        if hasattr(self.root, 'show_credit_data'):
            defaultactions.update(
                {POPUP_MENU_TEXT['Show credit data']: lambda: self.root.show_credit_data()})
        if hasattr(self.root, 'show_debit_data'):
            defaultactions.update(
                {POPUP_MENU_TEXT['Show debit data']: lambda: self.root.show_debit_data()})
        if hasattr(self.root, 'new_row'):
            defaultactions.update(
                {POPUP_MENU_TEXT['New Row']: lambda: self.root.new_row()})
        if hasattr(self.root, 'update_row'):
            defaultactions.update(
                {POPUP_MENU_TEXT['Update selected Row']: lambda: self.root.update_row()})
        if hasattr(self.root, 'del_row'):
            defaultactions.update(
                {POPUP_MENU_TEXT['Delete selected Row']: lambda: self.root.del_row()})
        if hasattr(self.root, 'excel_writer'):
            defaultactions.update(
                {POPUP_MENU_TEXT['Export to Excel']: lambda: self.root.excel_writer()})
        main = []
        for key in defaultactions.keys():
            main.append(key)

        popupmenu = Menu(self, tearoff=0)

        def popupFocusOut(event):
            popupmenu.unpost()
        for action in main:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)

        return popupmenu


class Table(Table):
    """
    Parameter:
        ...
        Special Banking ToolBar
        currency_code_button: adds currency_code button to ToolBarBanking
        currency_code_format: adds currency_code pandas table columns of type Decimal
    """

    def __init__(self, title=MESSAGE_TITLE, root=None,
                 parent=None, model=None, dataframe=None,
                 width=None, height=None, rows=20, cols=5,
                 mode=NUMERIC, instant_plotting=False):
        self.title = title
        self.root = root
        self.dataframe = dataframe
        self.toolbar_switch = ToolbarSwitch.toolbar_switch
        self.instant_plotting = instant_plotting
        if mode == EDIT_ROW:
            showtoolbar = False
            enable_menus = True
            editable = False
        elif mode == CURRENCY_SIGN:
            showtoolbar = False
            enable_menus = False
            editable = False
        elif mode == NUMERIC:
            showtoolbar = False
            enable_menus = True
            if self.toolbar_switch:
                editable = True
            else:
                editable = False
        elif mode == NO_CURRENCY_SIGN:
            showtoolbar = False
            enable_menus = True
            editable = False

        super().__init__(parent=parent, model=model, dataframe=dataframe,
                         width=width, height=height, rows=rows, cols=cols,
                         showtoolbar=showtoolbar,
                         editable=editable,
                         enable_menus=enable_menus)
        if mode == NUMERIC:
            self.toolbar = ToolBarBanking(
                parent, self, root, mode=mode)
            self.toolbar.grid(row=0, column=3, rowspan=2, sticky='news')
        if hasattr(self, 'pf'):
            self.pf.updateData()

    def show(self, callback=None):
        """Adds column header and scrollbars and combines them with
           the current table adding all to the master frame provided in constructor.
           Table is then redrawn."""

        # Add the table and header to the frame
        self.rowheader = RowHeader(self.parentframe, self)
        self.colheader = ColumnHeaderCallForms(
            self.parentframe, self, bgcolor='gray25')
        self.rowindexheader = IndexHeader(self.parentframe, self, bg='gray75')
        self.Yscrollbar = AutoScrollbar(
            self.parentframe, orient=VERTICAL, command=self.set_yviews)
        self.Yscrollbar.grid(row=1, column=2, rowspan=1,
                             sticky='news', pady=0, ipady=0)
        self.Xscrollbar = AutoScrollbar(
            self.parentframe, orient=HORIZONTAL, command=self.set_xviews)
        self.Xscrollbar.grid(row=2, column=1, columnspan=1, sticky='news')
        self['xscrollcommand'] = self.Xscrollbar.set
        self['yscrollcommand'] = self.Yscrollbar.set
        self.colheader['xscrollcommand'] = self.Xscrollbar.set
        self.rowheader['yscrollcommand'] = self.Yscrollbar.set
        self.parentframe.rowconfigure(1, weight=1)
        self.parentframe.columnconfigure(1, weight=1)

        self.rowindexheader.grid(row=0, column=0, rowspan=1, sticky='news')
        self.colheader.grid(row=0, column=1, rowspan=1, sticky='news')
        self.rowheader.grid(row=1, column=0, rowspan=1, sticky='news')
        self.grid(row=1, column=1, rowspan=1, sticky='news', pady=0, ipady=0)

        self.adjustColumnWidths()
        # bind redraw to resize, may trigger redraws when widgets added
        # self.redrawVisible)
        self.parentframe.bind("<Configure>", self.resized)
        self.colheader.xview("moveto", 0)
        self.xview("moveto", 0)
        if self.showtoolbar is True:
            self.toolbar = ToolBar(self.parentframe, self)
            self.toolbar.grid(row=0, column=3, rowspan=2, sticky='news')
        if self.showstatusbar is True:
            self.statusbar = statusBar(self.parentframe, self)
            self.statusbar.grid(row=3, column=0, columnspan=2, sticky='ew')
        # self.redraw(callback=callback)
        self.currwidth = self.parentframe.winfo_width()
        self.currheight = self.parentframe.winfo_height()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def plotSelected(self):

        if self.instant_plotting:
            self.pf = MyPlotViewer(table=self)
            self.pf.setOption('title', self.title)  # Plot title
            self.pf.setOption('grid', 1)  # grid lines
            self.pf.replot(data=self.dataframe)
        else:
            super().plotSelected()
            self.pf.setOption('title', self.title)  # Plot title
            self.pf.setOption('grid', 1)  # grid lines
            self.pf.replot()
        return

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        if self.root:
            defaultactions = {
                "Copy": lambda: self.copy(rows, cols),
                # "Undo" : lambda: self.undo(),
                # "Paste" : lambda: self.paste(),
                # "Fill Down" : lambda: self.fillDown(rows, cols),
                # "Fill Right" : lambda: self.fillAcross(cols, rows),
                # "Add Row(s)" : lambda: self.addRows(),
                # "Delete Row(s)" : lambda: self.deleteRow(),
                # "Add Column(s)" : lambda: self.addColumn(),
                # "Delete Column(s)" : lambda: self.deleteColumn(),
                # "Clear Data" : lambda: self.deleteCells(rows, cols),
                "Select All": self.selectAll,
                # "Auto Fit Columns": self.autoResizeColumns,
                "Table Info": self.showInfo,
                "Set Color": self.setRowColors,
                # "Show as Text" : self.showasText,
                "Filter Rows": self.queryBar,
                # "New": self.new,
                # "Open": self.load,
                # "Save": self.save,
                # "Save As": self.saveAs,
                # "Import Text/CSV": lambda: self.importCSV(dialog=True),
                # "Import hdf5": lambda: self.importHDF(dialog=True),
                # "Export": self.doExport,
                "Export": self.root.excel_writer,
                # "Plot Selected" : self.plotSelected,
                # "Hide plot" : self.hidePlot,
                # "Show plot" : self.showPlot,
                "Preferences": self.showPreferences,
                # "Table to Text" : self.showasText,
                # "Clean Data" : self.cleanData,
                "Clear Formatting": self.clearFormatting,
                # "#Undo Last Change": self.undo,
                "Copy Table": self.copyTable,
                # "Find/Replace": self.findText
            }
        else:
            defaultactions = {
                "Copy": lambda: self.copy(rows, cols),
                "Select All": self.selectAll,
                "Table Info": self.showInfo,
                "Set Color": self.setRowColors,
                "Filter Rows": self.queryBar,
                "Preferences": self.showPreferences,
                "Clear Formatting": self.clearFormatting,
                "Copy Table": self.copyTable,
            }

        main = ["Copy", "Set Color"]
        general = ["Select All", "Filter Rows",
                   "Table Info", "Preferences"]

        filecommands = ['Export']
        tablecommands = ['Clear Formatting']

        def createSubMenu(parent, label, commands):
            menu = Menu(parent, tearoff=0)
            popupmenu.add_cascade(label=label, menu=menu)
            for action in commands:
                menu.add_command(label=action, command=defaultactions[action])
            applyStyle(menu)
            return menu

        def add_commands(fieldtype):
            """Add commands to popup menu for column type and specific cell"""
            functions = self.columnactions[fieldtype]
            for f in list(functions.keys()):
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command=lambda: func(row, col))
            return

        popupmenu = Menu(self, tearoff=0)

        def popupFocusOut(event):
            popupmenu.unpost()

        if outside is None:
            # if outside table, just show general items
            row = self.get_row_clicked(event)
            col = self.get_col_clicked(event)
            coltype = self.model.getColumnType(col)

            def add_defaultcommands():
                """now add general actions for all cells"""
                for action in main:
                    if action == 'Fill Down' and (rows is None or len(rows) <= 1):
                        continue
                    if action == 'Fill Right' and (cols is None or len(cols) <= 1):
                        continue
                    if action == 'Undo' and self.prevdf is None:
                        continue
                    else:
                        popupmenu.add_command(
                            label=action, command=defaultactions[action])
                return

            if coltype in self.columnactions:
                add_commands(coltype)
            add_defaultcommands()

        for action in general:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.add_separator()
        if self.root:
            createSubMenu(popupmenu, 'File', filecommands)
        """
        createSubMenu(popupmenu, 'Edit', editcommands)
        createSubMenu(popupmenu, 'Plot', plotcommands)
        """
        createSubMenu(popupmenu, 'Table', tablecommands)
        popupmenu.bind("<FocusOut>", popupFocusOut)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)
        return popupmenu


class TableRowEdit(Table):
    """
    Parameter:
        ...
        Special Banking Row Edit Functions
    """

    def __init__(self, title=MESSAGE_TITLE, root=None,
                 parent=None, model=None, dataframe=None,
                 width=None, height=None, rows=20, cols=5):
        self.title = title
        TableRowEdit.root = root
        self.toolbar_switch = ToolbarSwitch.toolbar_switch
        super().__init__(parent=parent, model=model, dataframe=dataframe,
                         width=width, height=height, rows=rows, cols=cols,
                         mode=EDIT_ROW)

        if hasattr(self, 'pf'):
            self.pf.updateData()

    def show(self, callback=None):
        """Adds column header and scrollbars and combines them with
           the current table adding all to the master frame provided in constructor.
           Table is then redrawn."""

        # Add the table and header to the frame
        self.rowheader = RowHeaderCallForms(
            self.parentframe, self, root=TableRowEdit.root)
        self.colheader = ColumnHeaderCallForms(
            self.parentframe, self, bgcolor='gray25')
        self.rowindexheader = IndexHeader(self.parentframe, self, bg='gray75')
        self.Yscrollbar = AutoScrollbar(
            self.parentframe, orient=VERTICAL, command=self.set_yviews)
        self.Yscrollbar.grid(row=1, column=2, rowspan=1,
                             sticky='news', pady=0, ipady=0)
        self.Xscrollbar = AutoScrollbar(
            self.parentframe, orient=HORIZONTAL, command=self.set_xviews)
        self.Xscrollbar.grid(row=2, column=1, columnspan=1, sticky='news')
        self['xscrollcommand'] = self.Xscrollbar.set
        self['yscrollcommand'] = self.Yscrollbar.set
        self.colheader['xscrollcommand'] = self.Xscrollbar.set
        self.rowheader['yscrollcommand'] = self.Yscrollbar.set
        self.parentframe.rowconfigure(1, weight=1)
        self.parentframe.columnconfigure(1, weight=1)

        self.rowindexheader.grid(row=0, column=0, rowspan=1, sticky='news')
        self.colheader.grid(row=0, column=1, rowspan=1, sticky='news')
        self.rowheader.grid(row=1, column=0, rowspan=1, sticky='news')
        self.grid(row=1, column=1, rowspan=1, sticky='news', pady=0, ipady=0)

        # self.adjustColumnWidths()
        # bind redraw to resize, may trigger redraws when widgets added
        # self.redrawVisible)
        self.parentframe.bind("<Configure>", self.resized)
        self.colheader.xview("moveto", 0)
        self.xview("moveto", 0)
        if self.showtoolbar is True:
            self.toolbar = ToolBar(self.parentframe, self)
            self.toolbar.grid(row=0, column=3, rowspan=2, sticky='news')
        if self.showstatusbar is True:
            self.statusbar = statusBar(self.parentframe, self)
            self.statusbar.grid(row=3, column=0, columnspan=2, sticky='ew')
        # self.redraw(callback=callback)
        self.currwidth = self.parentframe.winfo_width()
        self.currheight = self.parentframe.winfo_height()
        if hasattr(self, 'pf'):
            self.pf.updateData()
        return

    def plotSelected(self):

        super().plotSelected()
        self.pf.setOption(
            'title', self.title)  # Plot title
        self.pf.replot()
        return
