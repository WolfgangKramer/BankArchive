"""
Created on 28.01.2020
__updated__ = "2023-11-29"
@author: Wolfgang Kramer
"""


from collections import namedtuple
from datetime import date
import inspect
import re
import sys
from threading import current_thread, main_thread
from tkinter import (
    Tk, TclError, ttk, messagebox, Toplevel, StringVar, IntVar, INSERT, Text,
    W, E, filedialog, BOTH, BOTTOM, TOP, HORIZONTAL,
    END, DISABLED)
from tkinter.ttk import (
    Entry, Frame, Label, Radiobutton, Checkbutton, Scrollbar, Progressbar)

from keyboard import add_hotkey
from pandas import to_numeric
from pandastable import setGeometry, config, TableModel
from tkcalendar import DateEntry

from banking.declarations import (
    DB_currency, EURO,
    HEIGHT_TEXT, HOLDING_T,
    Caller, Informations,
    INFORMATION, ERROR,
    KEY_GEOMETRY, KEY_PIN,
    MESSAGE_TEXT, MESSAGE_TITLE,
    OPERATORS,
    PRICES,
    WIDTH_TEXT, DB_status,
    BANK_MARIADB_INI,
    DB_opening_balance, DB_opening_currency, DB_price_currency, DB_posted_amount,
    DB_acquisition_amount, DB_market_price,
    DB_acquisition_price, DB_total_amount,
    DB_total_amount_portfolio, DB_amount, DB_amount_currency, DB_closing_balance,
    DB_closing_currency, DB_price, FN_COLUMNS_EURO, FN_COLUMNS_PERCENT
)
from banking.pandastable_extension import Table
from banking.utils import Amount, shelve_get_key, shelve_put_key, Calculate, list_positioning


ENTRY = 'Entry'
COMBO = 'ComboBox'
BUTTON_APPEND = 'APPEND'
BUTTON_ALPHA_VANTAGE = 'ALPHA_VANTAGE'
BUTTON_SAVE = 'SAVE'
BUTTON_SAVE_STANDARD = 'SAVE as Standard'
BUTTON_SELECT_ALL = 'SELECT All'
BUTTON_SELECT = 'SELECT'
BUTTON_STANDARD = 'STANDARD'
BUTTON_DELETE = 'DELETE'
BUTTON_DELETE_ALL = 'DELETE ALL'
BUTTON_CREATE = 'CREATE'
BUTTON_FIELDLIST = 'FIELDLIST'
BUTTON_PRINT = 'PRINT'
BUTTON_PREVIOUS = 'PREVIOUS'
BUTTON_REPLACE = 'REPLACE'
BUTTON_NEXT = 'NEXT'
BUTTON_NEW = 'NEW'
BUTTON_RESTORE = 'RESTORE'
BUTTON_OK = 'OK'
BUTTON_STORE = 'STORE'
BUTTON_UPDATE = 'UPDATE'
BUTTON_CHART = 'CHART'
BUTTON_DATA = 'DATA'
BUTTON_QUIT = 'QUIT'
BUTTON_QUIT_ALL = 'QUIT ALL'

COLOR_NEGATIVE = 'darkorange'
COLOR_HOLDING = 'yellow'
COLUMN_FORMATS_LEFT = 'LEFT'
COLUMN_FORMATS_RIGHT = 'RIGHT'
COLUMN_FORMATS_CURRENCY = 'CURRENCY'
COLUMN_FORMATS_COLOR_NEGATIVE = 'COLOR_NEGATIVE'
COLUMN_FORMATS_TYP_DECIMAL = 'decimal'
COLUMN_FORMATS_TYP_VARCHAR = 'varchar'
STANDARD = 'STANDARD'
FORMAT_FIXED = 'F'
FORMAT_VARIABLE = 'V'
TYP_ALPHANUMERIC = 'X'
TYP_DECIMAL = 'D'
TYP_DATE = 'DAT'
ROOT_WINDOW_POSITION = '+100+100'
BUILBOXT_WINDOW_POSITION = '+200+200'
BUILTEXT_WINDOW_POSITION = '+400+400'
WIDTH_WIDGET = 70
PANDAS_NAME_SHOW = 'SHOW'
PANDAS_NAME_ROW = 'ROW'

WM_DELETE_WINDOW = 'WM_DELETE_WINDOW'
LIGHTBLUE = 'LIGHTBLUE'
UNDEFINED = 'UNDEFINED'
FONTSIZE = 8

FIELDS_HOLDING = {}
FIELDS_STATEMENT = {}
FIELDS_TRANSACTION = {}
FIELDS_BANKIDENTIFIER = {}
FIELDS_SERVER = {}
FIELDS_ISIN = {}
FIELDS_PRICES = {}

re_amount = re.compile(r"\d+\.\d+")
re_amount_int = re.compile(r"\d+")
dec2 = Calculate(places=2)


def destroy_widget(widget):
    '''
    exit and destroys windows or
    destroys widget  and rest of root window will be left
    don't stop the tcl/tk interpreter
    '''
    try:
        widget.destroy()
    except TclError:
        pass


def quit_widget(widget):
    '''
    do not destroy widgets but it exits the tcl/tk interpreter i.e it stops the mainloop()
    '''
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


