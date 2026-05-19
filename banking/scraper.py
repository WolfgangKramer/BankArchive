#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
"""
Created on 27.06.2021
__updated__ = "2026-05-19"
@author: Wolfgang Kramer

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
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager

import banking.declarations as decl
import banking.declarations_mariadb as declm
import banking.message_handler as msg

from banking.forms import InputPIN
from banking.utils import dec2, http_error_code, get_menu_text
from banking.repository import Repository


def convert_date(date_):
    """
     convert string DD.MM.YYYY to date (YYYY.MM.DD)
    """
    date_fields_ = reversed(tuple(map(int, date_.split('.'))))
    return date(*date_fields_)


def setup_driver(title):

    options = webdriver.EdgeOptions()
    options.add_argument("--start-minimized")
    # suppressing of DevTools warnings
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
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
            msg.MessageBoxInfo(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'WEBDRIVER_INSTALL',
                    'Edge'
                    ),
                info_storage=msg.Informations.BANKDATA_INFORMATIONS
                )
        except Exception as e:
            msg.MessageBoxException(
                title=title,
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'WEBDRIVER',
                    'Edge',
                    f'{type(e).__name__}: {e}'
                    )
                )
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
            msg.MessageBoxException()

    def join(self, name, *args, **kwargs):
        """
            get result with >thread<.join()
        """
        while name.is_alive():
            time.sleep(1)
            self.progress.update_progressbar()
        super().join(*args, **kwargs)
        return self.result


class AlphaVantage(object):
    """
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
    """

    def __init__(self, progress, function_list, parameter_dict):

        self.repo = Repository()
        self.progress = progress
        self.parameter_dict = parameter_dict
        self.function_list = function_list
        if parameter_dict and function_list:
            pass
        else:
            self._refresh()

    def refresh(self):

        refresh_alpha_vantage = ReturnValueThread(
            self.progress, target=self._refresh)
        refresh_alpha_vantage.start()
        error = refresh_alpha_vantage.join(refresh_alpha_vantage)
        if error:
            msg.MessageBoxInfo(
                title=get_menu_text("Refresh Alpha Vantage"), message=error)
            return False
        return True

    def _refresh(self):

        error = None
        self.parameter_dict = {}
        self.function_list = []
        self.driver = setup_driver(get_menu_text("Refresh Alpha Vantage"))
        if self.driver:

            try:
                url = decl.ALPHA_VANTAGE_DOCUMENTATION
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
                self.repo.put_alpha_vantage_functions(self.function_list)
                self.repo.put_alpha_vantage_parameters(self.parameter_dict)
                return error
            except Exception as error:
                print(error)
                msg.MessageBoxException(
                    get_menu_text("Refresh Alpha Vantage"),
                    msg.get_message(
                        msg.MESSAGE_TEXT,
                        'ALPHA_VANTAGE_ERROR'
                        )
                    )
                return error


class BmwBank(object):
    """
    BMW Bank
    savings and daily transactions
    """

    def __init__(self):

        self.repo = Repository()
        self.bank_code = decl.BMW_BANK_CODE
        self.server, self.identifier_delimiter, self.storage_period = decl.SCRAPER_BANKDATA[
            decl.BMW_BANK_CODE]
        self.scraper = True
        self.user_id = None
        shelve_file = self.repo.shelve_get_keys(self.bank_code)
        self.bank_name = shelve_file[decl.KEY_BANK_NAME]
        self.title = self.bank_name
        try:
            self.user_id = shelve_file[decl.KEY_USER_ID]
            if decl.KEY_PIN in shelve_file.keys() and shelve_file[decl.KEY_PIN] not in ['', None]:
                decl.PNS[self.bank_code] = shelve_file[decl.KEY_PIN]
            self.bic = shelve_file[decl.KEY_BIC]
            self.server = shelve_file[decl.KEY_SERVER]
        except KeyError as key_error:
            msg.MessageBoxError(
                title=self.title,
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'LOGIN',
                    self.bank_code,
                    key_error
                    )
                )
            return   # thread checking
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in decl.HTTP_CODE_OK:
            msg.MessageBoxError(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'HTTP',
                    http_code,
                    self.bank_code,
                    self.server
                    )
                )
            return  # thread checking
        self.accounts = shelve_file[decl.KEY_ACCOUNTS]
        # Setting Dialog Variables
        self.iban = None
        self.account_number = None
        self.subaccount_number = None
        self.from_date = date.today()
        self.to_date = date.today()
        self.opened_bank_code = None
        self.warning_message = False
        self.period_message = False
        self.driver = setup_driver(self.bank_name)
        self.wait = WebDriverWait(self.driver, 20)

    def logoff(self):

        self.opened_bank_code = None
        try:
            self.driver.find_element(By.LINK_TEXT, "Abmelden").click()
            self.opened_bank_code = None
            self.driver.quit()
        except Exception:
            try:
                """
                The driver.quit() method is used to close all open browser windows or tabs and terminate the WebDriver session.
                This method is typically used at the end of a test script
                to ensure that all browser instances are closed properly and any associated resources are released.
                """
                self.opened_bank_code = None
                self.driver.quit()
            except Exception:
                pass

    def _exception_handling_logoff(self, no, error):

        if error:
            # Print detailed selenium error information
            msg.MessageBoxInfo(
                message= msg.get_message(
                    msg.MESSAGE_TEXT,
                    'SCRAPER_SELENIUM_EXCEPTION',
                    type(error).__name__,
                    error.msg
                    ),
                information=decl.ERROR,
                info_storage=msg.Informations.BANKDATA_INFORMATIONS
                )
        msg.MessageBoxException(
            message= 
            
            msg.get_message(
                msg.MESSAGE_TEXT,
                'SCRAPER_PAGE_ERROR'
                )
            )
        print(no)
        self.logoff()

    def _wait_ready_state(self, seconds=20):
        """
        wait until page is loaded
        """
        try:
            WebDriverWait(self.driver, seconds).until(
                lambda driver: driver.execute_script(
                    'return document.readyState') == 'complete'
            )
            return True
        except WebDriverException as error:
            self._exception_handling_logoff('01 _wait_ready_state', error)
            return False

    def credentials(self):

        time_out = 180
        if self.opened_bank_code != self.bank_code:
            while True:
                try:
                    if self.bank_code not in decl.PNS.keys():
                        inputpin = InputPIN(
                            self.bank_code, self.bank_name)
                        if inputpin.button_state == decl.WM_DELETE_WINDOW:
                            return None
                        decl.PNS[self.bank_code] = inputpin.pin
                    self.driver.get(self.server)
                    self.driver.fullscreen_window()
                    locator = "contentForm:Benutzerkennung"
                    element = self.wait.until(
                        EC.visibility_of_element_located((By.ID, locator)))
                    element.send_keys(self.user_id)
                    locator = "contentForm:password"
                    element = self.wait.until(
                        EC.visibility_of_element_located((By.ID, locator)))
                    element.send_keys(decl.PNS[self.bank_code])
                    locator = "contentForm:submitLogin"
                    element = self.wait.until(
                        EC.element_to_be_clickable((By.ID, locator)))
                    element.click()
                    try:
                        locator = "BMW Bank - Finanzstatus - Finanzstatus"
                        WebDriverWait(self.driver, time_out).until(
                            EC.title_is(locator))
                        self.opened_bank_code = self.bank_code
                        return True
                    except TimeoutException:
                        msg.MessageBoxInfo(
                            title=self.title,
                            message=msg.get_message(
                                msg.MESSAGE_TEXT,
                                'SCRAPER_TIMEOUT'
                                ),
                            information=decl.WARNING,
                            info_storage=msg.Informations.BANKDATA_INFORMATIONS
                            )
                        return False
                    except WebDriverException as error:
                        self._exception_handling_logoff(
                            '01 credentials', error)
                        return False
                except WebDriverException as error:
                    self._exception_handling_logoff('02 credentials', error)
                    decl.PNS.pop(self.bank_code, None)
                    return False
        else:
            return True

    def get_accounts(self):
        """
        get account data for all accounts (list of tuples):
            account_product_name, account_owner_name, iban, account_number
        """
        if not self.credentials():
            return []
        # find down arrow to view account details
        locator = "//a[contains(@class, 'accordion-container__header collapsed')]"
        self.wait.until(EC.presence_of_element_located((By.XPATH, locator)))
        result = self.driver.find_elements(By.XPATH, locator)
        if result:
            accounts = []
            for item in result:
                item.click()  # open account_details display
                class_text_list = item.text.split("\n")
                account_product_name = class_text_list[0]
                iban = class_text_list[1].replace(' ', '')
                account_number = iban[12:22]
                # find account_owber name in account detasis
                locator = "//div[contains(@class, 'col-sm-7')]"
                result_arrow_down = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, locator)))
                if result_arrow_down:
                    account_owner_name = result_arrow_down.text
                else:
                    account_owner_name = 'NA'
                accounts.append(
                    (account_product_name, account_owner_name, iban, account_number))
                item.click()  # # close account_details display
                self._wait_ready_state()
        return accounts

    def download_statements(self):
        """
        Only dailyTransfers and savingTransfers (list of dicts)
        """
        title = ' '.join([self.bank_name, self.account_product_name])
        result = self.credentials()
        if result is None:  # login aborted
            return None
        elif not result:  # selenium error
            self._exception_handling_logoff('01 download_statements', None)
            return None
        if self.account_product_name == 'BMW Online-Tagesgeld':
            url = self.server + "/pages/konten/daily_transactions.jsf"
        elif self.account_product_name == 'BMW Online-Sparkonto':
            url = self.server + "/pages/konten/savings_transactions.jsf"
        else:
            print("Account Produktname >",
                  self.account_product_name, "< not found")
            return []
        self.driver.get(url)
        if not self._wait_ready_state():
            return []
        try:
            transactions = read_html(
                StringIO(self.driver.page_source))
        except ValueError:
            self._exception_handling_logoff(
                '02 download_statements', None)
            return False
        # get dataframe of transactions
        dataframe = transactions[0]
        dataframe.reset_index()
        dataframe[declm.DB_entry_date] = dataframe['Buchungstag / Valutatag'].apply(
            lambda x: convert_date(x.split()[-1][0:10]))
        dataframe[declm.DB_date] = dataframe['Buchungstag / Valutatag'].apply(
            lambda x: convert_date(x.split()[-1][10:20]))
        dataframe.drop(
            columns='Buchungstag / Valutatag', inplace=True)
        dataframe.rename(columns={
            'Umsatzart': declm.DB_posting_text, 'Verwendungszweck': declm.DB_purpose, 'Betrag': declm.DB_amount}, inplace=True)
        dataframe[declm.DB_posting_text] = dataframe[declm.DB_posting_text].apply(
            lambda x: x.replace('Umsatzart  ', ''))
        dataframe[declm.DB_purpose] = dataframe[declm.DB_purpose].apply(
            lambda x: x.replace('Verwendungszweck  ', ''))
        dataframe[declm.DB_purpose_wo_identifier] = dataframe[declm.DB_purpose]
        dataframe[declm.DB_status] = dataframe[declm.DB_amount].apply(
            lambda x: decl.CREDIT if x.split()[-3] == '+' else decl.DEBIT)
        dataframe[declm.DB_amount] = dataframe[declm.DB_amount].apply(
            lambda x: x.split()[-2])
        dataframe[declm.DB_amount] = dataframe[declm.DB_amount].apply(
            lambda x: dec2.convert(x.replace('.', '').replace(',', '.')))
        dataframe[declm.DB_opening_status] = decl.CREDIT
        dataframe[declm.DB_opening_entry_date] = dataframe[declm.DB_entry_date]
        dataframe[declm.DB_closing_status] = decl.CREDIT
        dataframe[declm.DB_closing_entry_date] = dataframe[declm.DB_entry_date]
        statements = dataframe.to_dict(orient='records')
        # get last stored statement
        result = statement_row = self.repo.get_last_statement_of_iban(self.iban)
        if result:
            mariadb_closing_balance, closing_status, entry_date  = result
            # delete statements already stored in mariadb
            idx = len(statements) - 1
            while idx >= 0 and statements[idx][declm.DB_entry_date] <= entry_date:
                statements.pop(idx)
                idx -= 1
            if not statements:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT,
                        'SCRAPER_NO_TRANSACTION_TO_STORE',
                        self.account_product_name,
                        self.iban
                        ),
                    info_storage=msg.Informations.BANKDATA_INFORMATIONS
                    )
                return []
        # get last closing balance of transactions; Verf�gbarer Betrag
        locator = "//span[contains(@class, 'xl:text-2xl')]"
        element = self.wait.until(
            EC.presence_of_element_located((By.XPATH, locator)))
        amount_available = element.text.split()[-2]
        amount_available = dec2.convert(
            amount_available.replace('.', '').replace(',', '.'))
        # calculate opening and closing balance for each transactions
        idx = len(statements)-1
        closing_balance = amount_available
        while idx >= 0:
            statements[idx][declm.DB_closing_balance] = closing_balance
            amount = dec2.convert(statements[idx][declm.DB_amount])
            if statements[idx][declm.DB_status] == decl.CREDIT:
                statements[idx][declm.DB_opening_balance] = dec2.subtract(
                    closing_balance, amount)
            else:
                statements[idx][declm.DB_opening_balance] = dec2.add(
                    closing_balance, amount)
            closing_balance = statements[idx][declm.DB_opening_balance]
            idx -= 1
        # check if last closing balance of database with opening balance of transactions
        if statements and result and mariadb_closing_balance != statements[0][declm.DB_opening_balance]:
            message = msg.get_message(
                msg.MESSAGE_TEXT,
                'SCRAPER_BALANCE',
                mariadb_closing_balance,
                statements[0][declm.DB_opening_balance]
                )
            msg.MessageBoxInfo(
                title=title, message=message, information=decl.WARNING,
                info_storage=msg.Informations.BANKDATA_INFORMATIONS)
        return statements
