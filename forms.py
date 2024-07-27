"""
Created on 28.01.2020
__updated__ = "2024-07-18"
@author: Wolfgang Kramer
"""

import re
import webbrowser
import requests

from bisect import bisect_left
from collections import namedtuple
from dataclasses import asdict
from datetime import date, datetime, timedelta
from json import loads, dumps
from tkinter import filedialog, E
from fints.formals import CreditDebit2
from pandas import DataFrame, to_numeric, concat, to_datetime, set_option
from pandastable import TableModel

from banking.declarations import (
    ALPHA_VANTAGE, ALPHA_VANTAGE_PRICE_PERIOD, ALPHA_VANTAGE_REQUIRED, ALPHA_VANTAGE_REQUIRED_COMBO,
    ALPHA_VANTAGE_OPTIONAL_COMBO,
    HoldingAcquisition,
    BANK_MARIADB_INI, BANKIDENTIFIER,
    DATABASES,
    CURRENCIES, CURRENCY, CURRENCY_EXTENDED, CREDIT,
    DEBIT, DB_TYPES,
    DB_acquisition_amount, DB_acquisition_price, DB_adjustments,
    DB_amount,
    DB_bic,
    DB_closing_balance,
    DB_closing_currency, DB_closing_status, DB_comments, DB_counter, DB_currency, DB_entry_date,
    DB_date, DB_iban,
    DB_ISIN, DB_market_price, DB_name, DB_opening_balance, DB_opening_currency, DB_opening_status,
    DB_location,
    DB_origin, DB_origin_symbol, DB_pieces, DB_posted_amount, DB_amount_currency, DB_price,
    DB_price_currency, DB_price_date, DB_status, DB_total_amount,
    DB_type, DB_server, DB_validity, DB_wkn,
    DB_total_amount_portfolio, DB_transaction_type, DB_symbol,
    ERROR, EURO,
    FALSE,
    FN_DATE, FN_PROFIT_LOSS, FN_TOTAL_PERCENT, FN_PERIOD_PERCENT, FN_DAILY_PERCENT,
    FN_FROM_DATE, FN_TO_DATE, FN_SHARE, FN_TOTAL,
    FN_PROFIT_CUM, FN_PIECES_CUM, FN_PROFIT,
    FORMS_TEXT,
    HTTP_CODE_OK, HOLDING,
    Informations,
    PERCENT,
    INFORMATION, ISIN,
    HOLDING_SWITCH,
    KEY_ALPHA_VANTAGE, KEY_ALPHA_VANTAGE_PRICE_PERIOD,
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_DIRECTORY, KEY_MAX_PIN_LENGTH,
    KEY_MAX_TAN_LENGTH, KEY_MIN_PIN_LENGTH,
    KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_TAN, MAX_PIN_LENGTH, MAX_TAN_LENGTH, KEY_THREADING,
    KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_PRODUCT_NAME, KEY_ACC_BANK_CODE,
    KEY_HOLDING_SWITCH,
    KEY_LOGGING, KEY_MS_ACCESS,
    KEY_MARIADB_NAME,
    KEY_MARIADB_PASSWORD, KEY_MARIADB_USER, KEY_PIN, KEY_BIC, KEY_PRODUCT_ID,
    KEY_SERVER, KEY_SHOW_MESSAGE, KEY_USER_ID, KEY_IDENTIFIER_DELIMITER,
    LIGHTBLUE,
    MENU_TEXT,  MESSAGE_TEXT, MESSAGE_TITLE, MIN_PIN_LENGTH, MIN_TAN_LENGTH,
    ORIGIN_SYMBOLS,
    PRICES,
    SCRAPER_BANKDATA,
    SEPA_AMOUNT, SEPA_CREDITOR_BANK_LOCATION, SEPA_CREDITOR_BANK_NAME, SEPA_CREDITOR_BIC,
    SEPA_CREDITOR_IBAN, SEPA_CREDITOR_NAME, SEPA_EXECUTION_DATE, SEPA_PURPOSE_1, SEPA_PURPOSE_2,
    SEPA_REFERENCE, SERVER,
    SHOW_MESSAGE,
    SWITCH,
    TIME_SERIES_DAILY, TRUE,
    TransactionNamedTuple, TRANSACTION_TYPES, TRANSACTION_RECEIPT, TRANSACTION_DELIVERY,
    VALIDITY_DEFAULT, WARNING, KEY_ACC_ACCOUNT_NUMBER, NOT_ASSIGNED, YAHOO,
    WWW_YAHOO)
from banking.formbuilts import (
    Caller, COMBO,
    BUTTON_OK, BUTTON_ALPHA_VANTAGE, BUTTON_DATA,
    BUTTON_SAVE, BUTTON_NEW, BUTTON_FIELDLIST, BUTTON_APPEND, BUTTON_REPLACE, BUTTON_NEXT,
    BUTTON_DELETE, BUTTON_DELETE_ALL, BUTTON_STANDARD, BUTTON_SAVE_STANDARD, BUTTON_SELECT_ALL,
    COLOR_HOLDING, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL,
    BuiltCheckButton, BuiltEnterBox, BuiltColumnBox, BuiltText,
    END, ENTRY,
    FileDialogue,
    field_validation, FieldDefinition, FORMAT_FIXED,
    MessageBoxTermination, MessageBoxAsk, MessageBoxInfo,
    destroy_widget,
    STANDARD,
    TYP_DECIMAL, TYP_DATE,
    WM_DELETE_WINDOW, BuiltPandasBox)
from banking.utils import (
    check_iban,
    Calculate,
    date_db,
    dict_get_first_key, dictbank_names, dictaccount,
    listbank_codes,
    shelve_exist, shelve_get_key, shelve_put_key,
    http_error_code)


dec2 = Calculate(places=2)
dec6 = Calculate(places=6)
message_transaction_new = True  # Switch to show Message just once


def _set_defaults(field_defs=[FieldDefinition()], default_values=(1,)):

    if default_values:
        if len(field_defs) < len(default_values):
            MessageBoxTermination(
                info='SET_DEFAULTS: Items of Field Definition less than Items of Default_Values')
            return False  # thread checking
        for idx, item in enumerate(default_values):
            field_defs[idx].default_value = item
    return field_defs


def _field_defs_transaction(isin_values):
    names = {}
    for item in isin_values:
        isin_, name_ = item
        names[name_] = isin_
    field_defs = [FieldDefinition(definition=COMBO,
                                  name=DB_name, length=35, combo_values=names.keys(),
                                  selected=True, readonly=True),
                  FieldDefinition(name=DB_ISIN, length=12, protected=True),
                  FieldDefinition(name=DB_entry_date, length=19, typ=TYP_DATE),
                  FieldDefinition(definition=COMBO,
                                  name=DB_price_currency, length=3,
                                  combo_values=CURRENCY_EXTENDED, default_value=EURO),
                  FieldDefinition(name=DB_acquisition_price,
                                  length=16, typ=TYP_DECIMAL),
                  FieldDefinition(name=DB_price_date, length=21, typ=TYP_DATE),
                  FieldDefinition(name=DB_pieces, length=16, typ=TYP_DECIMAL),
                  FieldDefinition(definition=COMBO,
                                  name=DB_amount_currency, length=3, combo_values=CURRENCY,
                                  default_value=EURO),
                  FieldDefinition(name=DB_posted_amount,
                                  length=16, typ=TYP_DECIMAL)
                  ]
    return field_defs, names


