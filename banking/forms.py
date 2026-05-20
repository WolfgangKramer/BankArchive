#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 28.01.2020
    __updated__ = "2024-11-28"
@author: Wolfgang Kramer
"""

import re
import webbrowser
import requests
import ta

from typing import Dict, List, Any
from decimal import Decimal
from bisect import bisect_left
from collections import namedtuple
from datetime import date, timedelta, datetime
from tkinter import filedialog, Menu
from fints.formals import CreditDebit2
from pandas import DataFrame, to_numeric, concat, to_datetime, set_option
from pandastable import TableModel
from  copy import copy

import banking.declarations_mariadb as declm
import banking.declarations as decl
import banking.message_handler as msg

from banking.repository import Repository
from banking.services import Services
from banking.formbuilts import (
    BuiltTableRowBox, BuiltPandasBox, BuiltCheckButton, BuiltEnterBox, BuiltText, BuiltSelectBox,
    FieldDefinition, destroy_widget, )
from banking.utils import (
    application_store,
    Calculate,
    dec2,
    date_days,
    get_popup_menu_text, get_menu_text,
    http_error_code)

def _set_defaults(field_defs=[FieldDefinition()], default_values=(1,)):

    if default_values:
        if len(field_defs) < len(default_values):
            msg.MessageBoxTermination(
                info='SET_DEFAULTS: Items of Field Definition less than Items of Default_Values')
            return False  # thread checking
        for idx, item in enumerate(default_values):
            field_defs[idx].default_value = item
    return field_defs


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

        self.title = ' '.join([title, function.upper()])
        _field_defs = []
        decl.ALPHA_VANTAGE_REQUIRED_COMBO[declm.DB_symbol] = alpha_vantage_symbols
        for parameter in parameter_list:
            if parameter in decl.ALPHA_VANTAGE_REQUIRED:
                if parameter in decl.ALPHA_VANTAGE_REQUIRED_COMBO.keys():
                    _field_defs.append(FieldDefinition(
                        definition=decl.COMBO, name=parameter.upper(), length=25,
                        combo_values=decl.ALPHA_VANTAGE_REQUIRED_COMBO[parameter]))
                else:
                    _field_defs.append(FieldDefinition(
                        definition=decl.ENTRY, name=parameter.upper(), length=25))
            elif parameter in decl.ALPHA_VANTAGE_OPTIONAL_COMBO.keys():
                _field_defs.append(FieldDefinition(
                    definition=decl.COMBO, name=parameter.upper(), length=25, mandatory=False,
                    default_value=decl.ALPHA_VANTAGE_OPTIONAL_COMBO[parameter][0],
                    combo_values=decl.ALPHA_VANTAGE_OPTIONAL_COMBO[parameter]))
            elif parameter == 'apikey':
                _field_defs.append(FieldDefinition(
                    definition=decl.ENTRY, name=parameter.upper(), length=25,
                    default_value=api_key))
            else:
                _field_defs.append(FieldDefinition(
                    definition=decl.ENTRY, name=parameter.upper(), length=25, mandatory=False))
        FieldNames = namedtuple('FieldNames', parameter_list)
        self._field_defs = FieldNames(*_field_defs)
        if default_values:
            _set_defaults(_field_defs, default_values)
        super().__init__(title=title,
                         button1_text=decl.BUTTON_DATA, button2_text=decl.BUTTON_ALPHA_VANTAGE,
                         field_defs=self._field_defs)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():
            self.quit_widget()

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.quit_widget()


class AppCustomizing(BuiltTableRowBox):
    """
    Top-level window for application customizing.

    Attributes:
        button_state (str): Selected button action
        field_dict (dict): Current field values
    """

    def __init__(self, row_dict):
        # Available options for dropdowns
        alpha_vantage_price_period_list = [
            decl.TIME_SERIES_INTRADAY,
            decl.TIME_SERIES_DAILY,
            decl.TIME_SERIES_DAILY_ADJUSTED,
            decl.TIME_SERIES_WEEKLY,
            decl.TIME_SERIES_WEEKLY_ADJUSTED,
            decl.TIME_SERIES_MONTHLY,
        ]

        show_messages_list = [decl.INFORMATION, decl.WARNING, decl.ERROR]

        combo_dict = {
            declm.DB_alpha_vantage_price_period: alpha_vantage_price_period_list,
            declm.DB_show_messages: show_messages_list,
        }

        super().__init__(
            declm.APPLICATION,
            declm.APPLICATION_VIEW,
            row_dict,
            focus_in=[declm.DB_directory],
            combo_dict=combo_dict,
        )

    def focus_in_action(self, event):
        """Handle focus events for input fields."""

        if event.widget.myId == declm.DB_directory:
            # Open directory picker
            directory = filedialog.askdirectory()

            if directory:
                getattr(
                    self._field_defs,
                    declm.DB_directory
                ).textvar.set(directory)

            # Move focus to next field
            getattr(
                self._field_defs,
                declm.DB_show_messages
            ).widget.focus_set()


class SelectLedgerAccountCategory(BuiltSelectBox):
    """
    Selection: Ledger Account, Period
    Column Fields are not selectable
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Accounts
        combo_values = []
        accounts = self.repo.get_all_accounts()
        if accounts:
            for account_name in accounts:
                combo_values.append(
                    ' '.join([account_name[0], account_name[1]]))
            field_defs_list.append(self.create_combo_field(
                declm.DB_account, 50, decl.TYP_ALPHANUMERIC, combo_values))
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', declm.LEDGER_COA.upper()))
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[decl.FN_FROM_DATE] = date(datetime.now().year, 1, 1)
            self.data_dict[decl.FN_TO_DATE] = date(datetime.now().year, 12, 31)
        return field_defs_list


class SelectLedgerAccount(BuiltSelectBox):
    """
    Selection: Ledger Account, Period
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Accounts
        combo_values = []
        accounts = self.repo.get_all_accounts()
        if accounts:
            for account_name in accounts:
                combo_values.append(
                    ' '.join([account_name[0], account_name[1]]))
            field_defs_list.append(self.create_combo_field(
                declm.DB_account, 50, decl.TYP_ALPHANUMERIC, combo_values))
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', declm.LEDGER_COA.upper()))
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # separator line
        self.separator = [declm.DB_account, decl.FN_TO_DATE]
        # check_buttons
        for field_name in declm.TABLE_FIELDS_PROPERTIES[declm.LEDGER_VIEW].keys():
            field_defs_list.append(
                self.create_check_field(field_name, declm.TABLE_FIELDS_PROPERTIES[declm.LEDGER_VIEW][field_name].comment))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[decl.FN_FROM_DATE] = date(datetime.now().year, 1, 1)
            self.data_dict[decl.FN_TO_DATE] = date(datetime.now().year, 12, 31)
        return field_defs_list

class SelectLedgerDailyBalanceAccounts(BuiltSelectBox):
    """
    Selection: Accounts in table ledger_daily_balance
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Accounts
        accounts_dict = self.repo.get_ledger_daily_balance_account_name()
        if not accounts_dict:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', declm.LEDGER_DAILY_BALANCE.upper()))

        # check_buttons
        for account, account_name in accounts_dict.items():
            field_defs_list.append(
                self.create_check_field(decl.FN_ACCOUNT_NUMBER + account, account_name))
        return field_defs_list

class InputPeriod(BuiltSelectBox):
    """
    Selection: Period
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[decl.FN_FROM_DATE] = date(datetime.now().year, 1, 1)
            self.data_dict[decl.FN_TO_DATE] = date(datetime.now().year, 12, 31)
        return field_defs_list


class InputPeriodNew(InputPeriod):
    """
    Selection: Period
    """

    def get_selection(self):
        """
        no initialization of the selection fields with the used values of last session
        """

        pass


class InputDate(BuiltSelectBox):
    """
    Selection: Date
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # date
        field_defs_list.append(self.create_date_field(decl.FN_DATE))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[decl.FN_DATE] = date.today()
        return field_defs_list

    def validation_all_addon(self, field_defs):

        if (getattr(field_defs, decl.FN_DATE).widget.get() > '{:%Y-%m-%d}'.format(date.today())):
            getattr(self._field_defs, decl.FN_DATE).textvar.set(date.today())


class InputDateHolding(InputPeriod):
    """
    TOP-LEVEL-WINDOW        EnterBox ToDate FromDate
                            with adjusted dates

    PARAMETER:
        see BuiltSelectBox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {'TO_Date':YYYY-MM-DD, 'From_Date':YYYY-MM-DD}
    """

    def validation_all_addon(self, field_defs):
        from_date = getattr(field_defs, decl.FN_FROM_DATE).widget.get()
        _date = self._validate_date(from_date)
        if _date:
            getattr(self._field_defs, decl.FN_FROM_DATE).textvar.set(
                _date)  # adjusted date returned
        to_date = getattr(field_defs, decl.FN_TO_DATE).widget.get()
        _date = self._validate_date(to_date)
        if _date:
            getattr(self._field_defs, decl.FN_TO_DATE).textvar.set(
                _date)  # adjusted date returned
        if from_date == to_date:
            from_date = date_days.subtract(from_date, 1)
            getattr(self._field_defs, decl.FN_FROM_DATE).textvar.set(
                from_date)  # adjusted date returned
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATE_ADJUSTED'))
        if (from_date > to_date):
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATE', from_date))

    def _validate_date(self, _date):
        data_exists = self.repo.exist_holding_of_iban_price_date(self.container, _date)
        if not data_exists:
            _date = self._get_prev_date(_date)
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATE_ADJUSTED'))
        return _date

    def _get_prev_date(self, _date):

        data_ = self.repo.get_holding_price_dates_of_iban(self.container)
        if data_:
            data = list(map(lambda x: str(x[0]), data_))
            idx = bisect_left(data, _date)
            if idx != 0:
                idx = idx - 1
            return data[idx]
        else:
            return _date


class InputIsins(BuiltSelectBox):
    """
    Selection: Comparision Field  and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # comparision field_names
        combo_values = [declm.DB_pieces, declm.DB_market_price,
                        declm.DB_total_amount, declm.DB_acquisition_amount, decl.FN_PROFIT_LOSS]
        field_defs_list.append(self.create_combo_field(
            decl.FN_COMPARATIVE, 20, decl.TYP_ALPHANUMERIC, combo_values))
        # separator line
        self.separator = [decl.FN_COMPARATIVE, decl.FN_TO_DATE]
        # check_buttons
        for field_name in self.table.keys():
            field_defs_list.append(self.create_check_field(
                field_name, self.table[field_name]))
        # initialize empty data_dict
        if decl.FN_COMPARATIVE not in self.data_dict.keys():
            self.data_dict[decl.FN_COMPARATIVE] = declm.DB_market_price
        return field_defs_list


class InputDatePrices(BuiltSelectBox):
    """
    Selction: Period and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # selection field_names of table price
        fields_properties = declm.TABLE_FIELDS_PROPERTIES[declm.PRICES]
        for field_name in fields_properties.keys():
            if field_name not in [declm.DB_ISIN, declm.DB_price_date,declm.DB_symbol_prices, declm.DB_origin]:
                field_defs_list.append(self.create_check_field(
                    field_name, fields_properties[field_name].comment))
                if field_name not in self.data_dict.keys():
                    self.data_dict[field_name] = 0
        # separator line
        self.separator = [decl.FN_TO_DATE, declm.DB_splits]
        # selection ISIN name
        isin_names = self.repo.get_isin_names()
        for isin_dict in isin_names:
            field_defs_list.append(self.create_check_field(
                isin_dict[declm.DB_ISIN], isin_dict[declm.DB_name]))
            self.data_dict[field_name] = 0
        return field_defs_list


class InputDateTable(BuiltSelectBox):
    """
    Selection: Period and Table fields
    """

    def create_field_defs_list(self):

        field_defs_list = []
        fields_properties = declm.TABLE_FIELDS_PROPERTIES[self.table]
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # separator line
        self.separator = [decl.FN_TO_DATE]
        # check_buttons
        for field_name in fields_properties.keys():
            field_defs_list.append(self.create_check_field(
                field_name, fields_properties[field_name].comment))
        # initialize empty data_dict
        for field_name in fields_properties.keys():
            if not self.data_dict:
                self.data_dict[field_name] = 0
        return field_defs_list