def field_validation(name, field_def):
    """
        Returns footer text
    """
    if field_def.mandatory and field_def.widget.get() == '':
        footer = MESSAGE_TEXT['MANDATORY'].format(name)
        return footer
    if field_def.widget.get():
        if field_def.lformat == FORMAT_FIXED:
            if len(field_def.widget.get()) != field_def.length:
                return MESSAGE_TEXT['FIXED'].format(name, field_def.length)
        else:
            if len(field_def.widget.get()) > field_def.length:
                return MESSAGE_TEXT['LENGTH'].format(name, field_def.length)
            elif len(field_def.widget.get()) < field_def.min_length:
                return MESSAGE_TEXT['MIN_LENGTH'].format(
                    name, field_def.min_length)
                return footer
        if field_def.typ == TYP_DECIMAL:
            _decimal = field_def.widget.get().replace(',', '.')
            field_def.widget.delete(0, END)
            field_def.widget.insert(0, _decimal)
            if (re_amount.fullmatch(field_def.widget.get()) is None and
                    re_amount_int.fullmatch(field_def.widget.get()) is None):
                return MESSAGE_TEXT['DECIMAL'].format(name)
        if field_def.typ == TYP_DATE:
            if len(field_def.widget.get()) == 10:
                date_ = field_def.widget.get()[0:10]
                try:
                    day = int(date_.split('-')[2])
                    month = int(date_.split('-')[1])
                    year = int(date_.split('-')[0])
                    date_ = date(year, month, day)
                except (ValueError, EOFError, IndexError):
                    return MESSAGE_TEXT['DATE'].format(name)
            else:
                return MESSAGE_TEXT['DATE'].format(name)
        if (field_def.allowed_values
                and field_def.widget.get() not in field_def.allowed_values):
            return MESSAGE_TEXT['NOTALLOWED'].format(
                name, field_def.allowed_values)
    return ''


def geometry_get(standard=BUILBOXT_WINDOW_POSITION):
    """
    get window geometry
    """
    caller = Caller.caller
    GEOMETRY_DICT = shelve_get_key(BANK_MARIADB_INI, KEY_GEOMETRY)
    if GEOMETRY_DICT is None:
        GEOMETRY_DICT = {}
    if caller not in GEOMETRY_DICT:
        GEOMETRY_DICT[caller] = standard
        shelve_put_key(BANK_MARIADB_INI, (KEY_GEOMETRY, GEOMETRY_DICT))
    return GEOMETRY_DICT[caller]


def geometry_put(window):
    """
    put window geometry
    """
    if window.winfo_exists():
        caller = Caller.caller
        geometry = geometry_string(window)
        GEOMETRY_DICT = shelve_get_key(
            BANK_MARIADB_INI, KEY_GEOMETRY, none=False)
        if caller not in GEOMETRY_DICT or GEOMETRY_DICT[caller] != geometry:
            GEOMETRY_DICT[caller] = geometry
            shelve_put_key(BANK_MARIADB_INI, (KEY_GEOMETRY, GEOMETRY_DICT))


def geometry_string(window):
    """
    Generate geometry string
    """
    geometry = '+' + str(window.winfo_x()) + '+' + str(window.winfo_y())
    return geometry


def extend_message_len(title, message):
    '''
    returns possibly extended message 
    '''
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

    def __init__(self, title=MESSAGE_TITLE,
                 filetypes=(("csv files", "*.csv"), ("all files", "*.*"))):

        window = Tk()
        window.withdraw()
        window.title(title)
        self.filename = filedialog.askopenfilename(
            initialdir="/",
            title=title,
            filetypes=filetypes)


class MessageBoxInfo():
    """
    bank                  Instance of Class InitBank gathering fints_codes in ClassVar
    information_storage   Instance of Class Informations gathering messages in ClassVar informations
    """

    def __init__(self, message=None, title=MESSAGE_TITLE, bank=None, information_storage=None, information=INFORMATION):

        # check if its not the main thread, avoid Tk() or ..
        if not(current_thread() is main_thread()) or information_storage:
            if information_storage == PRICES:  # messages downloading prices threading
                message = message.replace('\n', ' // ')
                Informations.prices_informations = ' '.join(
                    [Informations.prices_informations, '\n' + information, message])
            elif information_storage == HOLDING_T:  # messages downloading prices threading
                message = message.replace('\n', ' // ')
                Informations.holding_t_informations = ' '.join(
                    [Informations.holding_t_informations, '\n' + information, message])
            else:
                if bank:  # messages downloading bank threading
                    message = message.replace('\n', ' // ')
                    bank.message_texts = ' '.join(
                        [bank.message_texts, '\n' + information, message])
                else:
                    print(message)
        else:
            window = Tk()
            window.withdraw()
            message = extend_message_len(title, message)
            window.title(title)
            messagebox.showinfo(title=title, message=message,)
            destroy_widget(window)


class MessageBoxError():

    def __init__(self, message=None, title=MESSAGE_TITLE, bank=None):

        # check if its not the main thread avoid Tk()
        if not(current_thread() is main_thread()):
            if bank:
                message = message.replace('\n', ' // ')
                bank.message_texts = ' '.join(
                    [bank.message_texts, '\n' + INFORMATION, message])
            else:
                Informations.informations = ' \n{} {} {} {}'.format(
                    ERROR, '', '', message)
        else:
            window = Tk()
            window.withdraw()
            message = extend_message_len(title, message)
            window.title(title)
            messagebox.showerror(title=title, message=message)
            MessageBoxTermination()


class MessageBoxTermination(MessageBoxInfo):

    def __init__(self, info='', bank=None):

        message = MESSAGE_TEXT['TERMINATION'] + ' '
        if info:
            message = message + info
        for stack_item in inspect.stack()[2:]:
            filename = stack_item[1]
            line = stack_item[2]
            method = stack_item[3]
            message = (
                message + '\n' + filename + '\n' + 'LINE:   ' +
                str(line) + '   METHOD: ' + method
            )
        # check if its not the main thread avoid Tk()
        if not(current_thread() is main_thread()):
            if bank:
                bank.message_texts = ' '.join([bank.message_texts, '\n' + ERROR, bank.bank_name,
                                               bank.iban, message])
            else:
                Informations.informations = ' \n{} {} {} {}'.format(
                    ERROR, bank.bank_name, bank.iban, message)
        else:
            super().__init__(message=message, title=MESSAGE_TITLE, bank=bank)
            sys.exit()