class Acquisition(BuiltColumnBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Acquisition Values

    PARAMETER:
        data        Array of HoldingAcquisition() instances
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        array               Array of HoldingAcquisition() instances
    """

    def __init__(self,  title=MESSAGE_TITLE, header=None, button2_text=None,
                 data=[HoldingAcquisition('2021-01-01', 'EUR', 1, 2, 3,
                                          'EUR', 4, 5, 'ORIGIN')]
                 ):

        Caller.caller = self.__class__.__name__
        array_def = []
        for item in data:
            row = asdict(item)
            array_def.append([

                FieldDefinition(name=DB_price_date, length=10, typ=TYP_DATE,
                                protected=True, default_value=row[DB_price_date]),
                FieldDefinition(name=DB_price_currency, length=3,
                                protected=True, default_value=row[DB_price_currency]),
                FieldDefinition(name=DB_market_price, length=15, typ=TYP_DECIMAL,
                                protected=True, default_value=row[DB_market_price]),
                FieldDefinition(name=DB_acquisition_price, length=15, typ=TYP_DECIMAL,
                                protected=True, default_value=row[DB_acquisition_price]),
                FieldDefinition(name=DB_pieces, length=10, typ=TYP_DECIMAL,
                                protected=True, default_value=row[DB_pieces]),
                FieldDefinition(name=DB_amount_currency, length=3,
                                protected=True, default_value=row[DB_amount_currency]),
                FieldDefinition(name=DB_total_amount, length=15, typ=TYP_DECIMAL,
                                protected=True, default_value=row[DB_total_amount]),
                FieldDefinition(name=DB_acquisition_amount, length=15, typ=TYP_DECIMAL,
                                protected=True, default_value=row[DB_acquisition_amount]),
                FieldDefinition(name=DB_origin, length=50,
                                protected=True, default_value=row[DB_origin])
            ]
            )
        array_def[-1][7].protected = False  # DB_acquisition_amount
        if array_def[-1][1].default_value == PERCENT:  # DB_acquisition_price
            array_def[-1][3].protected = False
        super().__init__(title=title, header=header,
                         button1_text=BUTTON_OK, button2_text=button2_text,
                         button3_text=None,
                         array_def=array_def)
        self._footer.set(MESSAGE_TEXT['SCROLL'])


class Adjustments(BuiltColumnBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Prices Adjustments (R-Factors which adjusted prices because of splits, special dividends, .. )

    PARAMETER:
        json_data            Adjustments of ISIN symbol
                             Format {symbol: {date: r-factor, ....}}
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
    """

    def __init__(self,  mariadb, isin, title=FORMS_TEXT['Adjust Prices']):

        Caller.caller = self.__class__.__name__

        field_dict = mariadb.select_table(
            ISIN, [DB_adjustments], result_dict=True, isin=isin)[0]
        json_data = field_dict[DB_adjustments]
        adjustments = loads(json_data)
        array_def = []
        if adjustments:
            # convert dictionary adjustmments of symbol to list of tuples
            adjustments = list(adjustments.items())
            for adjustment in adjustments:
                date_, r_factor = adjustment
                r_factor, used = r_factor
                if date_:
                    array_def.append(
                        [FieldDefinition(definition=ENTRY, name='Date', length=10,
                                         mandatory=False, typ=TYP_DATE, default_value=date_),
                         FieldDefinition(definition=ENTRY, name='R-Factor', length=16,
                                         mandatory=False, typ=TYP_DECIMAL, default_value=r_factor),
                         FieldDefinition(definition=COMBO, name='Used', length=5, protected=True,
                                         mandatory=False, default_value=used,
                                         combo_values=SWITCH, allowed_values=SWITCH)
                         ])
        array_def.append([FieldDefinition(definition=ENTRY, name='Date', length=10,
                                          mandatory=False, typ=TYP_DATE),
                          FieldDefinition(definition=ENTRY, name='R-Factor', length=16,
                                          mandatory=False, typ=TYP_DECIMAL),
                          FieldDefinition(definition=ENTRY, name='Used', length=5,  protected=True,
                                          mandatory=False, default_value=FALSE,
                                          combo_values=SWITCH, allowed_values=SWITCH)
                          ])
        super().__init__(title=title, array_def=array_def)
        if self.button_state == WM_DELETE_WINDOW:
            return
        json_data = {}  # new creation of adjustment of symbol
        adjustments = {}
        for row in self.array:
            if row[0] and row[1]:
                adjustments[row[0]] = (row[1], row[2])
        adjustments = dict(sorted(adjustments.items()))
        if field_dict[DB_adjustments] is None:
            field_dict[DB_adjustments] = {}
        field_dict[DB_adjustments] = dumps(adjustments)
        mariadb.execute_update(ISIN, field_dict, isin=isin)


class AlphaVantageParameter(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Alpha vantage API Parameters

    PARAMETER:
        options          Dictionary with Alpha Vantage Parameter Names of all Functions
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of Parameter Values of Function Value
    """

    def __init__(self, title, function, api_key, parameter_list, default_values, alpha_vantage_symbols):

        Caller.caller = self.__class__.__name__
        self.title = ' '.join([title, function.upper()])
        _field_defs = []
        ALPHA_VANTAGE_REQUIRED_COMBO[DB_symbol] = alpha_vantage_symbols
        for parameter in parameter_list:
            if parameter in ALPHA_VANTAGE_REQUIRED:
                if parameter in ALPHA_VANTAGE_REQUIRED_COMBO.keys():
                    _field_defs.append(FieldDefinition(
                        definition=COMBO, name=parameter.upper(), length=25,
                        combo_values=ALPHA_VANTAGE_REQUIRED_COMBO[parameter],
                        allowed_values=ALPHA_VANTAGE_REQUIRED_COMBO[parameter]))
                else:
                    _field_defs.append(FieldDefinition(
                        definition=ENTRY, name=parameter.upper(), length=25))
            elif parameter in ALPHA_VANTAGE_OPTIONAL_COMBO.keys():
                _field_defs.append(FieldDefinition(
                    definition=COMBO, name=parameter.upper(), length=25, mandatory=False,
                    default_value=ALPHA_VANTAGE_OPTIONAL_COMBO[parameter][0],
                    combo_values=ALPHA_VANTAGE_OPTIONAL_COMBO[parameter],
                    allowed_values=ALPHA_VANTAGE_OPTIONAL_COMBO[parameter]))
            elif parameter == 'apikey':
                _field_defs.append(FieldDefinition(
                    definition=ENTRY, name=parameter.upper(), length=25,
                    default_value=api_key))
            else:
                _field_defs.append(FieldDefinition(
                    definition=ENTRY, name=parameter.upper(), length=25, mandatory=False))
        FieldNames = namedtuple('FieldNames', parameter_list)
        self._field_defs = FieldNames(*_field_defs)
        if default_values:
            _set_defaults(_field_defs, default_values)
        super().__init__(title=title,
                         button1_text=BUTTON_DATA, button2_text=BUTTON_ALPHA_VANTAGE,
                         button3_text=MENU_TEXT['ISIN Table'],
                         field_defs=self._field_defs)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if self._footer.get() == '':
            self.quit_widget()

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = MENU_TEXT['ISIN Table']
        self.quit_widget()


class AppCustomizing(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Application Customizing
    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Applicat Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of Application Customizing Fields
    """

    def __init__(self,  header=MESSAGE_TEXT['APP'], shelve_app={}):

        Caller.caller = self.__class__.__name__
        self.shelve_app = shelve_app
        FieldNames = namedtuple('FieldNames', [
            KEY_PRODUCT_ID, KEY_ALPHA_VANTAGE, KEY_DIRECTORY, KEY_MARIADB_NAME, KEY_MARIADB_USER,
            KEY_MARIADB_PASSWORD, KEY_SHOW_MESSAGE,
            KEY_LOGGING, KEY_THREADING, KEY_MS_ACCESS,
            KEY_ALPHA_VANTAGE_PRICE_PERIOD, KEY_HOLDING_SWITCH])
        field_defs = FieldNames(
            FieldDefinition(name=KEY_PRODUCT_ID, length=50),
            FieldDefinition(name=KEY_ALPHA_VANTAGE,
                            length=50, mandatory=False),
            FieldDefinition(name=KEY_DIRECTORY, length=100,
                            readonly=True, focus_in=True),
            FieldDefinition(name=KEY_MARIADB_NAME, length=20,
                            definition=COMBO, combo_values=DATABASES, combo_positioning=False,
                            focus_in=True, focus_out=True),
            FieldDefinition(name=KEY_MARIADB_USER, length=20),
            FieldDefinition(name=KEY_MARIADB_PASSWORD, length=20),
            FieldDefinition(name=KEY_SHOW_MESSAGE, length=25,
                            definition=COMBO, combo_values=SHOW_MESSAGE,
                            allowed_values=SHOW_MESSAGE),
            FieldDefinition(name=KEY_LOGGING, length=5,
                            definition=COMBO, combo_values=SWITCH,
                            allowed_values=SWITCH),
            FieldDefinition(name=KEY_THREADING, length=5,
                            definition=COMBO, combo_values=SWITCH,
                            allowed_values=SWITCH),
            FieldDefinition(name=KEY_MS_ACCESS, length=100, readonly=True, focus_in=True,
                            mandatory=False),
            FieldDefinition(name=KEY_ALPHA_VANTAGE_PRICE_PERIOD, length=50,
                            definition=COMBO, combo_values=ALPHA_VANTAGE_PRICE_PERIOD,
                            allowed_values=ALPHA_VANTAGE_PRICE_PERIOD),
            FieldDefinition(name=KEY_HOLDING_SWITCH, length=10,
                            definition=COMBO, combo_values=HOLDING_SWITCH,
                            allowed_values=HOLDING_SWITCH),
        )
        if shelve_exist(BANK_MARIADB_INI):
            _set_defaults(field_defs=field_defs, default_values=(
                          shelve_app[KEY_PRODUCT_ID], shelve_app[KEY_ALPHA_VANTAGE],
                          shelve_app[KEY_DIRECTORY],
                          shelve_app[KEY_MARIADB_NAME], shelve_app[KEY_MARIADB_USER],
                          shelve_app[KEY_MARIADB_PASSWORD],
                          shelve_app[KEY_SHOW_MESSAGE], shelve_app[KEY_LOGGING],
                          shelve_app[KEY_THREADING],
                          shelve_app[KEY_MS_ACCESS], shelve_app[KEY_ALPHA_VANTAGE_PRICE_PERIOD],
                          shelve_app[KEY_HOLDING_SWITCH]))
        else:
            _set_defaults(field_defs=field_defs,
                          default_values=('', '', '', '', '', '', ERROR, FALSE, TRUE,
                                          '', TIME_SERIES_DAILY, HOLDING))
        super().__init__(header=header, grab=False, field_defs=field_defs)

    def focus_in_action(self, event):

        if event.widget.myId == KEY_DIRECTORY:
            directory = filedialog.askdirectory()
            if directory:
                getattr(self._field_defs, KEY_DIRECTORY).textvar.set(
                    directory + '/')
            getattr(self._field_defs, KEY_MARIADB_NAME).widget.focus_set()
        if event.widget.myId == KEY_MS_ACCESS:
            file_dialogue = FileDialogue(title=MESSAGE_TEXT['SELECT_ACCESS_DB'],
                                         filetypes=(("accdb files", "*.accdb"),
                                                    ("all files", "*.*")))
            if file_dialogue.filename not in ['', None]:
                getattr(self._field_defs, KEY_MS_ACCESS).textvar.set(
                    file_dialogue.filename)
            else:
                getattr(self._field_defs, KEY_MS_ACCESS).textvar.set('')
            getattr(self._field_defs, KEY_PRODUCT_ID).widget.focus_set()
        if event.widget.myId == KEY_MARIADB_NAME:
            getattr(self._field_defs, KEY_MS_ACCESS).textvar.set('')

    def focus_out_action(self, event):

        if event.widget.myId == KEY_MARIADB_NAME:
            mariadb_name = getattr(
                self._field_defs, KEY_MARIADB_NAME).widget.get()
            if shelve_exist(BANK_MARIADB_INI):
                if mariadb_name == self.shelve_app[KEY_MARIADB_NAME]:
                    getattr(self._field_defs, KEY_MS_ACCESS).textvar.set(
                        self.shelve_app[KEY_MS_ACCESS])


class InputDate(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox ToDate FromDate

    PARAMETER:
        header
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {'TO_Date':YYYY-MM-DD, 'From_Date':YYYY-MM-DD}
    """

    def __init__(self,  title=MESSAGE_TITLE, header=MESSAGE_TEXT['SELECT'],
                 from_date=date.today(), to_date=date.today()):

        Caller.caller = self.__class__.__name__
        FieldNames = namedtuple('FieldNames', [FN_FROM_DATE, FN_TO_DATE])
        super().__init__(
            title=title, header=header, grab=True,
            button1_text=BUTTON_OK, button2_text=None, button3_text=None,
            field_defs=FieldNames(
                FieldDefinition(name=FN_FROM_DATE, typ=TYP_DATE, length=10,
                                default_value=from_date),
                FieldDefinition(name=FN_TO_DATE, typ=TYP_DATE, length=10,
                                default_value=to_date))
        )

    def validation_all_addon(self, field_defs):

        if (getattr(field_defs, FN_FROM_DATE).widget.get() >
                getattr(field_defs, FN_TO_DATE).widget.get()):
            self._footer.set(MESSAGE_TEXT['DATE'].format(
                getattr(field_defs, FN_FROM_DATE).name))


class InputDateHoldingPerc(InputDate):
    """
    TOP-LEVEL-WINDOW        EnterBox ToDate FromDate

    PARAMETER:
        header
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {'TO_Date':YYYY-MM-DD, 'From_Date':YYYY-MM-DD}
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 from_date=(date.today() - timedelta(days=1)), to_date=date.today(),
                 mariadb=None, iban=''):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.iban = iban
        super().__init__(title=title, from_date=from_date, to_date=to_date)

    def validation_all_addon(self, field_defs):
        from_date = getattr(field_defs, FN_FROM_DATE).widget.get()
        _date = self._validate_date(from_date)
        if _date:
            getattr(self._field_defs, FN_FROM_DATE).textvar.set(
                _date)  # adjusted date returned
        to_date = getattr(field_defs, FN_TO_DATE).widget.get()
        _date = self._validate_date(to_date)
        if _date:
            getattr(self._field_defs, FN_TO_DATE).textvar.set(
                _date)  # adjusted date returned
        if from_date == to_date:
            from_date = date_db.subtract(from_date, 1)
            from_date = date_db.convert(from_date)
            getattr(self._field_defs, FN_FROM_DATE).textvar.set(
                from_date)  # adjusted date returned
            self._footer.set(MESSAGE_TEXT['DATE_ADJUSTED'])
        if (from_date > to_date):
            self._footer.set(MESSAGE_TEXT['DATE'].format(from_date))

    def _validate_date(self, _date):
        data_exists = self.mariadb.select_data_exist(
            HOLDING, iban=self.iban, price_date=_date)
        if not data_exists:
            _date = self._get_prev_date(_date)
            self._footer.set(MESSAGE_TEXT['DATE_ADJUSTED'])
        return _date

    def _get_prev_date(self, _date):

        data_ = self.mariadb.select_table_distinct(
            HOLDING, [DB_price_date], iban=self.iban, order=DB_price_date)
        if data_:
            data = list(map(lambda x: str(x[0]), data_))
            idx = bisect_left(data, _date)
            if idx != 0:
                idx = idx - 1
            return data[idx]
        else:
            return _date


class InputDateFieldlist(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox ToDate FromDate
                            Call of FieldList Form (SelectFields)
    PARAMETER:
        field_list           check_field description shown in checkbox
        standard             last selection stored in shelve files: key standard
        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {'TO_Date':YYYY-MM-DD, 'From_Date':YYYY-MM-DD}

        self.field_list        contains selected check_fields
    """

    def __init__(self,  title=MESSAGE_TITLE, header=MESSAGE_TEXT['SELECT'],
                 field_list=['Description of Checkbox1', 'Description of Checkbox2',
                             'Description of Checkbox3'],
                 default_texts=[],
                 from_date=date.today(), to_date=date.today(),
                 standard='STANDARD', period=True):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.field_list = field_list
        self.standard = standard
        standard_texts = ''
        self.default_texts = default_texts
        self.no_selection = True
        self.period = period
        if self.standard:
            standard_texts = shelve_get_key(BANK_MARIADB_INI, self.standard)
            if standard_texts:
                standard_texts = list(
                    set(standard_texts).intersection(set(self.field_list)))
                if not self.default_texts:
                    self.default_texts = standard_texts
        FieldNames = namedtuple('FieldNames', [FN_FROM_DATE, FN_TO_DATE])
        if self.period:
            FieldNames = namedtuple('FieldNames', [FN_FROM_DATE, FN_TO_DATE])
            field_defs = FieldNames(
                FieldDefinition(name=FN_FROM_DATE, typ=TYP_DATE, length=10,
                                default_value=from_date),
                FieldDefinition(name=FN_TO_DATE, typ=TYP_DATE, length=10,
                                default_value=to_date))
        else:
            FieldNames = namedtuple('FieldNames', [FN_DATE])
            field_defs = FieldNames(
                FieldDefinition(name=FN_DATE, typ=TYP_DATE, length=10,
                                default_value=from_date))
        super().__init__(
            title=title, header=header, grab=True,
            button1_text=BUTTON_OK, button2_text=BUTTON_FIELDLIST, button3_text=None,
            field_defs=field_defs)
        if self.no_selection and standard_texts:
            self.field_list = standard_texts

    def validation_all_addon(self, field_defs):

        if self.period:
            if (getattr(field_defs, FN_FROM_DATE).widget.get() > '{:%Y-%m-%d}'.format(date.today())):
                getattr(self._field_defs, FN_FROM_DATE).textvar.set(
                    date.today())

            if (getattr(field_defs, FN_FROM_DATE).widget.get() > getattr(field_defs, FN_TO_DATE).widget.get()):
                self._footer.set(MESSAGE_TEXT['DATE'].format(
                    getattr(field_defs, FN_FROM_DATE).name))
        else:
            if (getattr(field_defs, FN_DATE).widget.get() > '{:%Y-%m-%d}'.format(date.today())):
                getattr(self._field_defs, FN_DATE).textvar.set(date.today())

    def button_1_button2(self, event):
        if not self.field_list:
            return
        self.no_selection = False
        self.button_state = self._button2_text
        checkbutton = SelectFields(title=self.title, checkbutton_texts=self.field_list,
                                   default_texts=self.default_texts, standard=self.standard)
        if checkbutton.button_state == WM_DELETE_WINDOW:
            return
        self.field_list = checkbutton.field_list


class InputDateFieldlistPrices(InputDateFieldlist):
    """
        Select Prices
    """

    def button_1_button2(self, event):
        if not self.field_list:
            return
        self.no_selection = False
        self.button_state = self._button2_text
        checkbutton = SelectFields(
            title=self.title,
            button2_text=None, button3_text=None,
            default_texts=self.default_texts,
            checkbutton_texts=self.field_list)
        if checkbutton.button_state == WM_DELETE_WINDOW:
            return
        self.field_list = checkbutton.field_list


class InputDateFieldlistHolding(InputDateFieldlist):
    """
        Validation of price_date in database
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 field_list=['Description of Checkbox1', 'Description of Checkbox2',
                             'Description of Checkbox3'],
                 default_texts=[],
                 date=date.today(),  mariadb=None, iban=''):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.iban = iban
        super().__init__(title=title, header=MESSAGE_TEXT['SELECT'],
                         field_list=field_list, from_date=date, default_texts=default_texts,
                         standard=MENU_TEXT['Show'] + MENU_TEXT['Holding'], period=False)

    def validation_all_addon(self, field_defs):
        _date = self._validate_date(field_defs)
        if _date:
            getattr(self._field_defs, FN_DATE).textvar.set(_date)

    def _validate_date(self, field_defs):
        _date = getattr(field_defs, FN_DATE).widget.get()
        data_exists = self.mariadb.select_data_exist(
            HOLDING, iban=self.iban, price_date=_date)
        if data_exists:
            pass
        else:
            _date = self._get_prev_date(_date)
            self._footer.set(MESSAGE_TEXT['DATE_ADJUSTED'])
        return _date

    def _get_prev_date(self, _date):

        data_ = self.mariadb.select_table_distinct(
            HOLDING, [DB_price_date], iban=self.iban, order=DB_price_date)
        data = list(map(lambda x: str(x[0]), data_))
        idx = bisect_left(data, _date)
        if idx != 0:
            idx = idx - 1
        return data[idx]


class InputDay(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Date

    PARAMETER:
        header
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {'Date':YYYY-MM-DD}
    """

    def __init__(self,  title=MESSAGE_TITLE, header=None,
                 date=date.today()):

        Caller.caller = self.__class__.__name__
        FieldNames = namedtuple('FieldNames', [FN_DATE])
        super().__init__(
            title=title, header=header,
            button1_text=BUTTON_OK, button2_text=None, button3_text=None, grab=True,
            field_defs=FieldNames(
                FieldDefinition(name=FN_DATE, typ=TYP_DATE, length=10,
                                default_value=date))
        )

    def validation_all_addon(self, field_defs):

        if (getattr(field_defs, FN_DATE).widget.get() > '{:%Y-%m-%d}'.format(date.today())):
            getattr(self._field_defs, FN_DATE).textvar.set(date.today())


class InputISIN(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox IBAN, ToDate FromDate

    PARAMETER:
        header
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {Iban: >iban<, 'TO_Date':YYYY-MM-DD, 'From_Date':YYYY-MM-DD}
    """

    def __init__(self,  title=MESSAGE_TITLE, header=MESSAGE_TEXT['SELECT'],
                 names={}, default_values=None, footer=None, period=True):

        Caller.caller = self.__class__.__name__
        if names == {}:
            MessageBoxTermination()
            return False  # thread checking
        self.period = period
        FieldNames = namedtuple('FieldNames', [DB_name, DB_ISIN])
        self.__names = names
        self.combo_values = names.keys()
        field_defs = FieldNames(
            FieldDefinition(definition=COMBO, name=DB_name, length=35,
                            combo_values=self.combo_values, selected=True,
                            allowed_values=self.combo_values,
                            default_value=list(names.keys())[0]),
            FieldDefinition(name=DB_ISIN, length=12, protected=True,
                            default_value=list(names.values())[0]))
        if period:
            FieldNames = namedtuple('FieldNames', [*FieldNames._fields] +
                                    [FN_FROM_DATE, FN_TO_DATE])
            field_defs = FieldNames(
                *field_defs,
                FieldDefinition(name=FN_FROM_DATE, typ=TYP_DATE, length=10,
                                default_value=date.today()),
                FieldDefinition(name=FN_TO_DATE, typ=TYP_DATE, length=10,
                                default_value=date.today()),
            )
        _set_defaults(field_defs, default_values)
        super().__init__(
            title=title, header=header, grab=True,
            button1_text=BUTTON_OK, button2_text=None,
            field_defs=field_defs
        )

    def validation_all_addon(self, field_defs):

        if self.period:
            if (getattr(field_defs, FN_FROM_DATE).widget.get() >
                    getattr(field_defs, FN_TO_DATE).widget.get()):
                self._footer.set(MESSAGE_TEXT['DATE'].format(
                    getattr(field_defs, FN_FROM_DATE).name))

    def comboboxselected_action(self, event):

        if getattr(self._field_defs, DB_name).name == DB_name:
            getattr(self._field_defs, DB_ISIN).textvar.set(
                self.__names[event.widget.get()])


class InputPIN(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox PIN

    PARAMETER:
        bank_code           Bankleitzahl
        bank_name
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        pin
    """

    def __init__(self, bank_code, bank_name=''):

        self.pin = ''
        Caller.caller = self.__class__.__name__
        self._bank_code = bank_code
        pin_length = shelve_get_key(
            bank_code, [KEY_MAX_PIN_LENGTH, KEY_MIN_PIN_LENGTH])
        pin_max_length = MAX_PIN_LENGTH
        if pin_length[KEY_MAX_PIN_LENGTH] is not None:
            pin_max_length = pin_length[KEY_MAX_PIN_LENGTH]
        pin_min_length = MIN_PIN_LENGTH
        if pin_length[KEY_MIN_PIN_LENGTH] is not None:
            pin_min_length = pin_length[KEY_MIN_PIN_LENGTH]
        while True:
            super().__init__(
                header=MESSAGE_TEXT['PIN_INPUT'].format(bank_name, bank_code), title=MESSAGE_TITLE,
                button1_text=BUTTON_OK, button2_text=None, button3_text=None,
                field_defs=[FieldDefinition(name=KEY_PIN, length=pin_max_length,
                                            min_length=pin_min_length)]
            )
            if self.button_state == WM_DELETE_WINDOW:
                break
            self.pin = self.field_dict[KEY_PIN]
            if self.pin.strip() not in [None, '']:
                break


class InputTAN(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox TAN

    PARAMETER:
        bank_code           Bankleitzahl
        bank_name
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        tan
    """

    def __init__(self, bank_code, bank_name):

        Caller.caller = self.__class__.__name__
        self._bank_code = bank_code
        tan_max_length = shelve_get_key(bank_code, KEY_MAX_TAN_LENGTH)
        if not tan_max_length:
            tan_max_length = MAX_TAN_LENGTH
        while True:
            super().__init__(
                header=MESSAGE_TEXT['TAN_INPUT'].format(bank_code, bank_name), title=MESSAGE_TITLE,
                button1_text=BUTTON_OK, button2_text=None, button3_text=None,
                field_defs=[
                    FieldDefinition(name=KEY_TAN, length=tan_max_length, min_length=MIN_TAN_LENGTH)]
            )
            if self.button_state == WM_DELETE_WINDOW:
                break
            self.tan = self.field_dict[KEY_TAN]
            if self.tan.strip() not in [None, '']:
                break


class InputName(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Name (e.g. FileName)

    PARAMETER:
        bank_code           Bankleitzahl
        bank_name
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        name
    """

    def __init__(self,  header=MESSAGE_TEXT['NAME_INPUT']):

        Caller.caller = self.__class__.__name__
        FieldNames = namedtuple('FieldNames', [DB_name])
        super().__init__(
            header=header, title=MESSAGE_TITLE, grab=True,
            button1_text=BUTTON_OK, button2_text=None, button3_text=None,
            field_defs=FieldNames(FieldDefinition(
                name=DB_name, length=50, min_length=1))
        )
        self.name = self.field_dict[DB_name]

    def validation_addon(self, field_def):
        """
        Allowed characters: A-Z a-z 0-9 _  (MariaDB Naming Conventions)
        """
        name_ = field_def.widget.get()
        if (not bool(re.match('^[A-Za-z0-9_]+$', name_)) or not name_):
            self._footer.set(MESSAGE_TEXT['NAMING'])


class BankDataNew(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox New Bank BankData

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Bank Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictinionary Of BankData Fields
    """

    def __init__(self,  title, mariadb, bank_codes=[]):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.bank_codes = bank_codes
        FieldNames = namedtuple('FieldNames', [
            KEY_BANK_CODE, KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_SERVER,
            KEY_IDENTIFIER_DELIMITER])
        field_defs = FieldNames(
            FieldDefinition(definition=COMBO,
                            name=KEY_BANK_CODE, length=8, lformat=FORMAT_FIXED,
                            combo_values=self.bank_codes, selected=True),
            FieldDefinition(name=KEY_BANK_NAME, length=70, protected=True),
            FieldDefinition(name=KEY_USER_ID, length=20),
            FieldDefinition(name=KEY_PIN, length=10, mandatory=False),
            FieldDefinition(name=KEY_BIC, length=11, lformat=FORMAT_FIXED),
            FieldDefinition(name=KEY_SERVER, length=100),
            FieldDefinition(name=KEY_IDENTIFIER_DELIMITER, length=1, lformat=FORMAT_FIXED,
                            default_value=':')
        )
        super().__init__(title=title, button2_text=None, field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == KEY_BANK_CODE:
            if field_def.widget.get() in listbank_codes():
                self._footer.set(MESSAGE_TEXT['BANK_CODE_EXIST'].
                                 format(field_def.widget.get()))
            else:
                if field_def.widget.get() in list(SCRAPER_BANKDATA.keys()):
                    getattr(self._field_defs,
                            KEY_IDENTIFIER_DELIMITER).textvar.set(
                                SCRAPER_BANKDATA[field_def.widget.get()][1])
                return
        if field_def.name == KEY_SERVER:
            http_code = http_error_code(field_def.widget.get())
            if http_code not in HTTP_CODE_OK:
                self._footer.set(MESSAGE_TEXT['HTTP_INPUT'].
                                 format(http_code, field_def.widget.get()))

    def comboboxselected_action(self, event):

        bank_code = getattr(self._field_defs, KEY_BANK_CODE).widget.get()
        field_dict = self.mariadb.select_table(
            BANKIDENTIFIER, [DB_name, DB_bic], result_dict=True, code=bank_code)
        if field_dict and DB_name in field_dict[0]:
            getattr(self._field_defs, KEY_BANK_NAME).textvar.set(
                field_dict[0][DB_name])
        else:
            getattr(self._field_defs, KEY_BANK_NAME).textvar.set('')
        if field_dict and DB_bic in field_dict[0]:
            getattr(self._field_defs, KEY_BIC).textvar.set(
                field_dict[0][DB_bic])
        else:
            getattr(self._field_defs, KEY_BIC).textvar.set('')
        field_dict = self.mariadb.select_table(
            SERVER, [DB_server], result_dict=True, code=bank_code)
        if field_dict and DB_server in field_dict[0]:
            getattr(self._field_defs, KEY_SERVER).textvar.set(
                field_dict[0][DB_server])
        else:
            getattr(self._field_defs, KEY_SERVER).textvar.set('')


class BankDataChange(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox BankData

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Bank Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of BankData Fields
    """

    def __init__(self, title, mariadb, bank_code, login_data):

        Caller.caller = self.__class__.__name__
        servers = mariadb.select_server(code=bank_code)
        field_defs = [
            FieldDefinition(name=KEY_BANK_NAME, length=70, protected=True),
            FieldDefinition(name=KEY_USER_ID, length=20),
            FieldDefinition(name=KEY_PIN, length=10, mandatory=False),
            FieldDefinition(name=KEY_BIC, length=11, lformat=FORMAT_FIXED),
            FieldDefinition(definition=COMBO,
                            name=KEY_SERVER, length=100,
                            combo_values=servers),
            FieldDefinition(name=KEY_IDENTIFIER_DELIMITER, length=1, lformat=FORMAT_FIXED,
                            default_value=':')]
        _set_defaults(field_defs, (login_data[KEY_BANK_NAME],
                                   login_data[KEY_USER_ID], login_data[KEY_PIN],
                                   login_data[KEY_BIC], login_data[KEY_SERVER],
                                   login_data[KEY_IDENTIFIER_DELIMITER]))
        super().__init__(title=title, field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == KEY_SERVER:
            http_code = http_error_code(field_def.widget.get())
            if http_code not in HTTP_CODE_OK:
                self._footer.set(MESSAGE_TEXT['HTTP_INPUT'].
                                 format(http_code, field_def.widget.get()))


class BankDelete(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox BankData

    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field               Selected ComoboBox Value
    """

    def __init__(self,  title):

        Caller.caller = self.__class__.__name__
        FieldNames = namedtuple('FieldNames', [KEY_BANK_CODE, KEY_BANK_NAME])
        super().__init__(
            title=title,
            field_defs=FieldNames(
                FieldDefinition(definition=COMBO,
                                name=KEY_BANK_CODE, length=8, selected=True, readonly=True,
                                combo_values=listbank_codes()),
                FieldDefinition(name=KEY_BANK_NAME,
                                length=70, protected=True)
            )
        )

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.field_dict = {}
        self.field_dict[KEY_BANK_CODE] = getattr(
            self._field_defs, KEY_BANK_CODE).widget.get()
        self.field_dict[KEY_BANK_NAME] = getattr(
            self._field_defs, KEY_BANK_NAME).widget.get()
        self.quit_widget()

    def comboboxselected_action(self, event):

        getattr(self._field_defs, KEY_BANK_NAME).textvar.set(shelve_get_key(
            getattr(self._field_defs, KEY_BANK_CODE).widget.get(), KEY_BANK_NAME))


class Isin(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Isin Data

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Isin Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of IsinData Fields
    """

    def __init__(self, title, mariadb, key_aplpha_vantage, isin_name=''):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.key_aplpha_vantage = key_aplpha_vantage
        self.title = title
        self. get_isin_lists()
        self.field_list = [DB_ISIN, DB_name, DB_type,
                           DB_validity, DB_wkn, DB_origin_symbol,
                           DB_symbol, DB_adjustments, DB_currency]
        if self.isins:
            self.names = sorted(list(self.get_name_isin.keys()))
            if isin_name == '' and self.names:
                isin_name = self.names[0]
            isin = self.get_name_isin[isin_name]
            result = self.mariadb.select_table(
                ISIN, self.field_list[2:], order=DB_name, name=isin_name)
            if result:
                type_, validity, wkn, origin_symbol, self.symbol, adjustments, currency = result[
                    0]
            else:
                type_ = FN_SHARE
                validity = VALIDITY_DEFAULT
                wkn = ''
                origin_symbol = NOT_ASSIGNED
                self.symbol = NOT_ASSIGNED
                adjustments = FALSE
                currency = EURO
        else:
            self.isins = []
            self.names = []
            isin = ''
            self.names = ''
            type_ = FN_SHARE
            validity = VALIDITY_DEFAULT
            wkn = ''
            origin_symbol = NOT_ASSIGNED
            self.symbol = NOT_ASSIGNED
            adjustments = {}
            currency = EURO
        FieldNames = namedtuple(
            'FieldNames', self.field_list)
        self._field_defs = FieldNames(
            FieldDefinition(definition=COMBO,
                            name=DB_ISIN, length=12, lformat=FORMAT_FIXED,
                            default_value=isin, focus_out=True,
                            combo_values=self.isins, selected=True),
            FieldDefinition(definition=COMBO,
                            name=DB_name, length=35,
                            default_value=isin_name, focus_out=True,
                            combo_values=self.names, selected=True),
            FieldDefinition(definition=COMBO,
                            name=DB_type, length=50,
                            default_value=type_,
                            combo_values=DB_TYPES),
            FieldDefinition(definition=ENTRY,
                            name=DB_validity, typ=TYP_DATE, length=10,
                            default_value=validity),
            FieldDefinition(definition=ENTRY, mandatory=False,
                            name=DB_wkn, length=6,
                            default_value=wkn),
            FieldDefinition(definition=COMBO,
                            name=DB_origin_symbol, length=50,
                            default_value=origin_symbol,
                            combo_values=ORIGIN_SYMBOLS,
                            allowed_values=ORIGIN_SYMBOLS, focus_out=True),
            FieldDefinition(definition=ENTRY,
                            name=DB_symbol, length=50, default_value=self.symbol,
                            upper=True),
            FieldDefinition(definition=ENTRY, protected=True,
                            name=DB_adjustments, length=100, default_value=adjustments,
                            upper=True),
            FieldDefinition(definition=COMBO,
                            name=DB_currency, length=10, default_value=currency,
                            combo_values=CURRENCIES, combo_positioning=False),
        )
        super().__init__(title=title, header=MESSAGE_TEXT['ISIN_DATA'],
                         button3_text=BUTTON_DELETE, button4_text=BUTTON_NEW,
                         button5_text=MENU_TEXT['Prices'], button6_text=FORMS_TEXT['Adjust Prices'],
                         field_defs=self._field_defs)

    def get_isin_lists(self):

        self.get_name_isin = self.mariadb.select_dict(ISIN, DB_name, DB_ISIN)
        self.isins = sorted(list(self.get_name_isin.values()))
        self.names = sorted(list(self.get_name_isin.keys()))

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        if getattr(self._field_defs, DB_symbol).widget.get() == '':
            getattr(self._field_defs, DB_symbol).textvar.set(NOT_ASSIGNED)
        self.validation()
        if self._footer.get() == '':
            if self.field_dict[DB_symbol] != self.symbol and self.symbol != NOT_ASSIGNED:
                self.mariadb.execute_delete(
                    PRICES, symbol=self.symbol)  # old prices obsolete
            self.field_dict[DB_name] = self.field_dict[DB_name].upper()
            self.mariadb.execute_replace(ISIN, self.field_dict)
            self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        isin = getattr(self._field_defs, DB_ISIN).widget.get()
        name = getattr(self._field_defs, DB_name).widget.get()
        symbol = getattr(self._field_defs, DB_symbol).widget.get()
        self.mariadb.execute_delete(ISIN, isin=isin, name=name)
        if symbol != NOT_ASSIGNED:
            self.mariadb.execute_delete(
                PRICES, symbol=symbol)
        self.quit_widget()

    def button_1_button4(self, event):

        self.button_state = self._button4_text
        getattr(self._field_defs, DB_ISIN).textvar.set('')
        getattr(self._field_defs, DB_name).textvar.set('')
        getattr(self._field_defs, DB_type).textvar.set(FN_SHARE)
        getattr(self._field_defs, DB_validity).textvar.set(VALIDITY_DEFAULT)
        getattr(self._field_defs, DB_wkn).textvar.set('')
        getattr(self._field_defs, DB_symbol).textvar.set(NOT_ASSIGNED)
        getattr(self._field_defs, DB_origin_symbol).textvar.set(NOT_ASSIGNED)
        getattr(self._field_defs, DB_adjustments).textvar.set('')
        getattr(self._field_defs, DB_currency).textvar.set(EURO)
        getattr(self._field_defs, DB_ISIN).combo_positioning = False
        getattr(self._field_defs, DB_name).combo_positioning = False

    def button_1_button5(self, event):

        self.validation()
        BuiltEnterBox.button_1_button5(self, event)

    def button_1_button6(self, event):

        self.validation()
        BuiltEnterBox.button_1_button6(self, event)

    def handle_ctrl_left(self):

        self._get_next_row('<')

    def handle_ctrl_right(self):

        self._get_next_row('>')

    def _get_next_row(self, sign):

        try:
            getattr(self._field_defs, DB_type).widget.focus()
            name = getattr(self._field_defs, DB_name).widget.get()
            result = self.mariadb.select_table_next(
                ISIN, [DB_ISIN, DB_name], DB_name, sign, name)
            if result:
                isin, name = result[0]
                getattr(self._field_defs, DB_ISIN).widget.focus()
                getattr(self._field_defs, DB_ISIN).textvar.set(isin)
                getattr(self._field_defs, DB_type).widget.focus()
                getattr(self._field_defs, DB_type).widget.icursor('0')
        except Exception:
            pass

    def focus_out_action(self, event):

        if event.widget.myId == DB_ISIN:
            isin = getattr(self._field_defs, DB_ISIN).widget.get()
            if isin in self.isins:
                _name = dict_get_first_key(self.get_name_isin, isin)
                getattr(self._field_defs, DB_name).textvar.set(_name)
        if event.widget.myId == DB_name:
            _name = getattr(self._field_defs, DB_name).widget.get()
            if _name in self.names:
                isin = self.get_name_isin[_name]
                getattr(self._field_defs, DB_ISIN).textvar.set(isin)
        if event.widget.myId == DB_ISIN or event.widget.myId == DB_name:
            result = self.mariadb.select_table(
                ISIN, self.field_list[2:], order=DB_name,
                name=getattr(self._field_defs, DB_name).widget.get())
            if result:
                type_, validity, wkn, origin_symbol, self.symbol, adjustments, currency = result[
                    0]
                getattr(self._field_defs, DB_type).textvar.set(type_)
                getattr(self._field_defs, DB_validity).textvar.set(validity)
                getattr(self._field_defs, DB_wkn).textvar.set(wkn)
                getattr(self._field_defs, DB_symbol).textvar.set(self.symbol)
                getattr(self._field_defs, DB_origin_symbol).textvar.set(
                    origin_symbol)
                getattr(self._field_defs, DB_adjustments).textvar.set(
                    adjustments)
                getattr(self._field_defs, DB_currency).textvar.set(currency)
        if event.widget.myId == DB_origin_symbol:
            if ALPHA_VANTAGE == getattr(self._field_defs, DB_origin_symbol).widget.get():
                name = getattr(self._field_defs, DB_name).widget.get()
                keywords = name.split(' ')[0]
                url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=' + \
                    keywords + '&apikey=' + self.key_aplpha_vantage
                r = requests.get(url)
                data = r.json()
                symbol_informations = ' '.join(
                    [INFORMATION, ALPHA_VANTAGE, DB_name.upper() + ':', name, '\n     >', keywords,  '<', 3 * '\n'])
                for dict_symbols in data['bestMatches']:
                    if dict_symbols['8. currency'] == 'EUR':
                        str_dict_symbols = str(dict_symbols).replace('{', '')
                        str_dict_symbols = str_dict_symbols.replace('}', '')
                        str_dict_symbols = str_dict_symbols.replace(
                            ',', ',     \n, ')
                        str_dict_symbols = str_dict_symbols.split(",")
                        symbol_informations = symbol_informations + \
                            2 * '\n' + '   '.join(str_dict_symbols)
                Informations.prices_informations = ' '.join(
                    [Informations.prices_informations, '\n' + symbol_informations])
                PrintMessageCode(title=self.title, header=Informations.PRICES_INFORMATIONS,
                                 text=Informations.prices_informations)
            elif YAHOO == getattr(self._field_defs, DB_origin_symbol).widget.get():
                webbrowser.open(WWW_YAHOO)

    def comboboxselected_action(self, event):

        self.focus_out_action(event)

    def validation_addon(self, field_def):
        """
        more field validations
        """
        if field_def.name == DB_symbol:
            symbol = getattr(self._field_defs, DB_symbol).widget.get()
            if symbol != NOT_ASSIGNED:
                result = self.mariadb.select_table(
                    ISIN, [DB_name, DB_symbol], symbol=symbol)
                if len(result) > 0 and result[0][0] != getattr(self._field_defs, DB_name).widget.get():
                    MessageBoxInfo(
                        title=self.title, message=MESSAGE_TEXT['SYMBOL_USED'].format(result))
        elif field_def.name == DB_validity:
            validity = getattr(self._field_defs, DB_validity).widget.get()
            if validity > VALIDITY_DEFAULT:
                getattr(self._field_defs, DB_validity).textvar.set(
                    VALIDITY_DEFAULT)


class Transaction(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        Enter Box Statements of Transaction Data

    PARAMETER:
        selected            RowNumber of selected Transaction
        transactions        Table of existing  Transactions (Named Tuples)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Selected  Statements of Transactions Data
    """

    def __init__(self, title, header, iban, isin, name, selected, transactions, mariadb):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.iban = iban
        self.isin = isin
        if isinstance(selected, int):
            transaction = transactions[selected]
            FieldNames = namedtuple(
                'FieldNames', [DB_name, DB_ISIN, DB_price_date, DB_counter, DB_transaction_type,
                               DB_price_currency, DB_price, DB_pieces, DB_amount_currency,
                               DB_posted_amount, DB_comments]
            )
            self.transaction_field_defs = FieldNames(
                FieldDefinition(name=DB_name, length=35, default_value=name),
                FieldDefinition(name=DB_ISIN, length=12, default_value=isin),
                FieldDefinition(name=DB_price_date, length=19, typ=TYP_DATE,
                                default_value=transaction.price_date),
                FieldDefinition(name=DB_counter, length=3,
                                default_value=transaction.counter),
                FieldDefinition(definition=COMBO,
                                name=DB_transaction_type, length=4,
                                default_value=transaction.transaction_type,
                                combo_values=TRANSACTION_TYPES,
                                allowed_values=TRANSACTION_TYPES),
                FieldDefinition(definition=COMBO,
                                name=DB_price_currency, length=3,
                                default_value=transaction.price_currency,
                                combo_values=CURRENCY_EXTENDED),
                FieldDefinition(name=DB_price, length=16, typ=TYP_DECIMAL,
                                default_value=transaction.price),
                FieldDefinition(name=DB_pieces, length=16, typ=TYP_DECIMAL,
                                default_value=transaction.pieces),
                FieldDefinition(definition=COMBO,
                                name=DB_amount_currency, length=3, combo_values=CURRENCY,
                                default_value=transaction.amount_currency),
                FieldDefinition(name=DB_posted_amount, length=16, typ=TYP_DECIMAL,
                                focus_in=True, default_value=transaction.posted_amount),
                FieldDefinition(name=DB_comments, length=200, mandatory=False,
                                default_value=transaction.comments),
            )
            self.change_field_defs()
            super().__init__(title=title, header=header, field_defs=self.transaction_field_defs,
                             button1_text=BUTTON_SAVE, button2_text=None)

    def change_field_defs(self):

        pass

    def focus_in_action(self, event):

        if event.widget.myId == DB_posted_amount:
            footer = field_validation(DB_price, getattr(
                self.transaction_field_defs, DB_price))
            if footer:
                self._footer.set(footer)
                return
            footer = field_validation(DB_pieces, getattr(
                self.transaction_field_defs, DB_pieces))
            if footer:
                self._footer.set(footer)
                return
            if getattr(self.transaction_field_defs, DB_price_currency).widget.get() != PERCENT:
                posted_amount = dec2.multiply(
                    getattr(self.transaction_field_defs,
                            DB_price).widget.get(),
                    getattr(self.transaction_field_defs, DB_pieces).widget.get())
                getattr(self.transaction_field_defs,
                        DB_posted_amount).textvar.set(posted_amount)


class TransactionChange(Transaction):
    """
    TOP-LEVEL-WINDOW        Change Statements of Transaction Data

    PARAMETER:
        selected            RowNumber of selected Transaction
        transactions        Table of existing  Transactions (Named Tuples)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Selected  Statements of Transactions Data
    """

    def __init__(self, title, iban, isin, name, selected, transactions, mariadb):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.iban = iban
        self.isin = isin
        header = MESSAGE_TEXT['TRANSACTION_HEADER_CHG']
        super().__init__(title, header, iban, isin, name,
                         selected, transactions, mariadb)

    def change_field_defs(self):

        getattr(self.transaction_field_defs, DB_name).protected = True
        getattr(self.transaction_field_defs, DB_ISIN).protected = True
        getattr(self.transaction_field_defs, DB_price_date).protected = True

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if self._footer.get() == '':
            if self.field_dict[DB_transaction_type] == TRANSACTION_RECEIPT:
                self.field_dict[DB_acquisition_amount] = 0
            self.mariadb.transaction_change(self.iban, self.field_dict)
            self._footer.set(MESSAGE_TEXT['DATA_SAVED'])
            self.quit_widget()


class TransactionNew(Transaction):
    """
    TOP-LEVEL-WINDOW        Change Statements of Transaction Data

    PARAMETER:
        selected            RowNumber of selected Transaction
        transactions        Table of existing  Transactions (Named Tuples)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Selected  Statements of Transactions Data
    """

    def __init__(self, title, iban, isin, name, selected, transactions, mariadb):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.mariadb = mariadb
        self.iban = iban
        self.isin = isin
        self.transactions = transactions
        if not self.transactions:
            self.transactions.append(TransactionNamedTuple(
                date_db.convert(datetime.today().now()
                                ), 0, TRANSACTION_RECEIPT, EURO, '0',
                '0', EURO, '0', '0', '0', ''))
        header = MESSAGE_TEXT['TRANSACTION_HEADER_NEW']
        super().__init__(title, header, iban, isin, name,
                         selected, self.transactions, mariadb)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if self._footer.get() == '':
            if self.field_dict[DB_transaction_type] == TRANSACTION_RECEIPT:
                self.field_dict[DB_acquisition_amount] = 0
            self.mariadb.transaction_new(
                self.iban, self.field_dict, self.transactions)
            destroy_widget(self._box_window)

    def validation_addon(self, field_def):

        global message_transaction_new
        if field_def.name == DB_price_date:
            price_date = field_def.widget.get()
            if not self.mariadb.select_data_exist(HOLDING, price_date=price_date, iban=self.iban):
                if message_transaction_new:
                    message_transaction_new = False
                    MessageBoxInfo(title=self.title,
                                   message=MESSAGE_TEXT['DOWNLOAD_HOLDING'])


class TransactionSync(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        PandasBox Generated Transactions

    PARAMETER:
        transactions        List of generated Tranasactions
    """

    def __init__(self, mariadb, iban,
                 title=MESSAGE_TITLE, header=None, transactions=[]):
        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.header = header
        self.iban = iban
        self.title = title
        self.transactions = []
        for transaction in transactions:
            self.transactions.append(list(transaction.values()))
        super().__init__(title=title, root=self,
                         dataframe=DataFrame(self.transactions,
                                             columns=list(transactions[0].keys())),
                         message=MESSAGE_TEXT['TABLE_CLICK']
                         )

    def handle_click(self, event):

        selected_row = self.pandas_table.get_row_clicked(event)
        for self.data_row in self.dataframe.itertuples(index=False, name='Transaction'):
            if selected_row == 0:
                break
            selected_row -= 1
        TransactionChange(self.title, MESSAGE_TEXT['TRANSACTION_HEADER_CHG'],
                          self.iban, self.data_row[DB_ISIN], self.data_row[DB_name],
                          selected_row, [self.data_row], self.mariadb)


class SepaCreditBox(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox SEPA Credit Transfer Data

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary of SEPA Credit Transfer Data
    """

    def __init__(self, bank, mariadb, account, title=MESSAGE_TITLE):

        Caller.caller = self.__class__.__name__
        self.mariadb = mariadb
        self.combo_values = self.mariadb.select_sepa_transfer_creditor_names()
        self.combo_values.remove(None)
        Field_Names = namedtuple(
            'Field_Names', [SEPA_CREDITOR_NAME, SEPA_CREDITOR_IBAN, SEPA_CREDITOR_BIC,
                            SEPA_CREDITOR_BANK_NAME, SEPA_CREDITOR_BANK_LOCATION, SEPA_AMOUNT,
                            SEPA_PURPOSE_1, SEPA_PURPOSE_2, SEPA_REFERENCE]
        )

        field_defs = Field_Names(
            FieldDefinition(definition=COMBO, name=SEPA_CREDITOR_NAME, length=70, selected=True,
                            combo_values=self.combo_values, focus_out=True),
            FieldDefinition(name=SEPA_CREDITOR_IBAN,
                            length=34, focus_out=True),
            FieldDefinition(name=SEPA_CREDITOR_BIC,
                            length=11, lformat=FORMAT_FIXED),
            FieldDefinition(name=SEPA_CREDITOR_BANK_NAME, length=70, mandatory=False,
                            protected=True),
            FieldDefinition(name=SEPA_CREDITOR_BANK_LOCATION, length=70, mandatory=False,
                            protected=True),
            FieldDefinition(name=SEPA_AMOUNT, length=14, typ=TYP_DECIMAL),
            FieldDefinition(name=SEPA_PURPOSE_1, length=70, mandatory=False),
            FieldDefinition(name=SEPA_PURPOSE_2, length=70, mandatory=False),
            FieldDefinition(name=SEPA_REFERENCE, length=35, mandatory=False)
        )
        header = MESSAGE_TEXT['SEPA_CRDT_TRANSFER'].format(
            bank.bank_name, account[KEY_ACC_PRODUCT_NAME], account[KEY_ACC_ACCOUNT_NUMBER])
        if 'HKCSE' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
            Field_Names = namedtuple(
                'Field_Names', [*Field_Names._fields] + [SEPA_EXECUTION_DATE])
            field_defs = Field_Names(
                *field_defs,
                FieldDefinition(name=SEPA_EXECUTION_DATE, length=10, typ=TYP_DATE,
                                default_value=date.today(), mandatory=False))
        super().__init__(
            header=header, title=title,
            button1_text=BUTTON_OK, button2_text=BUTTON_DELETE_ALL, button3_text=BUTTON_NEW,
            field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == SEPA_CREDITOR_IBAN and not check_iban(field_def.widget.get()):
            return self._footer.set(MESSAGE_TEXT['IBAN'])
        if field_def.name == SEPA_EXECUTION_DATE:
            date_ = date_ = field_def.widget.get()[0:10]
            try:
                day = int(date_.split('-')[2])
                month = int(date_.split('-')[1])
                year = int(date_.split('-')[0])
                date_ = date(year, month, day)
            except (ValueError, EOFError, IndexError):
                return self._footer.set(MESSAGE_TEXT['DATE'])
            days = date_ - date.today()
            if days.days < 0:
                return self._footer.set(MESSAGE_TEXT['DATE_TODAY'])

    def button_1_button1(self, event):

        BuiltEnterBox.button_1_button1(self, event)
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_positioning = True

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        getattr(self._field_defs, SEPA_CREDITOR_BANK_NAME).default_value = ''
        getattr(self._field_defs, SEPA_CREDITOR_BANK_LOCATION).default_value = ''
        for field_def in self._field_defs:
            field_def.widget.delete(0, END)
            if field_def.default_value is not None:
                field_def.widget.insert(0, field_def.default_value)
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_positioning = True

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        getattr(self._field_defs, SEPA_CREDITOR_NAME).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_BANK_NAME).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_BANK_LOCATION).textvar.set('')
        getattr(self._field_defs, SEPA_AMOUNT).textvar.set('')
        getattr(self._field_defs, SEPA_PURPOSE_1).textvar.set('')
        getattr(self._field_defs, SEPA_PURPOSE_2).textvar.set('')
        getattr(self._field_defs, SEPA_REFERENCE).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_positioning = False

    def comboboxselected_action(self, event):

        applicant_iban, applicant_bic, purpose = (
            self.mariadb.select_sepa_transfer_creditor_data(
                applicant_name=getattr(self._field_defs, SEPA_CREDITOR_NAME).widget.get()))
        if applicant_bic is not None:
            getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set(
                applicant_bic)
        if applicant_iban is not None:
            getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set(
                applicant_iban)
            self._bankdata(applicant_iban)
        if purpose is not None:
            getattr(self._field_defs, SEPA_PURPOSE_1).textvar.set(purpose[:70])
            getattr(self._field_defs, SEPA_PURPOSE_2).textvar.set(purpose[70:])

    def focus_out_action(self, event):

        if event.widget.myId == SEPA_CREDITOR_NAME:
            applicant_iban, applicant_bic, purpose = (
                self.mariadb.select_sepa_transfer_creditor_data(
                    applicant_name=getattr(self._field_defs, SEPA_CREDITOR_NAME).widget.get()))
            if applicant_bic is not None:
                getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set(
                    applicant_bic)
            if applicant_iban is not None:
                getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set(
                    applicant_iban)
                self._bankdata(applicant_iban)
            if purpose is not None:
                getattr(self._field_defs, SEPA_PURPOSE_1).textvar.set(
                    purpose[:70])
                getattr(self._field_defs, SEPA_PURPOSE_2).textvar.set(
                    purpose[70:])
        if event.widget.myId == SEPA_CREDITOR_IBAN:
            iban = getattr(self._field_defs, SEPA_CREDITOR_IBAN).widget.get()
            iban = iban.replace(' ', '')
            getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set(iban)
            self._bankdata(iban)

    def _bankdata(self, iban):
        bank_code = iban[4:12]
        field_dict = self.mariadb.select_table(
            BANKIDENTIFIER, [DB_name, DB_location, DB_bic], result_dict=True, code=bank_code)
        if field_dict and DB_name in field_dict[0]:
            getattr(self._field_defs, SEPA_CREDITOR_BANK_NAME).textvar.set(
                field_dict[0][DB_name])
        if field_dict and DB_location in field_dict[0]:
            getattr(self._field_defs,
                    SEPA_CREDITOR_BANK_LOCATION).textvar.set(field_dict[0][DB_location])
        if field_dict and DB_bic in field_dict[0]:
            getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set(
                field_dict[0][DB_bic])


class SelectCreateHolding_t(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Select ISINs created in table holding_t

    PARAMETER:
        checkbutton_texts    List  of Fields

        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 button1_text=BUTTON_APPEND, button2_text=BUTTON_REPLACE,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        Caller.caller = self.__class__.__name__
        super().__init__(
            title=title, header=MESSAGE_TEXT['CHECKBOX'],
            button1_text=button1_text,
            button2_text=button2_text,
            checkbutton_texts=checkbutton_texts
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()


class SelectFields(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Checkbutton

    PARAMETER:
        checkbutton_texts    List  of Fields
        standard             last selection stored in shelve files: key standard
        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 button1_text=BUTTON_NEXT,
                 button2_text=BUTTON_STANDARD, button3_text=BUTTON_SAVE_STANDARD,
                 button4_text=BUTTON_SELECT_ALL,
                 default_texts=[], standard=STANDARD,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        Caller.caller = self.__class__.__name__
        self.standard = standard
        super().__init__(
            title=title, header=MESSAGE_TEXT['CHECKBOX'],
            button1_text=button1_text, button2_text=button2_text, button3_text=button3_text,
            button4_text=button4_text,
            default_texts=default_texts,
            checkbutton_texts=checkbutton_texts
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        standard = shelve_get_key(BANK_MARIADB_INI, self.standard)
        if standard:
            for idx, check_text in enumerate(self.checkbutton_texts):
                if check_text in standard:
                    self._check_vars[idx].set(1)
                else:
                    self._check_vars[idx].set(0)

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.validate_all()
        shelve_put_key(BANK_MARIADB_INI, (self.standard, self.field_list))

    def validate_all(self):

        if self.standard == MENU_TEXT['Show'] + MENU_TEXT['Statement']:
            if DB_amount in self.field_list:
                if DB_status not in self.field_list:
                    self.field_list.append(DB_status)
                if DB_currency not in self.field_list:
                    self.field_list.append(DB_currency)
            if DB_opening_balance in self.field_list:
                if DB_opening_status not in self.field_list:
                    self.field_list.append(DB_opening_status)
                if DB_opening_currency not in self.field_list:
                    self.field_list.append(DB_opening_currency)
            if DB_closing_balance in self.field_list:
                if DB_closing_status not in self.field_list:
                    self.field_list.append(DB_closing_status)
                if DB_closing_currency not in self.field_list:
                    self.field_list.append(DB_closing_currency)
        elif self.standard == MENU_TEXT['Show'] + MENU_TEXT['Holding']:
            if (
                (DB_total_amount in self.field_list or
                 DB_total_amount_portfolio in self.field_list or
                 DB_acquisition_amount in self.field_list)
                and
                    DB_amount_currency not in self.field_list):
                self.field_list.append(DB_amount_currency)
            if (
                (DB_market_price in self.field_list or
                 DB_acquisition_price in self.field_list)
                and
                    DB_price_currency not in self.field_list):
                self.field_list.append(DB_price_currency)


class SelectDownloadPrices(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Select ISINs download Prices

    PARAMETER:
        checkbutton_texts    List  of Fields

        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 button1_text=BUTTON_APPEND, button2_text=BUTTON_REPLACE, button3_text=BUTTON_DELETE,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        Caller.caller = self.__class__.__name__
        super().__init__(
            title=title, header=MESSAGE_TEXT['CHECKBOX'],
            button1_text=button1_text,
            button2_text=button2_text, button3_text=button3_text,
            checkbutton_texts=checkbutton_texts
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()


class PrintList(BuiltText):
    """
    TOP-LEVEL-WINDOW        TextBox with ScrollBars (Only Output)

    PARAMETER:
        header              Header Line (Column Desscription)
        text                String of Text Lines
    """

    def set_tags(self, textline, line):
        if not line % 2:
            self.text_widget.tag_add(LIGHTBLUE, str(line + 1) + '.0',
                                     str(line + 1) + '.' + str(len(textline)))
            self.text_widget.tag_config(LIGHTBLUE, background='LIGHTBLUE')


class PandasBoxHolding(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Holdings

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframed rows (named tuples 'PANDAS_NAME_SHOW'
    """

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            columns=[DB_amount_currency, DB_price_currency, DB_currency],
            axis=1, errors='ignore')
        self.dataframe = self.dataframe.fillna(value='')
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            (data, columns) = self.dataframe
            self.dataframe = DataFrame(data)[columns]
            if DB_total_amount in columns and DB_acquisition_amount in columns:
                self.dataframe[FN_PROFIT] = self.dataframe[DB_total_amount] - \
                    self.dataframe[DB_acquisition_amount]
        elif isinstance(self.dataframe, DataFrame):
            pass
        else:
            self.dataframe = DataFrame(self.dataframe)


class PandasBoxHoldingPercent(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Holdings
                            Period Changes in Percent

    PARAMETER:
        dataframe           (data_to_date, data_from_date)
    """

    def _get_name(self, position_dict):

        return position_dict[DB_name]

    def create_dataframe(self):

        data_to_date, data_from_date = self.dataframe
        # delete complete sale and buy positions of to_date and from_date
        to_map_set = {*map(self._get_name, data_to_date)}
        from_map_set = {*map(self._get_name, data_from_date)}
        removes = to_map_set.difference(from_map_set)
        data_to_date = [
            item for item in data_to_date if item[DB_name] not in removes]
        removes = from_map_set.difference(to_map_set)
        data_from_date = [
            item for item in data_from_date if item[DB_name] not in removes]
        data_to_date = sorted(data_to_date, key=lambda i: (i[DB_name]))
        data_from_date = sorted(data_from_date, key=lambda i: (i[DB_name]))
        # create dataframe
        self.dataframe = DataFrame(data_to_date)
        dataframe_from_date = DataFrame(data_from_date)
        columns = [DB_total_amount, DB_acquisition_amount,
                   DB_pieces, DB_market_price]
        self.dataframe[columns] = self.dataframe[columns].apply(to_numeric)
        dataframe_from_date[columns] = dataframe_from_date[columns].apply(
            to_numeric)
        # adjust sales and purchases
        if not dataframe_from_date[DB_pieces].equals(self.dataframe[DB_pieces]):
            dataframe_from_date[DB_total_amount] = (
                dataframe_from_date[DB_total_amount] * self.dataframe[DB_pieces] / dataframe_from_date[DB_pieces])
        # add sum row
        sum_row = {}
        sum_row[DB_total_amount] = self.dataframe[DB_total_amount].sum()
        sum_row[DB_acquisition_amount] = self.dataframe[DB_acquisition_amount].sum()
        sum_row[DB_amount_currency] = EURO
        self.dataframe.loc[len(self.dataframe.index)] = sum_row
        sum_row[DB_total_amount] = dataframe_from_date[DB_total_amount].sum()
        sum_row[DB_acquisition_amount] = dataframe_from_date[DB_acquisition_amount].sum()
        dataframe_from_date.loc[len(dataframe_from_date.index)] = sum_row

        # compute percentages
        self.dataframe[FN_PROFIT_LOSS] = self.dataframe[DB_total_amount] - \
            self.dataframe[DB_acquisition_amount]
        self.dataframe[FN_TOTAL_PERCENT] = (
            self.dataframe[FN_PROFIT_LOSS] / self.dataframe[DB_acquisition_amount] * 100)
        self.dataframe[FN_PERIOD_PERCENT] = (
            self.dataframe[DB_total_amount] /
            dataframe_from_date[DB_total_amount]
            * 100 - 100)
        self.dataframe = self.dataframe.drop(
            [FN_PROFIT_LOSS, DB_acquisition_amount], axis=1)
        self.dataframe = self.dataframe[[DB_name, DB_total_amount, DB_market_price, DB_pieces,
                                         FN_TOTAL_PERCENT, FN_PERIOD_PERCENT]]

    def set_column_format(self):

        self.column_format = {FN_TOTAL_PERCENT: (E, '%', 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL),
                              FN_PERIOD_PERCENT: (E, '%', 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)}
        BuiltPandasBox.set_column_format(self)


class PandasBoxHoldingPortfolios(PandasBoxHolding):
    """
    TOP-LEVEL-WINDOW        Shows Totals of Portfolios
                            Changes (Daily/Total) in Percent

    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        # create dataframe
        set_option('display.float_format', lambda x: '%0.2f' % x)
        columns = [DB_price_date, DB_total_amount_portfolio,
                   DB_acquisition_amount]
        self.dataframe = DataFrame(self.dataframe, columns=columns[:3])
        self.dataframe[columns[1:]
                       ] = self.dataframe[columns[1:]].apply(to_numeric)
        # Drop first row
        # self.dataframe.drop(
        #    index=self.dataframe.index[0], axis=0,  inplace=True)
        self.dataframe[DB_price_date] = to_datetime(
            self.dataframe[DB_price_date]).dt.date
        self.dataframe.set_index(DB_price_date, inplace=True)
        # compute percentages
        self.dataframe[FN_PROFIT_LOSS] = (
            self.dataframe[DB_total_amount_portfolio] -
            self.dataframe[DB_acquisition_amount]
        )
        self.dataframe[FN_TOTAL_PERCENT] = (
            self.dataframe[FN_PROFIT_LOSS] /
            self.dataframe[DB_acquisition_amount]
            * 100)
        self.dataframe[DB_total_amount_portfolio]
        price_date = self.dataframe.first_valid_index()
        self.dataframe[FN_PERIOD_PERCENT] = (
            self.dataframe[DB_total_amount_portfolio] /
            self.dataframe.loc[price_date, DB_total_amount_portfolio]
            * 100 - 100)
        self.dataframe = self.dataframe.round(2)


class PandasBoxHoldingTransaction(PandasBoxHolding):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe Transactions of Holdings

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframed rows (named tuples 'PANDAS_NAME_SHOW'
    """

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            (data, columns) = self.dataframe
            self.dataframe = DataFrame(data)[columns]
        elif isinstance(self.dataframe, DataFrame):
            pass
        else:
            self.dataframe = DataFrame(self.dataframe)
        if DB_transaction_type in self.dataframe.columns and DB_posted_amount in self.dataframe.columns:
            deliveries = self.dataframe[DB_transaction_type] == TRANSACTION_DELIVERY
            self.dataframe[DB_posted_amount].where(
                deliveries, -self.dataframe[DB_posted_amount], inplace=True)


class PandasBoxPrices(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Prices

    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (db_field, data, self.origin, mode) = self.dataframe
        dataframe = DataFrame(data)
        columns = [DB_name]
        self.dataframe = dataframe.pivot(
            index=DB_price_date, columns=columns, values=db_field)
        columns = list(self.dataframe)
        self.dataframe[columns[0]] = self.dataframe[columns[0]].apply(
            to_numeric, errors='ignore')
        if mode == PERCENT:
            for idx, dataframe_column in enumerate(self.dataframe.columns):
                for idx in range(self.dataframe.shape[0]):
                    base_value = self.dataframe.iat[0, idx]
                    if base_value != 0:
                        self.dataframe[dataframe_column] = (
                            self.dataframe[dataframe_column] / base_value - 1) * 100
                        break

    def set_column_format(self):

        for column in self.dataframe.columns:
            _, name_ = column
            if self.origin[name_] == ALPHA_VANTAGE:
                # AlphaVamtageColumns are aqua
                self.pandas_table.columncolors[column] = '#00FFFF'
            else:
                # Yahoo columns are violet
                self.pandas_table.columncolors[column] = '#EE82EE'
        BuiltPandasBox.set_column_format(self)


class PandasBoxIsins(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Isins

    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (db_field, data, mode, columns) = self.dataframe
        if db_field == FN_PROFIT_LOSS:
            dataframe = DataFrame(data, columns=[
                DB_name, DB_price_date, DB_total_amount,
                DB_acquisition_amount])
            dataframe[FN_PROFIT_LOSS] = dataframe[DB_total_amount] -\
                dataframe[DB_acquisition_amount]
            dataframe.drop(
                [DB_acquisition_amount, DB_total_amount], inplace=True, axis=1)
        else:
            dataframe = DataFrame(data)
        dataframe = dataframe.dropna(how='all', axis=1)
        base_rows = {}
        if mode == PERCENT:
            for column in columns:
                dataframe_column = dataframe[dataframe[DB_name].isin(
                    [column])]  # the index and column must match
                if not dataframe_column.empty:
                    base_rows[column] = dataframe_column.iloc[0, 2]

        self.dataframe = dataframe.pivot(
            index='price_date', columns='name', values=db_field)
        if mode == PERCENT:
            for name_ in base_rows.keys():
                if base_rows[name_] != 0:
                    self.dataframe[name_] = (
                        self.dataframe[name_] / base_rows[name_] - 1) * 100

    def set_column_format(self):

        self.column_format = {}
        for column in self.dataframe.columns:
            self.column_format[column] = (
                E, '%', 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)
        BuiltPandasBox.set_column_format(self)


class PandasBoxStatement(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Statements

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframed rows (named tuples 'PANDAS_NAME_SHOW'
    """

    def _debit(self, amount, status=CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            data, columns = self.dataframe
            self.dataframe = DataFrame(data=data, columns=columns)
        names = list(self.dataframe.columns)
        if DB_amount in names:
            self.dataframe[DB_amount] = self.dataframe[[DB_amount, DB_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if DB_opening_balance in names:
            self.dataframe[DB_opening_balance] = self.dataframe[[DB_opening_balance, DB_opening_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if DB_closing_balance in names:
            self.dataframe[DB_closing_balance] = self.dataframe[[DB_closing_balance, DB_closing_status]].apply(
                lambda x: self._debit(*x), axis=1)

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            axis=1, errors='ignore',
            columns=[DB_currency, DB_status, DB_opening_currency, DB_opening_status,
                     DB_closing_currency, DB_closing_status, DB_amount_currency, DB_price_currency
                     ]
        )
        self.dataframe = self.dataframe.fillna(value='')
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()


class PandasBoxBalances(PandasBoxStatement):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Balances

    PARAMETER:
        dataframe           DataFrame object
    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframe rows (named tuples 'PANDAS_NAME_SHOW'
    """

    def create_dataframe(self):

        PandasBoxStatement.create_dataframe(self)
        self.dataframe.drop(KEY_ACC_BANK_CODE, inplace=True, axis=1)


class PandasBoxBalancesAllBanks(PandasBoxStatement):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Balances

    PARAMETER:
        dataframe           DataFrame object
    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframe rows (named tuples 'PANDAS_NAME_SHOW'
    """

    def create_dataframe(self):

        bank_names = dictbank_names()
        dataframe_all = concat(self.dataframe)
        max_entry_date = dataframe_all[DB_entry_date].max()
        # total sum all Banks
        self.dataframe_append_sum(
            dataframe_all, [DB_closing_balance, DB_opening_balance])
        dataframe_all[KEY_BANK_NAME] = FN_TOTAL
        dataframe_all[DB_entry_date] = max_entry_date
        # total sum of each bank
        dataframes = []
        for dataframe in self.dataframe:
            self.dataframe_append_sum(
                dataframe, [DB_closing_balance, DB_opening_balance])
            dataframe[DB_entry_date] = max_entry_date
            dataframe[KEY_BANK_NAME] = ''
            dataframe.at[len(
                dataframe)-1, KEY_BANK_NAME] = bank_names[dataframe.at[0, KEY_BANK_CODE]]
            dataframes.append(dataframe)
        # append total sum all Bank
        dataframes.append(dataframe_all.tail(1))
        self.dataframe = concat(dataframes, ignore_index=True)
        PandasBoxStatement.create_dataframe(self)
        self.dataframe.reset_index()
        # calculate percent changes
        self.dataframe[FN_DAILY_PERCENT] = (
            ((self.dataframe[DB_closing_balance] - self.dataframe[DB_opening_balance])
             / self.dataframe[DB_opening_balance]) * 100
        ) .apply(lambda x: dec2.convert(x))
        # if no changes set set percent = 0
        self.dataframe[FN_DAILY_PERCENT] = self.dataframe.apply(
            lambda row: 0 if max_entry_date > row[DB_entry_date] else row[FN_DAILY_PERCENT], axis=1)
        # format display
        self.dataframe = self.dataframe[[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                         KEY_ACC_PRODUCT_NAME, DB_entry_date, DB_closing_balance,
                                         FN_DAILY_PERCENT, KEY_BANK_NAME]]
        bank_name = self.dataframe[KEY_BANK_NAME]
        self.dataframe.drop(
            [KEY_BANK_NAME, KEY_ACC_BANK_CODE, DB_entry_date], inplace=True, axis=1)
        self.dataframe.insert(0, KEY_BANK_NAME, bank_name)

    def set_column_format(self):

        self.column_format = {FN_TOTAL: (
            E, EURO, 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)}
        PandasBoxStatement.set_column_format(self)

    def set_row_format(self):

        for i, row in self.pandas_table.model.df.iterrows():
            if row[KEY_BANK_NAME]:
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')


class PandasBoxTotals(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Totals

    PARAMETER:
        dataframe           data_total_amounts (list of tuples)

    INSTANCE ATTRIBUTES:
        selected_row        list index of selected row
        data_table          list of dataframed rows (named tuples 'PANDAS_NAME_SHOW'
    """

    def _debit(self, amount, status=CREDIT, places=2):

        if status == DEBIT:
            amount = amount * -1
        return amount

    def _acc_product_name(self, x):

        acc_product_name = dictaccount(x[4:12], x[12:])[KEY_ACC_PRODUCT_NAME]
        if acc_product_name:
            return acc_product_name
        else:
            return x[12:]

    def create_dataframe(self):

        self.dataframe = DataFrame(self.dataframe, columns=[
            DB_iban, DB_date, DB_status, DB_total_amount])
        bank_names = dictbank_names()
        self.dataframe['BANK'] = self.dataframe.apply(
            lambda row: bank_names[row[DB_iban][4:12]], axis=1)
        self.dataframe['ACCOUNT'] = self.dataframe.apply(
            lambda row: self._acc_product_name(row[DB_iban]), axis=1)
        self.dataframe[DB_iban] = self.dataframe[DB_iban].apply(
            lambda x: x[12:].lstrip('0'))
        self.dataframe[DB_total_amount] = self.dataframe[[DB_total_amount, DB_status]].apply(
            lambda x: self._debit(*x), axis=1)
        self.dataframe = self.dataframe.sort_values([DB_iban, DB_date])
        self.dataframe = self.dataframe.pivot_table(index=[DB_date], columns=[
            'BANK', 'ACCOUNT'], values=[DB_total_amount])
        last_index = None
        for row_index, row in self.dataframe.iterrows():
            for column_index, x in row.items():
                if x != x and last_index is not None:
                    self.dataframe.at[row_index,
                                      column_index] = self.dataframe.at[last_index, column_index]
            last_index = row_index
        self.dataframe[FN_TOTAL] = self.dataframe.sum(
            axis=1).apply(lambda x: dec2.convert(x))


class PandasBoxTransactionProfit(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Transactions

    PARAMETER:
        dataframe           List of tuples with transaction data
    """

    def create_dataframe(self):

        self.dataframe = DataFrame(
            self.dataframe,
            columns=[DB_ISIN, DB_name, FN_PROFIT, DB_amount_currency, DB_pieces])
        self.dataframe.drop(columns=[DB_pieces], inplace=True, axis=1)
        sum_row = {DB_ISIN: '',  DB_name: 'TOTAL: ',
                   FN_PROFIT: self.dataframe[FN_PROFIT].sum(), DB_amount_currency: EURO}
        self.dataframe.loc[len(self.dataframe.index)] = sum_row

    def set_column_format(self):

        self.column_format = {FN_PROFIT: (
            E, DB_amount_currency, 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)}
        BuiltPandasBox.set_column_format(self)


class PandasBoxTransactionDetail(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Transactions

    PARAMETER:
        dataframe           List of tuples with transaction data
    """

    def create_dataframe(self):

        self.count_transactions, data = self.dataframe
        self.dataframe = DataFrame(
            data,
            columns=[DB_price_date, DB_counter, DB_transaction_type,
                     DB_price, DB_pieces, DB_posted_amount])
        deliveries = self.dataframe[DB_transaction_type] == TRANSACTION_RECEIPT
        self.dataframe[DB_pieces].where(  # Replace values where the condition is False.
            deliveries, -self.dataframe[DB_pieces], inplace=True)
        self.dataframe[FN_PIECES_CUM] = self.dataframe[DB_pieces].cumsum()

        receipts = self.dataframe[DB_transaction_type] == TRANSACTION_DELIVERY
        self.dataframe[DB_posted_amount].where(receipts, -self.dataframe[DB_posted_amount],
                                               inplace=True)
        self.dataframe[FN_PROFIT_CUM] = self.dataframe[DB_posted_amount].cumsum()
        closed_postion = self.dataframe[FN_PIECES_CUM] == 0
        self.dataframe[FN_PROFIT_CUM].where(
            closed_postion, other=0, inplace=True)
        self.dataframe.drop(
            columns=[DB_counter], inplace=True)

    def set_column_format(self):

        self.column_format = {FN_PIECES_CUM: (E, '', 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL),
                              FN_PROFIT_CUM: (E, DB_amount_currency, 2, COLOR_NEGATIVE, COLUMN_FORMATS_TYP_DECIMAL)}
        BuiltPandasBox.set_column_format(self)

    def set_row_format(self):

        if self.count_transactions < self.dataframe.shape[0]:
            self.pandas_table.setRowColors(
                self.count_transactions, COLOR_HOLDING, 'all')


class PandasBoxAcquisitionTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Holding Acquisition Amounts
    """

    def __init__(self, title, header, bank_name, iban, isin, name_, period, acquisition_data, mariadb):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.bank_name = bank_name
        self.iban = iban
        self.isin = isin
        self.name_ = name_
        self.acquisition_data = acquisition_data
        self.mariadb = mariadb
        self.period = period
        super().__init__(title=title, dataframe=self.acquisition_data, name='Acquisition',
                         message=header,  enable_menus=False, editable=False, showtoolbar=False)

    def create_dataframe(self):

        self.dataframe = DataFrame(
            self.dataframe,
            columns=[
                DB_price_date, DB_price_currency, DB_market_price,
                DB_acquisition_price, DB_pieces, DB_amount_currency,
                DB_total_amount, DB_acquisition_amount, DB_origin])

    def handle_click(self, event):
        """
        Get selected Row Number (start with 0) and Row_Ddata
        """
        self.selected_row = self.pandas_table.get_row_clicked(
            event)  # starts with 0
        self.processing()
        self.quit_widget()

    def processing(self):

        acquisition_values = Acquisition(
            header=self.title,
            data=[HoldingAcquisition(*self.data_table[self.selected_row])]
        )
        if acquisition_values.button_state == WM_DELETE_WINDOW:
            return
        data_row = asdict(HoldingAcquisition(*acquisition_values.array[0]))
        data_row[DB_acquisition_amount] = dec2.convert(
            data_row[DB_acquisition_amount])
        if data_row[DB_price_currency] == PERCENT:
            data_row[DB_acquisition_price] = dec6.convert(
                data_row[DB_acquisition_price])
        else:
            data_row[DB_acquisition_price] = dec6.divide(data_row[DB_acquisition_amount],
                                                         data_row[DB_pieces])
        self.mariadb.update_holding_acquisition(
            self.iban, self.isin, HoldingAcquisition(**data_row), period=self.period, mode="ALL")

    def set_properties(self):

        for index, _ in self.dataframe.iterrows():
            if index != 0:
                if ((self.dataframe.iloc[index - 1][DB_acquisition_price] !=
                        self.dataframe.iloc[index][DB_acquisition_price])
                    or
                    (self.dataframe.iloc[index - 1][DB_pieces] !=
                     self.dataframe.iloc[index][DB_pieces])):
                    self.pandas_table.setRowColors(
                        rows=index, clr='red', cols='all')
                else:
                    self.pandas_table.setRowColors(
                        rows=index, clr='#F4F4F3', cols='all')


class PandasBoxTransactionTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Transactions
    """

    def __init__(self, title, header, bank_name, iban, isin, name_, period, transactions_data, mariadb):

        Caller.caller = self.__class__.__name__
        self.bank_name = bank_name
        self.iban = iban
        self.isin = isin
        self.name_ = name_
        self.transactions_data = transactions_data
        self.mariadb = mariadb
        super().__init__(title=title, dataframe=self.transactions_data, name='Transaction',
                         message=header, root=self, editable=False, enable_menus=False, edit_rows=True)

    def create_dataframe(self):

        self.dataframe = DataFrame(
            self.dataframe,
            columns=[DB_price_date, DB_counter, DB_transaction_type,
                     DB_price_currency, DB_price, DB_pieces,
                     DB_amount_currency, DB_posted_amount, DB_comments])

    def new_row(self):  # caller class ToolBarRows

        TransactionNew(MESSAGE_TEXT['TRANSACTION_TITLE'].format(self.bank_name, self.name_),
                       self.iban, self.isin, self.name_, self.selected_row, self.data_table,
                       self.mariadb)
        self.quit_widget()

    def change_row(self):  # caller class ToolBarRows

        TransactionChange(MESSAGE_TEXT['TRANSACTION_TITLE'].format(self.bank_name, self.name_),
                          self.iban, self.isin, self.name_, self.selected_row, self.data_table,
                          self.mariadb)
        self.quit_widget()

    def del_row(self):  # caller class ToolBarRows

        if isinstance(self.selected_row, int):
            msg = MessageBoxAsk(
                title=MESSAGE_TEXT['TRANSACTION_TITLE'].format(
                    self.bank_name, self.name_),
                message=MESSAGE_TEXT['TRANSACTION_HEADER_DEL_MESSAGE'].format(
                    self.name_, self.data_table[self.selected_row].price_date,
                    self.data_table[self.selected_row].counter)
            )
            if msg.result:
                self.mariadb.transaction_delete(iban=self.iban, ISIN=self.isin,
                                                counter=self.data_table[self.selected_row].counter,
                                                price_date=self.data_table[self.selected_row].price_date,)
            self.quit_widget()


class PrintMessageCode(BuiltText):
    """
    TOP-LEVEL-WINDOW        TextBox with ScrollBars (Only Output)

    PARAMETER:
        header              Header Line (Column Description)
        text                String of Text Lines

    SHOWS Text Sheet if one of following text line qualifiers exist:

        INFORMATION = 'INFORMATION: '
        WARNING = 'WARNING:     '
        ERROR = 'ERROR:       '
    """

    def set_tags(self, textline, line):
        if len(textline) > 13:
            if textline[0:13] == ERROR:
                self.text_widget.tag_add(ERROR, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(ERROR, foreground='RED')
            elif textline[0:13] == WARNING:
                self.text_widget.tag_add(WARNING, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(WARNING, foreground='BLUE')
            elif textline[0:13] == INFORMATION:
                self.text_widget.tag_add(INFORMATION, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(INFORMATION, foreground='GREEN')

    def destroy_widget(self, text):

        info = re.compile(INFORMATION)
        if info.search(text):
            return False
        warn = re.compile(WARNING)
        if warn.search(text):
            return False
        err = re.compile(ERROR)
        if err.search(text):
            return False
        return True


class VersionTransaction(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Version of HKKAZ, HKSAL, HKWPD to use

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion)
                            Transactions HKAKZ, HKSAL, HKWPD
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of Version of Used Transactions
    """

    def __init__(self, title, bank_code, transaction_versions):

        Caller.caller = self.__class__.__name__
        self.bank_code = bank_code
        transaction_version_allowed = shelve_get_key(self.bank_code,
                                                     KEY_VERSION_TRANSACTION_ALLOWED)
        if transaction_version_allowed:
            field_defs = [
                FieldDefinition(definition=COMBO,
                                name='HKKAZ statements', length=1,
                                allowed_values=transaction_version_allowed['KAZ'],
                                combo_values=transaction_version_allowed['KAZ']),
                FieldDefinition(definition=COMBO,
                                name='HKWPD holdings', length=1,
                                allowed_values=transaction_version_allowed['WPD'],
                                combo_values=transaction_version_allowed['WPD']),
            ]
            _set_defaults(field_defs,
                          (transaction_versions['KAZ'], transaction_versions['WPD']))
            super().__init__(title=title,
                             header='Transaction Versions ({})'.format(
                                 self.bank_code),
                             field_defs=field_defs)
        else:
            MessageBoxTermination()

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if self._footer.get() == '':
            for key in self.field_dict.keys():
                self.field_dict[key] = int(self.field_dict[key])
            self.quit_widget()
