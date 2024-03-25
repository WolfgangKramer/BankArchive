#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 27.06.2021
__updated__ = "2024-03-25"
@author: Wolfg

  Attention! new Scraper Class, see     Module: mariadb.py
                                        Method: import_server(self, filename)()
"""

import os
import time

from datetime import date
from io import StringIO
from threading import Thread
from pandas import read_html
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from banking.declarations import (
    ALPHA_VANTAGE_DOCUMENTATION,
    BANK_MARIADB_INI, BMW_BANK_CODE,
    DEBIT, CREDIT, EURO,
    HTTP_CODE_OK,
    KEY_ALPHA_VANTAGE_FUNCTION, KEY_ALPHA_VANTAGE_PARAMETER,
    KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_SERVER, KEY_BANK_NAME, KEY_ACCOUNTS,
    MESSAGE_TEXT, MENU_TEXT, PNS,
    SCRAPER_BANKDATA, SHELVE_KEYS
)
from banking.formbuilts import MessageBoxInfo, MessageBoxError, MessageBoxTermination, WM_DELETE_WINDOW
from banking.forms import InputPIN
from banking.utils import (
    Calculate, find_pattern, http_error_code, shelve_get_key, exception_error, shelve_put_key
)


dec2 = Calculate(places=2)


def amount_to_decimal(amount):

    amount = amount.replace(u'\xa0' + EURO, '')
    amount = amount.replace('.', '')
    amount = dec2.convert(amount.replace(',', '.'))
    status = CREDIT
    if amount < 0:

        amount = amount * -1
        status = DEBIT
    return amount, status


def convert_date(date_):
    """
     convert string DD.MM.YYYY to date (YYYY.MM.DD)
    """
    date_fields_ = reversed(tuple(map(int, date_.split('.'))))
    return date(*date_fields_)


def setup_driver(title):

    options = webdriver.EdgeOptions()
    options.add_argument("--start-minimized")
    try:
        driver = webdriver.Edge(service=Service(), options=options)
    except Exception:
        try:

            # By default, all driver binaries are saved to user.home/.wdm folder. You can override this setting and save binaries to project.root/.wdm
            # see:
            # https://github.com/SergeyPirogov/webdriver_manager/blob/master/README.md
            os.environ['WDM_LOCAL'] = '1'
            driver = webdriver.Edge(options=options, service=Service(
                EdgeChromiumDriverManager().install()))
            MessageBoxInfo(
                message=MESSAGE_TEXT['WEBDRIVER_INSTALL'].format('Edge'))
        except Exception as e:
            exception_error(
                title=title, message=MESSAGE_TEXT['WEBDRIVER'].format('Edge', f'{type(e).__name__}: {e}'))
            driver = None
    return driver


class ReturnValueThread(Thread):
    def __init__(self, progress, *args, **kwargs):
        self.progress = progress
        super().__init__(*args, **kwargs)
        self.result = None

    def run(self):
        self.result = None
        try:
            self.result = self._target(*self._args, **self._kwargs)
        except Exception:
            exception_error()

    def join(self, name, *args, **kwargs):
        '''
            get result with >thread<.join()
        '''
        while name.is_alive():
            time.sleep(1)
            self.progress.update_progressbar()
        super().join(*args, **kwargs)
        return self.result


class AlphaVantage(object):
    '''
    Creates:
        Dictionary of API Parameters of all Functions of Alpha Vantage Website
        List of all Alpha Vantage Functions
    WEBSITE:
        https://www.alphavantage.co/documentation
    PARAMETER:
        function_list   contains list of all Alpha Vantage Functions
        parameter_dict  contains options type list for each AlphaVantageFunction
            without option datatype (By default, datatype=json)
            Dict Structure:
                Key:          Function
                Value:        List of API Parameters
    '''

    def __init__(self, progress, function_list, parameter_dict):

        self.progress = progress
        self.parameter_dict = parameter_dict
        self.function_list = function_list
        if self.parameter_dict and self.function_list:
            pass
        else:
            self.refresh

    def refresh(self):

        refresh_alpha_vantage = ReturnValueThread(
            self.progress, target=self._refresh)
        refresh_alpha_vantage.start()
        error = refresh_alpha_vantage.join(refresh_alpha_vantage)
        if error:
            MessageBoxInfo(
                title=MENU_TEXT['Refresh Alpha Vantage'], message=error)
            return False
        return True

    def _refresh(self):

        error = None
        self.parameter_dict = {}
        self.function_list = []
        self.driver = setup_driver(MENU_TEXT['Refresh Alpha Vantage'])
        if self.driver:

            try:
                url = ALPHA_VANTAGE_DOCUMENTATION
                self.driver.get(url)

                self.driver.set_window_size(1531, 1160)
                elements = self.driver.find_elements(
                    By.PARTIAL_LINK_TEXT, "www.alphavantage.co/query")

                self.function_list = []
                self.parameter_dict = {}
                for e in elements:

                    split_list = e.text.split('&')
                    function = split_list[0].removeprefix(
                        'https://www.alphavantage.co/query?function=')
                    self.function_list.append(function)
                    del split_list[0]
                    option_list = list(
                        map(lambda x: x.split('=')[0], split_list))
                    try:
                        option_list.remove('datatype')
                    except Exception:
                        pass
                    if function in self.parameter_dict.keys():
                        self.parameter_dict[function] = self.parameter_dict[function] + option_list
                    else:
                        self.parameter_dict[function] = option_list
                for key, value in self.parameter_dict.items():
                    value = value + value
                    self.parameter_dict[key] = list(set(value))
                self.function_list = list(set(self.function_list))
                self.function_list.sort()
                self.driver.quit()
                data = [(KEY_ALPHA_VANTAGE_FUNCTION, self.function_list),
                        (KEY_ALPHA_VANTAGE_PARAMETER,  self.parameter_dict)]
                shelve_put_key(BANK_MARIADB_INI, data)
                return error
            except Exception as error:
                print(error)
                exception_error(title=MENU_TEXT['Refresh Alpha Vantage'],
                                message=MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
                return error


class BmwBank(object):
    """
    BMW Bank
    """

    def __init__(self):

        self.bank_code = BMW_BANK_CODE
        self.server, self.identifier_delimiter, self.storage_period = SCRAPER_BANKDATA[
            BMW_BANK_CODE]
        self.scraper = True
        self.user_id = None
        shelve_file = shelve_get_key(self.bank_code, SHELVE_KEYS)
        try:
            self.user_id = shelve_file[KEY_USER_ID]
            if KEY_PIN in shelve_file.keys() and shelve_file[KEY_PIN] not in ['', None]:
                PNS[self.bank_code] = shelve_file[KEY_PIN]
            self.bic = shelve_file[KEY_BIC]
            self.server = shelve_file[KEY_SERVER]
        except KeyError as key_error:
            MessageBoxError(title=shelve_file[KEY_BANK_NAME],
                            message=MESSAGE_TEXT['LOGIN'].format(self.bank_code, key_error))
            return   # thread checking
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=MESSAGE_TEXT['HTTP'].format(http_code,
                                                                self.bank_code, self.server))
            return  # thread checking
        self.bank_name = shelve_file[KEY_BANK_NAME]
        self.accounts = shelve_file[KEY_ACCOUNTS]
        # Setting Dialog Variables
        self.iban = None
        self.account_number = None
        self.subaccount_number = None
        self.from_date = date.today()
        self.to_date = date.today()
        self.opened_bank_code = None
        self.warning_message = False
        self.period_message = False
        self.driver = setup_driver(shelve_file[KEY_BANK_NAME])

    def _get_url(self, url, bank):

        try:
            url = self.server + url
            if self.driver.current_url != url:
                self.driver.get(url)
            return True
        except Exception:
            page = self.driver.page_source
            self._logoff()
            MessageBoxTermination(info=page, bank=bank)
            return False  # thread checking

    def _logoff(self):

        self.opened_bank_code = None
        try:
            self.driver.find_element(By.LINK_TEXT, "Abmelden").click()
        except Exception:
            pass

    def credentials(self):

        if self.opened_bank_code != self.bank_code:
            while True:
                try:
                    if self.bank_code not in PNS.keys():
                        inputpin = InputPIN(self.bank_code, self.bank_name)
                        if inputpin.button_state == WM_DELETE_WINDOW:
                            return False
                        PNS[self.bank_code] = inputpin.pin
                    self.driver.get(self.server + "Public/content/Login")
                    self.driver.set_window_size(500, 500)
                    self.driver.find_element(
                        By.ID, "id783308527_username").send_keys(self.user_id)
                    self.driver.find_element(
                        By.ID, "id783308527_password").send_keys(PNS[self.bank_code])
                    self.driver.find_element(
                        By.CSS_SELECTOR, ".button-login").click()
                    if self.driver.current_url == self.server + "Welcome/content/Welcome":
                        self.opened_bank_code = self.bank_code
                        return True
                    else:
                        self.driver.close()
                except exceptions.InvalidSessionIdException:
                    MessageBoxInfo(message=MESSAGE_TEXT['BANK_LOGIN'].format(
                        'Invalid Session Id', self.server, PNS[self.bank_code], self.user_id))
                    del PNS[self.bank_code]
                except Exception:
                    exception_error()
                    del PNS[self.bank_code]
                    return False
        else:
            return True

    def get_accounts(self, bank):

        if not self.credentials():
            return []
        if not self._get_url(
                "Overview/content/BankAccounts/Overview?$event=init", bank):
            return []
        dataframe = read_html(StringIO(self.driver.page_source))[0]
        shape = dataframe.shape
        accounts = []
        for i in range(0, shape[0]):
            cell = dataframe.iat[i, 0]
            if isinstance(cell, str):
                cell = cell.replace(u'\xa0', '')
                cell = cell.strip()
            iban_end = find_pattern(cell, 'Kontodetails')
            if iban_end is not None:
                iban_start = find_pattern(cell, 'DE')
                if iban_start is not None:
                    account_product_name = cell[0:iban_start]
                    account_iban = cell[iban_start:iban_end]
                    account_iban = account_iban[0:22]
                    account_number = account_iban[12:22]
                    accounts.append(
                        (account_product_name, account_iban, account_number))
        self._logoff()
        return accounts

    def download_statements(self, bank):

        if not self.credentials():
            return None
        url = "FinanceState/content/FinanceStatePrivate/BankAccounts?$event=accountOverviewChangeTurnOverSearch&preAccNo=" + bank.account_number
        if not self._get_url(url, bank):
            return []
        self.driver.find_element(By.ID, "id-2103151465_slDateRange").click()
        dropdown = self.driver.find_element(By.ID, "id-2103151465_slDateRange")
        dropdown.find_element(
            By.XPATH, "//option[. = 'letzten 360 Tage']").click()
        self.driver.find_element(By.ID, "submitButton").click()
        if self.driver.page_source.find('keine Ums') != -1:
            return None
        dataframe = read_html(StringIO(self.driver.page_source))
        try:
            dataframe = dataframe[5]
            shape = dataframe.shape
            for i in range(0, shape[0] - 1):
                if isinstance(dataframe.iat[i, 4], str):
                    dataframe.iat[i, 4] = dataframe.iat[i, 4].replace(
                        u'\xa0EUR', '')  # Betrag
                    dataframe.iat[i, 4] = dataframe.iat[i, 4].strip()
                    dataframe.iat[i, 5] = dataframe.iat[i,
                                                        # Saldo
                                                        5].replace(u'\xa0EUR', '')
                    dataframe.iat[i, 5] = dataframe.iat[i, 5].strip()
        except IndexError:
            return None
        dataframe.columns = ["entry_date", "date",
                             "posting_text", "purpose", "amount", "closing_balance"]
        dataframe.head(1)
        dataframe_list = list(dataframe.itertuples(index=False))
        statements = []
        for tuple_ in dataframe_list:
            statement = dict(tuple_._asdict())
            statement['entry_date'] = convert_date(statement['entry_date'])
            statement['date'] = convert_date(statement['date'])
            statement['amount'], statement['status'] = amount_to_decimal(
                statement['amount'])
            statement['closing_balance'], statement['closing_status'] = amount_to_decimal(
                statement['closing_balance'])
            statement['closing_entry_date'] = statement['entry_date']
            statement['opening_entry_date'] = statement['entry_date']
            if statement['status'] == CREDIT:
                statement['opening_balance'] = dec2.subtract(
                    statement['closing_balance'], statement['amount'])
            else:
                statement['opening_balance'] = dec2.add(
                    statement['closing_balance'], statement['amount'])
            statement['opening_status'] = CREDIT
            statement['opening_entry_date'] = statement['entry_date']
            if statement['opening_balance'] < 0:
                statement['opening_status'] = DEBIT
            statements.append(statement)
        self._logoff()
        return statements