class MessageBoxAsk():

    def __init__(self, message=None, title=MESSAGE_TITLE):

        window = Tk()
        window.withdraw()
        window.title(title)
        self.result = messagebox.askyesno(
            title=title, message=message, default='no')
        destroy_widget(window)


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

    >definiton<         String      Defintion (Entry, Combobox)
    >name<              String      Description of EntryField
    >format<            String      Fixed ('F') or variable ('V')
                                    EntryField Length (max. Length see >Length<)
    >length<            Integer     Max. Length of EntryField
    >typ>               String      Type ('X'), ('D') Decimal, ('DAT') Date
    >min_length<        Integer     Min. Length of EntryField
    >mandatory<         Boolean     True: Input is Mandatory
    >protected<         Boolean     True: No Input allowed
    >selected<          Boolean     True: User selects an element
    >readonly<          Boolean     True: Only selection allowed
    >allowed_values<    List        List of Allowed Values (optional)
    >default_value<                 Default Value (optional)
    >combo_values<      List        List of ComboBox Values;
                                    generates ComboBoxEntryField if not empty
    >combo_positioning< Boolean     True: Positioning  while enter. False allows input of values outside of >combo_values<
    >validate<          String      None or ALL (validate Option)
    >textvariable<                  None or StringVar()
    >focus_in<          Boolean     True: Action if Field got Focus
    >focus_out<         Boolean     True: Action if Field lost Focus
    """

    def __init__(self, definition=ENTRY,
                 name=UNDEFINED, lformat=FORMAT_VARIABLE, length=0, typ=TYP_ALPHANUMERIC,
                 min_length=0, mandatory=True, protected=False, readonly=False, allowed_values=[],
                 default_value='', combo_values=[], combo_positioning=True, focus_out=False, focus_in=False,
                 upper=False, selected=False):

        self.definition = definition
        self.name = name
        self.lformat = lformat
        self.length = length
        self.typ = typ
        self.min_length = min_length
        self.mandatory = mandatory
        self.protected = protected
        self.readonly = readonly
        self.allowed_values = []
        for item in allowed_values:
            self.allowed_values.append(str(item))
        self.default_value = default_value
        self.selected = selected
        self.combo_values = []
        for item in combo_values:
            self.combo_values.append(str(item))
        self.combo_positioning = combo_positioning
        self.focus_out = focus_out
        self.focus_in = focus_in
        self.upper = upper
        self.widget = None
        self.textvar = None

    @property
    def definition(self):
        return self._definition

    @definition.setter
    def definition(self, value):
        self._definition = value
        if self._definition not in [ENTRY, COMBO]:
            MessageBoxTermination(
                info='Field Definition Definiton not ENTRY (EntryField) or COMBO (ComboBoxField')

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
            self, title=MESSAGE_TITLE, header=MESSAGE_TEXT['ENTRY'], columnspan=2,
            button1_text=BUTTON_OK, button2_text=None, button3_text=None,
            button4_text=None, button5_text=None, button6_text=None,
            width=WIDTH_WIDGET, grab=True):

        Caller.caller = self.__class__.__name__
        self.button_state = None
        if current_thread() is main_thread():
            self._header = header
            self._columnspan = columnspan
            self._button1_text = button1_text
            self._button2_text = button2_text
            self._button3_text = button3_text
            self._button4_text = button4_text
            self._button5_text = button5_text
            self._button6_text = button6_text
            self._width = width
            self._footer = ''
            self._box_window = Toplevel()
            if grab:
                self._box_window.grab_set()
            self._box_window.title(title)

            # -------------------- the message widget -------------------------
            self._row = 1
            self._create_header()
            # --------- entry ----------------------------------------------
            self._create_fields()
            # ------------------ Message -------------------------------
            self._create_footer()
            # ------------------ Buttons -------------------------------
            self._create_buttons()
            # ------------------ Keyboard Events ------------------------------
            self._keyboard()
            # --------------------------------------------------------------
            geometry = geometry_get()
            self._box_window.geometry(geometry)
            self._box_window.protocol(
                WM_DELETE_WINDOW, self._wm_deletion_window)
            self._box_window.mainloop()
            destroy_widget(self._box_window)
        else:
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['THREAD'].format(Caller.caller
                                                                              ))

    def _create_header(self):

        if self._header is None:
            self._header = ''
        else:
            list_header = list(self._header)
            line_feed = False
            for idx in range(len(list_header)):
                if idx % 100 == 0 and idx > 0:
                    line_feed = True
                if list_header[idx] == ' ' and line_feed:
                    list_header.insert(idx, '\n')
                    line_feed = False
            self._header = ''.join(list_header)
        header_widget = Label(
            self._box_window, width=self._width, text=self._header)
        header_widget.grid(
            row=self._row, columnspan=self._columnspan, padx='3m', pady='3m')
        self._row += 1

    def _create_footer(self):

        self._footer = StringVar()
        self.message_widget = Label(self._box_window, width=self._width, textvariable=self._footer,
                                    foreground='RED')
        self._footer.set('')
        self.message_widget.grid(
            row=self._row, columnspan=self._columnspan, padx='3m', pady='3m')
        self._row += 1

    def _create_buttons(self):
        button_frame = Frame(self._box_window, width=self._width)
        button_frame.grid(row=self._row, column=1, columnspan=5, sticky=W)
        if self._button1_text is not None:
            button1 = ttk.Button(button_frame, text=self._button1_text)
            button1.grid(row=0, column=0, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button1.bind('<Return>', self._button_1_button1)
            button1.bind('<Button-1>', self._button_1_button1)
        if self._button2_text is not None:
            button2 = ttk.Button(button_frame, text=self._button2_text,)
            button2.grid(row=0, column=1, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button2.bind('<Return>', self._button_1_button2)
            button2.bind('<Button-1>', self._button_1_button2)
        if self._button3_text is not None:
            button3 = ttk.Button(button_frame, text=self._button3_text)
            button3.grid(row=0, column=2, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button3.bind('<Return>', self._button_1_button3)
            button3.bind('<Button-1>', self._button_1_button3)
        if self._button4_text is not None:
            button4 = ttk.Button(button_frame, text=self._button4_text)
            button4.grid(row=0, column=3, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button4.bind('<Return>', self._button_1_button4)
            button4.bind('<Button-1>', self._button_1_button4)
        if self._button5_text is not None:
            button5 = ttk.Button(button_frame, text=self._button5_text)
            button5.grid(row=0, column=4, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button5.bind('<Return>', self._button_1_button5)
            button5.bind('<Button-1>', self._button_1_button5)
        if self._button6_text is not None:
            button6 = ttk.Button(button_frame, text=self._button6_text)
            button6.grid(row=0, column=5, sticky=E, padx='3m',
                         pady='3m', ipadx='2m', ipady='1m')
            button6.bind('<Return>', self._button_1_button6)
            button6.bind('<Button-1>', self._button_1_button6)

    def _create_fields(self):

        pass

    def _wm_deletion_window(self):

        geometry_put(self._box_window)
        self.button_state = WM_DELETE_WINDOW
        self.quit_widget()

    def quit_widget(self):

        geometry_put(self._box_window)
        quit_widget(self._box_window)

    def _button_1_button1(self, event):

        self.button_state = self._button1_text
        if self._footer.get() == '':
            self.quit_widget()

    def _button_1_button2(self, event):

        self.button_state = self._button2_text
        self.quit_widget()

    def _button_1_button3(self, event):

        self.button_state = self._button3_text
        self.quit_widget()

    def _button_1_button4(self, event):

        self.button_state = self._button4_text
        self.quit_widget()

    def _button_1_button5(self, event):

        self.button_state = self._button5_text
        self.quit_widget()

    def _button_1_button6(self, event):

        self.button_state = self._button6_text
        self.quit_widget()

    def _keyboard(self):

        add_hotkey("ctrl+right", self._handle_ctrl_right)
        add_hotkey("ctrl+left", self._handle_ctrl_left)
        add_hotkey("ctrl+up", self._handle_ctrl_up)
        add_hotkey("ctrl+down", self._handle_ctrl_down)

    def _handle_ctrl_right(self):

        pass

    def _handle_ctrl_left(self):

        pass

    def _handle_ctrl_up(self):

        pass

    def _handle_ctrl_down(self):

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
            self, header=MESSAGE_TEXT['RADIOBUTTON'], title=MESSAGE_TITLE,
            button1_text=BUTTON_SAVE, button2_text=BUTTON_RESTORE,
            button3_text=None, button4_text=None, button5_text=None,
            default_value=None,
            radiobutton_dict={'123': 'Description of RadioButton1',
                              '234': 'Description of RadioButton2',
                              '345': 'Description of RadioButton3'}):

        Caller.caller = self.__class__.__name__
        self.field = None
        self._radiobutton_dict = radiobutton_dict
        self._default_value = default_value
        super().__init__(title=title, header=header,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text)

    def _create_fields(self):

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

    def _button_1_button1(self, event):

        self.button_state = self._button1_text
        self.field = self._radiobutton_value.get()
        if self.field == '':
            self._footer.set(MESSAGE_TEXT['SELECT'])
        else:
            self.quit_widget()

    def _button_1_button2(self, event):

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
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_list           list of selected Checkbutton Texts
    """

    def __init__(
            self, header=MESSAGE_TEXT['CHECKBOX'], title=MESSAGE_TITLE, width_widget=WIDTH_WIDGET,
            button1_text=BUTTON_NEXT, button2_text=None,
            button3_text=None, button4_text=BUTTON_SELECT_ALL,
            button5_text=BUTTON_DELETE_ALL,
            default_texts=[],
            checkbutton_texts=['Description of Checkbox1', 'Description of Checkbox2',
                               'Description of Checkbox3']):

        Caller.caller = self.__class__.__name__
        self.field_list = None
        self.default_texts = default_texts
        self.checkbutton_texts = checkbutton_texts
        super().__init__(title=title, header=header,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text)

    def _create_fields(self):

        self._check_vars = []
        row = self._row
        column = 0
        for idx, check_text in enumerate(self.checkbutton_texts):
            self._check_vars.append(IntVar())
            checkbutton = Checkbutton(self._box_window, text=check_text.upper(),
                                      variable=self._check_vars[idx])
            checkbutton.grid(row=row, column=column, padx='3m', sticky=W)
            if (idx + 1) % 15 == 0:
                column += 1
                row = 1
            row += 1
        self._row = 20
        for idx, check_text in enumerate(self.checkbutton_texts):
            if check_text in self.default_texts:
                self._check_vars[idx].set(1)

    def _button_1_button1(self, event):

        self.button_state = self._button1_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
                self._validate()
        self._validate_all()
        # self.field_list = list(set(self.field_list))  # delete duplicates
        self.quit_widget()

    def _button_1_button4(self, event):

        self.button_state = self._button4_text
        for idx, _ in enumerate(self.checkbutton_texts):
            self._check_vars[idx].set(1)

    def _button_1_button5(self, event):

        self.button_state = self._button5_text
        for idx, _ in enumerate(self.checkbutton_texts):
            self._check_vars[idx].set(0)

    def _validate(self):

        pass

    def _validate_all(self):

        pass


