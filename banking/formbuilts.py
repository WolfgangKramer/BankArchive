"""
Created on 28.01.2020
__updated__ = "2026-05-17"
@author: Wolfgang Kramer
"""


import re

import banking.declarations_mariadb as declm

from inspect import stack
from pathlib import Path
from collections import namedtuple
from datetime import date, timedelta
from tkinter import (
    Tk, TclError, ttk, Toplevel, StringVar, IntVar, INSERT, Text,
    W, E, filedialog, BOTH, BOTTOM, TOP, HORIZONTAL, Canvas,
    END, DISABLED)
from tkinter.ttk import (
    Entry, Frame, Label, Radiobutton, Checkbutton, Separator, Scrollbar, Progressbar)
from tkinter.font import Font
from keyboard import add_hotkey
from pandas import to_numeric, ExcelWriter, DataFrame
from pandastable import config
from tkcalendar import DateEntry

from banking.declarations_mariadb import (
    HOLDING, HOLDING_VIEW, PRICES, PRICES_ISIN_VIEW, STATEMENT, TRANSACTION, TRANSACTION_VIEW,
    TABLE_FIELDS, TABLE_FIELDS_PROPERTIES, DATABASE_FIELDS_PROPERTIES,
    TINYINT, INTEGER, DATABASE_TYP_DECIMAL,
)
from banking.declarations import (

    ToolbarSwitch,
    EURO, EDIT_ROW,
    FN_COLUMNS_EURO, FN_COLUMNS_PERCENT, FN_FROM_DATE, FN_TO_DATE,
    HEIGHT_TEXT,
    NO_CURRENCY_SIGN, NUMERIC, NOT_ASSIGNED,
    # form declaratives
    ENTRY,
    COMBO,
    CHECK,
    BUTTON_NEXT,
    BUTTON_OK,
    BUTTON_DELETE_ALL,
    BUTTON_RESTORE,
    BUTTON_SAVE,
    BUTTON_SELECT_ALL,
    COLOR_NEGATIVE,
    FORMAT_FIXED,
    FORMAT_VARIABLE,
    TYP_ALPHANUMERIC,
    TYP_DECIMAL,
    TYP_DATE,
    )
from banking.pandastable_extension import Table, TableRowEdit, MyPlotViewer
from banking.utils import (
    application_store,
    Amount, dec2, list_positioning
    )
from banking.message_handler import (
    MESSAGE_TITLE, MESSAGE_TEXT,
    is_main_thread, get_message,
    Informations,
    MessageBoxInfo, MessageBoxTermination
    )
from banking.repository import Repository
from banking.connect_data import connectionresult
from banking.trading_calendar import xetra_cls


# package pandastable: standard values  (see class table self.font and self.fontsize
ROOT_WINDOW_POSITION = '+100+100'
BUILTBOX_WINDOW_POSITION = '+200+200'
BUILTPANDASBOX_WINDOW_POSITION = '+1+1'
BUILTEXT_WINDOW_POSITION = '+400+0'
WIDTH_WIDGET = 70
WIDTH_CANVAS = 700
HEIGHT_CANVAS = 800
PANDAS_NAME_SHOW = 'SHOW'
PANDAS_NAME_ROW = 'ROW'

WM_DELETE_WINDOW = 'WM_DELETE_WINDOW'
LIGHTBLUE = 'LIGHTBLUE'
UNDEFINED = 'UNDEFINED'
FONTSIZE = 8
MAX_FIELD_LENGTH = 65

re_amount = re.compile(r"\d+\.\d+")
re_amount_int = re.compile(r"\d+")


def destroy_widget(widget):
    """
    exit and destroys windows or
    destroys widget  and rest of root window will be left
    don't stop the tcl/tk interpreter
    """
    try:
        widget.destroy()
    except TclError:
        pass


def quit_widget(widget):
    """
    do not destroy widgets but it exits the tcl/tk interpreter i.e it stops the mainloop()
    """
    try:
        widget.quit()
    except TclError:
        pass


def find_list_index(list_, substring, mode='START'):
    """
    Returns index of 1st item in list containing substring
    mode='START at the beginning
    mode='END'  at the end
    else at anywhere in item
    """
    idx = 0
    if isinstance(substring, str):
        if mode == 'START':
            substring = '^' + substring
        elif mode == 'END':
            substring = substring + '$'
        for item in list_:
            if isinstance(item, str):
                if re.search(substring, item):
                    idx = list_.index(item)
    return idx




def extend_message_len(title, message):
    """
    returns possibly extended message
    """
    try:
        title_len = max(len(x) for x in list(title.splitlines()))
        message_len = max(len(x) for x in list(message.splitlines()))
        if title_len > message_len:
            return message + '\n' + ' ' * title_len
        else:
            return message
    except Exception:
        return message


class FileDialogue():

    def __init__(self, title=MESSAGE_TITLE, initialdir="/", create_file=False,
                 filetypes=None):

        window = Tk()
        window.withdraw()
        window.title(title)
        if filetypes is None:
            if create_file:
                filetypes = (("Microsoft Office Excel files", "*.xlsx"),)
            else:
                filetypes = (("CSV files", "*.csv"), ("all files", "*.*"))
        else:
            if filetypes == 'zip':
                filetypes = (("Zip files", "*.zip"),)
            elif filetypes == 'csv':
                filetypes = (("CSV files", "*.csv"),)
            else:
                filetypes = (("all files", "*.*"),)
        if create_file:
            directory = application_store.get(declm.DB_directory)
            if directory:
                initialdir = directory
            self.filename = filedialog.asksaveasfilename(
                initialdir=initialdir, title=title, filetypes=filetypes)
            filepath = Path(self.filename)
            if filepath.suffix != '.xlsx':
                self.filename.replace(filepath.suffix, '')
        else:
            self.filename = filedialog.askopenfilename(
                initialdir=initialdir, title=title, filetypes=filetypes)


class ProgressBar(Progressbar):

    def __init__(self, master):

        super().__init__(master=master, orient=HORIZONTAL, length=600, mode='indeterminate')

    def start(self, interval=None):

        self.pack()
        Progressbar.start(self, interval=interval)
        self.update_progressbar()

    def update_progressbar(self):

        self.update()

    def stop(self):

        Progressbar.stop(self)
        self.pack_forget()