class InputDateTransactions(BuiltSelectBox):
    """
    Selection: Period and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Isin name
        if declm.DB_iban not in self.data_dict.keys():
            transaction_isin = self.repo.get_transaction_name_isin()
        else:
            transaction_isin = self.repo.get_transactions_name_isin_of_iban(self.data_dict[declm.DB_iban])
        if not transaction_isin:
            msg.MessageBoxInfo(
                title=self.title,
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_NO',
                    '',
                    self.data_dict[declm.DB_iban]
                    )
                )
            combo_values = []
        else:
            combo_values = list(transaction_isin.keys())
        field_defs_list.append(self.create_combo_field(
            declm.DB_name,  declm.DATABASE_FIELDS_PROPERTIES[declm.DB_name].length,
            declm.DATABASE_FIELDS_PROPERTIES[declm.DB_name].typ, combo_values))
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # initialize empty data_dict
        if combo_values and declm.DB_name not in self.data_dict.keys():
            self.data_dict[declm.DB_name] = combo_values[0]
        if decl.FN_FROM_DATE not in self.data_dict.keys():
            self.data_dict[decl.FN_FROM_DATE] = decl.START_DATE_TRANSACTIONS
        if decl.FN_TO_DATE not in self.data_dict.keys():
            self.data_dict[decl.FN_TO_DATE] = date.today() + timedelta(days=360)
        field_defs_list.append(self.create_combo_field(
            decl.FN_COST_METHOD, 8, decl.TYP_ALPHANUMERIC, decl.COST_METHOD))
        # initialize empty data_dict
        if combo_values and decl.FN_COST_METHOD not in self.data_dict.keys():
            self.data_dict[decl.FN_COST_METHOD] = decl.COST_FIFO
        return field_defs_list


class InputISIN(BuiltSelectBox):
    """
    Selection: Period and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        if self.container:
            combo_values = self.container  # list of isin names
        else:
            msg.MessageBoxInfo(title=self.title, message=msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', declm.ISIN, ''))
            combo_values = []
        field_def = self.create_combo_field(
            declm.DB_name,  declm.DATABASE_FIELDS_PROPERTIES[declm.DB_name].length,
            declm.DATABASE_FIELDS_PROPERTIES[declm.DB_name].typ, combo_values)
        field_def.selected = True
        field_defs_list.append(field_def)
        field_def = self.create_entry_field(
            declm.DB_ISIN,  declm.DATABASE_FIELDS_PROPERTIES[declm.DB_ISIN].length+1,
            declm.DATABASE_FIELDS_PROPERTIES[declm.DB_ISIN].typ)
        field_def.protected = True
        field_defs_list.append(field_def)
        # from_date
        field_defs_list.append(self.create_date_field(decl.FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(decl.FN_TO_DATE))
        # initialize empty data_dict
        if combo_values and declm.DB_name not in self.data_dict.keys():
            self.data_dict[declm.DB_name] = combo_values[0]
        if declm.DB_ISIN not in self.data_dict.keys():
            if combo_values:
                self.data_dict[declm.DB_ISIN] = self.repo.get_isin_of_name(self.data_dict[declm.DB_name])
        if decl.FN_FROM_DATE not in self.data_dict.keys():
            self.data_dict[decl.FN_FROM_DATE] = date_days.subtract(date.today(), 1)
        if decl.FN_TO_DATE not in self.data_dict.keys():
            self.data_dict[decl.FN_TO_DATE] = date.today()
        return field_defs_list

    def comboboxselected_action(self, event):

        if getattr(self._field_defs, declm.DB_name).name == declm.DB_name:
            getattr(self._field_defs, declm.DB_ISIN).textvar.set(
                self.repo.get_isin_of_name(event.widget.get()))


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

        self.repo = Repository()
        self.pin = ''
        self._bank_code = bank_code
        bank_names_dict = self.repo.dictbank_names()
        if bank_code in bank_names_dict:
            title = bank_names_dict[bank_code]
        else:
            title = msg.MESSAGE_TITLE
        pin_length = self.repo.shelve_get_pin_length(bank_code)
        pin_max_length = decl.MAX_PIN_LENGTH
        if pin_length[decl.KEY_MAX_PIN_LENGTH] is not None:
            pin_max_length = pin_length[decl.KEY_MAX_PIN_LENGTH]
        pin_min_length = decl.MIN_PIN_LENGTH
        if pin_length[decl.KEY_MIN_PIN_LENGTH] is not None:
            pin_min_length = pin_length[decl.KEY_MIN_PIN_LENGTH]
        while True:
            super().__init__(
                header=msg.get_message(msg.MESSAGE_TEXT, 'PIN_INPUT', bank_name, bank_code), title=title,
                button1_text=decl.BUTTON_OK, button2_text=None, button3_text=None,
                field_defs=[FieldDefinition(name=decl.KEY_PIN, length=pin_max_length,
                                            min_length=pin_min_length)], grab=True
            )
            if self.button_state == decl.WM_DELETE_WINDOW:
                break
            self.pin = self.field_dict[decl.KEY_PIN]
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

        self.repo = Repository()
        self._bank_code = bank_code
        bank_names_dict = self.repo.dictbank_names()
        if bank_code in bank_names_dict:
            title = bank_names_dict[bank_code]
        else:
            title = msg.MESSAGE_TITLE
        tan_max_length = self.repo.shelve_get_tan_max_length(bank_code)
        if not tan_max_length:
            tan_max_length = decl.MAX_TAN_LENGTH
        while True:
            super().__init__(
                header=msg.get_message(msg.MESSAGE_TEXT, 'TAN_INPUT', bank_code, bank_name), title=title,
                button1_text=decl.BUTTON_OK, button2_text=None, button3_text=None,
                field_defs=[
                    FieldDefinition(name=decl.KEY_TAN, length=tan_max_length, min_length=decl.MIN_TAN_LENGTH)]
            )
            if self.button_state == decl.WM_DELETE_WINDOW:
                break
            self.tan = self.field_dict[decl.KEY_TAN]
            if self.tan.strip() not in [None, '']:
                break


class BankDataNew(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox New Bank BankData

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Bank Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictinionary Of BankData Fields
    """

    def __init__(self,  title, bank_codes=[]):

        self.bank_codes = bank_codes
        FieldNames = namedtuple('FieldNames', [
            
            decl.KEY_BANK_CODE, decl.KEY_BANK_NAME, decl.KEY_USER_ID, decl.KEY_PIN, decl.KEY_BIC, decl.KEY_SERVER,
            decl.KEY_IDENTIFIER_DELIMITER, decl.KEY_DOWNLOAD_ACTIVATED, decl.KEY_LOGIN_ONLINE_BANKING])
        field_defs = FieldNames(
            FieldDefinition(definition=decl.COMBO,
                            name=decl.KEY_BANK_CODE, length=8, lformat=decl.FORMAT_FIXED,
                            combo_values=self.bank_codes, selected=True, focus_out=True),
            FieldDefinition(name=decl.KEY_BANK_NAME, length=70, protected=True),
            FieldDefinition(name=decl.KEY_USER_ID, length=20),
            FieldDefinition(name=decl.KEY_PIN, length=10, mandatory=False),
            FieldDefinition(name=decl.KEY_BIC, length=11, lformat=decl.FORMAT_FIXED),
            FieldDefinition(name=decl.KEY_SERVER, length=100),
            FieldDefinition(name=decl.KEY_IDENTIFIER_DELIMITER,
                            length=1, lformat=decl.FORMAT_FIXED, default_value=':'),
            FieldDefinition(name=decl.KEY_DOWNLOAD_ACTIVATED,
                            definition=decl.CHECK,
                            checkbutton_text=decl.KEY_DOWNLOAD_ACTIVATED),
            FieldDefinition(name=decl.KEY_LOGIN_ONLINE_BANKING, length=300,
                            mandatory=False),
        )
        super().__init__(title=title, button2_text=None, field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == decl.KEY_BANK_CODE:
            if field_def.widget.get() in self.repo.listbank_codes():
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'BANK_CODE_EXIST', field_def.widget.get()))
            else:
                if field_def.widget.get() in list(decl.SCRAPER_BANKDATA.keys()):
                    getattr(self._field_defs,
                            decl.KEY_IDENTIFIER_DELIMITER).textvar.set(
                                decl.SCRAPER_BANKDATA[field_def.widget.get()][1])
                return
        if field_def.name == decl.KEY_SERVER:
            http_code = http_error_code(field_def.widget.get())
            if http_code not in decl.HTTP_CODE_OK:
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'HTTP_INPUT', http_code, field_def.widget.get()))

    def comboboxselected_action(self, event):

        bank_code = getattr(self._field_defs, decl.KEY_BANK_CODE).widget.get()
        field_dict = self.repo.get_bankidentifier_name_bic_of_bankcode(bank_code)
        if declm.DB_name in field_dict:
            getattr(self._field_defs, decl.KEY_BANK_NAME).textvar.set(
                field_dict[declm.DB_name])
        else:
            getattr(self._field_defs, decl.KEY_BANK_NAME).textvar.set('')
        if declm.DB_bic in field_dict:
            getattr(self._field_defs, decl.KEY_BIC).textvar.set(
                field_dict[declm.DB_bic])
        else:
            getattr(self._field_defs, decl.KEY_BIC).textvar.set('')
        field_dict = self.repo.get_server_of_bankcode(bank_code)
        if declm.DB_server in field_dict:
            getattr(self._field_defs, decl.KEY_SERVER).textvar.set(
                field_dict[declm.DB_server])
        else:
            getattr(self._field_defs, decl.KEY_SERVER).textvar.set('')

    def focus_out_action(self, event):
        if event.widget.myId == decl.KEY_BANK_CODE:
            bank_code = getattr(self._field_defs, decl.KEY_BANK_CODE).widget.get()
            field_dict = self.repo.get_bankidentifier_name_bic_of_bankcode(bank_code)
            if not field_dict:
                getattr(self._field_defs, decl.KEY_BANK_NAME).textvar.set('')
                getattr(self._field_defs, decl.KEY_BIC).textvar.set('')
                getattr(self._field_defs, decl.KEY_SERVER).textvar.set('')
            

class BankDataChange(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox BankData

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Bank Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of BankData Fields
    """

    def __init__(self, title, bank_code, login_data):

        self.repo = Repository()
        field_defs = [
            FieldDefinition(name=decl.KEY_BANK_NAME, length=70, protected=True),
            FieldDefinition(name=decl.KEY_USER_ID, length=20),
            FieldDefinition(name=decl.KEY_PIN, length=10, mandatory=False),
            FieldDefinition(name=decl.KEY_BIC, length=11, lformat=decl.FORMAT_FIXED),
            FieldDefinition(name=decl.KEY_SERVER, length=100,
                            default_value=self.repo.get_server_of_bankcode(bank_code)),
            FieldDefinition(name=decl.KEY_IDENTIFIER_DELIMITER, length=1, lformat=decl.FORMAT_FIXED,
                            default_value=':'),
            FieldDefinition(name=decl.KEY_DOWNLOAD_ACTIVATED,
                            definition=decl.CHECK,
                            checkbutton_text=decl.KEY_DOWNLOAD_ACTIVATED), 
            FieldDefinition(name=decl.KEY_LOGIN_ONLINE_BANKING, length=300,
                            mandatory=False),            ]
        _set_defaults(field_defs, (login_data[decl.KEY_BANK_NAME],
                                   login_data[decl.KEY_USER_ID], login_data[decl.KEY_PIN],
                                   login_data[decl.KEY_BIC], login_data[decl.KEY_SERVER],
                                   login_data[decl.KEY_IDENTIFIER_DELIMITER],
                                   login_data[decl.KEY_DOWNLOAD_ACTIVATED],
                                   login_data[decl.KEY_LOGIN_ONLINE_BANKING],))
        super().__init__(title=title, field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == decl.KEY_SERVER:
            http_code = http_error_code(field_def.widget.get())
            if http_code not in decl.HTTP_CODE_OK:
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'HTTP_INPUT', http_code, field_def.widget.get()))


class BankDelete(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox BankData

    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field               Selected ComoboBox Value
    """

    def __init__(self,  title):

        FieldNames = namedtuple('FieldNames', [decl.KEY_BANK_CODE, decl.KEY_BANK_NAME])
        super().__init__(
            title=title, button1_text=decl.BUTTON_DELETE,
            field_defs=FieldNames(
                FieldDefinition(definition=decl.COMBO,
                                name=decl.KEY_BANK_CODE, length=8, selected=True, readonly=True,
                                combo_values=Repository().listbank_codes()),
                FieldDefinition(name=decl.KEY_BANK_NAME,
                                length=70, protected=True)
            )
        )

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.field_dict = {}
        self.field_dict[decl.KEY_BANK_CODE] = getattr(
            self._field_defs, decl.KEY_BANK_CODE).widget.get()
        self.field_dict[decl.KEY_BANK_NAME] = getattr(
            self._field_defs, decl.KEY_BANK_NAME).widget.get()
        self.quit_widget()

    def comboboxselected_action(self, event):

        getattr(self._field_defs, decl.KEY_BANK_NAME).textvar.set(
            self.repo.shelve_get_bank_name(getattr(self._field_defs, decl.KEY_BANK_CODE).widget.get())
            )


class IsinTableRowBox(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Isin Table Values
    """

    def set_field_def(self, field_def):
        if field_def.name==declm.DB_symbol:
            field_def.length = decl.MAX_FIELD_LENGTH
        return field_def

    def button_1_button3(self, event):
        """
        Import Prices
        """
        self.validation()
        BuiltEnterBox.button_1_button3(self, event)

    def focus_out_action(self, event):
        
        if event.widget.myId == declm.DB_ISIN:
            if getattr(self._field_defs, declm.DB_type).widget.get() == decl.FN_INDEX:
                isin_name = getattr(self._field_defs, declm.DB_name).widget.get()
                getattr(self._field_defs, declm.DB_ISIN).textvar.set(isin_name.ljust(12, "0"))
            else:
                isin_code = getattr(self._field_defs, declm.DB_ISIN).widget.get()
                isin_name = self.repo.get_isin_of_name(isin_code)
                if isin_name:
                    getattr(self._field_defs, declm.DB_name).textvar.set(isin_name[0])
        if event.widget.myId == declm.DB_name:
            isin_name = getattr(self._field_defs, declm.DB_name).widget.get()
            isin_code = self.repo.get_isin_of_name(isin_name)
            if isin_code:
                getattr(self._field_defs, declm.DB_ISIN).textvar.set(isin_code)
        if event.widget.myId == declm.DB_ISIN or event.widget.myId == declm.DB_name:
            result = self.repo.select_isin_table(
                declm.TABLE_FIELDS[declm.ISIN][2:],
                name=getattr(self._field_defs, declm.DB_name).widget.get()
                )
            if result:
                result = result[0]
                self.symbol = result[declm.DB_symbol]
                getattr(self._field_defs, declm.DB_type).textvar.set(result[declm.DB_type])
                getattr(self._field_defs, declm.DB_validity).textvar.set(result[declm.DB_validity])
                getattr(self._field_defs, declm.DB_wkn).textvar.set(result[declm.DB_wkn])
                getattr(self._field_defs, declm.DB_symbol).textvar.set(result[declm.DB_symbol])
                getattr(self._field_defs, declm.DB_origin_symbol).textvar.set(result[declm.DB_origin_symbol])
                getattr(self._field_defs, declm.DB_currency).textvar.set(result[declm.DB_currency])
                getattr(self._field_defs, declm.DB_exchange).textvar.set(result[declm.DB_exchange])
                getattr(self._field_defs, declm.DB_price_currency_valid).textvar.set(result[declm.DB_price_currency_valid])
                getattr(self._field_defs, declm.DB_last_check).textvar.set(result[declm.DB_last_check])
                getattr(self._field_defs, declm.DB_industry).textvar.set(result[declm.DB_industry])
        if event.widget.myId == declm.DB_type and getattr(self._field_defs, declm.DB_type).widget.get() == decl.FN_INDEX:
            isin_name = getattr(self._field_defs, declm.DB_name).widget.get()
            getattr(self._field_defs, declm.DB_ISIN).textvar.set(isin_name[:12].ljust(12, "_"))
        if event.widget.myId == declm.DB_symbol:
                symbol = getattr(self._field_defs, declm.DB_origin_symbol).widget.get()
                exchange = self.repo.get_ticker_exchange(symbol)
                getattr(self._field_defs, declm.DB_exchange).textvar.set(exchange)
        if event.widget.myId == declm.DB_origin_symbol:
            if decl.ALPHA_VANTAGE == getattr(self._field_defs, declm.DB_origin_symbol).widget.get():
                key_alpha_vantage = application_store.get(declm.DB_alpha_vantage)
                if key_alpha_vantage:
                    name = getattr(self._field_defs, declm.DB_name).widget.get()
                    keywords = name.split(' ')[0]
                    url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=' + \
                        keywords + '&apikey=' + key_alpha_vantage
                    r = requests.get(url)
                    data = r.json()
                    message = ' '.join(
                        [decl.INFORMATION, decl.ALPHA_VANTAGE, declm.DB_name.upper() + ':', name, '\n     >', keywords,  '<', 3 * '\n'])
                    for dict_symbols in data['bestMatches']:
                        if dict_symbols['8. currency'] == 'EUR':
                            str_dict_symbols = str(
                                dict_symbols).replace('{', '')
                            str_dict_symbols = str_dict_symbols.replace(
                                '}', '')
                            str_dict_symbols = str_dict_symbols.replace(
                                ',', ',     \n, ')
                            str_dict_symbols = str_dict_symbols.split(",")
                            message = message + \
                                2 * '\n' + '   '.join(str_dict_symbols)
                    msg.prices_informations_append(decl.INFORMATION, message)
                    PrintMessageCode(title=self.title, header=msg.Informations.PRICES_INFORMATIONS,
                                     text=msg.Informations.prices_informations)
            elif decl.YAHOO == getattr(self._field_defs, declm.DB_origin_symbol).widget.get():
                name = getattr(self._field_defs, declm.DB_name).widget.get()
                self.yahoo_symbols = self.repo.get_yahoo_symbols(name)
                if self.yahoo_symbols:
                    getattr(self._field_defs, declm.DB_name).widget.values = self.yahoo_symbols
                else:
                    webbrowser.open(decl.WWW_YAHOO)    



    def comboboxselected_action(self, event):

        self.focus_out_action(event)

    def validation_addon(self, field_def):
        """
        more field validations
        """
        if field_def.name==declm.DB_symbol:
            symbol = field_def.widget.get().partition(" ")[0]  # 1. part of string (without following text)
            if symbol != decl.NOT_ASSIGNED:                    
                field_def.textvar.set(symbol)
                exchange = self.repo.get_ticker_exchange(symbol)
                getattr(self._field_defs, declm.DB_exchange).textvar.set(exchange)             

                name_symbol = self.repo.select_isin_table([declm.DB_name, declm.DB_symbol], symbol=symbol)
                if name_symbol and name_symbol[0][declm.DB_name] != getattr(self._field_defs, declm.DB_name).widget.get():
                    self.header = set(msg.get_message(msg.MESSAGE_TEXT, 'SYMBOL_USED', name_symbol))
        elif field_def.name == declm.DB_validity:
            validity = getattr(self._field_defs, declm.DB_validity).widget.get()
            if validity > decl.VALIDITY_DEFAULT:
                getattr(self._field_defs, declm.DB_validity).textvar.set(
                    decl.VALIDITY_DEFAULT)
        elif field_def.name == declm.DB_ISIN:
            isin_code = getattr(self._field_defs, declm.DB_ISIN).widget.get()
            isin_code = isin_code.replace(" ", "")
            isin_code = isin_code.ljust(12, "_")
            getattr(self._field_defs, declm.DB_ISIN).textvar.set(isin_code)
            if not isin_code[0].isalpha():
                # necessary because of use as field name in named tuples (otherwise runtime error)
                self.header = (msg.get_message(msg.MESSAGE_TEXT, 'ISIN_ALPHABETIC'))


class LedgerCoaTableRowBox(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox LedgerCoa Table Values
    """

    def validation_addon(self, field_def):
        """
        check if account is already used in table ledger_coa
        """
        if field_def.name == declm.DB_iban:
            iban = field_def.widget.get()
            if not iban:
                field_def.widget.insert(0, decl.NOT_ASSIGNED)
                iban = decl.NOT_ASSIGNED
            if iban != decl.NOT_ASSIGNED and self.repo.exist_ledger_coa_with_iban(iban):
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'IBAN_USED'))

class LedgerTableRowBox(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Ledger Table Values
    """

    def set_field_def(self, field_def):
        if field_def.name == declm.DB_credit_account:
            field_def.length = declm.DATABASE_FIELDS_PROPERTIES[declm.DB_credit_account].length + \
                declm.DATABASE_FIELDS_PROPERTIES[declm.DB_credit_name].length
            field_def.lformat = decl.FORMAT_VARIABLE   # standard data_type char would be FORMAT_FIXED
        elif field_def.name == declm.DB_debit_account:
            field_def.length = declm.DATABASE_FIELDS_PROPERTIES[declm.DB_debit_account].length + \
                declm.DATABASE_FIELDS_PROPERTIES[declm.DB_debit_name].length
            field_def.lformat = decl.FORMAT_VARIABLE   # standard data_type char would be FORMAT_FIXED
        elif field_def.name == declm.DB_category:
            field_def.upper = True
        return field_def

    def button_1_button1(self, event):

        debit_account = getattr(
            self._field_defs, declm.DB_debit_account).textvar.get()
        if debit_account:
            getattr(self._field_defs, declm.DB_debit_account).textvar.set(
                debit_account[:declm.TABLE_FIELDS_PROPERTIES[declm.LEDGER][declm.DB_credit_account].length])
        credit_account = getattr(
            self._field_defs, declm.DB_credit_account).textvar.get()
        if credit_account:
            getattr(self._field_defs, declm.DB_credit_account).textvar.set(
                credit_account[:declm.TABLE_FIELDS_PROPERTIES[declm.LEDGER][declm.DB_debit_account].length])
        BuiltEnterBox.button_1_button1(self, event)

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        if self.button_state == decl.BUTTON_COPY:
            self.quit_widget()  # selected row as template in insert mode
        else:
            # restore data in update_mode
            BuiltEnterBox.button_1_button2(self, event)

    def show_data(self, status):

        id_no = getattr(self._field_defs, declm.DB_id_no).textvar.get()
        ledger_statement = self.repo.get_ledger_statement_data(id_no, status)
        if ledger_statement:
            if status == decl.CREDIT:
                title = ' '.join([decl.BUTTON_CREDIT, declm.STATEMENT.upper()])
            else:
                title = ' '.join([decl.BUTTON_DEBIT, declm.STATEMENT.upper()])
            statement = self.repo.get_statement(ledger_statement[declm.DB_iban], ledger_statement[declm.DB_entry_date], ledger_statement[declm.DB_counter])
            if statement:
                statement = BuiltTableRowBox(declm.STATEMENT, declm.STATEMENT, statement,
                                             protected=declm.TABLE_FIELDS[declm.STATEMENT],
                                             title=title,  button1_text=None, button2_text=None)
                if statement.button_state == decl.WM_DELETE_WINDOW:
                    return
        else:
            self.message = msg.get_message(msg.MESSAGE_TEXT, 'LEDGER_ROW')
        self.quit_widget()

    def button_1_button3(self, event):

        self.show_data(decl.CREDIT)

    def button_1_button4(self, event):

        self.show_data(decl.DEBIT)


class LedgerTableSearchRowBox(BuiltTableRowBox):
    """Top-level window for entering ledger search values."""

    def set_field_def(self, field_def):
        """Adjust field definition for search input."""

        # allow partial date input
        if field_def.typ == decl.TYP_DATE:
            field_def.typ = decl.TYP_ALPHANUMERIC

        reset_fields = {
            declm.DB_id_no,
            declm.DB_entry_date,
            declm.DB_date,
            declm.DB_amount,
            declm.DB_vat_amount,
            declm.DB_vat_rate,
            declm.DB_upload_check,
            declm.DB_bank_statement_checked,
        }

        if field_def.name in reset_fields:
            field_def.default = ''

        # extend account fields to include name
        if field_def.name in (declm.DB_credit_account, declm.DB_debit_account):
            account_key = (
                declm.DB_credit_account
                if field_def.name == declm.DB_credit_account
                else declm.DB_debit_account
            )
            name_key = (
                declm.DB_credit_name
                if field_def.name == declm.DB_credit_account
                else declm.DB_debit_name
            )

            field_def.length = (
                declm.DATABASE_FIELDS_PROPERTIES[account_key].length +
                declm.DATABASE_FIELDS_PROPERTIES[name_key].length
            )
            field_def.lformat = decl.FORMAT_VARIABLE

        return field_def

    def button_1_button1(self, event):
        """Trim account input fields before submit."""

        for field_name, target_length_key in [
            (declm.DB_debit_account, declm.DB_credit_account),
            (declm.DB_credit_account, declm.DB_debit_account),
        ]:
            field = getattr(self._field_defs, field_name)
            value = field.textvar.get()

            if value:
                max_length = declm.TABLE_FIELDS_PROPERTIES[declm.LEDGER][target_length_key].length
                field.textvar.set(value[:max_length])

        BuiltEnterBox.button_1_button1(self, event)

    def validation(self):
        """Collect and normalize user input."""

        excluded_fields = {
            declm.DB_bank_statement_checked,
            declm.DB_upload_check
        }

        # collect values
        self.field_dict = {
            field_def.name: field_def.widget.get()
            for field_def in self._field_defs
            if field_def.name not in excluded_fields
        }

        # apply uppercase normalization
        for field_def in self._field_defs:
            if field_def.upper and field_def.name in self.field_dict:
                self.field_dict[field_def.name] = (
                    self.field_dict[field_def.name].upper()
                )

                
class StatementTableSearchRowBox(BuiltTableRowBox):

    def set_field_def(self, field_def):
        if field_def.typ in [decl.TYP_DATE, decl.TYP_DECIMAL]:
            field_def.typ = decl.TYP_ALPHANUMERIC   # enables the input of partial date strings
            field_def.length = 10

        if field_def.definition == decl.CHECK:
            field_def.typ = decl.TYP_ALPHANUMERIC
            field_def.length = 1  # enables the input of 0 or 1

        field_def.default = ''
        return field_def

    def validation(self):
        self.field_dict = {}
        self.footer.set('')

        mandatory_fields = {declm.DB_iban, declm.DB_entry_date}

        for field_def in self._field_defs:
            value = field_def.widget.get()

            if field_def.name in mandatory_fields and not value:
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'MANDATORY', field_def.name.upper())
                )
                return

            if field_def.typ == decl.TYP_DATE:
                field_def.textvar = value

            if value:
                self.field_dict[field_def.name] = value

        for name in self.field_dict:
            field_def = next(fd for fd in self._field_defs if fd.name == name)
            if field_def.upper:
                self.field_dict[name] = self.field_dict[name].upper()


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

    def __init__(self,  title=msg.MESSAGE_TITLE,
                 button1_text=decl.BUTTON_NEXT,
                 button2_text=decl.BUTTON_STANDARD, button3_text=decl.BUTTON_SAVE_STANDARD,
                 button4_text=decl.BUTTON_SELECT_ALL,
                 default_texts=[], standard=decl.STANDARD,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        self.standard = standard
        super().__init__(
            title=title, header=msg.get_message(msg.MESSAGE_TEXT, 'CHECKBOX'),
            button1_text=button1_text, button2_text=button2_text, button3_text=button3_text,
            button4_text=button4_text,
            default_texts=default_texts,
            checkbutton_texts=checkbutton_texts
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        standard = self.repo.selection_get(self.standard)
        if standard:
            for idx, check_text in enumerate(self.checkbutton_texts):
                if check_text in standard:
                    self._check_vars[idx].set(1)
                else:
                    self._check_vars[idx].set(0)
        else:
            for idx, check_text in enumerate(self.checkbutton_texts):
                self._check_vars[idx].set(0)

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.validate_all()
        self.repo.selection_put(self.standard, self.field_list)

    def validate_all(self):

        if self.standard == get_menu_text("Show") + get_menu_text("Statement"):
            if declm.DB_amount in self.field_list:
                if declm.DB_status not in self.field_list:
                    self.field_list.append(declm.DB_status)
                if declm.DB_currency not in self.field_list:
                    self.field_list.append(declm.DB_currency)
            if declm.DB_opening_balance in self.field_list:
                if declm.DB_opening_status not in self.field_list:
                    self.field_list.append(declm.DB_opening_status)
                if declm.DB_opening_currency not in self.field_list:
                    self.field_list.append(declm.DB_opening_currency)
            if declm.DB_closing_balance in self.field_list:
                if declm.DB_closing_status not in self.field_list:
                    self.field_list.append(declm.DB_closing_status)
                if declm.DB_closing_currency not in self.field_list:
                    self.field_list.append(declm.DB_closing_currency)
        elif self.standard == get_menu_text("Show") + get_menu_text("Holding"):
            if (
                (declm.DB_total_amount in self.field_list or
                 declm.DB_total_amount_portfolio in self.field_list or
                 declm.DB_acquisition_amount in self.field_list)
                and
                    declm.DB_amount_currency not in self.field_list):
                self.field_list.append(declm.DB_amount_currency)
            if (
                (declm.DB_market_price in self.field_list or
                 declm.DB_acquisition_price in self.field_list)
                and
                    declm.DB_price_currency not in self.field_list):
                self.field_list.append(declm.DB_price_currency)


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

    def __init__(self,  title=msg.MESSAGE_TITLE,
                 button1_text=decl.BUTTON_APPEND, button2_text=decl.BUTTON_REPLACE, button3_text=decl.BUTTON_DELETE,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        super().__init__(
            title=title, header=msg.get_message(msg.MESSAGE_TEXT, 'CHECKBOX'),
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
            self.text_widget.tag_add(decl.LIGHTBLUE, str(line + 1) + '.0',
                                     str(line + 1) + '.' + str(len(textline)))
            self.text_widget.tag_config(decl.LIGHTBLUE, background=decl.LIGHTBLUE)


class PandasBoxBalance(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of  Bank Balances

    PARAMETER:
        dataframe           Dataframe
    """

    def create_dataframe(self):

        self.dataframe[decl.KEY_ACC_OWNER_NAME] = self.dataframe[decl.KEY_ACC_OWNER_NAME].where(
            self.dataframe[decl.KEY_ACC_OWNER_NAME] != self.dataframe[decl.KEY_ACC_OWNER_NAME].shift(), ""
            )          

    def set_row_format(self):

        last_index = self.pandas_table.model.df.index[-1]
        self.pandas_table.setRowColors(rows=[last_index], clr='lightgreen', cols='all')


class PandasBoxBalanceAll(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Balances

    PARAMETER:
        dataframe           list of Dataframes
    """

    def create_dataframe(self):

        def calc_pct(balance, opening):
            return 0 if opening == 0 else (balance - opening) / opening * 100

        dataframe = concat(d for d in self.dataframe)
        
        df = dataframe.sort_values(by=[decl.FN_BANK_NAME, decl.KEY_ACC_OWNER_NAME]).reset_index(drop=True)
        
        result = []
        
        for bank, bank_group in df.groupby(decl.FN_BANK_NAME):
            
            for owner, owner_group in bank_group.groupby(decl.KEY_ACC_OWNER_NAME):
                
                # Detailzeilen (decl.FN_DAILY_PERCENT bleibt wie vorhanden)
                owner_group["level"] = "DETAIL"
                result.append(owner_group)
                
                # Owner-Summe
                owner_sum = DataFrame({
                    decl.FN_BANK_NAME: [bank],
                    decl.KEY_ACC_OWNER_NAME: [owner],
                    decl.FN_BALANCE: [owner_group[decl.FN_BALANCE].sum()],
                    declm.DB_opening_balance: [owner_group[declm.DB_opening_balance].sum()],
                    decl.FN_DAILY_PERCENT: [calc_pct(
                        owner_group[decl.FN_BALANCE].sum(),
                        owner_group[declm.DB_opening_balance].sum()
                    )],
                    "level": ["OWNER_SUM"]
                })
                
                result.append(owner_sum)
            
            # Bank-Summe
            bank_sum = DataFrame({
                decl.FN_BANK_NAME: [bank],
                decl.KEY_ACC_OWNER_NAME: [decl.FN_TOTAL],
                decl.FN_BALANCE: [bank_group[decl.FN_BALANCE].sum()],
                declm.DB_opening_balance: [bank_group[declm.DB_opening_balance].sum()],
                decl.FN_DAILY_PERCENT: [calc_pct(
                    bank_group[decl.FN_BALANCE].sum(),
                    bank_group[declm.DB_opening_balance].sum()
                )],
                "level": ["BANK_SUM"]
            })
            
            result.append(bank_sum)
        
        # Zusammenführen
        df_final = concat(result, ignore_index=True)
        
        # --- Gesamt-Summe ---
        total_sum = DataFrame({
            decl.FN_BANK_NAME: [decl.FN_TOTAL],
            decl.KEY_ACC_OWNER_NAME: [decl.FN_TOTAL],
            decl.FN_BALANCE: [df[decl.FN_BALANCE].sum()],
            declm.DB_opening_balance: [df[declm.DB_opening_balance].sum()],
            decl.FN_DAILY_PERCENT: [calc_pct(
                df[decl.FN_BALANCE].sum(),
                df[declm.DB_opening_balance].sum()
            )],
            "level": ["GRAND_TOTAL"]
        })
        
        self.dataframe = concat([df_final, total_sum], ignore_index=True)
        self.dataframe[decl.FN_BANK_NAME] = self.dataframe[decl.FN_BANK_NAME].where(
            self.dataframe[decl.FN_BANK_NAME] != self.dataframe[decl.FN_BANK_NAME].shift(), ""
            )        
        self.dataframe[decl.KEY_ACC_OWNER_NAME] = self.dataframe[decl.KEY_ACC_OWNER_NAME].where(
            self.dataframe[decl.KEY_ACC_OWNER_NAME] != self.dataframe[decl.KEY_ACC_OWNER_NAME].shift(), ""
            )        

    def set_row_format(self):

        for i, row in self.pandas_table.model.df.iterrows():
            if row['level'] == "BANK_SUM":
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')
            if row['level'] == "GRAND_TOTAL":
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightgreen', cols='all')
        self.pandas_table.model.df = self.dataframe.drop(columns=["level"])



class PandasBoxHolding(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Holdings

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    """

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            columns=[declm.DB_amount_currency, declm.DB_price_currency, declm.DB_currency],
            axis=1, errors='ignore')
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            (data, columns) = self.dataframe
            self.dataframe = DataFrame(data)[columns]
            if declm.DB_total_amount in columns and declm.DB_acquisition_amount in columns:
                self.dataframe[decl.FN_PROFIT] = self.dataframe[declm.DB_total_amount] - \
                    self.dataframe[declm.DB_acquisition_amount]
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

        return position_dict[declm.DB_name]

    def create_dataframe(self):

        data_to_date, data_from_date = self.dataframe

        to_map_set = {*map(self._get_name, data_to_date)}
        from_map_set = {*map(self._get_name, data_from_date)}
        # purchase positions: insert to data_from_date
        inserts = to_map_set.difference(from_map_set)
        data_to_date_insert = [
            item for item in data_to_date if item[declm.DB_name] in inserts]
        data_from_date = data_from_date + data_to_date_insert
        # sale position delete form data_from_date
        removes = from_map_set.difference(to_map_set)
        data_from_date = [
            item for item in data_from_date if item[declm.DB_name] not in removes]

        data_to_date = sorted(data_to_date, key=lambda i: (i[declm.DB_name]))
        data_from_date = sorted(data_from_date, key=lambda i: (i[declm.DB_name]))
        # create dataframe
        self.dataframe = DataFrame(data_to_date)
        dataframe_from_date = DataFrame(data_from_date)
        columns = [declm.DB_total_amount, declm.DB_acquisition_amount,
                   declm.DB_pieces, declm.DB_market_price]
        self.dataframe[columns] = self.dataframe[columns].apply(to_numeric)
        dataframe_from_date[columns] = dataframe_from_date[columns].apply(
            to_numeric)
        # adjust sales and purchases
        if not dataframe_from_date[declm.DB_pieces].equals(self.dataframe[declm.DB_pieces]):
            dataframe_from_date[declm.DB_total_amount] = (
                dataframe_from_date[declm.DB_total_amount] * self.dataframe[declm.DB_pieces] / dataframe_from_date[declm.DB_pieces])
        # add sum row
        sum_row = {}
        sum_row[declm.DB_total_amount] = self.dataframe[declm.DB_total_amount].sum()
        sum_row[declm.DB_acquisition_amount] = self.dataframe[declm.DB_acquisition_amount].sum()
        sum_row[declm.DB_amount_currency] = decl.EURO
        self.dataframe.loc[len(self.dataframe.index)] = sum_row
        sum_row[declm.DB_total_amount] = dataframe_from_date[declm.DB_total_amount].sum()
        sum_row[declm.DB_acquisition_amount] = dataframe_from_date[declm.DB_acquisition_amount].sum()
        dataframe_from_date.loc[len(dataframe_from_date.index)] = sum_row

        # compute percentages
        self.dataframe[decl.FN_PROFIT_LOSS] = self.dataframe[declm.DB_total_amount] - \
            self.dataframe[declm.DB_acquisition_amount]
        self.dataframe[decl.FN_TOTAL_PERCENT] = (
            self.dataframe[decl.FN_PROFIT_LOSS] / self.dataframe[declm.DB_acquisition_amount] * 100)
        self.dataframe[decl.FN_PERIOD_PERCENT] = (
            self.dataframe[declm.DB_total_amount] /
            dataframe_from_date[declm.DB_total_amount]
            * 100 - 100)
        self.dataframe = self.dataframe.drop(
            [decl.FN_PROFIT_LOSS, declm.DB_acquisition_amount], axis=1)
        self.dataframe = self.dataframe[[declm.DB_name, declm.DB_total_amount, declm.DB_market_price, declm.DB_pieces,
                                         decl.FN_TOTAL_PERCENT, decl.FN_PERIOD_PERCENT]]


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
        columns = [declm.DB_price_date, declm.DB_total_amount_portfolio,
                   declm.DB_acquisition_amount]
        self.dataframe = DataFrame(self.dataframe, columns=columns[:3])
        self.dataframe[columns[1:]
                       ] = self.dataframe[columns[1:]].apply(to_numeric)
        # Drop first row
        # self.dataframe.drop(
        #    index=self.dataframe.index[0], axis=0,  inplace=True)
        self.dataframe[declm.DB_price_date] = to_datetime(
            self.dataframe[declm.DB_price_date]).dt.date
        self.dataframe.set_index(declm.DB_price_date, inplace=True)
        # compute percentages
        self.dataframe[decl.FN_PROFIT_LOSS] = (
            self.dataframe[declm.DB_total_amount_portfolio] -
            self.dataframe[declm.DB_acquisition_amount]
        )
        self.dataframe[decl.FN_TOTAL_PERCENT] = (
            self.dataframe[decl.FN_PROFIT_LOSS] /
            self.dataframe[declm.DB_acquisition_amount]
            * 100)
        self.dataframe[declm.DB_total_amount_portfolio]
        price_date = self.dataframe.first_valid_index()
        self.dataframe[decl.FN_PERIOD_PERCENT] = (
            self.dataframe[declm.DB_total_amount_portfolio] /
            self.dataframe.loc[price_date, declm.DB_total_amount_portfolio]
            * 100 - 100)
        self.dataframe = self.dataframe.round(2)


class PandasBoxHoldingTransaction(PandasBoxHolding):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe Transactions of Holdings

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    """

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            (data, columns) = self.dataframe
            self.dataframe = DataFrame(data)[columns]
        elif isinstance(self.dataframe, DataFrame):
            pass
        else:
            self.dataframe = DataFrame(self.dataframe)
        if declm.DB_transaction_type in self.dataframe.columns and declm.DB_posted_amount in self.dataframe.columns:
            deliveries = self.dataframe[declm.DB_transaction_type] == decl.TRANSACTION_DELIVERY
            self.dataframe[declm.DB_posted_amount] = self.dataframe[declm.DB_posted_amount].where(
                deliveries, -self.dataframe[declm.DB_posted_amount])


class PandasBoxPrices(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Prices

    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (selected_fields, data, self.origin, sign) = self.dataframe
        if sign == decl.PERCENT:
            dataframe = DataFrame(data)
            dataframe = dataframe.dropna(how='all', axis=1)
            self.dataframe = dataframe.pivot(
                index='price_date', columns='name', values=selected_fields)
            columns = self.dataframe.columns
            base_row = self.dataframe.head(1)
            for idx, column, in enumerate(columns):
                if base_row.iloc[0, idx] != 0:
                    self.dataframe[column] = (
                        self.dataframe[column] / dec2.convert(base_row.iloc[0, idx]) - 1) * 100
        else:
            dataframe = DataFrame(data)
            columns = [declm.DB_name]
            self.dataframe = dataframe.pivot(
                index=declm.DB_price_date, columns=columns, values=selected_fields)
            columns = list(self.dataframe)
            self.dataframe[columns[0]] = self.dataframe[columns[0]].apply(
                to_numeric)

    def set_column_format(self):

        for column in self.dataframe.columns:
            _, name_ = column
            if self.origin[name_] == decl.ALPHA_VANTAGE:
                # AlphaVamtageColumns are aqua
                self.pandas_table.columncolors[column] = '#00FFFF'
            else:
                # Yahoo columns are violet
                self.pandas_table.columncolors[column] = '#EE82EE'
        BuiltPandasBox.set_column_format(self)


class PandasBoxIsinTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Isin Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def __init__(self, title, data, message, mode=decl.EDIT_ROW, selected_row=0):

        self.repo = Repository()
        self.title = title
        self.data = data
        self.message = message
        self.selected_row = selected_row
        if data:
            self.isins_exist = True
            decl.ToolbarSwitch.toolbar_switch = False
            super().__init__(title=title, dataframe=data,
                             message=message, mode=mode, selected_row=self.selected_row)
        else:
            self.isins_exist = False
            self.button_state = self.new_row()

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def set_row_format(self):

        isin_codes = self.repo.get_holding_existing_isin_codes()
        for i, row in self.pandas_table.model.df.iterrows():
            if row[declm.DB_ISIN] in isin_codes:
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')

    def drop_currencies(self):

        pass

    def show_row(self):

        row_dict = self.get_selected_row()
        isin = BuiltTableRowBox(declm.ISIN, declm.ISIN, row_dict,
                                protected=declm.TABLE_FIELDS[declm.ISIN],
                                title=self.title,  button1_text=None, button2_text=None)
        self.button_state = isin.button_state
        if isin.button_state == decl.WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            isin = BuiltTableRowBox(declm.ISIN, declm.ISIN, row_dict,
                                    protected=declm.TABLE_FIELDS[declm.ISIN],
                                    title=self.title, button1_text=decl.BUTTON_DELETE, button2_text=None)
            self.button_state = isin.button_state
            if isin.button_state == decl.WM_DELETE_WINDOW:
                return
            elif isin.button_state == decl.BUTTON_DELETE:
                self.repo.delete_isin(isin.field_dict[declm.DB_ISIN])
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_DELETED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_ISIN.upper(),
                            isin.field_dict[declm.DB_ISIN],
                            '\n',
                            isin.field_dict[declm.DB_name]
                            ]
                        )
                    )
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            if row_dict[declm.DB_type] == decl.FN_INDEX:
                protected = [declm.DB_ISIN, declm.DB_wkn, declm.DB_industry]
            else:
                protected = [declm.DB_ISIN]
            mandatory = [declm.DB_name, declm.DB_type, declm.DB_validity, declm.DB_currency]
            focus_out = [declm.DB_ISIN, declm.DB_name, declm.DB_type, declm.DB_origin_symbol]
            upper = [declm.DB_symbol]
            if row_dict[declm.DB_symbol] == decl.NOT_ASSIGNED:
                button3_text = None
            else:
                button3_text = decl.BUTTON_PRICES_IMPORT  # symbol mandatory for import of prices
            isin = IsinTableRowBox(
                declm.ISIN, declm.ISIN, row_dict,
                combo_dict=self._create_combo_dict(name=row_dict[declm.DB_name]), combo_insert_value=[declm.DB_industry, declm.DB_symbol],
                protected=protected, mandatory=mandatory,
                focus_out=focus_out, upper=upper,
                title=self.title, button1_text=decl.BUTTON_UPDATE,
                button3_text=button3_text)
            self.button_state = isin.button_state
            if isin.button_state == decl.WM_DELETE_WINDOW:
                return
            elif isin.button_state == decl.BUTTON_UPDATE:
                isin.field_dict[declm.DB_symbol] = isin.field_dict[declm.DB_symbol].split(" ", 1)[0]
                if not isin.field_dict[declm.DB_last_check]:
                    isin.field_dict[declm.DB_last_check] = date_days.today()
                self.repo.replace_isin(isin.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_CHANGED',
                    ' '.join(
                        [
                            self.title,
                            declm.DB_ISIN.upper(),
                            isin.field_dict[declm.DB_ISIN],
                            isin.field_dict[declm.DB_name]
                            ]
                        )
                    )
            elif isin.button_state == decl.BUTTON_PRICES_IMPORT:
                self.selected_row_dict = isin.field_dict
        self.quit_widget()

    def new_row(self):

        mandatory = [declm.DB_ISIN, declm.DB_name, declm.DB_type, declm.DB_validity, declm.DB_currency]
        focus_out = [declm.DB_ISIN, declm.DB_name, declm.DB_type, declm.DB_origin_symbol]
        upper = [declm.DB_symbol]
        row_dict = {}
        row_dict[declm.DB_type] = decl.FN_SHARE
        row_dict[declm.DB_validity] = decl.VALIDITY_DEFAULT
        row_dict[declm.DB_wkn] = decl.NOT_ASSIGNED
        row_dict[declm.DB_origin_symbol] = decl.NOT_ASSIGNED
        row_dict[declm.DB_symbol] = decl.NOT_ASSIGNED
        row_dict[declm.DB_currency] = decl.EURO
        isin = IsinTableRowBox(declm.ISIN, declm.ISIN, row_dict,
                               combo_dict=self._create_combo_dict(), mandatory=mandatory,
                               combo_insert_value=[declm.DB_industry, declm.DB_symbol],
                               focus_out=focus_out, upper=upper,
                               title=self.title, button1_text=decl.BUTTON_NEW)
        self.button_state = isin.button_state
        if isin.button_state == decl.WM_DELETE_WINDOW:
            return isin.button_state
        elif isin.button_state == decl.BUTTON_NEW:
            if self.repo.exist_isin_isin_code(isin.field_dict[declm.DB_ISIN]):
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_ROW_EXIST',
                    ' '.join(
                        [
                            declm.ISIN.upper(),
                            '\n',
                            declm.DB_ISIN.upper(),
                            isin.field_dict[declm.DB_ISIN]
                            ]
                        )
                    )
            elif self.repo.exist_isin_name(isin.field_dict[declm.DB_name]):
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_ROW_EXIST',
                    ' '.join(
                        [
                            declm.ISIN.upper(),
                            '\n',
                            declm.DB_name.upper(),
                            isin.field_dict[declm.DB_name]
                            ]
                        )
                    )
            else:
                if not isin.field_dict[declm.DB_last_check]:
                    isin.field_dict[declm.DB_last_check] = date_days.today()
                self.repo.insert_isin(isin.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_INSERTED',
                    ' '.join(
                        [
                            self.title,
                            declm.DB_ISIN.upper(),
                            '\n',
                            isin.field_dict[declm.DB_ISIN],
                            isin.field_dict[declm.DB_name]
                            ]
                        )
                    )
        if self.isins_exist:
            self.quit_widget()  # see BuiltPandasBox
        else:
            isin.quit_widget()  # see BuiltTableRowBox

    def _create_combo_dict(self, name=None):

        currency_dict = {declm.DB_currency: decl.CURRENCIES}
        type_dict = {declm.DB_type: declm.DB_TYPES}
        origin_symbol_dict = {declm.DB_origin_symbol: decl.ORIGIN_SYMBOLS}
        industry_list = self.repo.get_isin_industries()
        industry_dict = {declm.DB_industry: industry_list}
        if name:
            yahoo_symbols = self.repo.get_yahoo_symbols(name)
            symbol_dict = {declm.DB_symbol: yahoo_symbols}        
            return {**currency_dict, **type_dict, **origin_symbol_dict, **industry_dict, **symbol_dict}
        else:
            return {**currency_dict, **type_dict, **origin_symbol_dict, **industry_dict}

class PandasBoxIsinComparision(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows market_prices, total_amounts, pieces, profit_loss of compared isin_codes
    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (selected_isins, data) = self.dataframe
        dataframe = DataFrame(data)
        dataframe = dataframe.dropna(how='all', axis=1)
        self.dataframe = dataframe.pivot(
            index='price_date', columns='name', values=selected_isins)


class PandasBoxIsinComparisionPercent(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows market_prices, total_amounts, pieces, profit_loss of compared isin_codes
                            Shows data of isin_codes with their the maximum common time interval
    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (selected_isins, data) = self.dataframe
        dataframe = DataFrame(data)
        dataframe = dataframe.dropna(how='all', axis=1)
        self.dataframe = dataframe.pivot(
            index='price_date', columns='name', values=selected_isins)
        self.dataframe = self.dataframe.dropna(how='all', axis=1)
        columns = self.dataframe.columns
        base_row = self.dataframe.head(1)
        for idx, column, in enumerate(columns):
            if base_row.iloc[0, idx] != 0:
                self.dataframe[column] = (
                    self.dataframe[column] / base_row.iloc[0, idx] - 1) * 100


class PandasBoxStatementBalances(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Statements

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    """

    def _debit(self, amount, status=decl.CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == decl.DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            data, columns = self.dataframe
            self.dataframe = DataFrame(data=data, columns=columns)
        names = self.dataframe.columns.tolist()
        if declm.DB_amount in names:
            self.dataframe[declm.DB_amount] = self.dataframe[[declm.DB_amount, declm.DB_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if declm.DB_opening_balance in names:
            self.dataframe[declm.DB_opening_balance] = self.dataframe[[declm.DB_opening_balance, declm.DB_opening_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if declm.DB_closing_balance in names:
            self.dataframe[declm.DB_closing_balance] = self.dataframe[[declm.DB_closing_balance, declm.DB_closing_status]].apply(
                lambda x: self._debit(*x), axis=1)

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            axis=1, errors='ignore',
            columns=[declm.DB_currency, declm.DB_status, declm.DB_opening_currency, declm.DB_opening_status,
                     declm.DB_closing_currency, declm.DB_closing_status, declm.DB_amount_currency, declm.DB_price_currency
                     ]
        )
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()


class PandasBoxHoldingTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        HOLDING Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def __init__(self, title, data, message, iban, mode=decl.EDIT_ROW):

        self.repo = Repository()
        self.title = title
        self.data = data

        self.message = message
        if data:
            decl.ToolbarSwitch.toolbar_switch = False
            super().__init__(title=title, dataframe=data, message=message, mode=mode)
        else:
            holding = self.new_row_insert({declm.DB_iban: iban})
            self.button_state = holding.button_state

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def drop_currencies(self):

        pass

    def show_row(self):

        row_dict = self.get_selected_row()
        holding = BuiltTableRowBox(declm.HOLDING, declm.HOLDING_VIEW, row_dict,
                                   protected=declm.TABLE_FIELDS[declm.HOLDING_VIEW],
                                   title=self.title,  button1_text=None, button2_text=None)
        self.button_state = holding.button_state
        if holding.button_state == decl.WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            holding = BuiltTableRowBox(declm.HOLDING, declm.HOLDING_VIEW, row_dict,
                                       protected=declm.TABLE_FIELDS[declm.HOLDING_VIEW],
                                       title=self.title, button1_text=decl.BUTTON_DELETE, button2_text=None)
            self.button_state = holding.button_state
            if holding.button_state == decl.WM_DELETE_WINDOW:
                return
            elif holding.button_state == decl.BUTTON_DELETE:
                self.repo.delete_holding_position(holding.field_dict[declm.DB_iban], holding.field_dict[declm.DB_price_date], holding.field_dict[declm.DB_ISIN])
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_DELETED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_price_date.upper(),
                            holding.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_ISIN.upper(),
                            holding.field_dict[declm.DB_ISIN],
                            '\n',
                            holding.field_dict[declm.DB_name]
                            ]
                        )
                    )
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            holding_dict = self.repo.select_holding_view_row(row_dict[declm.DB_iban], row_dict[declm.DB_price_date], row_dict[declm.DB_ISIN])
            protected = declm.TABLE_FIELDS[declm.HOLDING_VIEW].copy()
            protected.remove(declm.DB_market_price)
            protected.remove(declm.DB_pieces)
            protected.remove(declm.DB_acquisition_amount)
            protected.remove(declm.DB_acquisition_price)
            mandatory = [declm.DB_market_price, declm.DB_pieces,
                         declm.DB_acquisition_amount, declm.DB_acquisition_price]
            holding = BuiltTableRowBox(declm.HOLDING, declm.HOLDING_VIEW, holding_dict,
                                       protected=protected, mandatory=mandatory,
                                       title=self.title, button1_text=decl.BUTTON_UPDATE)
            self.button_state = holding.button_state
            if holding.button_state == decl.WM_DELETE_WINDOW:
                return
            elif holding.button_state == decl.BUTTON_UPDATE:
                if holding.field_dict[declm.DB_market_price] != str(holding_dict[declm.DB_market_price]) or holding.field_dict[declm.DB_pieces] != str(holding_dict[declm.DB_pieces]):
                    holding.field_dict[declm.DB_total_amount] = dec2.multiply(
                        holding.field_dict[declm.DB_market_price], holding.field_dict[declm.DB_pieces])

                    holding.field_dict[declm.DB_origin] = decl.ORIGIN_BANKDATA_CHANGED
                if holding.field_dict[declm.DB_acquisition_price] != str(holding_dict[declm.DB_acquisition_price]) or holding.field_dict[declm.DB_pieces] != str(holding_dict[declm.DB_pieces]):
                    holding.field_dict[declm.DB_acquisition_amount] = dec2.multiply(
                        holding.field_dict[declm.DB_acquisition_price], holding.field_dict[declm.DB_pieces])
                name = holding.field_dict[declm.DB_name]
                holding.field_dict.pop(declm.DB_name, None)
                holding.field_dict.pop(declm.DB_symbol, None)
                self.repo.replace_holding(holding.field_dict)
                result = self.repo.select_holding_total_of_iban(
                    iban=row_dict[declm.DB_iban], period=(row_dict[declm.DB_price_date], row_dict[declm.DB_price_date]))
                if result:
                    field_dict = {declm.DB_total_amount_portfolio: result[0][1]}
                    self.repo.update_holding_all_isin_codes(field_dict, row_dict[declm.DB_iban], row_dict[declm.DB_price_date]) # update all isin_codes
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_CHANGED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_price_date.upper(),
                            holding.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_ISIN.upper(),
                            holding.field_dict[declm.DB_ISIN], name
                            ]
                        )
                    )
        self.quit_widget()

    def new_row(self):

        row_dict = self.get_selected_row()
        self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        combo_dict,  combo_positioning_dict, protected, mandatory = self.new_row_properties()
        holding = BuiltTableRowBox(declm.HOLDING, declm.HOLDING_VIEW, row_dict,
                                   combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict, protected=protected, mandatory=mandatory,
                                   title=self.title, button1_text=decl.BUTTON_NEW)
        self.button_state = holding.button_state
        if holding.button_state == decl.WM_DELETE_WINDOW:
            return holding
        elif holding.button_state == decl.BUTTON_NEW:
            name = holding.field_dict[declm.DB_name]
            if self.repo.exist_holding_position(holding.field_dict[declm.DB_iban], holding.field_dict[declm.DB_ISIN], holding.field_dict[declm.DB_price_date]):
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_ROW_EXIST',
                    ' '.join(
                        [
                            declm.HOLDING.upper(),
                            '\n',
                            declm.DB_price_date.upper(),
                            holding.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_ISIN.upper(),
                            holding.field_dict[declm.DB_ISIN],
                            name
                            ]
                        )
                    )
            else:
                holding.field_dict[declm.DB_origin] = decl.ORIGIN_INSERTED
                holding.field_dict.pop(declm.DB_name, None)
                holding.field_dict.pop(declm.DB_symbol, None)
                self.repo.insert_holding( holding.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_INSERTED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_price_date.upper(),
                            holding.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_ISIN.upper(),
                            holding.field_dict[declm.DB_ISIN],
                            name
                            ]
                        )
                    )
        return holding

    def new_row_properties(self):

        protected = [declm.DB_iban, declm.DB_name, declm.DB_symbol]
        price_currency_dict = {declm.DB_price_currency: decl.CURRENCIES}
        amount_currency_dict = {declm.DB_amount_currency: decl.CURRENCIES}
        exchange_currency_1_dict = {declm.DB_exchange_currency_1: decl.CURRENCIES}
        exchange_currency_2_dict = {declm.DB_exchange_currency_2: decl.CURRENCIES}
        origin_dict = self.create_combo_list(declm.HOLDING, declm.DB_origin)
        combo_dict = {**price_currency_dict, **amount_currency_dict, **
                      exchange_currency_1_dict, **exchange_currency_2_dict, **origin_dict}
        isin_code_dict = self.create_combo_list(declm.ISIN, declm.DB_ISIN, from_date=None)
        combo_positioning_dict = isin_code_dict
        mandatory = declm.TABLE_FIELDS[declm.HOLDING_VIEW].copy()
        mandatory.remove(declm.DB_total_amount_portfolio)
        mandatory.remove(declm.DB_exchange_rate)
        mandatory.remove(declm.DB_exchange_currency_2)
        mandatory.remove(declm.DB_exchange_currency_1)
        mandatory.remove(declm.DB_name)
        return combo_dict,  combo_positioning_dict, protected, mandatory


class PandasBoxLedgerAccountCategory(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Ledger Pandastable
    """

    def create_dataframe(self):

        account = self.title.split()[4]
        dataframe = DataFrame(data=self.dataframe)
        dataframe[declm.DB_amount] = dataframe.apply(
            lambda row: row[declm.DB_amount] if row[declm.DB_credit_account] == account else -row[declm.DB_amount], axis=1)
        # total sum
        total_sum = dataframe[declm.DB_amount].sum()

        # Sort by 'Category'
        dataframe = dataframe.sort_values(by=[declm.DB_category, declm.DB_entry_date])

        # Group by 'Category' and append sum rows
        result = DataFrame()
        for group, group_df in dataframe.groupby(declm.DB_category):
            group_df = group_df.copy()
            group_df.loc[decl.FN_TOTAL] = {
                declm.DB_id_no: decl.FN_TOTAL,  declm.DB_entry_date: group, declm.DB_amount: group_df[declm.DB_amount].sum()}
            result = concat(
                [result, group_df], ignore_index=True)
        result.loc[decl.FN_TOTAL] = {
            declm.DB_entry_date: decl.FN_TOTAL, declm.DB_amount: total_sum}
        self.dataframe = result

    def set_row_format(self):

        for i, row in self.pandas_table.model.df.iterrows():
            if row[declm.DB_id_no] == decl.FN_TOTAL:
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')


class PandasBoxLedgerTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Ledger Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def __init__(self, title, data, message, mode=decl.EDIT_ROW, period=None, selected_row=0):

        self.repo = Repository()
        self.button_state = ''
        self.title = title
        self.data = data
        self.period = period

        self.selected_row = selected_row
        self.repo = Repository()
        self.credit_statement_missed = self.debit_statement_missed = []        
        if period:
            result = self.repo.select_ledger_statement_missed(self.period)
            if result:
                self.credit_statement_missed, self.debit_statement_missed = result
        self.message = message
        if data:
            super().__init__(title=title, dataframe=data, message=message,
                             mode=mode, selected_row=self.selected_row)
        else:
            self.new_row_insert({})

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def dataframe_append_sum(self):
        """
        Append Sum Row for column amount for Menu Ledger > Account
        """
        if ( get_menu_text("Account") in self.title
                and declm.DB_credit_account in self.dataframe.columns
                and declm.DB_debit_account in self.dataframe.columns):
            account = self.title.split()[3]
            self.dataframe[declm.DB_amount] = self.dataframe.apply(
                lambda row: row[declm.DB_amount] if row[declm.DB_credit_account] == account else -row[declm.DB_amount], axis=1)
            self.dataframe.loc[len(self.dataframe.index)] = {
                declm.DB_id_no: '',
                declm.DB_amount: self.dataframe[declm.DB_amount].sum()}

    def color_columns(self, column):

        if column == declm.DB_category:
            self.pandas_table.setColorByMask(
                declm.DB_category, self.dataframe[declm.DB_category] == decl.NOT_ASSIGNED, decl.COLOR_NOT_ASSIGNED)
        if column == declm.DB_debit_account:
            self.pandas_table.setColorByMask(
                declm.DB_debit_account, self.dataframe[declm.DB_debit_account] == decl.NOT_ASSIGNED, decl.COLOR_ERROR)
        if column == declm.DB_credit_account:
            self.pandas_table.setColorByMask(
                declm.DB_credit_account, self.dataframe[declm.DB_credit_account] == decl.NOT_ASSIGNED, decl.COLOR_ERROR)
        if column == declm.DB_credit_account:
            mask = self.dataframe[declm.DB_id_no].apply(
                lambda x: True if x in self.credit_statement_missed else False)
            self.pandas_table.setColorByMask(
                declm.DB_credit_account, mask, decl.COLOR_ERROR)
        if column == declm.DB_debit_account:
            mask = self.dataframe[declm.DB_id_no].apply(
                lambda x: True if x in self.debit_statement_missed else False)
            self.pandas_table.setColorByMask(
                declm.DB_debit_account, mask, decl.COLOR_ERROR)

    def _ledger_statement_missed(self, id_no, status=decl.DEBIT):
        """
        Determines the bank accounts in the ledger table
        that have no assignment to a bank transaction
        """
        highlight_list = self.repo.select_ledger_statement_missed(status, self.period)
        if id_no in highlight_list:
            return True
        else:
            return False

    def show_row(self):

        row_dict = self.get_selected_row()
        ledger = LedgerTableRowBox(declm.LEDGER, declm.LEDGER_VIEW, row_dict,
                                   protected=declm.TABLE_FIELDS[declm.LEDGER_VIEW],
                                   title=self.title,  button1_text=None, button2_text=None)
        self.message = ''
        if ledger.button_state == decl.WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def show_data(self, title, status):

        row_dict = self.get_selected_row()
        self.message = ''
        if row_dict:
            result = self.repo.get_statement_of_ledger(row_dict[declm.DB_id_no], status)
            if result:
                BuiltTableRowBox(declm.STATEMENT, declm.STATEMENT, result,
                                 protected=declm.TABLE_FIELDS[declm.STATEMENT],
                                 title=title,  button1_text=None, button2_text=None)
                self.message = ''
            else:
                # self.repo.delete_ledger_statement_with_idno_status(row_dict[declm.DB_id_no], status)
                # self.repo.delete_ledger(row_dict[declm.DB_id_no])                
                self.message = msg.get_message(msg.MESSAGE_TEXT, 'LEDGER_ROW')
        self.quit_widget()

    def show_credit_data(self):

        title = ' '.join([self.title, get_popup_menu_text("Show credit data")])
        self.show_data(title, decl.CREDIT)

    def show_debit_data(self):

        title = ' '.join([self.title, get_popup_menu_text("Show debit data")])
        self.show_data(title, decl.DEBIT)

    def del_row(self):

        row_dict = self.get_selected_row()
        self.message = ''
        if row_dict:
            ledger = LedgerTableRowBox(declm.LEDGER, declm.LEDGER_VIEW, row_dict,
                                       protected=declm.TABLE_FIELDS[declm.LEDGER_VIEW],
                                       title=self.title, button1_text=decl.BUTTON_DELETE, button2_text=None)
            if ledger.button_state == decl.WM_DELETE_WINDOW:
                return
            elif ledger.button_state == decl.BUTTON_DELETE:
                for field_name in declm.TABLE_FIELDS[declm.LEDGER_DELETE]:
                    if not ledger.field_dict[field_name]:
                        ledger.field_dict.pop(field_name, None)
                ledger.field_dict.pop(declm.DB_credit_name, None)
                ledger.field_dict.pop(declm.DB_debit_name, None)
                ledger.field_dict[declm.DB_amount] = ledger.field_dict[declm.DB_amount].removeprefix("-")  # menu ledger>account shows -amounts
                self.repo.insert_ledger_delete(ledger.field_dict)
                self.repo.delete_ledger(ledger.field_dict[declm.DB_id_no])
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_DELETED',
                    ' '.join([declm.DB_id_no.upper(), ledger.field_dict[declm.DB_id_no]])
                    )
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        self.message = ''
        if row_dict:
            row_dict = self.repo.get_ledger_view(row_dict[declm.DB_id_no])
            combo_dict,  combo_insert_value, combo_positioning_dict, protected, mandatory = self.new_row_properties()
            if self.repo.exist_ledger_statement_with_id_no_and_status(row_dict[declm.DB_id_no], decl.CREDIT):
                button3_text = decl.BUTTON_CREDIT
            else:
                button3_text = None
            if self.repo.exist_ledger_statement_with_id_no_and_status(row_dict[declm.DB_id_no], decl.DEBIT):
                button4_text = decl.BUTTON_DEBIT
            else:
                button4_text = None
            ledger = LedgerTableRowBox(declm.LEDGER, declm.LEDGER_VIEW, row_dict,
                                       protected=protected, mandatory=mandatory, combo_insert_value=combo_insert_value, combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict,
                                       title=self.title, button1_text=decl.BUTTON_UPDATE, button3_text=button3_text, button4_text=button4_text)
            if ledger.button_state == decl.WM_DELETE_WINDOW:
                return
            elif ledger.button_state == decl.BUTTON_UPDATE:
                for field_name in protected:
                    if field_name != declm.DB_id_no:
                        ledger.field_dict.pop(field_name, None)
                self.repo.update_ledger(ledger.field_dict, ledger.field_dict[declm.DB_id_no])
                # Update LEDGER_STATEMENT connection
                self._update_ledger_statement(
                    decl.CREDIT, ledger.field_dict, row_dict)
                self._update_ledger_statement(
                    decl.DEBIT, ledger.field_dict, row_dict)
                # Special for LEDGER Check Upload
                if get_menu_text("Check Upload") in self.title:
                    self.repo.update_ledger_upload_check(ledger.field_dict[declm.DB_id_no])
                # Special for LEDGER Check Bank Statement
                if get_menu_text("Check Bank Statement") in self.title:
                    self.repo.update_ledger({declm.DB_bank_statement_checked: 1}, ledger.field_dict[declm.DB_id_no])
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_CHANGED',
                    ' '.join([declm.DB_id_no.upper(), ledger.field_dict[declm.DB_id_no]])
                    )
        self.quit_widget()

    def _update_ledger_statement(self, status, ledger_dict, row_dict):
        """
        Connect ledger row to credit or debit statement row
        """

        if status == decl.CREDIT:
            ledger_account = ledger_dict[declm.DB_credit_account]
            row_account = row_dict[declm.DB_credit_account]
        else:
            ledger_account = ledger_dict[declm.DB_debit_account]
            row_account = row_dict[declm.DB_debit_account]
        if row_account != ledger_account:
            # disconnect old ledger statement credit/debit connection
            if self.repo.exist_ledger_statement_with_id_no_and_status(ledger_dict[declm.DB_id_no], status):
                self.repo.delete_ledger_statement_id_no(ledger_dict[declm.DB_id_no])
        ledger_coa = self.repo.get_ledger_coa_of_account(ledger_account)
        if not (ledger_coa and ledger_coa[declm.DB_iban] != decl.NOT_ASSIGNED and not ledger_coa[declm.DB_portfolio]):
            # its not a bank statement account
            return
        if row_account != ledger_account:
            # its a bank account, show selection of statements to assign
            PandasBoxLedgerStatement(
                self.title, ledger_coa[declm.DB_iban], status, ledger_dict)
        elif not self.repo.exist_ledger_statement_with_id_no_and_status(ledger_dict[declm.DB_id_no], status):
            # account not changed, its a bank account, but ledger statement connection not yet done
            PandasBoxLedgerStatement(
                self.title, ledger_coa[declm.DB_iban], status, ledger_dict)

    def new_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        combo_dict, combo_insert_value, combo_positioning_dict, protected, mandatory = self.new_row_properties()
        # create ledger
        ledger_dict = {declm.DB_currency: decl.EURO}
        while True:
            ledger = LedgerTableRowBox(declm.LEDGER, declm.LEDGER_VIEW, ledger_dict,
                                       protected=protected, mandatory=mandatory, combo_insert_value=combo_insert_value,
                                       combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict,
                                       title=self.title, button1_text=decl.BUTTON_NEW, button2_text=decl.BUTTON_COPY)
            if ledger.button_state == decl.BUTTON_COPY:
                ledger_dict = row_dict
                ledger_dict[declm.DB_currency] = decl.EURO
                ledger_dict.pop(declm.DB_id_no, None)
            else:
                break
        if ledger.button_state == decl.WM_DELETE_WINDOW:
            return ledger
        elif ledger.button_state == decl.BUTTON_NEW:
            for field_name in protected:
                if field_name != declm.DB_id_no:
                    ledger.field_dict.pop(field_name, None)
            ledger.field_dict[declm.DB_origin] = decl.ORIGIN_LEDGER
            if declm.DB_entry_date in ledger.field_dict:
                id_no = self.repo.get_new_id_no_of_year(ledger.field_dict[declm.DB_entry_date])
                ledger.field_dict[declm.DB_id_no] = id_no
                self.repo.insert_ledger(ledger.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_INSERTED',
                    ' '.join(
                        [
                            declm.LEDGER.upper(),
                            '\n',
                            declm.DB_id_no.upper(),
                            str(id_no)
                            ]
                        )
                    )
            else:
                self.message = msg.get_message(msg.MESSAGE_TEXT, 'ENTRY_DATE')
        return ledger

    def new_row_properties(self):

        protected = [declm.DB_id_no, declm.DB_date, declm.DB_debit_name, declm.DB_credit_name]
        mandatory = [declm.DB_entry_date, declm.DB_credit_account,
                     declm.DB_debit_account, declm.DB_amount, declm.DB_currency, declm.DB_purpose_wo_identifier]
        # get allowed accounts
        accounts_list = []
        accounts = self.repo.get_all_accounts()
        if accounts:
            for account_name in accounts:
                accounts_list.append(
                    ' '.join([account_name[0], account_name[1]]))
        # create combo_dict
        origin_dict = self.create_combo_list(
            declm.LEDGER, declm.DB_origin, date_name=declm.DB_entry_date)
        if not origin_dict:
            origin_dict = decl.ORIGINS
        category_dict = self.create_combo_list(
            declm.LEDGER, declm.DB_category, date_name=declm.DB_entry_date)
        applicant_name_dict = self.create_combo_list(
            declm.LEDGER, declm.DB_applicant_name, date_name=declm.DB_entry_date)
        combo_dict = {**origin_dict}
        combo_insert_value = [declm.DB_category, declm.DB_applicant_name]
        combo_positioning_dict = {**category_dict, **applicant_name_dict}
        combo_positioning_dict[declm.DB_currency] = decl.CURRENCIES
        combo_positioning_dict[declm.DB_credit_account] = accounts_list
        combo_positioning_dict[declm.DB_debit_account] = accounts_list
        return combo_dict,  combo_insert_value, combo_positioning_dict, protected, mandatory


class PandasBoxLedgerCoaTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        LedgerCoa Pandastable
                            Row Actions: Show, Delete, Update, New
    """
    NOT_USED = [declm.DB_eur_accounting, declm.DB_tax_on_input, declm.DB_value_added_tax,
                declm.DB_earnings, declm.DB_spendings, declm.DB_transfer_account, declm.DB_transfer_rate]

    def __init__(self, title, data, message, mode=decl.EDIT_ROW, selected_row=0):

        self.repo = Repository()
        self.title = title
        self.data = data
        self.message = message
        self.selected_row = selected_row
        if data:
            super().__init__(title=title, dataframe=data,
                             message=message, mode=mode, selected_row=self.selected_row)
        else:
            self.repo = Repository()
            ledger_coa = self.new_row_insert({})
            self.button_state = ledger_coa.button_state

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def show_row(self):

        row_dict = self.get_selected_row()
        ledger_coa = LedgerCoaTableRowBox(declm.LEDGER_COA, declm.LEDGER_COA, row_dict,
                                          protected=declm.TABLE_FIELDS[declm.LEDGER_COA],
                                          title=self.title,  button1_text=None, button2_text=None)
        self.button_state = ledger_coa.button_state
        if ledger_coa.button_state == decl.WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            ledger_coa = LedgerCoaTableRowBox(
                declm.LEDGER_COA, declm.LEDGER_COA, row_dict, protected=declm.TABLE_FIELDS[declm.LEDGER_COA],
                title=self.title, button1_text=decl.BUTTON_DELETE, button2_text=None
                )
            self.button_state = ledger_coa.button_state
            if ledger_coa.button_state == decl.WM_DELETE_WINDOW:
                return
            elif ledger_coa.button_state == decl.BUTTON_DELETE:
                self.repo.delete_ledger_coa(ledger_coa.field_dict[declm.DB_account])
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_DELETED',
                    ' '.join([self.title, '\n', declm.DB_account.upper(), ledger_coa.field_dict[declm.DB_account]])
                    )
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            protected = [declm.DB_account] + PandasBoxLedgerCoaTable.NOT_USED
            mandatory = [declm.DB_name]
            ledger_coa = LedgerCoaTableRowBox(declm.LEDGER_COA, declm.LEDGER_COA, row_dict,
                                              protected=protected, mandatory=mandatory,
                                              combo_positioning_dict={declm.DB_iban: self.get_all_ibans()},
                                              combo_insert_value=[declm.DB_iban], 
                                              title=self.title, button1_text=decl.BUTTON_UPDATE)

            self.button_state = ledger_coa.button_state
            if ledger_coa.button_state == decl.WM_DELETE_WINDOW:
                return
            elif ledger_coa.button_state == decl.BUTTON_UPDATE:
                self.repo.replace_ledger_coa(ledger_coa.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_CHANGED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_account.upper(),
                            ledger_coa.field_dict[declm.DB_account]
                            ]
                        )
                    )
        self.quit_widget()

    def new_row(self):

        row_dict = self.get_selected_row()
        self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        mandatory = [declm.DB_account, declm.DB_name]
        ledger_coa = LedgerCoaTableRowBox(declm.LEDGER_COA, declm.LEDGER_COA, row_dict,
                                          mandatory=mandatory, protected=PandasBoxLedgerCoaTable.NOT_USED,
                                          title=self.title, button1_text=decl.BUTTON_NEW)
        self.button_state = ledger_coa.button_state
        if ledger_coa.button_state == decl.WM_DELETE_WINDOW:
            return ledger_coa
        elif ledger_coa.button_state == decl.BUTTON_NEW:
            if self.repo.exist_ledger_coa_with_account(ledger_coa.field_dict[declm.DB_account]):
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_ROW_EXIST',
                    ' '.join(
                        [
                            declm.LEDGER_COA.upper(),
                            '\n',
                            declm.DB_account.upper(),
                            ledger_coa.field_dict[declm.DB_account]
                            ]
                        )
                    )
            else:
                self.repo.insert_ledger_coa(ledger_coa.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_INSERTED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_account.upper(),
                            ledger_coa.field_dict[declm.DB_account]
                            ]
                        )
                    )
        return ledger_coa

    def get_all_ibans(self):
        
        bank_codes = self.repo.listbank_codes()
        ibans = []
        for bank_code in bank_codes:
            accounts = self.repo.shelve_get_accounts(bank_code)
            for acc in accounts:
                ibans.append(acc[decl.KEY_ACC_IBAN])
        return ibans        

class PandasBoxLedgerStatement(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows selection of statements for allocation in the ledger
    """

    def __init__(self, title, iban, status, ledger_dict):

        self.title = title
        self.status = status
        self.iban = iban
        self.ledger_dict = ledger_dict
        if status == decl.CREDIT:
            # Credit always 2nd account transaction (after debit) , therefore 5 days back
            self.from_date = self.ledger_dict[declm.DB_entry_date]
            self.to_date = date_days.add(self.ledger_dict[declm.DB_entry_date], 5)
        if status == decl.DEBIT:
            # Debit always 1st account transaction (before credit), therefore 5 days in advance
            self.from_date = date_days.subtract(self.ledger_dict[declm.DB_entry_date], 5)
            self.to_date = self.ledger_dict[declm.DB_entry_date]            
        title = ' '.join(
            [
                self.title,
                msg.get_message(
                    msg.MESSAGE_TEXT,
                    'ASSINGNABLE_STATEMENTS',
                    self.from_date,
                    self.to_date
                    )
                ]
            )
        super().__init__(title=title,
                         message=msg.get_message(msg.MESSAGE_TEXT, 'SELECT_ROW'), mode=decl.CURRENCY_SIGN)

    def create_dataframe(self):

        period = (self.from_date, self.to_date)
        statement_list = self.repo.get_statements_of_amount(self.iban, period, self.status,self.ledger_dict[declm.DB_amount])
        new_statement_list = []
        for statement_dict in statement_list:
            if not self.repo.exist_ledger_statement(statement_dict[declm.DB_iban], statement_dict[declm.DB_entry_date], statement_dict[declm.DB_counter]):
                new_statement_list.append(statement_dict)
        if new_statement_list:
            self.dataframe = DataFrame(new_statement_list)
        else:
            if self.status == decl.CREDIT:
                msg.MessageBoxInfo(
                    msg.get_message(
                        msg.MESSAGE_TEXT,
                        'LEDGER_STATEMENT_ASSIGMENT_EMPTY',
                        self.ledger_dict[declm.DB_id_no],
                        self.ledger_dict[declm.DB_credit_account]
                        )
                    )
            else:
                msg.MessageBoxInfo(
                    msg.get_message(
                        msg.MESSAGE_TEXT,
                        'LEDGER_STATEMENT_ASSIGMENT_EMPTY',
                        self.ledger_dict[declm.DB_id_no],
                        self.ledger_dict[declm.DB_debit_account]
                        )
                    )
            self.abort = True
            destroy_widget(self.dataframe_window)

    def processing(self):

        statement_dict = self.get_selected_row()
        if statement_dict:
            ledger_statement_dict = {}
            ledger_statement_dict[declm.DB_iban] = statement_dict[declm.DB_iban]
            ledger_statement_dict[declm.DB_entry_date] = statement_dict[declm.DB_entry_date]
            ledger_statement_dict[declm.DB_counter] = statement_dict[declm.DB_counter]
            ledger_statement_dict[declm.DB_status] = self.status
            ledger_statement_dict[declm.DB_id_no] = self.ledger_dict[declm.DB_id_no]
            self.repo.insert_ledger_statement(ledger_statement_dict)
        self.quit_widget()


class PandasBoxStatementTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Statement Pandastable
                            Row Actions: Show
    """

    def __init__(self, title, data, message, mode=decl.EDIT_ROW):

        self.title = title
        self.data = data
        self.message = message
        super().__init__(title=title, dataframe=data,
                         message=message, mode=mode)

    def _debit(self, amount, status=decl.CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == decl.DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)
        names = self.dataframe.columns.tolist()
        if declm.DB_amount in names:
            self.dataframe[declm.DB_amount] = self.dataframe[[declm.DB_amount, declm.DB_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if declm.DB_opening_balance in names:
            self.dataframe[declm.DB_opening_balance] = self.dataframe[[declm.DB_opening_balance, declm.DB_opening_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if declm.DB_closing_balance in names:
            self.dataframe[declm.DB_closing_balance] = self.dataframe[[declm.DB_closing_balance, declm.DB_closing_status]].apply(
                lambda x: self._debit(*x), axis=1)

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            axis=1, errors='ignore',
            columns=[declm.DB_currency, declm.DB_status, declm.DB_opening_currency, declm.DB_opening_status,
                     declm.DB_closing_currency, declm.DB_closing_status, declm.DB_amount_currency, declm.DB_price_currency
                     ]
        )
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()

    def show_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            row_dict = self.repo.get_statement(row_dict[declm.DB_iban], row_dict[declm.DB_entry_date], row_dict[declm.DB_counter])
            if not row_dict:
                return
            statement = BuiltTableRowBox(
                declm.STATEMENT, declm.STATEMENT, row_dict, title=self.title,
                protected=declm.TABLE_FIELDS[declm.STATEMENT],
                button1_text=None, button2_text=None)
            self.button_state = statement.button_state
            if statement.button_state == decl.WM_DELETE_WINDOW:
                return
        self.quit_widget()


class PandasBoxStatementNoLedgerTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Statement (without assigned Ledger) rowPandastable
                            Row Actions: Show
    """

    def __init__(self, title, data, message, mode=decl.EDIT_ROW):

        self.title = title
        self.data = data
        self.message = message
        super().__init__(title=title, dataframe=data,
                         message=message, mode=mode)

    def _debit(self, amount, status=decl.CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == decl.DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)
        names = self.dataframe.columns.tolist()
        if declm.DB_amount in names:
            self.dataframe[declm.DB_amount] = self.dataframe[[declm.DB_amount, declm.DB_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if declm.DB_opening_balance in names:
            self.dataframe[declm.DB_opening_balance] = self.dataframe[[declm.DB_opening_balance, declm.DB_opening_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if declm.DB_closing_balance in names:
            self.dataframe[declm.DB_closing_balance] = self.dataframe[[declm.DB_closing_balance, declm.DB_closing_status]].apply(
                lambda x: self._debit(*x), axis=1)

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            axis=1, errors='ignore',
            columns=[declm.DB_currency, declm.DB_status, declm.DB_opening_currency, declm.DB_opening_status,
                     declm.DB_closing_currency, declm.DB_closing_status, declm.DB_amount_currency, declm.DB_price_currency
                     ]
        )
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()

    def new_row(self):
        #  inserts new row in ledger table !!!
        row_dict = self.get_selected_row()  #  row of selected Statement
        if row_dict:
            self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):
        """
        Creates a new ledger row !!!
        if the selected statement row is unassigned to any ledger row.
        The new ledger row is then assigned to this selected statement row.
        """
        ledger_row = self.repo.get_ledger_of_statement(
            row_dict[declm.DB_iban],
            row_dict[declm.DB_entry_date],
            row_dict[declm.DB_counter]
            )
        if ledger_row:
            self.message = msg.get_message(msg.MESSAGE_TEXT, 'LEDGER_ALREADY_ASSIGNED',  str(ledger_row[declm.DB_id_no]))
            return
        statement_row = self.repo.get_statement_copy_to_ledger(
            row_dict[declm.DB_iban],
            row_dict[declm.DB_entry_date],
            row_dict[declm.DB_counter]            
            )
        combo_positioning_dict, mandatory = self.new_row_properties()
        # create ledger
        ledger_dict = {}
        ledger_dict[declm.DB_entry_date] = row_dict[declm.DB_entry_date]
        ledger_dict[declm.DB_date] = statement_row[declm.DB_date]
        if statement_row[declm.DB_status]==decl.CREDIT:
            ledger_dict[declm.DB_credit_account] = self.repo.get_account_of_iban(row_dict[declm.DB_iban])
        else:    
            ledger_dict[declm.DB_debit_account] = self.repo.get_account_of_iban(row_dict[declm.DB_iban])
        ledger_dict[declm.DB_purpose_wo_identifier] = statement_row[declm.DB_purpose_wo_identifier]
        ledger_dict[declm.DB_amount] = statement_row[declm.DB_amount]
        account = self.repo.get_account_of_iban(row_dict[declm.DB_iban])
        if account:
            name = self.repo.get_name_of_account(account)
        else:
            self.message = msg.get_message(msg.MESSAGE_TEXT, 'IBAN_MISSED',  row_dict[declm.DB_iban])
            return
        protected = declm.TABLE_FIELDS[declm.LEDGER].copy()
        if statement_row[declm.DB_status]==decl.CREDIT:
            ledger_dict[declm.DB_credit_account] = account
            protected.remove(declm.DB_debit_account)            
            ledger_dict[declm.DB_credit_name] = name
        else:    
            ledger_dict[declm.DB_debit_account] = account
            protected.remove(declm.DB_credit_account)            
            ledger_dict[declm.DB_debit_name] = name
        ledger_dict[declm.DB_applicant_name] = statement_row[declm.DB_applicant_name]
        ledger_dict[declm.DB_currency] = decl.EURO
        ledger_dict[declm.DB_origin] = decl.ORIGIN_INSERTED
        ledger = LedgerTableRowBox(declm.LEDGER, declm.LEDGER_VIEW, ledger_dict,
                                   protected=protected, mandatory=mandatory,
                                   combo_positioning_dict=combo_positioning_dict,
                                   title=msg.get_message(msg.MESSAGE_TEXT, 'LEDGER_CREATE', declm.LEDGER), button1_text=decl.BUTTON_NEW)
        if ledger.button_state == decl.WM_DELETE_WINDOW:
            return
        elif ledger.button_state == decl.BUTTON_NEW:
            id_no = self.repo.get_new_id_no_of_year(row_dict[declm.DB_entry_date])
            ledger.field_dict[declm.DB_id_no] = id_no
            ledger.field_dict.pop(declm.DB_credit_name, None)
            ledger.field_dict.pop(declm.DB_debit_name, None)
            self.repo.insert_ledger( ledger.field_dict)
            # connect to ledger_statemnt
            ledger_statement_dict = {}
            ledger_statement_dict[declm.DB_iban] = row_dict[declm.DB_iban]
            ledger_statement_dict[declm.DB_entry_date] = row_dict[declm.DB_entry_date]
            ledger_statement_dict[declm.DB_counter] = row_dict[declm.DB_counter]
            ledger_statement_dict[declm.DB_status] = statement_row[declm.DB_status]
            ledger_statement_dict[declm.DB_id_no] = id_no
            self.repo.insert_ledger_statement(ledger_statement_dict)            
            self.message = msg.get_message(
                msg.MESSAGE_TEXT,
                'DATA_INSERTED',
                ' '.join(
                    [
                        declm.LEDGER.upper(),
                        '\n',
                        declm.DB_id_no.upper(),
                        str(id_no)
                        ]
                    )
                )
        return

    def new_row_properties(self):

        mandatory = [declm.DB_credit_account,  declm.DB_debit_account]
        # get allowed accounts
        accounts_list = []
        accounts = self.repo.get_all_accounts()
        if accounts:
            for account_name in accounts:
                accounts_list.append(
                    ' '.join([account_name[0], account_name[1]]))
        # create combo_dict
        combo_positioning_dict = {}
        combo_positioning_dict[declm.DB_credit_account] = accounts_list
        combo_positioning_dict[declm.DB_debit_account] = accounts_list
        return combo_positioning_dict, mandatory


class PandasBoxTotals(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Totals

    PARAMETER:
        data           data_total_amounts (list of tuple: (iban/account, entry_date, sum)
    """

    def __init__(self, title, data):

        self.title = title
        self.data = data
        super().__init__(title=title, dataframe=data, mode=decl.NUMERIC)

    def create_dataframe(self):

        self.dataframe = DataFrame(self.data)
        self.dataframe[declm.DB_account] = self.dataframe[declm.DB_account].astype(str) + "/" + self.dataframe[declm.DB_name].astype(str)
        self.dataframe = self.dataframe.sort_values([declm.DB_account, declm.DB_entry_date])
        self.dataframe = self.dataframe.pivot_table(index=[declm.DB_entry_date], columns=[
            declm.DB_account], values=[decl.FN_BALANCE])
        self.dataframe[decl.FN_TOTAL] = self.dataframe.sum(
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
            columns=[declm.DB_ISIN, declm.DB_name, decl.FN_PROFIT, declm.DB_amount_currency, declm.DB_pieces])
        self.dataframe.drop(columns=[declm.DB_pieces], inplace=True, axis=1)
        sum_row = {declm.DB_ISIN: '',  declm.DB_name: 'TOTAL: ',
                   decl.FN_PROFIT: self.dataframe[decl.FN_PROFIT].sum(), declm.DB_amount_currency: decl.EURO}
        self.dataframe.loc[len(self.dataframe.index)] = sum_row


class PandasBoxTransactionDetail(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Transactions

    PARAMETER:
        dataframe           List of tuples with transaction data
    """

    def create_dataframe(self):

        self.dataframe = DataFrame(
            self.dataframe,
            columns=[declm.DB_price_date, declm.DB_counter, declm.DB_transaction_type,
                     declm.DB_price, declm.DB_pieces, decl.FN_PIECES_CUM, declm.DB_posted_amount, decl.FN_PROFIT_LOSS, declm.DB_iban])
        """
        deliveries = self.dataframe[declm.DB_transaction_type] == TRANSACTION_RECEIPT
        # Replace values where the condition is False.
        self.dataframe[declm.DB_pieces] = self.dataframe[declm.DB_pieces].where(deliveries, -self.dataframe[declm.DB_pieces])

        receipts = self.dataframe[declm.DB_transaction_type] == TRANSACTION_DELIVERY
        self.dataframe[declm.DB_posted_amount] = self.dataframe[declm.DB_posted_amount].where(receipts, -self.dataframe[declm.DB_posted_amount])
        """
        self.dataframe[decl.FN_PROFIT_CUM] = self.dataframe[decl.FN_PROFIT_LOSS].cumsum()
        closed_postion = self.dataframe[decl.FN_PIECES_CUM] == 0
        self.dataframe[decl.FN_PROFIT_CUM] = self.dataframe[decl.FN_PROFIT_CUM].where(closed_postion, other=0)
        print
        if decl.FN_ALL_BANKS in self.title:
            account_names = self.repo.get_ledger_coa_names_with_iban()
            self.dataframe[decl.FN_BANK_NAME] = self.dataframe[declm.DB_iban].apply(lambda x: account_names[x])
            self.dataframe.sort_values(
                by=[declm.DB_price_date, declm.DB_counter, declm.DB_transaction_type],
                ascending=[True, True, False],
                inplace=True)
        self.dataframe.drop(columns=[declm.DB_counter, declm.DB_iban], inplace=True)

    def set_row_format(self):

        for i, row in self.pandas_table.model.df.iterrows():
            if row[declm.DB_transaction_type] == 'CLOSE':
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')
            elif row[decl.FN_PIECES_CUM] == 0:
                self.pandas_table.setRowColors(
                    rows=[i], clr='yellow', cols='all')


class PandasBoxTransactionTableShow (BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        TRANSACTION Pandastable
                            Row Actions: Show
    """

    def __init__(self, title, data, message, iban, isin='', isin_name='', mode=decl.EDIT_ROW):

        self.title = title
        self.data = data
        self.message = message
        if data:
            super().__init__(title=title, dataframe=data, message=message, mode=mode)
        else:
            self.repo = Repository()
            transaction = self.new_row_insert(
                {declm.DB_iban: iban, declm.DB_ISIN: isin, declm.DB_name: isin_name})
            self.button_state = transaction.button_state

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def show_row(self):

        row_dict = self.get_selected_row()
        transaction = BuiltTableRowBox(
            declm.TRANSACTION, declm.TRANSACTION_VIEW, row_dict, title=self.title,
            protected=declm.TABLE_FIELDS[declm.TRANSACTION_VIEW],
            button1_text=None, button2_text=None)
        self.button_state = transaction.button_state
        if transaction.button_state == decl.WM_DELETE_WINDOW:
            return
        self.quit_widget()


class PandasBoxTransactionTable(PandasBoxTransactionTableShow):
    """
    TOP-LEVEL-WINDOW        TRANSACTION Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            transaction = BuiltTableRowBox(
                declm.TRANSACTION, declm.TRANSACTION_VIEW, row_dict, title=self.title,
                protected=declm.TABLE_FIELDS[declm.TRANSACTION_VIEW],
                button1_text=decl.BUTTON_DELETE, button2_text=None)
            self.button_state = transaction.button_state
            if transaction.button_state == decl.WM_DELETE_WINDOW:
                return
            elif transaction.button_state == decl.BUTTON_DELETE:
                self.repo.delete_transaction(
                    transaction.field_dict[declm.DB_iban], transaction.field_dict[declm.DB_ISIN],
                    transaction.field_dict[declm.DB_price_date], transaction.field_dict[declm.DB_counter]
                    )
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_DELETED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_price_date.upper(),
                            transaction.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_counter.upper(),
                            transaction.field_dict[declm.DB_counter]
                            ]
                        )
                    )
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            row_dict = self.repo.get_transaction(row_dict[declm.DB_iban], row_dict[declm.DB_ISIN], row_dict[declm.DB_price_date], row_dict[declm.DB_counter])
            if not row_dict:
                return
            protected = [declm.DB_iban, declm.DB_ISIN, declm.DB_price_date, declm.DB_counter, declm.DB_name]
            mandatory = [declm.DB_transaction_type, declm.DB_price_currency,
                         declm.DB_price, declm.DB_pieces, declm.DB_amount_currency]
            transaction_type_dict = {declm.DB_transaction_type: decl.TRANSACTION_TYPES}
            price_currency_dict = {declm.DB_price_currency: decl.CURRENCIES}
            amount_currency_dict = {declm.DB_amount_currency: decl.CURRENCIES}
            origin_dict = self.create_combo_list(declm.TRANSACTION, declm.DB_origin)
            combo_dict = origin_dict
            combo_positioning_dict = {**transaction_type_dict,
                                      **price_currency_dict, **amount_currency_dict}
            transaction = BuiltTableRowBox(declm.TRANSACTION, declm.TRANSACTION_VIEW, row_dict,
                                           protected=protected, mandatory=mandatory, combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict,
                                           title=self.title)
            self.button_state = transaction.button_state
            if transaction.button_state == decl.WM_DELETE_WINDOW:
                return
            elif transaction.button_state == decl.BUTTON_SAVE:
                transaction.field_dict.pop(declm.DB_name, None)
                self.repo.replace_transaction(transaction.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_CHANGED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_price_date.upper(),
                            transaction.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_counter.upper(),
                            transaction.field_dict[declm.DB_counter]
                            ]
                        )
                    )
        self.quit_widget()

    def new_row(self):

        row_dict = self.get_selected_row()
        row_dict[declm.DB_origin] = ''
        row_dict[declm.DB_counter] = 0
        self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        combo_dict,  combo_positioning_dict, protected, mandatory = self.new_row_properties()
        row_dict[declm.DB_price_currency] = decl.EURO
        row_dict[declm.DB_amount_currency] = decl.EURO
        transaction = BuiltTableRowBox(declm.TRANSACTION, declm.TRANSACTION_VIEW, row_dict,
                                       combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict, protected=protected, mandatory=mandatory,
                                       title=self.title, button1_text=decl.BUTTON_NEW)
        self.button_state = transaction.button_state
        if transaction.button_state == decl.WM_DELETE_WINDOW:
            return transaction
        elif transaction.button_state == decl.BUTTON_NEW:
            if self.repo.exist_transaction(transaction.field_dict[declm.DB_iban], transaction.field_dict[declm.DB_ISIN], transaction.field_dict[declm.DB_price_date], transaction.field_dict[declm.DB_counter]):
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_ROW_EXIST',
                    ' '.join(
                        [
                            declm.TRANSACTION.upper(),
                            '\n',
                            declm.DB_price_date.upper(),
                            transaction.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_ISIN.upper(),
                            transaction.field_dict[declm.DB_ISIN],
                            '\n',
                            declm.DB_counter.upper(),
                            transaction.field_dict[declm.DB_counter]
                            ]
                        )
                    )
            else:
                if transaction.field_dict[declm.DB_posted_amount]:
                    pass
                else:
                    transaction.field_dict[declm.DB_posted_amount] = dec2.multiply(
                        transaction.field_dict[declm.DB_price], transaction.field_dict[declm.DB_pieces])
                transaction.field_dict[declm.DB_origin] = decl.ORIGIN_INSERTED
                transaction.field_dict.pop(declm.DB_name, None)
                self.repo.insert_transaction(transaction.field_dict)
                self.message = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DATA_INSERTED',
                    ' '.join(
                        [
                            self.title,
                            '\n',
                            declm.DB_price_date.upper(),
                            transaction.field_dict[declm.DB_price_date],
                            '\n',
                            declm.DB_ISIN.upper(),
                            transaction.field_dict[declm.DB_ISIN],
                            '\n',
                            declm.DB_counter.upper(),
                            transaction.field_dict[declm.DB_counter]
                            ]
                        )
                    )
        return transaction

    def new_row_properties(self):

        protected = [declm.DB_iban, declm.DB_ISIN, declm.DB_name]
        mandatory = [declm.DB_ISIN, declm.DB_price_date, declm.DB_counter, declm.DB_transaction_type, declm.DB_price_currency,
                     declm.DB_price, declm.DB_pieces, declm.DB_amount_currency]
        transaction_type_dict = {declm.DB_transaction_type: decl.TRANSACTION_TYPES}
        price_currency_dict = {declm.DB_price_currency: decl.CURRENCIES}
        amount_currency_dict = {declm.DB_amount_currency: decl.CURRENCIES}
        origin_dict = self.create_combo_list(declm.TRANSACTION, declm.DB_origin)
        combo_dict = origin_dict
        combo_positioning_dict = {**transaction_type_dict,
                                  **price_currency_dict, **amount_currency_dict}
        return combo_dict,  combo_positioning_dict, protected, mandatory


class PandasBoxPiecesConsistency(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe 
                            whether the accumulated pieces from TRANSACTION table
                            match the HOLDING table pieces.

    PARAMETER:
        dataframe           DataFrame object
    """

    def create_dataframe(self):

        self.dataframe = DataFrame(self.dataframe)
        cols_to_check = [declm.DB_ISIN, "holding_pieces", "transaction_cum_pieces"]
        self.dataframe = self.dataframe.loc[~self.dataframe[cols_to_check].eq(self.dataframe[cols_to_check].shift()).all(axis=1)]
        #self.dataframe = self.dataframe.sort_values(by=declm.DB_price_date)

    def show_row(self):

        row_dict = self.get_selected_row()
        iban = row_dict[declm.DB_iban]
        isin_code = row_dict[declm.DB_ISIN]
        name = row_dict[declm.DB_name]
        period = (decl.START_DATE_TRANSACTIONS, date_days.today())
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        while True:
            data = self.repo.get_transactions_of_iban_isin_code(iban, isin_code, period)
            transaction_table = PandasBoxTransactionTable(
                self.title, data, message, iban, isin_code, name, mode=decl.EDIT_ROW)
            message = transaction_table.message
            if transaction_table.button_state == decl.WM_DELETE_WINDOW:
                break

class TechnicalIndicator(InputISIN):
    """
    Parameter
     selection_name --> Storage name for last used selection values
     data_dict --> default values of select_data

    1. Volume Indicators
    2. Volatility Indicators
    3. Trend Indicators
    4. Momentum Indicators
    5. Other Indicators
    Details (see in declarations.py TechnicalIndicatorData)
    """

    TA_MENU_TEXT = {
        'Volume': 'Volume',
        'Volatility': 'Volatility',
        'Trend': 'Trend',
        'Momentum': 'Momentum',
        'Others': 'Others'
        }

    def __init__(self, title=msg.MESSAGE_TITLE, data_dict={}, container=[], selection_name=None):
        
        self.repo = Repository()
        self.srv = Services(self.repo)        

        super().__init__(title=title, header=None, table=None,
                         button1_text=decl.BUTTON_INDICATOR, button2_text=None,
                         button3_text=None, button4_text=None,
                         selection_name=selection_name,
                         data_dict=data_dict,
                         upper=[], separator=[],
                         container=container
                         )

    def comboboxselected_action(self, event):

        self._box_window_top.config(menu='')  # remove technical indicator  menu
        InputISIN.comboboxselected_action(self, event)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():
            self.srv.import_prices_and_corporate_actions(self.title, [self.field_dict[declm.DB_name]], state=decl.BUTTON_APPEND)
            data = self.repo.get_prices_of_period(
                self.repo.get_isin_of_name(self.field_dict[declm.DB_name]),
                (self.field_dict[decl.FN_FROM_DATE], self.field_dict[decl.FN_TO_DATE])
                )
            if data:
                dataframe = self._convert_decimals_to_float(DataFrame(data))
                # extend to technical indicator dataframe
                dataframe = ta.utils.dropna(dataframe)
                dataframe = ta.add_all_ta_features(
                    dataframe,
                    open=declm.DB_open,
                    high=declm.DB_high,
                    low=declm.DB_low,
                    close=declm.DB_close,
                    volume=declm.DB_volume,
                    fillna=True
                )
                dataframe = dataframe.set_index(dataframe.columns[0])
                self._set_menu(dataframe)
            else:
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', declm.PRICES.upper(), self.field_dict[declm.DB_name]))

    def quit_widget(self):

        self._geometry_put(self._box_window_top)
        destroy_widget(self._box_window_top)

    def _convert_decimals_to_float(self, df: DataFrame) -> DataFrame:
        for col in df.columns:
            # Check if the column contains at least one Decimal value
            if df[col].map(lambda x: isinstance(x, Decimal)).any():
                # Convert only Decimal values to float; leave all other values unchanged
                df[col] = df[col].map(lambda x: float(x) if isinstance(x, Decimal) else x)
        return df

    def _set_menu(self, dataframe):
        """
        create menu with technical indicators
        """
        try:
            menubar = Menu(self._box_window_top)
            volume_menu = Menu(menubar, tearoff=0)
            for indicator in decl.TechnicalIndicatorData.TA_VOLUME.keys():
                volume_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=decl.TechnicalIndicatorData.TA_VOLUME[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT.get("Volume"), menu=volume_menu)
            volatility_menu = Menu(menubar, tearoff=0)
            for indicator in decl.TechnicalIndicatorData.TA_VOLATILITY.keys():
                volatility_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=decl.TechnicalIndicatorData.TA_VOLATILITY[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT.get("Volatility"), menu=volatility_menu)
            trend_menu = Menu(menubar, tearoff=0)
            for indicator in decl.TechnicalIndicatorData.TA_TREND.keys():
                trend_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=decl.TechnicalIndicatorData.TA_TREND[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT.get("Trend"), menu=trend_menu)
            momentum_menu = Menu(menubar, tearoff=0)
            for indicator in decl.TechnicalIndicatorData.TA_MOMENTUM.keys():
                momentum_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=decl.TechnicalIndicatorData.TA_MOMENTUM[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT.get("Momentum"), menu=momentum_menu)
            others_menu = Menu(menubar, tearoff=0)
            for indicator in decl.TechnicalIndicatorData.TA_OTHERS.keys():
                others_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=decl.TechnicalIndicatorData.TA_OTHERS[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT.get("Others"), menu=others_menu)
            self._box_window_top.config(menu=menubar)
        except Exception as e:
            import traceback
            print("Error in menu command:", e)
            traceback.print_exc()

    def _show_indicator(self, dataframe, indicator_columns, indicator):

        title = ' '.join([indicator, self.field_dict[declm.DB_name]])
        line_columns = []
        if indicator in decl.TechnicalIndicatorData.TA_LINES.keys():
            for line_column in decl.TechnicalIndicatorData.TA_LINES[indicator]:
                line_column_name, line_column_value = line_column
                dataframe[line_column_name] = line_column_value
                line_columns.append(line_column_name)
        decl.TechnicalIndicatorData.TA_CLOSE = []
        BuiltPandasBox(title=title, dataframe=dataframe[indicator_columns + line_columns],
                       mode=decl.NUMERIC, instant_plotting=True)
        if self.button_state == decl.WM_DELETE_WINDOW:
            return
        BuiltPandasBox(title=title, dataframe=dataframe[indicator_columns + decl.TechnicalIndicatorData.TA_CLOSE + line_columns],
                       mode=decl.NUMERIC, instant_plotting=True)


class SelectCloseVolume(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Select additional charts

    Select addtional charts to technical indicator chart

    PARAMETER:
        checkbutton_texts    List  of Fields

        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self):

        super().__init__(
            title=msg.get_message(msg.MESSAGE_TEXT, 'TA_ADD_CHART'), header=msg.get_message(msg.MESSAGE_TEXT, 'CHECKBOX'),
            button1_text=decl.BUTTON_ADD_CHART, button2_text=None,
            checkbutton_texts=[declm.DB_close, declm.DB_volume],
            default_texts=decl.TechnicalIndicatorData.TA_CLOSE
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
            if textline[0:12] == decl.ERROR:
                self.text_widget.tag_add(decl.ERROR, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(decl.ERROR, foreground='RED')
            elif textline[0:12] == decl.WARNING:
                self.text_widget.tag_add(decl.WARNING, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(decl.WARNING, foreground='BLUE')
            elif textline[0:12] == decl.INFORMATION:
                self.text_widget.tag_add(decl.INFORMATION, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(decl.INFORMATION, foreground='GREEN')

    def destroy_widget(self, text):

        info = re.compile(decl.INFORMATION)
        if info.search(text):
            return False
        warn = re.compile(decl.WARNING)
        if warn.search(text):
            return False
        err = re.compile(decl.ERROR)
        if err.search(text):
            return False
        return True


class VersionTransaction(BuiltEnterBox):
    """
    Top-level window to select transaction versions (e.g. HKKAZ, HKCAZ, HKWPD).

    Parameters:
        title (str): Window title
        bank_code (str): Bank identifier
        transaction_versions (Dict[str, int]): Predefined transaction versions
            Example: {'KAZ': 7, 'WPD': 6, 'TAN': 7}

    Attributes:
        button_state (str): Text of selected button
        field_dict (Dict[str, int]): Selected transaction versions
    """

    def __init__(self, title: str, bank_code: str, transaction_versions: Dict[str, int]):
        self.bank_code = bank_code
        self.transaction_versions = transaction_versions or {}

        # Load allowed versions from repository
        self.transaction_version_allowed: Dict[str, List[int]] = (
            Repository().shelve_get_version_transaction_allowed(self.bank_code)
        )

        if not self.transaction_version_allowed:
            msg.MessageBoxTermination()
            return

        field_defs = self._create_field_defs()
        field_defs = self._set_defaults(
            field_defs,
            self.transaction_version_allowed,
            self.transaction_versions
        )

        super().__init__(
            title=title,
            header=f'Transaction Versions ({self.bank_code})',
            field_defs=field_defs
        )

    def _create_field_defs(self) -> List[Any]:
        """
        Create UI field definitions based on allowed transactions.
        """

        def label(key: str) -> str:
            return "statements" if key.endswith("AZ") else "holdings"

        return [
            FieldDefinition(
                definition=decl.COMBO,
                name=f"HK{key} {label(key)}",
                length=1,
                combo_values=values
            )
            for key, values in self.transaction_version_allowed.items()
        ]

    def _set_defaults(
        self,
        field_defs: List[Any],
        allowed: Dict[str, List[int]],
        selected: Dict[str, int]
    ) -> List[Any]:
        """
        Set default values for each field.

        Priority:
        1. Use value from `selected` (transaction_versions) if available
        2. Otherwise fallback to first value from `allowed`

        Args:
            field_defs: List of field definitions
            allowed: Allowed versions per transaction (e.g. {'KAZ': [1,2]})
            selected: Preselected versions (e.g. {'KAZ': 7})

        Returns:
            New list of field definitions with defaults applied
        """

        new_fields = []

        for field in field_defs:
            new_field = copy(field)

            # Extract key: "HKKAZ statements" -> "KAZ"
            field_prefix = new_field.name.split()[0]  # "HKKAZ"
            key = field_prefix.replace("HK", "")      # "KAZ"

            if key in selected:
                # Use explicitly provided version
                new_field.default_value = selected[key]

            elif key in allowed and allowed[key]:
                # Fallback to first allowed version
                new_field.default_value = allowed[key][0]

            else:
                # No valid default
                new_field.default_value = None

            new_fields.append(new_field)

        return new_fields

    def button_1_button1(self, event):
        """
        Handle confirmation button click.
        Converts selected values to integers.
        """
        self.button_state = self._button1_text
        self.validation()

        if not self.footer.get():
            for key in self.field_dict.keys():
                self.field_dict[key] = int(self.field_dict[key])

            self.quit_widget()