class BuiltEnterBox(BuiltBox):
    """
    TOP-LEVEL-WINDOW        EnterBox (Simple Input Fields and ComboList Fields)

    PARAMETER:
        ...
        field_defs          Named Tuple of Field Definitions (see Class FieldDefintion)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary with fieldnames and values (e.g.{name: value,..})
    """
    Field_Names = namedtuple('Field_Names', ['Feld1', 'Feld2'])

    def __init__(self,
                 title=MESSAGE_TITLE, header=MESSAGE_TEXT['ENTRY'],
                 button1_text=BUTTON_SAVE, button2_text=BUTTON_RESTORE, button3_text=None,
                 button4_text=None, button5_text=None, button6_text=None,
                 width=WIDTH_WIDGET, grab=False,
                 field_defs=Field_Names(
                     FieldDefinition(definition=COMBO, name='Feld1', length=8, lformat=FORMAT_FIXED,
                                     selected=True, combo_values=['Wert1', 'Wert2']),
                     FieldDefinition(name='Feld2', length=70,
                                     default_value='Default Wert fuer Feld2')
                 )):

        Caller.caller = self.__class__.__name__
        self.field_dict = None
        self._field_defs = field_defs
        super().__init__(title=title, header=header, width=width, grab=grab,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text, button6_text=button6_text)

    def _create_fields(self):

        # --------- entry ----------------------------------------------
        for field_def in self._field_defs:
            field_def.textvar = StringVar()
            field_def.textvar.set('')
        for field_def in self._field_defs:
            self._field_def = field_def
            if field_def.mandatory:
                widget_lab = Label(self._box_window, width=len(field_def.name) + 5,
                                   text=field_def.name.upper(), anchor=W)
            else:
                widget_lab = Label(self._box_window, width=len(field_def.name) + 5,
                                   text=field_def.name.upper(), anchor=W, style='OPT.TLabel')
            widget_lab.grid(row=self._row, sticky=W, padx='3m', pady='1m')
            if field_def.definition == ENTRY:
                if field_def.typ == TYP_DATE:
                    DateEntry(locale='de_de')
                    widget_entry = DateEntry(self._box_window, width=16, background="magenta3",
                                             textvariable=field_def.textvar,
                                             foreground="white", bd=2, locale='de_de',
                                             date_pattern='yyyy-mm-dd')
                    widget_entry.myId = field_def.name
                else:
                    widget_entry = Entry(self._box_window, width=field_def.length + 4,
                                         textvariable=field_def.textvar)
                    widget_entry.myId = field_def.name
            else:
                widget_entry = ttk.Combobox(self._box_window, values=field_def.combo_values,
                                            width=field_def.length + 4,
                                            textvariable=field_def.textvar)
                widget_entry.myId = field_def.name
                widget_entry.bind('<KeyRelease>', self._combo_position)

                if field_def.selected:
                    widget_entry.bind("<<ComboboxSelected>>",
                                      self._comboboxselected_action)
                if field_def.readonly:
                    widget_entry.config(state='readonly')
            if field_def.focus_out:
                widget_entry.bind("<FocusOut>", self._focus_out_action)
            if field_def.focus_in:
                widget_entry.bind("<FocusIn>", self._focus_in_action)
            if field_def.protected:
                widget_entry.config(state=DISABLED)
            if field_def.name in [KEY_PIN]:
                widget_entry.config(show='*')
            if field_def.default_value is not None:
                field_def.textvar.set(field_def.default_value)
            widget_entry.grid(row=self._row, column=1,
                              columnspan=2, sticky=W, padx='3m', pady='1m')
            self._row += 1
            field_def.widget = widget_entry
        self._field_defs[0].widget.focus_set()

    def _button_1_button1(self, event):

        self.button_state = self._button1_text
        self._validation()
        if self._footer.get() == '':
            self.quit_widget()

    def _button_1_button2(self, event):

        self.button_state = self._button2_text
        for field_def in self._field_defs:
            field_def.widget.delete(0, END)
            if field_def.default_value is not None:
                field_def.widget.insert(0, field_def.default_value)

    def _validation(self):

        self.field_dict = {}
        self._footer.set('')
        for field_def in self._field_defs:
            if not field_def.protected:
                self._footer.set(field_validation(field_def.name, field_def))
                if self._footer.get():
                    break
                self._validation_addon(field_def)
                if self._footer.get():
                    break
            self.field_dict[field_def.name] = field_def.widget.get()
        self._validation_all_addon(self._field_defs)
        for field_def in self._field_defs:
            if field_def.upper:
                self.field_dict[field_def.name] = self.field_dict[field_def.name].upper(
                )

    def _validation_addon(self, field_def):
        """
        more field validations
        """
        pass

    def _validation_all_addon(self, field_defs):
        """
        validations of the fields on the whole
        """
        pass

    def _comboboxselected_action(self, event):

        pass

    def _combo_position(self, event):
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
                _, index = list_positioning(field_attr.combo_values, get)
                event.widget.current(index)
                self._comboboxselected_action(event)
        except Exception:
            pass

    def _focus_out_action(self, event):

        pass

    def _focus_in_action(self, event):

        pass