class FieldDefinition(object):

    """
    Defines Attributes of EntryFields/ComboBoxFields

    >definiton<           String      Defintion (Entry, Combobox, Checkbutton)
    >name<                String      Description of EntryField
    >lformat<             String      Fixed ('F') or variable ('V')
                                      EntryField Length (max. Length see >Length<)
    >length<              Integer     Max. Length of EntryField
    >typ>                 String      Type ('X'), ('D') Decimal, ('DAT') Date
    >min_length<          Integer     Min. Length of EntryField
    >mandatory<           Boolean     True: Input is Mandatory
    >protected<           Boolean     True: No Input allowed
    >selected<            Boolean     True: User selects an element.
                                         Method self.comboboxselected_action excuted(class BuiltEnterBox)
    >readonly<            Boolean     True: Only selection allowed
    >default_value<                   Default Value (optional)
    >combo_values<        List        List of ComboBox Values;
                                      generates ComboBoxEntryField if not empty
    >combo_positioning<   Boolean     True: positions in >combo_values< during input
    >combo_insert_value<  Boolean     True: allows input of value outside of >combo_values<,
    >validate<            String      None or ALL (validate Option)
    >textvariable<                    None or StringVar()
    >focus_in<            Boolean     True: Action if Field got Focus
    >focus_out<           Boolean     True: Action if Field lost Focus
    >separator<           Boolean     True: insert separator Line after Widget
    """

    def __init__(self, definition=ENTRY,
                 name=UNDEFINED, lformat=FORMAT_VARIABLE, length=0, typ=TYP_ALPHANUMERIC,
                 min_length=0, mandatory=True, protected=False, readonly=False,
                 default_value='', combo_values=[],
                 combo_positioning=True, combo_insert_value=False,
                 focus_out=False, focus_in=False,
                 upper=False, selected=False, checkbutton_text='', separator=False):

        self.definition = definition
        self.name = name
        self.lformat = lformat
        self.length = length
        self.typ = typ
        self.min_length = min_length
        self.mandatory = mandatory
        self.protected = protected
        self.readonly = readonly
        self.default_value = default_value
        self.selected = selected
        self.combo_values = []
        for item in combo_values:
            self.combo_values.append(str(item))
        self.combo_positioning = combo_positioning
        self.combo_insert_value = combo_insert_value
        self.focus_out = focus_out
        self.focus_in = focus_in
        self.upper = upper
        self.widget = None
        self.textvar = None
        self.separator = separator
        self.checkbutton_text = checkbutton_text

    @property
    def definition(self):
        return self._definition

    @definition.setter
    def definition(self, value):
        self._definition = value
        if self._definition not in [ENTRY, COMBO, CHECK]:
            MessageBoxTermination(
                info='Field Definition Definiton not ENTRY (EntryField), COMBO (ComboBoxField), CHECK(CheckButtonField)')

    @property
    def lformat(self):
        return self._lformat

    @lformat.setter
    def lformat(self, value):
        self._lformat = value
        if self._lformat not in [FORMAT_FIXED, FORMAT_VARIABLE]:
            MessageBoxTermination(
                info='Field Definition Format not F (fixed length) or V (variable Length)')

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        try:
            self._length = value
            int(self._length)
        except (ValueError, TypeError):
            MessageBoxTermination(info='Field Definition Length no Integer')

    @property
    def typ(self):
        return self._typ

    @typ.setter
    def typ(self, value):
        self._typ = value
        if self._typ not in [TYP_ALPHANUMERIC, TYP_DECIMAL, TYP_DATE]:
            MessageBoxTermination(
                info='Field Definition Typ not X or D (decimal), DAT (date)')

    @property
    def min_length(self):
        return self._min_length

    @min_length.setter
    def min_length(self, value):
        try:
            self._min_length = value
            int(self._min_length)
            if value > int(self.length):
                MessageBoxTermination(
                    info='Field Definition min. Length greater Length')
        except (ValueError, TypeError):
            MessageBoxTermination(
                info='Field Definition min. Length no Integer')

    @property
    def mandatory(self):
        return self._mandatory

    @mandatory.setter
    def mandatory(self, value):
        self._mandatory = value
        if self._mandatory not in [True, False]:
            MessageBoxTermination(
                info='Field Definition Mandatory not True or False')

    @property
    def readonly(self):
        return self._readonly

    @readonly.setter
    def readonly(self, value):
        self._readonly = value
        if self._readonly not in [True, False]:
            MessageBoxTermination(
                info='Field Definition Readonly not True or False')

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
        if self._selected not in [True, False]:
            MessageBoxTermination(
                info='Field Definition Selected not True or False')

    @property
    def protected(self):
        return self._protected

    @protected.setter
    def protected(self, value):
        self._protected = value
        if self._protected not in [True, False]:
            MessageBoxTermination(
                info='Field Definition Protected not True or False')

    @property
    def combo_positioning(self):
        return self._combo_positioning

    @combo_positioning.setter
    def combo_positioning(self, value):
        self._combo_positioning = value
        if self._combo_positioning not in [True, False]:
            MessageBoxTermination(
                info='Field Definition ComboPositioning not True or False')

    @property
    def combo_insert_value(self):
        return self._combo_insert_value

    @combo_insert_value.setter
    def combo_insert_value(self, value):
        self._combo_insert_value = value
        if self._combo_insert_value not in [True, False]:
            MessageBoxTermination(
                info='Field Definition ComboInsertValue not True or False')

    @property
    def focus_out(self):
        return self._focus_out

    @focus_out.setter
    def focus_out(self, value):
        self._focus_out = value
        if self._focus_out not in [True, False]:
            MessageBoxTermination(
                info='Field Definition FocusOut not True or False')

    @property
    def focus_in(self):
        return self._focus_in

    @focus_in.setter
    def focus_in(self, value):
        self._focus_in = value
        if self._focus_in not in [True, False]:
            MessageBoxTermination(
                info='Field Definition FocusIn not True or False')

    @property
    def upper(self):
        return self._upper

    @upper.setter
    def upper(self, value):
        self._upper = value
        if self._upper not in [True, False]:
            MessageBoxTermination(
                info='Field Definition UpperCase not True or False')