class BuiltColumnBox(BuiltBox):
    """
    TOP-LEVEL-WINDOW        EnterColumnBox (1-n Entry Rows and 1-n, Entry Columns)

    PARAMETER:
        field_defs          Array of Field Definitions (see Class FieldDefintion)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        array               list of tuples; each row one tuple in list
    """

    def __init__(
            self,
            header='Enter Values: ', title=MESSAGE_TITLE,
            button1_text=BUTTON_OK, button2_text=None, button3_text=None,
            button4_text=None, button5_text=None, width=WIDTH_WIDGET,
            array_def=[
            [FieldDefinition(definition=COMBO,
                             name='COL1', length=8, default_value='ROW 1', protected=True),
             FieldDefinition(definition=COMBO,
                             name='COL2', length=10, mandatory=False, combo_values=OPERATORS,
                             allowed_values=OPERATORS),
             FieldDefinition(name='COL3', lformat='F', length=10)],
            [FieldDefinition(length=8, default_value='ROW 2', protected=True),
             FieldDefinition(definition=COMBO,
                             name='ROW1', length=10, mandatory=False, combo_values=OPERATORS,
                             allowed_values=OPERATORS),
             FieldDefinition(name='ROW2', length=40)]
            ]):

        self.array = []
        self._array_def = array_def
        columnspan = 1
        if self._array_def:
            columnspan = len(self._array_def[0])
        super().__init__(title=title, header=header, columnspan=columnspan, width=width,
                         button1_text=button1_text, button2_text=button2_text,
                         button3_text=button3_text, button4_text=button4_text,
                         button5_text=button5_text)

    def _create_fields(self):

        self._row += 2
        if self._array_def:
            for icx, field_def in enumerate(self._array_def[0]):
                if field_def.name != UNDEFINED:
                    widget_lab = Label(self._box_window, width=int(field_def.length * 0.8 + 2),
                                       text=field_def.name.upper(), anchor=W, style='OPT.TLabel')
                    widget_lab.grid(row=self._row, column=icx,
                                    sticky=W, padx='3m', pady='1m')
        self._row += 2
        # --------- entry ----------------------------------------------
        for row_def in self._array_def:
            for field_def in row_def:
                field_def.textvar = StringVar()
                field_def.textvar.set('')
        for irx, row_def in enumerate(self._array_def):
            for icx, field_def in enumerate(row_def):
                if field_def.protected:
                    widget_lab = Label(self._box_window, width=int(field_def.length * 0.8 + 2),
                                       text=field_def.default_value, anchor=W, style='OPT.TLabel')
                    widget_lab.grid(row=self._row, column=icx,
                                    sticky=W, padx='3m', pady='1m')
                elif field_def.definition == ENTRY:
                    if field_def.typ == TYP_DATE:
                        DateEntry(locale='de_de')
                        widget_entry = DateEntry(self._box_window, width=16, background="magenta3",
                                                 textvariable=field_def.textvar,
                                                 foreground="white", bd=2, locale='de_de',
                                                 date_pattern='yyyy-mm-dd')
                    else:
                        widget_entry = Entry(self._box_window, width=int(field_def.length * 0.8 + 2),
                                             textvariable=field_def.textvar)
                    widget_entry.grid(row=self._row, column=icx,
                                      sticky=W, padx='3m', pady='1m')
                    field_def.widget = widget_entry
                else:
                    widget_entry = ttk.Combobox(self._box_window, values=field_def.combo_values,
                                                width=int(
                                                    field_def.length * 0.8 + 2),
                                                textvariable=field_def.textvar)
                    widget_entry.grid(row=self._row, column=icx,
                                      sticky=W, padx='3m', pady='1m')
                    field_def.widget = widget_entry
                    if field_def.selected:
                        widget_entry.bind(
                            "<<ComboboxSelected>>", self._comboboxselected_action)
                    if field_def.readonly:
                        widget_entry.config(state='readonly')
                if field_def.focus_out:
                    widget_entry.bind("<FocusOut>", self._focus_out_action)
                if field_def.focus_in:
                    widget_entry.bind("<FocusIn>", self._focus_in_action)
                row_def[icx] = field_def
                if field_def.default_value is not None:
                    field_def.textvar.set(field_def.default_value)
            self._array_def[irx] = row_def
            self._row += 1

    def _button_1_button1(self, event):

        self.button_state = self._button1_text
        self._validation()
        if self._footer.get() == '':
            self.quit_widget()

    def _validation(self):

        for row_def in self._array_def:
            for field_def in row_def:
                if field_def.typ == TYP_DECIMAL and not field_def.protected:
                    _decimal = field_def.widget.get().replace(',', '.')
                    field_def.widget.delete(0, END)
                    field_def.widget.insert(0, _decimal)
        self._footer.set('')
        self.array = []
        for irx, row_def in enumerate(self._array_def):
            row = []
            for icx, field_def in enumerate(row_def):
                if not field_def.protected:
                    name = 'Row' + str(irx + 1) + ' / ' + \
                        self._array_def[0][icx].name
                    self._footer.set(field_validation(name, field_def))
                    if self._footer.get():
                        return

                    self._validation_addon(field_def)
                    if self._footer.get():
                        return
                    row.append(field_def.widget.get())
                else:
                    row.append(field_def.default_value)
            self.array.append(tuple(row))

        self._validation_all_addon(self._array_def)

    def _validation_addon(self, field_def):

        pass

    def _validation_all_addon(self, array_def):

        pass

    def _comboboxselected_action(self, event):

        pass

    def _focus_out_action(self, event):

        pass

    def _focus_in_action(self, event):

        pass


class BuiltText(object):
    """
    TOP-LEVEL-WINDOW        TextBox with ScrollBars (Only Output)

    PARAMETER:
        text                String of Text Lines
    """

    def __init__(self, title=MESSAGE_TITLE, header='', text=''):

        Caller.caller = self.__class__.__name__
        if header == Informations.PRICES_INFORMATIONS:
            Informations.prices_informations = ''
        elif header == Informations.BANKDATA_INFORMATIONS:
            Informations.bankdata_informations = ''
        elif header == Informations.HOLDING_T_INFORMATIONS:
            Informations.holding_t_informations = ''
        self._builttext_window = Toplevel()
        self._builttext_window.title(title)
        self._builttext_window.geometry(BUILTEXT_WINDOW_POSITION)
        if self._destroy_widget(text):  # check: discard output
            destroy_widget(self._builttext_window)
            return
        # --------------------------------------------------------------
        if header is not None:
            header = ''
        if header:
            width = len(header) + 5
            if width > WIDTH_TEXT:
                width = WIDTH_TEXT
        else:
            width = WIDTH_TEXT
        height = len(list(enumerate(text.splitlines()))) + 5
        if height > HEIGHT_TEXT:
            height = HEIGHT_TEXT
        self._header = header
        self._header_text = StringVar()
        header_widget = Label(self._builttext_window, width=width,
                              textvariable=self._header_text, style='HDR.TLabel')
        self._header_text.set(self._header)
        header_widget.grid(sticky=W)
        self.text_widget = Text(self._builttext_window, height=height, width=width,
                                font=('Courier', 8), wrap='none')
        self.text_widget.grid(sticky=W)
        self._scroll_x = Scrollbar(self._builttext_window, orient="horizontal",
                                   command=self.text_widget.xview)
        self._scroll_x.grid(sticky="ew")

        scroll_y = Scrollbar(self._builttext_window, orient="vertical",
                             command=self.text_widget.yview)
        scroll_y.grid(row=1, column=1, sticky="ns")

        self.text_widget.configure(yscrollcommand=scroll_y.set,
                                   xscrollcommand=self._handle_scroll_x)
        textlines = text.splitlines()
        for line, textline in enumerate(textlines):
            self.text_widget.insert(END, textline + '\n')
            self._set_tags(textline, line)

        # self.text_widget.config(state=DISABLED)
        # --------------------------------------------------------------
        self._builttext_window.protocol(
            WM_DELETE_WINDOW, self._wm_deletion_window)
        self._builttext_window.lift
        self._builttext_window.mainloop()
        destroy_widget(self._builttext_window)

    def _wm_deletion_window(self):

        self.field = None
        self.quit_widget()

    def quit_widget(self):

        quit_widget(self._builttext_window)

    def _set_tags(self, textline, line):
        pass

    def _destroy_widget(self, text):
        # insert text checking code
        return False

    def _handle_scroll_x(self, x0, x1):
        self._scroll_x.set(x0, x1)
        start, _ = self._scroll_x.get()
        header_start = int(len(self._header) * start)
        self._header_text.set(self._header[header_start:])