class BuiltBox(object):
    """
    TOP-LEVEL-WINDOW        BuiltBox

    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
    """

    def __init__(
        self,
        title=MESSAGE_TITLE,
        header=get_message(MESSAGE_TEXT, 'ENTRY'),
        columnspan=2,
        button1_text=BUTTON_OK,
        button2_text=None,
        button3_text=None,
        button4_text=None,
        button5_text=None,
        button6_text=None,
        width=WIDTH_WIDGET,
        width_canvas=WIDTH_CANVAS,
        height_canvas=HEIGHT_CANVAS,
        grab=True,
        scrollable=False
    ):
        # --- Thread safety check (must happen BEFORE any UI creation) ---
        self.window_id = self.__class__.__name__
    
        if not is_main_thread():
            MessageBoxInfo(
                title=title,
                message=get_message(MESSAGE_TEXT, 'THREAD', self.window_id)
            )
            return
    
        # --- Safe to create UI from here ---
        self.repo = Repository()
        self.button_state = None
        self._box_window_top = Toplevel()
    
        # --- Header & layout setup ---
        self.header = header
    
        buttons = [
            button1_text, button2_text, button3_text,
            button4_text, button5_text, button6_text
        ]
    
        button_count = sum(btn is not None for btn in buttons)
        self.columnspan = max(columnspan, button_count)
    
        (
            self._button1_text,
            self._button2_text,
            self._button3_text,
            self._button4_text,
            self._button5_text,
            self._button6_text
        ) = buttons
    
        self._width = width
        self._height_canvas = height_canvas
        self._row = 0
    
        # --- UI creation ---
        self._create_header()
    
        if scrollable:
            self._row += 1
            self.frame = Frame(self._box_window_top)
            self.frame.grid(row=self._row, column=0, sticky="nsew")
    
            self._box_window_top.columnconfigure(0, weight=1)
            self._box_window_top.rowconfigure(0, weight=1)
            self.frame.columnconfigure(0, weight=1)
    
            canvas = Canvas(self.frame)
            canvas.grid(row=self._row, column=0, sticky="nsew")
    
            self.frame.grid_rowconfigure(0, weight=1)
            self.frame.grid_columnconfigure(0, weight=1)
    
            self._box_window = Frame(canvas)
            canvas.create_window((0, 0), window=self._box_window, anchor="nw")
    
            scrollbar = Scrollbar(self.frame, orient="vertical", command=canvas.yview)
            scrollbar.grid(row=self._row, column=1, sticky="ns")
    
            canvas.configure(
                yscrollcommand=scrollbar.set,
                height=height_canvas
            )
    
            self._box_window.bind(
                "<Configure>",
                lambda _: canvas.configure(scrollregion=canvas.bbox("all"))
            )
        else:
            self._box_window = self._box_window_top
    
        # --- Window title ---
        db_name = connectionresult.database.upper()
        self._box_window_top.title(
            title if title.startswith(db_name) else f"{db_name} {title}"
        )
    
        # --- Content ---
        self.create_fields()
    
        if scrollable:
            self._row = 3
    
        self._create_footer()
        self._create_buttons()
        self._keyboard()
    
        self.set_geometry()
    
        if grab:
            self._activate_window()
        else:    
            self._box_window_top.focus_force()
            # Focus first input widget
            self._focus_first_input()

        if scrollable:
            canvas.configure(width=self.calculate_width_canvas())
    
        self._box_window_top.protocol(
            WM_DELETE_WINDOW,
            self._wm_deletion_window
        )
    
        self._box_window_top.mainloop()
        destroy_widget(self._box_window_top)
    def _activate_window(self):
        """
        Activates this dialog window in a fully modal and
        Windows-safe way.

        - Makes window transient to its parent
        - Applies grab_set() for modality
        - Brings window to foreground
        - Assigns keyboard focus safely
        - Restores parent focus when closed
        """

        win = self._box_window_top
        parent = win.master

        win.update_idletasks()

        # If there is a parent window, make dialog transient
        if parent and parent.winfo_exists():
            win.transient(parent)
            
        # Apply modal grab
        win.grab_set()

        # Ensure visibility and foreground
        win.deiconify()
        win.lift()

        # Temporary topmost (important for Windows)
        win.attributes("-topmost", True)
        win.after(80, lambda: win.attributes("-topmost", False))

        win.focus_force()

        # Focus first input widget
        self._focus_first_input()

        # Ensure parent regains focus when dialog closes
        win.protocol(WM_DELETE_WINDOW, self._safe_close)

    def _focus_first_input(self):
        """
        Sets focus to the first Entry or Combobox widget
        in the dialog.
        """

        win = self._box_window_top

        def set_focus():
            for child in win.winfo_children():
                if child.winfo_class() in ("TEntry", "Entry", "TCombobox"):
                    child.focus_set()
                    return

        win.after(120, set_focus)

    def _safe_close(self):
        """
        Releases grab safely and restores parent focus.
        """

        win = self._box_window_top
        parent = win.master

        try:
            win.grab_release()
        except Exception:
            pass

        self._geometry_put(win)
        self.button_state = WM_DELETE_WINDOW

        win.destroy()

        # Restore parent focus
        if parent and parent.winfo_exists():
            parent.lift()
            parent.focus_force()

    def calculate_width_canvas(self):
        # Get the number of (rows not used and) columns
        _, columns = self._box_window_top.grid_size()
        width_canvas = 0
        for column_index in range(columns):
            bbox = self._box_window_top.grid_bbox(column=column_index, row=0)
            # bbox returns (x, y, width, height), so we extract the width
            padx = 10
            ipadx = 1
            width_canvas = width_canvas + \
                bbox[2] + columns * padx + columns * ipadx
        return width_canvas

    def set_geometry(self):

        geometry = self.repo.select_geometry_of_caller(self.window_id)
        if not geometry:
            geometry = BUILTBOX_WINDOW_POSITION
        self._box_window_top.geometry(geometry)

    def _create_header(self):

        if self.header is None:
            self.header = ''
        else:
            list_header = list(self.header)
            line_feed = False
            for idx in range(len(list_header)):
                if idx % 100 == 0 and idx > 0:
                    line_feed = True
                if list_header[idx] == ' ' and line_feed:
                    list_header.insert(idx, '\n')
                    line_feed = False
            self.header = ''.join(list_header)
        header_widget = Label(
            self._box_window_top, width=self._width, text=self.header)
        header_widget.grid(
            row=self._row, columnspan=self.columnspan, padx='3m', pady='3m')
        self._row += 1

    def _create_footer(self):

        self.footer = StringVar()
        self.message_widget = Label(self._box_window_top, width=self._width, textvariable=self.footer,
                                    foreground='RED')
        self.message_widget.grid(
            row=self._row, columnspan=self.columnspan, padx='3m', pady='3m')
        self._row += 1

    def _create_buttons(self):
        button_frame = Frame(self._box_window_top, width=self._width)
        button_frame.grid(row=self._row, column=0,
                          columnspan=self.columnspan, sticky=W)
        button_column = 0
        if self._button1_text is not None:
            button1 = ttk.Button(button_frame, text=self._button1_text)
            button1.grid(row=0, column=button_column, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button1.bind('<Return>', self.button_1_button1)
            button1.bind('<Button-1>', self.button_1_button1)
            button_column += 1
        if self._button2_text is not None:
            button2 = ttk.Button(button_frame, text=self._button2_text,)
            button2.grid(row=0, column=button_column, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button2.bind('<Return>', self.button_1_button2)
            button2.bind('<Button-1>', self.button_1_button2)
            button_column += 1
        if self._button3_text is not None:
            button3 = ttk.Button(button_frame, text=self._button3_text)
            button3.grid(row=0, column=button_column, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button3.bind('<Return>', self.button_1_button3)
            button3.bind('<Button-1>', self.button_1_button3)
            button_column += 1
        if self._button4_text is not None:
            button4 = ttk.Button(button_frame, text=self._button4_text)
            button4.grid(row=0, column=button_column, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button4.bind('<Return>', self.button_1_button4)
            button4.bind('<Button-1>', self.button_1_button4)
            button_column += 1
        if self._button5_text is not None:
            button5 = ttk.Button(button_frame, text=self._button5_text)
            button5.grid(row=0, column=button_column, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button5.bind('<Return>', self.button_1_button5)
            button5.bind('<Button-1>', self.button_1_button5)
            button_column += 1
        if self._button6_text is not None:
            button6 = ttk.Button(button_frame, text=self._button6_text)
            button6.grid(row=0, column=button_column, sticky=E, x='3m',
                         y='3m', ix='2m', ipady='1m')
            button6.bind('<Return>', self.button_1_button6)
            button6.bind('<Button-1>', self.button_1_button6)

    def create_fields(self):

        pass

    def _wm_deletion_window(self):
        """
        Safe window close handling with proper grab management.
        """

        win = self._box_window_top
        current_grab = win.grab_current()
        # Case 1: Another window holds the grab
        if current_grab and current_grab is not win:
            top = current_grab.winfo_toplevel()

            if top.winfo_exists():
                top.deiconify()
                top.lift()
                top.attributes("-topmost", True)
                top.after(80, lambda: top.attributes("-topmost", False))
                top.focus_force()
                top.bell()

            return  # prevent closing
        # Case 2: This window holds the grab
        if current_grab is win:
            try:
                win.grab_release()
            except Exception:
                pass
        # Normal close
        self._geometry_put(win)
        self.button_state = WM_DELETE_WINDOW
        if win.winfo_exists():
            win.update_idletasks()

        self.quit_widget()

    def quit_widget(self):

        self._geometry_put(self._box_window_top)
        quit_widget(self._box_window_top)

    def _geometry_put(self, window):
        """
        put window geometry
        """
        if window.winfo_exists():  # window exists
            width = window.winfo_width()
            height = window.winfo_height()
            geometry = ''.join([str(width), 'x', str(
                height), '+', str(window.winfo_x()), '+', str(window.winfo_y())])
        else:
            geometry = BUILTBOX_WINDOW_POSITION
        self.repo.replace_geometry_only(self.window_id, geometry)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        if not self.footer.get():
            self.quit_widget()

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.quit_widget()

    def button_1_button4(self, event):

        self.button_state = self._button4_text
        self.quit_widget()

    def button_1_button5(self, event):

        self.button_state = self._button5_text
        self.quit_widget()

    def button_1_button6(self, event):

        self.button_state = self._button6_text
        self.quit_widget()

    def _keyboard(self):

        add_hotkey("ctrl+right", self.handle_ctrl_right)
        add_hotkey("ctrl+left", self.handle_ctrl_left)
        add_hotkey("ctrl+up", self.handle_ctrl_up)
        add_hotkey("ctrl+down", self.handle_ctrl_down)

    def handle_ctrl_right(self):

        pass

    def handle_ctrl_left(self):

        pass

    def handle_ctrl_up(self):

        pass

    def handle_ctrl_down(self):

        pass


class BuiltRadioButtons(BuiltBox):
    """
    TOP-LEVEL-WINDOW        Radiobuttons

    PARAMETER:
        radiobutton_dict    Dictionary defining Radiobuttons {key: description, .... }
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field               Key of selected Radiobutton
    """

    def __init__(
            self, header=get_message(MESSAGE_TEXT, 'RADIOBUTTON'), title=MESSAGE_TITLE,
            button1_text=BUTTON_SAVE, button2_text=BUTTON_RESTORE,
            button3_text=None, button4_text=None, button5_text=None,
            default_value=None,
            radiobutton_dict={'123': 'Description of RadioButton1',
                              '234': 'Description of RadioButton2',
                              '345': 'Description of RadioButton3'}):

        self.field = None
        self._radiobutton_dict = radiobutton_dict
        self._default_value = default_value
        super().__init__(title=title, header=header,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text)

    def create_fields(self):

        self._radiobutton_value = StringVar()
        radiobutton_key_length = len(
            max(self._radiobutton_dict.keys(), key=len))
        radiobutton_val_length = len(
            max(self._radiobutton_dict.values(), key=len))
        for radiobutton_key in self._radiobutton_dict:
            radiobutton = Radiobutton(self._box_window, text=radiobutton_key,
                                      width=radiobutton_key_length,
                                      variable=self._radiobutton_value, value=radiobutton_key)
            radiobutton.grid(row=self._row, column=0, padx='3m', sticky='w')
            radiobutton.columnconfigure(0, weight=1)
            radiobuttondescription = Label(self._box_window, width=radiobutton_val_length,
                                           text=self._radiobutton_dict[radiobutton_key])
            radiobuttondescription.grid(row=self._row, column=1, padx='3m')
            radiobuttondescription.columnconfigure(1, weight=3)
            self._row += 1
            if self._default_value == radiobutton_key:
                radiobutton.invoke()

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.field = self._radiobutton_value.get()
        if self.field == '':
            self.footer.set(get_message(MESSAGE_TEXT, 'SELECT_DATA'))
        else:
            self.quit_widget()

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        try:
            radiobutton_key = next(radiobutton_key for radiobutton_key in self._radiobutton_dict
                                   if radiobutton_key == self._default_value)
            radiobutton = Radiobutton(self._box_window, text=radiobutton_key,
                                      variable=self._radiobutton_value, value=radiobutton_key)
            radiobutton.invoke()
        except StopIteration:
            pass


class BuiltCheckButton(BuiltBox):
    """
    TOP-LEVEL-WINDOW        Checkbutton

    PARAMETER:
        checkbutton_texts   List  of Checkbutton Texts
        default_texts       initializes check_buttons to on
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_list          list of selected Checkbutton Texts
                            ordered as selected
    """

    def __init__(
            self, header=get_message(MESSAGE_TEXT, 'CHECKBOX'), title=MESSAGE_TITLE, width_widget=WIDTH_WIDGET,
            button1_text=BUTTON_NEXT, button2_text=None,
            button3_text=None, button4_text=BUTTON_SELECT_ALL,
            button5_text=BUTTON_DELETE_ALL,
            default_texts=[],
            checkbutton_texts=['Description of Checkbox1', 'Description of Checkbox2',
                               'Description of Checkbox3']):

        self.field_list = default_texts.copy()
        self.default_texts = default_texts
        self.checkbutton_texts = checkbutton_texts
        super().__init__(title=title, header=header,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text)

    def create_fields(self):

        self._check_vars = []
        row = self._row
        column = 0
        for idx, check_text in enumerate(self.checkbutton_texts):
            self._check_vars.append(IntVar())
            checkbutton = Checkbutton(self._box_window, text=check_text,
                                      variable=self._check_vars[idx])
            checkbutton.myId = str(idx)
            checkbutton.bind("<FocusOut>", self.focus_out_action)
            checkbutton.grid(row=row, column=column, padx='3m', sticky=W)
            if (idx + 1) % 15 == 0:
                column += 1
                row = 1
            row += 1
        self._row = 20
        for idx, check_text in enumerate(self.checkbutton_texts):
            if check_text in self.default_texts:
                self._check_vars[idx].set(1)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 0:
                if self.checkbutton_texts[idx] in self.field_list:
                    self.field_list.remove(self.checkbutton_texts[idx])
            else:
                if self.checkbutton_texts[idx] not in self.field_list:
                    self.field_list.append(self.checkbutton_texts[idx])
        self.validate_all()
        self.quit_widget()

    def button_1_button4(self, event):

        self.button_state = self._button4_text
        for idx, _ in enumerate(self.checkbutton_texts):
            self._check_vars[idx].set(1)
        self.field_list = self.checkbutton_texts.copy()

    def button_1_button5(self, event):

        self.button_state = self._button5_text
        for idx, _ in enumerate(self.checkbutton_texts):
            self._check_vars[idx].set(0)
        self.field_list = []

    def focus_out_action(self, event):

        idx = int(event.widget.myId)
        if self._check_vars[idx].get() == 1:
            self.field_list.append(self.checkbutton_texts[idx])
        else:
            if self.checkbutton_texts[idx] in self.field_list:
                self.field_list.remove(self.checkbutton_texts[idx])

    def validate_all(self):

        pass


class BuiltEnterBox(BuiltBox):
    """
    TOP-LEVEL-WINDOW        EnterBox (Entry Input Fields and ComboList Fields)

    PARAMETER:
        ...
        field_defs          Named Tuple of Field Definitions (see Class FieldDefintion)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary with fieldnames and values (e.g.{name: value,..})
    """
    Field_Names = namedtuple('Field_Names', ['Feld1', 'Feld2'])

    def __init__(self,
                 title=MESSAGE_TITLE, header=get_message(MESSAGE_TEXT, 'ENTRY'),
                 button1_text=BUTTON_SAVE, button2_text=BUTTON_RESTORE, button3_text=None,
                 button4_text=None, button5_text=None, button6_text=None,
                 width=WIDTH_WIDGET, width_canvas=WIDTH_CANVAS, height_canvas=HEIGHT_CANVAS,
                 grab=False, scrollable=False,
                 field_defs=Field_Names(
                     FieldDefinition(definition=COMBO, name='Feld1', length=8, lformat=FORMAT_FIXED,
                                     selected=True, combo_values=['Wert1', 'Wert2']),
                     FieldDefinition(name='Feld2', length=70,
                                     default_value='Default Wert fuer Feld211111111111111111111111111111111111111111111111111')
                 )):

        self.field_dict = None
        self._field_defs = field_defs
        super().__init__(title=title, header=header, width=width, grab=grab,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text, button6_text=button6_text,
                         width_canvas=width_canvas, height_canvas=HEIGHT_CANVAS,
                         scrollable=scrollable, columnspan=2)

    def create_fields(self):

        for field_def in self._field_defs:
            if field_def.definition == CHECK:
                field_def.textvar = IntVar()
                field_def.textvar.set('0')
            else:
                field_def.textvar = StringVar()
                field_def.textvar.set('')
        check_text_length = 0
        for field_def in self._field_defs:
            self._field_def = field_def
            if field_def.mandatory:
                widget_lab = Label(self._box_window, width=len(field_def.name) + 5,
                                   text=field_def.name, anchor=W)
            else:
                widget_lab = Label(self._box_window, width=len(field_def.name) + 5,
                                   text=field_def.name, anchor=W, style='OPT.TLabel')
            widget_lab.grid(row=self._row, sticky=W, padx='3m', pady='1m')
            if field_def.definition == ENTRY:
                if field_def.typ == TYP_DATE:
                    widget_entry = DateEntry(self._box_window, width=16, background="magenta3",
                                             textvariable=field_def.textvar,
                                             foreground="white", bd=2, locale='de_de',
                                             date_pattern='yyyy-mm-dd')
                    widget_entry.myId = field_def.name
                else:
                    if field_def.length < MAX_FIELD_LENGTH:
                        widget_entry = Entry(self._box_window, width=field_def.length + 2,
                                             textvariable=field_def.textvar)
                    else:
                        widget_entry = Entry(self._box_window, width=MAX_FIELD_LENGTH,
                                             textvariable=field_def.textvar)
                        if field_def.protected and field_def.default_value is not None and len(field_def.default_value) > MAX_FIELD_LENGTH:
                            # Create a frame to hold the Entry and Scrollbar
                            frame = Frame(self._box_window)
                            frame.grid(row=self._row, column=5,
                                       padx=10, pady=10)
                            # Create a horizontal Scrollbar if field protected
                            scrollbar = Scrollbar(
                                frame, orient="horizontal", command=widget_entry.xview)
                            scrollbar.grid(
                                row=self._row, column=5, sticky="ew")
                            # Configure the Entry to work with the Scrollbar
                            widget_entry.configure(
                                xscrollcommand=scrollbar.set)
                    widget_entry.myId = field_def.name
            elif field_def.definition == CHECK:
                if check_text_length < len(field_def.checkbutton_text):
                    check_text_length = len(field_def.checkbutton_text)
                widget_entry = Checkbutton(self._box_window, text=field_def.checkbutton_text,
                                           variable=field_def.textvar)
                widget_entry.myId = field_def.name
            else:
                widget_entry = ttk.Combobox(self._box_window, values=field_def.combo_values,
                                            width=field_def.length + 2,
                                            textvariable=field_def.textvar)
                widget_entry.myId = field_def.name
                widget_entry.bind('<KeyRelease>', self.combo_position)

                if field_def.selected:
                    widget_entry.bind("<<ComboboxSelected>>",
                                      self.comboboxselected_action)
                if field_def.readonly:
                    widget_entry.config(state='readonly')
            if field_def.focus_out:
                widget_entry.bind("<FocusOut>", self.focus_out_action)
            if field_def.focus_in:
                widget_entry.bind("<FocusIn>", self.focus_in_action)
            if field_def.protected:
                widget_entry.config(state=DISABLED)
            # if field_def.name in [KEY_PIN]:
            #    widget_entry.config(show='*')
            if field_def.definition == CHECK:
                if field_def.default_value:
                    field_def.textvar.set(1)
                else:
                    field_def.textvar.set(0)
            else:
                if field_def.default_value:
                    field_def.textvar.set(field_def.default_value)
                else:
                    if field_def.typ == TYP_DECIMAL:
                        field_def.textvar.set('0')
                    elif field_def.name in DATABASE_FIELDS_PROPERTIES and DATABASE_FIELDS_PROPERTIES[field_def.name].data_type in INTEGER:
                        field_def.textvar.set('0')
                    else:
                        field_def.textvar.set('')
            widget_entry.grid(row=self._row, column=1,
                              columnspan=self.columnspan, sticky='W', padx='3m', pady='1m')
            self._row += 1
            if field_def.separator:
                separator = Separator(self._box_window, orient='horizontal')
                separator.grid(row=self._row, columnspan=self.columnspan,
                               sticky=(W, E), pady=5)
                self._row += 1
            field_def.widget = widget_entry

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():

            self.quit_widget()

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        for field_def in self._field_defs:
            if field_def.definition == CHECK:
                if field_def.default_value:
                    field_def.textvar.set(1)
                else:
                    field_def.textvar.set(0)
            else:
                field_def.widget.delete(0, END)
                if field_def.default_value is not None:
                    field_def.widget.insert(0, field_def.default_value)

    def validation(self):

        self.field_dict = {}
        self.footer.set('')
        for field_def in self._field_defs:
            if not field_def.protected:
                self.footer.set(self.field_validation(field_def.name, field_def))
                if self.footer.get():
                    break
                self.validation_addon(field_def)
                if self.footer.get():
                    break
            if field_def.definition == CHECK:
                self.field_dict[field_def.name] = field_def.textvar.get()
            else:
                self.field_dict[field_def.name] = field_def.widget.get()
        self.validation_all_addon(self._field_defs)
        self.field_dict_adjust_period()
        for field_def in self._field_defs:
            if field_def.upper:
                if field_def.name in self.field_dict:
                    self.field_dict[field_def.name] = self.field_dict[field_def.name].upper(
                    )
        
    def field_dict_adjust_period(self):
        # adjusts period using trading_calendar XETRA
        if all(key in self.field_dict for key in [FN_FROM_DATE, FN_TO_DATE]):
            self.field_dict[FN_FROM_DATE], self.field_dict[FN_TO_DATE] = xetra_cls.adjust_period(
                self.field_dict[FN_FROM_DATE],
                self.field_dict[FN_TO_DATE]
                )

    def field_validation(self, name, field_def):
        """
            Returns footer text
        """
        if field_def.definition == CHECK:
            return ''
        field_value = field_def.widget.get()
        if field_def.mandatory and field_value == '':
            footer = get_message(MESSAGE_TEXT, 'MANDATORY', name)
            return footer
        if name in DATABASE_FIELDS_PROPERTIES:
            if DATABASE_FIELDS_PROPERTIES[name].data_type in INTEGER and not field_value.isdigit():
                return get_message(MESSAGE_TEXT, 'ISDIGIT', name)
        if field_value:
            if field_def.lformat == FORMAT_FIXED:
                if len(field_value) != field_def.length and field_value != NOT_ASSIGNED:
                    return get_message(MESSAGE_TEXT, 'FIXED', name, field_def.length)
            else:
                if len(field_value) > field_def.length:
                    return get_message(MESSAGE_TEXT, 'LENGTH', name, field_def.length)
                elif len(field_value) < field_def.min_length:
                    return get_message(MESSAGE_TEXT, 'MIN_LENGTH', name, field_def.min_length)
            if field_def.typ == TYP_DECIMAL:
                field_value = field_value.strip()
                if ',' in field_value:
                    # German format
                    field_value = field_value.replace('.', '').replace(',', '.')            
                field_def.widget.delete(0, END)
                field_def.widget.insert(0, field_value)
                if (re_amount.fullmatch(field_value) is None and
                        re_amount_int.fullmatch(field_value) is None):
                    return get_message(MESSAGE_TEXT, 'DECIMAL', name)
            if field_def.typ == TYP_DATE:
                if len(field_value) == 10:
                    date_ = field_value[0:10]
                    try:
                        day = int(date_.split('-')[2])
                        month = int(date_.split('-')[1])
                        year = int(date_.split('-')[0])
                        date_ = date(year, month, day)
                    except (ValueError, EOFError, IndexError):
                        return get_message(MESSAGE_TEXT, 'DATE', name)
                else:
                    return get_message(MESSAGE_TEXT, 'DATE', name)
            # if combo_list contains extended values e.g. declm.DB_credit_account in class BuitlTableBoxRow Ledger
            combo_values = [
                field_value for item in field_def.combo_values if item.startswith(field_value)]
            if (field_def.definition == COMBO and not field_def.combo_insert_value  # means insert not allowed
                    and not combo_values):
                return get_message(MESSAGE_TEXT, 'NOTALLOWED', name, field_def.combo_values)
        return ''

    def validation_addon(self, field_def):
        """
        more field validations
        """
        pass

    def validation_all_addon(self, field_defs):
        """
        validations of the fields on the whole
        """
        pass

    def comboboxselected_action(self, event):

        pass

    def combo_position(self, event):
        """
        positioning combolist on key release
        only combo_values selectable
        """

        try:
            field_attr = getattr(self._field_defs, event.widget.myId)
            combo_positioning = field_attr.combo_positioning
            definition = field_attr.definition
            if definition == COMBO and combo_positioning:
                field_attr.widget.delete(
                    field_attr.widget.index(INSERT), END)
                get = field_attr.widget.get()
                item, index = list_positioning(
                    field_attr.combo_values, get.upper())
                if item.upper().startswith(get.upper()):
                    event.widget.current(index)
                    self.comboboxselected_action(event)
        except Exception:
            pass

    def focus_out_action(self, event):

        pass

    def focus_in_action(self, event):

        pass


class BuiltSelectBox(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox of Selction Criteria

     selection_name --> Storage name for last used selection values
     data_dict --> default values of select_data
     upper --> list of fields with upper_in field_property
     separator --> list of fields followed by a separator
     container --> contains additional data from caller


    """
    Field_Row = namedtuple(
        'FieldRow', ['name', 'definition', 'length', 'typ', 'comment'])

    def __init__(self, title=MESSAGE_TITLE, header=None, table=None,
                 button1_text=BUTTON_OK, button2_text=BUTTON_RESTORE,
                 button3_text=None, button4_text=None,
                 selection_name=None,
                 data_dict={},
                 upper=None, separator=None,
                 container=None
                 ):

        self.title = title
        self.header = header
        self.table = table
        self.repo = Repository()
        self.selection_name = selection_name
        self.data_dict = data_dict
        self.get_selection()
        self.check_button_exist = False
        if upper:
            self.upper = upper
        else:
            self.upper = []
        if separator:
            self.separator = separator
        else:
            self.separator = []
        self.container = container
        field_defs = self.create_field_defs()
        if len(field_defs) > 25:
            scrollable = True
        else:
            scrollable = False
        if self.check_button_exist:
            button3_text = BUTTON_SELECT_ALL
            button4_text = BUTTON_DELETE_ALL
        super().__init__(title=title, header=header, field_defs=field_defs,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         scrollable=scrollable)
        

    def get_selection(self):
        """
        initializes the selection fields with the used values of last session
        """
        if not self.selection_name:
            self.selection_name = self.title
        if not self.data_dict:
            result = self.repo.selection_get(self.selection_name)
            if result:
                self.data_dict = result

    def create_check_field(self, name, comment):

        if ((self.table == STATEMENT and name in [declm.DB_iban, declm.DB_entry_date, declm.DB_counter])
                or
                (self.table in [HOLDING, HOLDING_VIEW] and name in [declm.DB_iban, declm.DB_price_date, declm.DB_ISIN])
                or
                (self.table in [PRICES, PRICES_ISIN_VIEW] and name in [declm.DB_symbol, declm.DB_price_date])
                or
                (self.table in [TRANSACTION, TRANSACTION_VIEW] in [declm.DB_iban, declm.DB_ISIN, declm.DB_price_date, declm.DB_counter])
                or
                name == declm.DB_id_no):
            # Mandatory fields are always selected and cannot be removed from the selection
            self.data_dict[name] = 1
            field_def = FieldDefinition(definition=CHECK, name=name,
                                        checkbutton_text=comment, protected=True)
        else:
            field_def = FieldDefinition(definition=CHECK, name=name,
                                        checkbutton_text=comment)
        self.check_button_exist = True
        return field_def

    def create_date_field(self, name):

        field_def = FieldDefinition(definition=ENTRY, name=name,
                                    length=16,
                                    typ=TYP_DATE)
        return field_def

    def create_combo_field(self, name, length, typ, combo_list):

        field_def = FieldDefinition(definition=COMBO, name=name,
                                    length=length,
                                    typ=typ,
                                    combo_values=combo_list)
        if name in self.upper:
            field_def.upper = True
        return field_def

    def create_entry_field(self, name, length, typ):

        field_def = FieldDefinition(definition=ENTRY, name=name,
                                    length=length,
                                    typ=typ,
                                    )
        if name in self.upper:
            field_def.upper = True
        return field_def

    def create_field_defs_list(self):

        field_defs_list = []
        # call self.create_..._field()
        return field_defs_list

    def create_field_defs(self):
        """
        Creates attributes of form fields
        """
        field_defs_list = self.create_field_defs_list()
        field_name_list = []
        for field_def in field_defs_list:
            field_name_list.append(field_def.name)
            if field_def.name in self.separator:
                field_def.separator = True
            if field_def.name in self.data_dict.keys():
                field_def.default_value = self.data_dict[field_def.name]
            else:
                if field_def.typ == TYP_DECIMAL:
                    field_def.default_value = 0
                else:
                    field_def.default_value = ''
        FieldNames = namedtuple('FieldNames', field_name_list)
        field_defs_tuple = FieldNames(*field_defs_list)
        return field_defs_tuple

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():
            if self.selection_name:
                self.repo.selection_put(self.selection_name, self.field_dict)
            self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        for field_def in self._field_defs:
            if field_def.definition == CHECK:
                getattr(self._field_defs, field_def.name).textvar.set('1')

    def button_1_button4(self, event):

        self.button_state = self._button3_text
        for field_def in self._field_defs:
            if field_def.definition == CHECK:
                getattr(self._field_defs, field_def.name).textvar.set('0')

    def validation_all_addon(self, field_defs):

        if hasattr(field_defs, FN_FROM_DATE) and hasattr(field_defs, FN_TO_DATE):
            from_date = getattr(field_defs, FN_FROM_DATE).widget.get()
            to_date = getattr(field_defs, FN_TO_DATE).widget.get()
            if (from_date > to_date):
                self.footer.set(
                    get_message(
                        MESSAGE_TEXT, 'DATE', getattr(field_defs, FN_FROM_DATE).name)
                    )
                getattr(self._field_defs, FN_TO_DATE).textvar.set(
                    from_date)  # adjusted date returned


class BuiltTableRowBox(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Table Values

     table -->  database table
     table_view --> form fields
     combo_dict --> dictionary af combo fields, key: field_name, value: combo_list
     combo_positioning_dict   --> dictionary af combo fields, key: field_name, value: combo_list
                                  only values of combo_list are allowed if combo_field_name not in combo_insert_value
     combo_insert_value --> list of combo fields which allows new items
     protected --> list of protected fields
     mandatory --> list of mandatory fields
     focus_in --> list of fields with focus_in field_property
     focus_out --> list of fields with focus_out field_property
     upper --> list of fields with upper_in field_property


    """

    def __init__(self, table, table_view, data_row_dict,
                 combo_dict={}, combo_positioning_dict={}, combo_insert_value=[],
                 protected=[], mandatory=[], focus_in=[], focus_out=[], upper=[],
                 title=MESSAGE_TITLE, header=None,
                 button1_text=BUTTON_SAVE, button2_text=BUTTON_RESTORE,
                 button3_text=None, button4_text=None):

        self.title = title
        self.header = header
        self.table = table
        self.table_view = table_view
        self.data_row_dict = data_row_dict
        self.combo_dict = combo_dict
        self.combo_positioning_dict = combo_positioning_dict
        self.combo_insert_value = combo_insert_value
        self.protected = protected
        self.mandatory = mandatory
        self.focus_out = focus_out
        self.focus_in = focus_in
        self.upper = upper
        if isinstance(table_view, list):
            self.field_name_list = table_view
        else:
            self.repo = Repository()
            self.field_name_list = TABLE_FIELDS[table_view]

        # create form field definitions
        field_defs = self.create_field_defs()
        if len(self.field_name_list) > 25:
            scrollable = True
        else:
            scrollable = False
        super().__init__(title=title, header=header, field_defs=field_defs,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         grab=True, scrollable=scrollable)

    def create_field_defs(self):
        """
        Creates attributes of form fields
        """
        check_fields = []
        if isinstance(self.table_view, list):
            fields_properties = TABLE_FIELDS_PROPERTIES[self.table]
        else:
            fields_properties = TABLE_FIELDS_PROPERTIES[self.table_view]
        for column in fields_properties.keys():
            if fields_properties[column].data_type == TINYINT:
                check_fields.append(column)
        field_defs = []
        for field_name in self.field_name_list:
            if field_name in self.combo_insert_value:
                combo_insert_value = True
            else:
                combo_insert_value = False
            # create field_defs
            if field_name in check_fields:
                field_def = FieldDefinition(definition=CHECK, name=field_name,
                                            checkbutton_text=fields_properties[field_name].comment)
            elif field_name in self.combo_dict.keys():
                # combo field without positioning, new items allowed if fieldname in self.combo_insert_value
                field_def = FieldDefinition(definition=COMBO, name=field_name,
                                            length=fields_properties[field_name].length,
                                            typ=fields_properties[field_name].typ,
                                            combo_insert_value=combo_insert_value,
                                            combo_positioning=False,
                                            combo_values=self.combo_dict[field_name])
                if fields_properties[field_name].data_type == 'char':
                    field_def.lformat = FORMAT_FIXED
            elif field_name in self.combo_positioning_dict.keys():
                # combo field with positioning, new items allowed if fieldname in self.combo_insert_value
                field_def = FieldDefinition(definition=COMBO, name=field_name,
                                            length=fields_properties[field_name].length,
                                            typ=fields_properties[field_name].typ,
                                            combo_insert_value=combo_insert_value,
                                            combo_positioning=True,
                                            combo_values=self.combo_positioning_dict[field_name])
                if fields_properties[field_name].data_type == 'char':
                    field_def.lformat = FORMAT_FIXED
            else:
                field_def = FieldDefinition(definition=ENTRY, name=field_name,
                                            length=fields_properties[field_name].length,
                                            typ=fields_properties[field_name].typ,
                                            )
                if fields_properties[field_name].data_type == 'char':
                    field_def.lformat = FORMAT_FIXED
            if field_name in self.protected:
                field_def.protected = True
            if field_name not in self.mandatory:
                field_def. mandatory = False  # standard is mandatory
            if field_name in self.focus_in:
                field_def.focus_in = True
            if field_name in self.focus_out:
                field_def.focus_out = True
            if field_name in self.upper:
                field_def.upper = True
            if field_name in self.data_row_dict:
                field_def.default_value = self.data_row_dict[field_name]
            else:
                if fields_properties[field_name].typ == TYP_DECIMAL:
                    field_def.default_value = 0
                else:
                    field_def.default_value = ''

            field_def = self.set_field_def(field_def)
            field_defs.append(field_def)
        FieldNames = namedtuple('FieldNames', self.field_name_list)
        field_defs_tuple = FieldNames(*field_defs)
        return field_defs_tuple

    def set_field_def(self, field_def):

        return field_def


class BuiltText(object):
    """
    TOP-LEVEL-WINDOW        TextBox with ScrollBars (Only Output)

    PARAMETER:
        text                String of Text Lines
    """

    def __init__(self, title=MESSAGE_TITLE, header='', text='', fullscreen=False):

        self.window_id = self.__class__.__name__
        if is_main_thread():
            if header == Informations.PRICES_INFORMATIONS:
                Informations.prices_informations = ''
            elif header == Informations.BANKDATA_INFORMATIONS:
                Informations.bankdata_informations = ''
            elif header == Informations.HOLDING_INFORMATIONS:
                Informations.holding_informations = ''
            header = ''
            self._builttext_window = Toplevel()
            self._builttext_window.title(title)
            self._builttext_window.geometry(BUILTEXT_WINDOW_POSITION)
            if self.destroy_widget(text):  # check: discard output
                destroy_widget(self._builttext_window)
                return
            # --------------------------------------------------------------
            height = len(list(enumerate(text.splitlines()))) + 5
            if height > HEIGHT_TEXT:
                height = HEIGHT_TEXT
            self.text_widget = Text(
                self._builttext_window, font=('Courier', 8), wrap='none')
            self.text_widget.grid(sticky=W)
            scroll_x = Scrollbar(self._builttext_window, orient="horizontal",
                                 command=self.text_widget.xview)
            scroll_x.grid(sticky="ew")

            scroll_y = Scrollbar(self._builttext_window, orient="vertical",
                                 command=self.text_widget.yview)
            scroll_y.grid(row=1, column=1, sticky="ns")

            self.text_widget.configure(yscrollcommand=scroll_y.set,
                                       xscrollcommand=scroll_x.set)
            textlines = text.splitlines()
            line_length = 1
            for line, textline in enumerate(textlines):
                if line_length < len(textline):
                    line_length = len(textline)
                self.text_widget.insert(END, textline + '\n')
                self.set_tags(textline, line)
            self.text_widget.configure(
                height=HEIGHT_TEXT, width=line_length+10)
            # self.text_widget.config(state=DISABLED)
            # --------------------------------------------------------------
            self._builttext_window.protocol(
                WM_DELETE_WINDOW, self._wm_deletion_window)
            self._builttext_window.lift
            self._builttext_window.mainloop()
            destroy_widget(self._builttext_window)
        else:
            MessageBoxInfo(
                title=title,
                message=get_message(
                    MESSAGE_TEXT, 'THREAD', self.window_id
                    )
                )

    def _wm_deletion_window(self):

        self.field = None
        self.quit_widget()

    def quit_widget(self):

        quit_widget(self._builttext_window)

    def set_tags(self, textline, line):
        pass

    def destroy_widget(self, text):
        # insert text checking code
        return False


class BuiltPandasBox(Frame):
    """
    see:
    Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education. Journal of Open
    Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
    and
    https://readthedocs.org/projects/pandastable/downloads/pdf/latest/


    TOP-LEVEL-WINDOW        Shows Dataframe

    PARAMETER:
        dataframe           DataFrame object or Dataframe data with dataframe method
        dataframe_sum       total sum column_names
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        message             shown in header of pandastable
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
        mode                EDIT_ROW:    banking left_side menu(edit rows),
                                         standard column menu.
                                         no right side toolbar,
                                         decimals without currency_symbol
                            CURRENCY_SIGN:
                                           standard left_side menu,
                                           standard column menu,
                                           no right side toolbar,
                                           decimals with currency_symbol
                            NO_CURRENCY_SIGN:
                                              standard left_side menu,
                                              standard column menu,
                                              no right side toolbar,
                                              decimals without currency_symbol
                            NUMERIC:
                                        switch between decimals with or without currency_symbol (ToolbarSwitch.toolbar_switch)
                                        ToolbarSwitch.toolbar_switch False:
                                                 standard left_side menu,
                                                 standard column menu,
                                                 no right side toolbar,
                                                 decimals with currency_symbol
                                        ToolbarSwitch.toolbar_switch True:
                                                 standard left_side menu,
                                                 standard column menu,
                                                 right side toolbar,
                                                 decimals without currency_symbol
        instant_plotting    True:        Shows instant plotting of table of the whole dataframe
        cellwidth_resizeable     True:    F1-, F2, F3 keys change cellwidth (standard)
    """
    RIGHT = ['int', 'smallint', 'decimal', 'bigint', TYP_DECIMAL]
    COLUMN_CURRENCY = {declm.DB_amount: declm.DB_amount_currency,
                       declm.DB_closing_balance: declm.DB_closing_currency,
                       declm.DB_opening_balance: declm.DB_opening_currency,
                       declm.DB_price: declm.DB_price_currency,
                       declm.DB_posted_amount: declm.DB_amount_currency,
                       declm.DB_acquisition_amount: declm.DB_amount_currency,
                       declm.DB_market_price: declm.DB_price_currency,
                       declm.DB_acquisition_price: declm.DB_price_currency,
                       declm.DB_total_amount: declm.DB_amount_currency,
                       declm.DB_total_amount_portfolio: declm.DB_amount_currency
                       }
    CELLWIDTH = 80

    re_decimal = re.compile(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*')
    re_negative = re.compile('-')

    def __init__(self, title='MESSAGE_TITLE', root=None,
                 dataframe=None, dataframe_sum=[], dataframe_typ=TYP_ALPHANUMERIC,
                 message=None, mode=NO_CURRENCY_SIGN, instant_plotting=False,
                 cellwidth_resizeable=True, selected_row=0
                 ):

        self.title = title
        self.window_id = self.__class__.__name__
        self.button_state = ''
        if not self.title.startswith(connectionresult.database.upper()):
            self.title = ' '.join([connectionresult.database.upper(), self.title])
        self.repo = Repository()
        # Changes must be made in the duplicate (deepcopy) of the DataFrame, if a DataFrame is passed,
        # because Pandastable saves changes in the passed original
        # e.g. added summary rows would be added to the DataFrame with each run
        # Only the NUMERIC mode switches between decimals with or without currency symbols
        if isinstance(dataframe, DataFrame) and mode == NUMERIC:
            self.dataframe = dataframe.copy(deep=True)
        else:
            self.dataframe = dataframe
        self.dataframe_sum = dataframe_sum
        self.dataframe_typ = dataframe_typ
        self.mode = mode
        self.cellwidth_resizeable = cellwidth_resizeable
        self.selected_row = selected_row
        self.dataframe_window = Toplevel()
        self.dataframe_window.bind_all("<F1>", self._increase_col_width)
        self.dataframe_window.bind_all("<F2>", self._decrease_col_width)
        self.dataframe_window.bind_all("<F3>", self._standard_col_width)
        self.dataframe_window.title(self.title)
        self.create_dataframe()
        if not hasattr(self, "abort"):
            self.create_dataframe_append_sum()
            if message is not None:
                message_widget = Label(self.dataframe_window,
                                       text=message, foreground='RED',
                                       font=('Arial', 10, 'bold'))
                message_widget.pack(side=TOP, anchor=W)
            Frame.__init__(self)
            self.frame_widget = Frame(self.dataframe_window)
            self.frame_widget.pack(side=BOTTOM, fill=BOTH, expand=True)
            self.selected_row_dict = {}  # selected pandastable row
            if not isinstance(self.dataframe, DataFrame):
                quit_widget(self.dataframe_window)
                return
            if mode == EDIT_ROW:
                self.pandas_table = TableRowEdit(
                    title=self.title, root=self, parent=self.frame_widget, dataframe=self.dataframe)
            else:
                self.pandas_table = Table(
                    title=self.title, root=self, parent=self.frame_widget, dataframe=self.dataframe,
                    mode=mode, instant_plotting=instant_plotting)
            self.pandas_table.fontsize = FONTSIZE
            self.font = Font(family=self.pandas_table.font,
                             size=self.pandas_table.fontsize)
            if instant_plotting:
                if self.dataframe_window not in MyPlotViewer.WINDOW:
                    MyPlotViewer.WINDOW.append(self.dataframe_window)  # used to close table
                self.set_geometry()
                self.pandas_table.plotSelected()
                self.dataframe_window.withdraw()
                self.button_state = self.pandas_table.pf.button_state
            else:
                self.column_width = self._get_col_width()
                self.pandas_table.set_defaults()
                self.pandas_table.showindex = True
                self.set_geometry()
                self._set_options()
                self.set_properties()
                self.set_column_format()
                self.set_row_format()
                self.pandas_table.show()
                self.first_scroll_page_row = 0
                self._move_to_selection()
                self.pandas_table.yview_scroll(10, "units")
                self.pandas_table.rowheader.bind('<Button-1>', self._handle_click)
                self.pandas_table.rowheader.bind('<Configure>', self._on_scroll)
            # --------------------------------------------------------------
            self.dataframe_window.protocol(
                WM_DELETE_WINDOW, self._wm_deletion_window)
            self.dataframe_window.mainloop()
        destroy_widget(self.dataframe_window)

    def _handle_click(self, event):
        """
        Get selected Row Number (start with 0) and Row_Ddata
        """
        self.selected_row = self.pandas_table.get_row_clicked(
            event)  # starts with 0
        self.processing()

    def _move_to_selection(self):

        self.pandas_table.redraw()
        last_row_index = self.pandas_table.model.df.shape[0] - 1
        if self.selected_row > last_row_index:
            self.selected_row = last_row_index
        self.pandas_table.movetoSelection(row=self.selected_row)

    def _on_scroll(self, event):
        '''
        Pandastable Bug:
         When scrollin to the last page of a table with vertical scroll,
         only the following rows are displayed but not the previous rows.
         Therefore, the last line of the second to last scroll page is positioned.
        '''
        canvas_height = self.pandas_table.winfo_height(
        )  # Height of the canvas showing the table
        # Approximate row height (default is 20, but may vary)
        row_height = self.pandas_table.rowheight
        visible_rows = canvas_height // row_height  # Number of visible rows
        if self.selected_row >= len(self.pandas_table.model.df) - visible_rows:
            # positioning to last row of the penultimate scrolling page
            self.selected_row = len(
                self.pandas_table.model.df) - visible_rows - 1
            self._move_to_selection()

    def _standard_col_width(self, event):

        if not self.cellwidth_resizeable:
            return
        columns = self.dataframe.columns.tolist()
        standard_column_width = 0
        for dataframe_column in columns:
            column = dataframe_column
            if isinstance(dataframe_column, tuple):  # multi level column_name
                for i in range(len(dataframe_column)):
                    if len(column) < len(dataframe_column[i]):
                        column = dataframe_column[i]
            # max length of column names
            column_width = self.font.measure(column)
            if column_width > standard_column_width:
                standard_column_width = column_width
        self._save_col_width(standard_column_width + self.font.measure('A'))
        self.quit_widget()

    def _increase_col_width(self, event):

        if not self.cellwidth_resizeable:
            return
        if self._get_col_width() < 200:
            self.column_width = self.column_width + 20
            self._save_col_width(self.column_width)
        self.quit_widget()

    def _decrease_col_width(self, event):

        if not self.cellwidth_resizeable:
            return
        if self._get_col_width() > 30:
            self.column_width = self.column_width - 20
            self._save_col_width(self.column_width)
        self.quit_widget()

    def _save_col_width(self, column_width):

        self.column_width = column_width
        self.repo.update_geometry_width_of_caller(column_width, self.window_id)
 
    def _get_col_width(self):

        self.column_width = self.pandas_table.maxcellwidth / 2
        column_width = self.repo.select_geometry_width_of_caller(self.window_id)
        if column_width:
            self.column_width = column_width
        return self.column_width

    def _geometry_put(self, window):
        """
        put window geometry
        """
        if window.winfo_exists():
            try:
                width = window.winfo_width()
                height = window.winfo_height()
                geometry = ''.join([str(width), 'x', str(
                    height), '+', str(window.winfo_x()), '+', str(window.winfo_y())])
                self.repo.replace_geometry(self.window_id, geometry, self.column_width)
            except AttributeError:
                pass  # column_with used in subclasses

    def set_geometry(self):

        geometry = self.repo.select_geometry_of_caller(self.window_id)
        if geometry:
            geometry = geometry.replace('x', ' ')
            geometry = geometry.replace('+', ' ')
            geometry_values = geometry.split()
            if len(geometry_values) == 4:
                height = self._get_pandastable_height()
                if height != geometry_values[1]:
                    # geometry = >width<x>height<+>x-position<+>y-position<
                    geometry = ''.join(
                        [geometry_values[0], 'x', str(height), '+', geometry_values[2], '+', geometry_values[3]])
                    self.repo.update_geometry_of_caller(geometry, self.window_id)
        else:
            cellwidth = self.pandas_table.maxcellwidth / 2
            width = int(cellwidth * (self.pandas_table.cols + 1))
            window_width = self.dataframe_window.winfo_screenwidth()
            if width > window_width:
                width = window_width - 10
            height = self._get_pandastable_height()
            geometry = ''.join([str(width), 'x', str(height),
                               BUILTPANDASBOX_WINDOW_POSITION])
        self.dataframe_window.geometry(geometry)

    def _get_pandastable_height(self):

        height = int((self.pandas_table.rows + 8) *
                     (self.pandas_table.rowheight + 3))
        screenheight = self.dataframe_window.winfo_screenheight()
        if height > screenheight:
            height = screenheight - 150
        if self.mode == NUMERIC and ToolbarSwitch.toolbar_switch:
            if height < 300:
                height = 300
        return height

    def _wm_deletion_window(self):

        self._geometry_put(self.dataframe_window)
        self.button_state = WM_DELETE_WINDOW
        self.quit_widget()

    def quit_widget(self):

        self._geometry_put(self.dataframe_window)
        if stack()[1].function == 'del_row':
            self.selected_row = 0
        else:
            self.selected_row = self.pandas_table.getSelectedRow()
        quit_widget(self.dataframe_window)

    def insert_row(self, row_dict):
        self.df = self.df._append(row_dict, ignore_index=True)
        self.table.model.df = self.df
        self.table.redraw()

    def get_selected_row(self):
        """
        Get dict of selected Row of Pandastable
        """
        selected_row = self.pandas_table.getSelectedRow()
        try:
            dataframe_row = self.pandas_table.model.df.iloc[[selected_row]]
            row_dict = dataframe_row.iloc[[0]].to_dict('records')[0]
            keys = list(row_dict.keys()).copy()
            for _key in keys:
                row_dict[_key.lower()] = row_dict.pop(_key)
            return row_dict
        except Exception:
            return {}

    def create_dataframe(self):

        pass

    def create_dataframe_append_sum(self):
        """
        Append Sum Row for columns in self.dataframe_sum
        """
        self.dataframe_append_sum()

    def dataframe_append_sum(self,):
        """
        Append Sum Row for columns in dataframe_sum
        """
        sum_row = {}
        for column in self.dataframe_sum:
            self.dataframe[column] = self.dataframe[column].apply(
                lambda x: Amount(x).to_decimal())
            if column in self.dataframe.columns:
                sum_row[column] = to_numeric(
                    self.dataframe[column]).sum()
                sum_row[column] = dec2.convert(sum_row[column])
        if sum_row != {}:
            sum_row[declm.DB_price_currency] = EURO
            sum_row[declm.DB_amount_currency] = EURO
            sum_row[declm.DB_currency] = EURO
            self.dataframe.loc[len(self.dataframe.index)] = sum_row

    def processing(self):

        pass

    def set_properties(self):

        pass

    def set_row_format(self):

        pass

    def set_column_format(self):
        """
        Pandas Table Colummn Format properties:
            Tuple (align, currency, places, color, typ)
                align             --> alignment
                currency          --> currency or column_name of currencies (see BuiltPandasBox.COLUMN_CURRENCY)
                places            --> decimal places
                color             --> background color of negative numbers
                typ               --> data type
        """

        standard_column_width = 0
        columns = self.dataframe.columns.tolist()
        for dataframe_column in columns:
            column = dataframe_column
            # Include column heading for width calculation, if cellwidth unchangeable by f_keys
            if not self.cellwidth_resizeable:
                if isinstance(dataframe_column, tuple):  # multi level column_name
                    for i in range(len(dataframe_column)):
                        if len(column) < len(dataframe_column[i]):
                            column = dataframe_column[i]
                # max length of column names
                font = Font(family=self.pandas_table.font,
                            size=self.pandas_table.fontsize)
                column_width = font.measure(column)
                if column_width > standard_column_width:
                    standard_column_width = column_width
                self.column_width = standard_column_width + \
                    font.measure('A')
            ######
            column_levels = False
            if isinstance(dataframe_column, tuple):  # multi level column_name
                column = dataframe_column[0]
            # create format tuple of pandastable column
            if (column in FN_COLUMNS_EURO):
                align = E
                currency = EURO
                places = 2
                color = COLOR_NEGATIVE
                typ = TYP_DECIMAL
            elif (column in FN_COLUMNS_PERCENT):
                align = E
                currency = '%'
                places = 2
                color = COLOR_NEGATIVE
                typ = TYP_DECIMAL
            elif column in DATABASE_FIELDS_PROPERTIES:
                _, places, typ,  _, _ = DATABASE_FIELDS_PROPERTIES[column]
                if typ in BuiltPandasBox.RIGHT:
                    align = E
                else:
                    align = W
                if column in BuiltPandasBox.COLUMN_CURRENCY:
                    if column_levels:
                        currency = EURO
                    else:
                        currency = BuiltPandasBox.COLUMN_CURRENCY[column]
                    color = COLOR_NEGATIVE
                else:
                    currency = ''
                    color = ''
                if typ == DATABASE_TYP_DECIMAL:
                    typ = TYP_DECIMAL
            elif self.dataframe_typ == TYP_DECIMAL:
                align = E
                currency = EURO
                places = 2
                color = COLOR_NEGATIVE
                typ = TYP_DECIMAL
            else:
                align = W
                currency = ''
                places = ''
                color = ''
                typ = TYP_ALPHANUMERIC
            # format dataframe column
            column = dataframe_column  # in case of multi-level column name
            self.color_columns(column)
            if typ == TYP_DECIMAL:
                if color:
                    self.dataframe[column]
                    self.dataframe[column] = self.dataframe[column].apply(
                        lambda x: Amount(x).to_decimal())
                    self.dataframe[column] = to_numeric(
                        self.dataframe[column], errors='coerce')
                    self.pandas_table.setColorByMask(
                        column, self.dataframe[column] < 0, color)
                if self.mode == NUMERIC and ToolbarSwitch.toolbar_switch or self.mode in [NO_CURRENCY_SIGN, EDIT_ROW]:
                    if places:
                        self.dataframe[column] = self.dataframe[column].apply(
                            lambda x: x if isinstance(x, str) else dec2.convert(x))
                else:
                    # mode:  CURRENCY_SIGN, formatted NUMERIC mode
                    if currency in self.dataframe.columns.tolist():
                        self.dataframe[column] = self.dataframe[[column, currency]].apply(
                            lambda x: Amount(*x, places), axis=1)
                    elif currency in [EURO, '%']:
                        if places:
                            self.dataframe[column] = self.dataframe[column].apply(
                                lambda x: Amount(x, currency, places))
                        else:
                            self.dataframe[column] = self.dataframe[column].apply(
                                lambda x: Amount(x, currency))
                    else:
                        if currency == '':  # e.g.pieces
                            self.dataframe[column] = self.dataframe[column].apply(
                                lambda x: Amount(x, currency))
                        else:
                            self.dataframe[column] = self.dataframe[column].apply(
                                lambda x: Amount(x))
            if align in [E, W]:
                self.pandas_table.columnformats['alignment'][column] = align
        self.pandas_table.cellwidth = self.column_width
        self.drop_currencies()

    def drop_currencies(self):

        self.dataframe = self.dataframe.drop(
            axis=1, index=None, errors='ignore',
            columns=[declm.DB_currency, declm.DB_status, declm.DB_opening_currency, declm.DB_opening_currency,
                     declm.DB_closing_currency, declm.DB_closing_currency, declm.DB_amount_currency,
                     declm.DB_price_currency
                     ]
        )
        self.dataframe = self.dataframe.fillna(value='')

    def color_columns(self, column):

        pass

    def _set_options(self, align=E):
        options = {'align': align,
                   'cellbackgr': '#F4F4F3',
                   'cellwidth': self.column_width,
                   'thousandseparator': '',
                   'font': 'Arial',
                   'fontsize': 8,
                   'fontstyle': '',
                   'grid_color': '#ABB1AD',
                   'linewidth': 1,
                   'rowheight': 22,
                   'rowselectedcolor': '#E4DED4',
                   'textcolor': 'blue'
                   }
        config.apply_options(options, self.pandas_table)

    def excel_writer(self, sheet_name=None):

        if sheet_name is None:
            sheet_name = self.title
        for column in self.dataframe.columns:
            if column in DATABASE_FIELDS_PROPERTIES.keys() and DATABASE_FIELDS_PROPERTIES[column].typ == TYP_DECIMAL:
                self.dataframe[column] = to_numeric(
                    self.dataframe[column], errors='ignore')
        file_dialogue = FileDialogue(title=self.title, create_file=True)
        filename = file_dialogue.filename.removesuffix('.xlsx')
        with ExcelWriter(filename + ".xlsx", mode='w') as writer:
            self.dataframe.to_excel(writer, sheet_name=sheet_name[:30])
        MessageBoxInfo(
            title=self.title,
            message=get_message(
                MESSAGE_TEXT, 'EXCEL', file_dialogue.filename
                )
            )

    def create_combo_list(self, table, field_name, from_date=date.today()-timedelta(weeks=104), date_name=declm.DB_price_date):
        """
        returns dict  {field_name: field_value_list} in table of last year
        """
        combo_list = []
        if from_date:
            period = (from_date, date.today())
            select_field_values = self.repo.get_field_values_of_table_in_period(table, field_name, date_name, period)
        else:
            select_field_values = self.repo.get_field_values_of_table(table, field_name)
        if select_field_values:
            combo_list = list(sum(select_field_values, ()))
        while None in combo_list:
            combo_list.remove(None)
        return {field_name: sorted(combo_list)}