class BuiltPandasBox(Frame):
    """
    see:
    Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education. Journal of Open
    Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
    and
    https://readthedocs.org/projects/pandastable/downloads/pdf/latest/


    TOP-LEVE

    L-WINDOW        Shows Dataframe

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
        dataframe_sum       total sum column_names
        plot                True: convert columns to_numeric
    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframed rows (named tuples 'PANDAS_NAME_SHOW'
    """
    RIGHT = ['int', 'smallint', 'decimal', 'bigint']
    COLUMN_CURRENCY = {DB_amount: DB_amount_currency,
                       DB_closing_balance: DB_closing_currency,
                       DB_opening_balance: DB_opening_currency,
                       DB_price: DB_price_currency,
                       DB_posted_amount: DB_amount_currency,
                       DB_acquisition_amount: DB_amount_currency,
                       DB_market_price: DB_price_currency,
                       DB_acquisition_price: DB_price_currency,
                       DB_total_amount: DB_amount_currency,
                       DB_total_amount_portfolio: DB_amount_currency
                       }

    re_decimal = re.compile(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*')
    re_negative = re.compile('-')

    def __init__(self, title='MESSAGE_TITLE',
                 dataframe=None, dataframe_sum=[], dataframe_group=[],
                 message=None, name=PANDAS_NAME_SHOW,
                 root=None, showtoolbar=True, editable=True, edit_rows=False,
                 ):

        Caller.caller = self.__class__.__name__
        self.button_state = None
        self.dataframe = dataframe
        self.dataframe_sum = dataframe_sum
        self.dataframe_group = dataframe_group
        self.column_format = {}
        self.fields = {**FIELDS_HOLDING, **FIELDS_STATEMENT, **FIELDS_TRANSACTION,
                       **FIELDS_BANKIDENTIFIER, **FIELDS_SERVER, **FIELDS_ISIN,
                       **FIELDS_PRICES}
        self._dataframe()
        self._dataframe_group()
        self._dataframe_sum()
        self.name = name
        self.showtoolbar = showtoolbar
        self.selected_row = None
        self.data_table = self.create_data_table()
        self.dataframe_window = Toplevel()
        self.dataframe_window.title(title)
        self.negative = re.compile('-')
        rows, columns = self.dataframe.shape
        framewidth = columns * 100 + 150
        screenwidth = self.dataframe_window.winfo_screenwidth()
        if framewidth > screenwidth:
            framewidth = screenwidth
        frameheight = rows * 30 + 60
        if frameheight < 100:
            frameheight = 100
        screenheight = self.dataframe_window.winfo_screenheight()
        if frameheight > screenheight:
            frameheight = screenheight - 100
        if message is not None:
            message_widget = Label(self.dataframe_window,
                                   text=message, foreground='RED')
            message_widget.pack(side=TOP, anchor=W)
        Frame.__init__(self)
        self.frame_widget = Frame(self.dataframe_window)
        self.frame_widget.pack(side=BOTTOM, fill=BOTH, expand=True)
        self.pandas_table = Table(parent=self.frame_widget, dataframe=self.dataframe, showstatusbar=True,
                                  showtoolbar=showtoolbar, editable=editable, title=title,
                                  root=self, edit_rows=edit_rows)
        self.pandas_table.fontsize = FONTSIZE
        self.pandas_table.set_defaults()
        self.pandas_table.showindex = True
        setGeometry(self.dataframe_window)
        self._set_options()
        self._set_properties()
        self._set_column_format()
        self._set_row_format()
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()
        self.pandas_table.show()
        self.pandas_table.rowheader.bind('<Button-1>', self.handle_click)
        # --------------------------------------------------------------
        self.dataframe_window.protocol(
            WM_DELETE_WINDOW, self._wm_deletion_window)
        self.dataframe_window.mainloop()
        destroy_widget(self.dataframe_window)

    def _wm_deletion_window(self):

        self.button_state = WM_DELETE_WINDOW
        self.quit_widget()

    def quit_widget(self):

        quit_widget(self.dataframe_window)

    def handle_click(self, event):
        """
        Get selected Row Number (start with 0) and Row_Ddata
        """
        self.selected_row = self.pandas_table.get_row_clicked(
            event)  # starts with 0
        self._processing()

    def create_data_table(self):
        """
        Creates Table of named Tuples (Default Tuple Name: name=PANDAS_NAME_SHOW)
        ( e.g. used by Class AcquisitionTable)
        """
        self.data_table = []
        for data_row in self.dataframe.itertuples(index=False, name=self.name):
            """
            index : bool, default True
                If True, return the index as the first element of the tuple.
            name : str or None, default "Pandas"
                The name of the returned namedtuples or None to return regular
                tuples.
            """
            self.data_table.append(data_row)
        return self.data_table

    def _dataframe(self):

        pass

    def _dataframe_group(self):

        pass

    def _dataframe_sum(self):
        """
        Append Total Row
        """
        sum_row = {}
        for column in self.dataframe_sum:
            if column in self.dataframe.columns:
                sum_row[column] = to_numeric(self.dataframe[column]).sum()
                sum_row[column] = dec2.convert(sum_row[column])
        if sum_row != {}:
            sum_row[DB_price_currency] = EURO
            sum_row[DB_amount_currency] = EURO
            sum_row[DB_currency] = EURO
            self.dataframe.loc[len(self.dataframe.index)] = sum_row

    def _processing(self):

        pass

    def _set_properties(self):

        pass

    def _set_row_format(self):

        pass

    def _set_column_format(self):

        columns = list(self.dataframe.columns)
        for column in columns:
            if column in self.fields:
                self.column_format[column] = self._get_column_format(column)
            elif isinstance(column, tuple) and column[0] in self.fields:
                self.column_format[column] = self._get_column_format(column[0])
            elif (column in FN_COLUMNS_EURO or
                  isinstance(column, tuple) and column[0] in FN_COLUMNS_EURO):
                self.column_format[column] = (
                    E, EURO, 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)
            elif (column in FN_COLUMNS_PERCENT or
                  isinstance(column, tuple) and column[0] in FN_COLUMNS_PERCENT):
                self.column_format[column] = (
                    E, '%', 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)
            else:
                if column not in self.column_format:
                    self.column_format[column] = (
                        W, '', '', '', COLUMN_FORMATS_TYP_VARCHAR)
        try:
            for column in columns:
                self.column_format[column.upper()] = self.column_format[column]
            self.dataframe.rename(str.upper, axis='columns', inplace=True)
            columns = list(self.dataframe.columns)
        except AttributeError:  # dataframe with leveled column names
            pass
        for column in columns:
            col_align, col_currency, col_places, col_color, typ = self.column_format[column]
            if typ in [COLUMN_FORMATS_TYP_DECIMAL]:
                if col_color:
                    self._color_negative(column, color=col_color)
                self.format_decimal(column=column, currency=col_currency,
                                    places=col_places)
            if col_align in [E, W]:
                self.pandas_table.columnformats['alignment'][column] = col_align
        self.dataframe = self.dataframe.drop(
            axis=1, index=None, errors='ignore',
            columns=[DB_currency, DB_status, DB_opening_currency, DB_opening_currency,
                     DB_closing_currency, DB_closing_currency, DB_amount_currency,
                     DB_price_currency
                     ]
        )
        self.dataframe = self.dataframe.fillna(value='')

    def _get_column_format(self, column):

        _, places, typ = self.fields[column]
        if places == 0:
            places = ''
        if typ in BuiltPandasBox.RIGHT:
            align = 'e'
        else:
            align = 'w'
        if column in BuiltPandasBox.COLUMN_CURRENCY:
            currency = BuiltPandasBox.COLUMN_CURRENCY[column]
            color = COLOR_NEGATIVE
        else:
            currency = ''
            color = ''
        return (align, currency, places, color, typ)

    def _color_negative(self, column, color=COLOR_NEGATIVE):

        if not isinstance(column, tuple):  # don t work with leveled columns
            mask = to_numeric(self.dataframe[column]) < 0
            self.pandas_table.setColorByMask(column, mask, color)

    def format_decimal(self, column=None, currency=None, places=None):
        '''
        Creates columns of type object Amount > plotting fails
        '''

        self.dataframe[column] = self.dataframe[column].apply(lambda x: str(x))
        if currency in list(self.dataframe.columns):
            self.dataframe[column] = self.dataframe[[column, currency]].apply(
                lambda x: Amount(*x, places), axis=1)
        elif len(currency) > 3:
            self.dataframe[currency] = EURO
            self.dataframe[column] = self.dataframe[[column, currency]].apply(
                lambda x: Amount(*x, places), axis=1)
        else:
            self.dataframe[column] = self.dataframe[column].apply(
                lambda x: Amount(x, currency, places))

    def _set_options(self, align=E):
        options = {'align': align,
                   'cellbackgr': '#F4F4F3',
                   'cellwidth': 150,
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

    def _dataframe_total_sum(self):

        pass
