"""
Created on 09.12.2019
__updated__ = "2024-03-25"
Author: Wolfang Kramer
"""

import io
import sys
import time
import requests
import webbrowser

from contextlib import redirect_stdout
from datetime import datetime, date, timedelta
from threading import Thread
from tkinter import Tk, Menu, TclError, GROOVE, ttk, PhotoImage, Canvas, StringVar, font
from tkinter.ttk import Label
from fints.types import ValueList
from pandas import DataFrame
from yfinance import Ticker

from banking.bank import InitBank, InitBankSync, InitBankAnonymous
from banking.declarations import (
    APP_SHELVE_KEYS, ALPHA_VANTAGE,
    Balance, BANKIDENTIFIER, BANK_MARIADB_INI,
    BMW_BANK_CODE, BUNDESBANK_BLZ_MERKBLATT, BUNDEBANK_BLZ_DOWNLOAD,
    DB_acquisition_price,  DB_amount_currency,
    DB_opening_balance, DB_opening_currency, DB_opening_status,
    DB_closing_balance, DB_closing_currency, DB_closing_status,
    DB_counter,
    DB_code, DB_ISIN, DB_entry_date,
    DB_name, DB_pieces,
    DB_total_amount, DB_acquisition_amount, DB_price_date,
    DB_price_currency, DB_total_amount_portfolio,
    DB_iban, DB_posted_amount, DB_market_price,
    DB_price, DB_transaction_type, DB_symbol,
    DB_origin, DB_origin_symbol,
    DB_open, DB_low, DB_high, DB_close, DB_adjclose, DB_volume, DB_dividends, DB_splits,
    EURO, ERROR,
    FINTS_SERVER, FINTS_SERVER_ADDRESS,
    FROM_BEGINNING_DATE,
    FN_DATE, FN_PROFIT_LOSS, FN_PROFIT, FN_FROM_DATE, FN_TO_DATE,
    FN_PIECES_CUM, FN_ALL_BANKS, FN_SOLD_PIECES,
    FORMS_TEXT,
    HOLDING, HOLDING_VIEW, HOLDING_T,
    INFORMATION, Informations, ISIN,
    JSON_KEY_ERROR_MESSAGE, JSON_KEY_META_DATA,
    KEY_ACCOUNTS, KEY_ACC_BANK_CODE, KEY_ACC_OWNER_NAME, KEY_ALPHA_VANTAGE_PRICE_PERIOD,
    KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_IBAN,
    KEY_ACC_PRODUCT_NAME, KEY_ALPHA_VANTAGE, KEY_ALPHA_VANTAGE_PARAMETER,  KEY_ALPHA_VANTAGE_FUNCTION,
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_DIRECTORY, KEY_LOGGING,
    KEY_MARIADB_NAME, KEY_MS_ACCESS,
    KEY_MARIADB_PASSWORD, KEY_MARIADB_USER, KEY_PIN, KEY_BIC, KEY_PRODUCT_ID,
    KEY_SECURITY_FUNCTION,
    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_SHOW_MESSAGE, KEY_STORAGE_PERIOD,
    KEY_THREADING,
    KEY_USER_ID, KEY_VERSION_TRANSACTION,
    MENU_TEXT, MESSAGE_TEXT, MESSAGE_TITLE,
    PRICES_ISIN_VIEW, PERCENT, PRICES,
    SCRAPER_BANKDATA,
    SERVER, SEPA_AMOUNT, SEPA_CREDITOR_BIC,
    SEPA_CREDITOR_IBAN, SEPA_CREDITOR_NAME, SEPA_EXECUTION_DATE, SEPA_PURPOSE,
    SEPA_PURPOSE_1, SEPA_PURPOSE_2, SEPA_REFERENCE,
    SHELVE_KEYS,
    STATEMENT,
    TRANSACTION, TRANSACTION_VIEW, TRANSACTION_DELIVERY, TRUE, TRANSACTION_RECEIPT,
    UNKNOWN, WEBSITES, WARNING,
    YAHOO, NOT_ASSIGNED,
    OUTPUTSIZE_FULL, OUTPUTSIZE_COMPACT, ALPHA_VANTAGE_DOCUMENTATION,
    KEY_HOLDING_SWITCH,
)
from banking.formbuilts import (
    BUTTON_OK, BUTTON_SAVE, BUTTON_NEW, BUTTON_APPEND, BUTTON_DELETE, BUTTON_REPLACE, BUTTON_UPDATE,
    MessageBoxInfo, ProgressBar,
    FileDialogue,
    BuiltRadioButtons, BuiltPandasBox,
    destroy_widget,
    WM_DELETE_WINDOW, BUTTON_ALPHA_VANTAGE
)
from banking.forms import (
    Adjustments, AlphaVantageParameter, AppCustomizing,
    BankDataChange, BankDataNew, BankDelete,
    InputISIN,  Isin,
    InputDate, InputDateHoldingPerc,
    InputDateFieldlist, InputDateFieldlistPrices, InputDateFieldlistHolding,
    PandasBoxIsins,
    PandasBoxStatement, PandasBoxHolding, PandasBoxBalancesAllBanks,
    PandasBoxHoldingPercent, PandasBoxTotals, PandasBoxTransactionDetail,
    PandasBoxHoldingPortfolios, PandasBoxBalances,
    PandasBoxAcquisitionTable, PandasBoxTransactionTable, PandasBoxTransactionProfit,
    PandasBoxHoldingTransaction, PandasBoxPrices,
    PrintList, PrintMessageCode,
    SelectFields, SelectCreateHolding_t,
    SepaCreditBox,
    TransactionNew,
    TransactionSync, VersionTransaction, SelectDownloadPrices,
)
from banking.mariadb import MariaDB
from banking.scraper import AlphaVantage, BmwBank
from banking.sepa import SepaCreditTransfer
from banking.tools import import_holding_from_access, update_holding_total_amount_portfolio
from banking.utils import (
    Calculate,
    Datulate, dictaccount, dict_get_first_key,
    exception_error,
    listbank_codes,
    shelve_exist, shelve_put_key, shelve_get_key,
    dictbank_names, delete_shelve_files,
)


PRINT_LENGTH = 140
PAGE_FEED = 50

dec2 = Calculate(places=2)
dec6 = Calculate(places=6)
dec10 = Calculate(places=10)

dat = Datulate()


class FinTS_MariaDB_Banking(object):
    """
    Start of Application
    Execution of Application Customizing
    Execution of MARIADB Retrievals
    Execution of Bank Dialogues
    """

    def __init__(self):

        if shelve_exist(BANK_MARIADB_INI):
            self.shelve_app = shelve_get_key(
                BANK_MARIADB_INI, APP_SHELVE_KEYS)
            # Connecting DB
            try:
                MariaDBuser = self.shelve_app[KEY_MARIADB_USER]
                MariaDBpassword = self.shelve_app[KEY_MARIADB_PASSWORD]
                MariaDBname = self.shelve_app[KEY_MARIADB_NAME]
            except KeyError:
                exception_error(message=MESSAGE_TEXT['DBLOGIN'])
            try:
                self.mariadb = MariaDB(
                    MariaDBuser, MariaDBpassword, MariaDBname, self.shelve_app[KEY_HOLDING_SWITCH])
            except Exception:
                exception_error(message=MESSAGE_TEXT['CONN'].format(
                    MariaDBuser, MariaDBname))
        else:
            MariaDBname = UNKNOWN
            self.shelve_app = {}
        while True:
            self.wpd_iban = []
            self.kaz_iban = []
            self.bank_names = dictbank_names()
            self.window = None
            self.window = Tk()
            self.progress = ProgressBar(self.window)
            self.window.title(MESSAGE_TITLE)
            self.window.geometry('600x400+1+1')
            self.window.resizable(0, 0)
            _canvas = Canvas(self.window)
            _canvas.pack(expand=True, fill='both')
            _canvas_image = PhotoImage(file=("background.gif"))
            _canvas.create_image(0, 0, anchor='nw', image=_canvas_image)
            _canvas.create_text(300, 200, fill="lightblue", font=('Arial', 20, 'bold'),
                                text=MESSAGE_TEXT['DATABASE'].format(MariaDBname))
            self._def_styles()
            self._create_menu(MariaDBname)
            self._footer = StringVar()
            self.message_widget = Label(self.window,
                                        textvariable=self._footer, foreground='RED', justify='center')
            self._footer.set('')
            if shelve_exist(BANK_MARIADB_INI):
                if self.shelve_app[KEY_HOLDING_SWITCH] == HOLDING_T:
                    self._footer.set(MESSAGE_TEXT['HOLDING_USE_TRANSACTION'])
            self.message_widget.pack()
            self.window.protocol(WM_DELETE_WINDOW, self._wm_deletion_window)
            if shelve_exist(BANK_MARIADB_INI):
                self.alpha_vantage = AlphaVantage(self.progress, self.shelve_app[KEY_ALPHA_VANTAGE_FUNCTION],
                                                  self.shelve_app[KEY_ALPHA_VANTAGE_PARAMETER])
            self.window.mainloop()
        try:
            self.window.destroy()
        except TclError:
            pass

    def _wm_deletion_window(self):

        try:
            self.window.destroy()
        except TclError:
            pass
        try:
            self.mariadb.destroy_connection()
        except AttributeError:
            pass
        sys.exit()

    def _bank_name(self, bank_code):

        bank_name = bank_code
        if bank_code in self.bank_names:
            bank_name = self.bank_names[bank_code]
        return bank_name

    def _show_message(self, bank, message=None):
        """
        show messages of FINTS dialogue
        """
        if Informations.bankdata_informations:
            PrintMessageCode(text=Informations.bankdata_informations)
            Informations.bankdata_informations = ''
        if bank.warning_message:
            self._footer.set(MESSAGE_TEXT['TASK_WARNING'])
        else:
            bank_name = self._bank_name(bank.bank_code)
            if message:
                self._footer.set(
                    ' '.join([message, '\n', MESSAGE_TEXT['TASK_DONE']]))
            else:
                self._footer.set(
                    ' '.join([bank_name, '\n', MESSAGE_TEXT['TASK_DONE']]))

        bank.warning_message = False

    def _show_informations(self):
        """
        show informations of threads, if exist
        """
        # downloaad prices
        title = ' '.join([MENU_TEXT['Download'], MENU_TEXT['Prices']])
        PrintMessageCode(title=title, header=Informations.PRICES_INFORMATIONS,
                         text=Informations.prices_informations)
        # download bankdata
        title = ' '.join([MENU_TEXT['Download'], MENU_TEXT['All_Banks']])
        PrintMessageCode(title=title, header=Informations.BANKDATA_INFORMATIONS,
                         text=Informations.bankdata_informations)
        # create holding_t
        title = ' '.join([MENU_TEXT['Database'], MENU_TEXT['Holding_T']])
        PrintMessageCode(title=title, header=Informations.HOLDING_T_INFORMATIONS,
                         text=Informations.holding_t_informations)

    def _delete_footer(self):

        try:
            self._footer.set('')
        except Exception:
            pass
        self._show_informations()

    def _acquisition_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Acquisition Amount Table']])
        acquisition_table = AcquisitionTable(
            title=title, mariadb=self.mariadb, table=HOLDING_VIEW, bank_name=bank_name, iban=iban)
        self._footer.set(acquisition_table.footer)

    def _all_banks(self):

        self._delete_footer()
        CANCELED = ''
        if self.shelve_app[KEY_THREADING] == TRUE:
            banks_credentials = listbank_codes()
            banks_download = []
            for bank_code in banks_credentials:
                # PIN input outside of Thread
                bank = self._bank_init(bank_code)
                if bank.scraper:
                    self._footer.set(MESSAGE_TEXT['CREDENTIALS_CHECK'].format(
                        self.bank_names[bank_code]))
                    if bank.credentials():
                        banks_download.append(bank_code)
                    else:
                        MessageBoxInfo(MESSAGE_TEXT['CREDENTIALS'].format(
                            self.bank_names[bank_code]))
                else:
                    self._footer.set(MESSAGE_TEXT['CREDENTIALS_CHECK'].format(
                        self.bank_names[bank_code]))
                    if bank.dialogs._start_dialog(bank):
                        banks_download.append(bank_code)
                    else:
                        MessageBoxInfo(MESSAGE_TEXT['CREDENTIALS'].format(
                            self.bank_names[bank_code]))
            bank.opened_bank_code = None  # triggers bank opening messages
            threads = []
            for bank_code in banks_download:
                bank = self._bank_init(bank_code)
                self._footer.set(
                    MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(FN_ALL_BANKS))
                download_thread = Download(self.mariadb, bank)
                threads.append(download_thread)
                download_thread.start()
            self.progress.start()
            for thread in threads:
                while thread.is_alive():
                    time.sleep(1)
                    self.progress.update_progressbar()
        else:
            for bank_code in listbank_codes():
                self._all_accounts(bank_code)
        self.progress.stop()
        self._footer.set(
            MESSAGE_TEXT['DOWNLOAD_DONE'].format(CANCELED, 10 * '!'))
        self._show_informations()

    def _all_accounts(self, bank_code):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        if bank:
            self._footer.set(
                MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(bank.bank_name))
            self.progress.start()
            self.mariadb.all_accounts(bank)
            self.progress.stop()
            self._footer.set(
                MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name, 10 * '!'))
            self._show_message(bank)

    def _all_holdings(self, bank_code):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        if bank:
            self._footer.set(
                MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(bank.bank_name))
            self.mariadb.all_holdings(bank)
            self._footer.set(
                MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name, 10 * '!'))
            self._show_message(bank)

    def _appcustomizing(self):

        self._delete_footer()
        while True:
            app_data_box = AppCustomizing(shelve_app=self.shelve_app)
            if app_data_box.button_state == WM_DELETE_WINDOW:
                return
            data = [(KEY_PRODUCT_ID,  app_data_box.field_dict[KEY_PRODUCT_ID]),
                    (KEY_ALPHA_VANTAGE,
                     app_data_box.field_dict[KEY_ALPHA_VANTAGE]),
                    (KEY_DIRECTORY,  app_data_box.field_dict[KEY_DIRECTORY]),
                    (KEY_MARIADB_NAME,
                     app_data_box.field_dict[KEY_MARIADB_NAME].upper()),
                    (KEY_MARIADB_USER,
                     app_data_box.field_dict[KEY_MARIADB_USER]),
                    (KEY_MARIADB_PASSWORD,
                     app_data_box.field_dict[KEY_MARIADB_PASSWORD]),
                    (KEY_SHOW_MESSAGE,
                     app_data_box.field_dict[KEY_SHOW_MESSAGE]),
                    (KEY_LOGGING,  app_data_box.field_dict[KEY_LOGGING]),
                    (KEY_THREADING,  app_data_box.field_dict[KEY_THREADING]),
                    (KEY_MS_ACCESS,  app_data_box.field_dict[KEY_MS_ACCESS]),
                    (KEY_ALPHA_VANTAGE_PRICE_PERIOD,
                     app_data_box.field_dict[KEY_ALPHA_VANTAGE_PRICE_PERIOD]),
                    (KEY_HOLDING_SWITCH,
                     app_data_box.field_dict[KEY_HOLDING_SWITCH])
                    ]
            shelve_put_key(BANK_MARIADB_INI, data, flag='c')
            if app_data_box.button_state == BUTTON_SAVE:
                MessageBoxInfo(message=MESSAGE_TEXT['DATABASE_REFRESH'])
                self._wm_deletion_window()
            self.shelve_app = shelve_get_key(BANK_MARIADB_INI, APP_SHELVE_KEYS)

    def _create_menu(self, MariaDBname):

        menu_font = font.Font(family='Arial', size=11)
        menu = Menu(self.window)
        self.window.config(menu=menu, borderwidth=10, relief=GROOVE)
        if self.bank_names != {} and MariaDBname != UNKNOWN:
            """
             SHOW Menu
            """
            show_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
            menu.add_cascade(label=MENU_TEXT['Show'], menu=show_menu)
            site_menu = Menu(show_menu, tearoff=0,
                             font=menu_font, bg='Lightblue')
            show_menu.add_cascade(
                label=MENU_TEXT["WebSites"], menu=site_menu, underline=0)
            for website in WEBSITES.keys():
                site_menu.add_command(label=website,
                                      command=lambda x=WEBSITES[website]: self._websites(x))

            if self.shelve_app[KEY_ALPHA_VANTAGE]:
                show_menu.add_command(
                    label=MENU_TEXT['Alpha Vantage'], command=self._show_alpha_vantage)
            if self.shelve_app[KEY_ALPHA_VANTAGE]:
                show_menu.add_command(
                    label=MENU_TEXT['Alpha Vantage Symbol Search'], command=self._show_alpha_vantage_search_symbol)
            show_menu.add_command(
                label=MENU_TEXT['Balances'], command=self._show_balances_all_banks)
            for bank_name in self.bank_names.values():
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                account_menu = Menu(show_menu, tearoff=0,
                                    font=menu_font, bg='Lightblue')
                account_menu.add_command(label=MENU_TEXT['Balances'],
                                         command=lambda x=bank_code, y=bank_name: self._show_balances(x, y))
                if accounts:
                    for acc in accounts:
                        if 'HKKAZ' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            self.kaz_iban.append(acc[KEY_ACC_IBAN])
                            label = acc[KEY_ACC_PRODUCT_NAME]
                            if not label:
                                label = acc[KEY_ACC_ACCOUNT_NUMBER]
                            label = ' '.join([MENU_TEXT['Statement'], label])
                            account_menu.add_command(
                                label=label,
                                command=lambda x=bank_code, y=acc: self._show_statements(x, y))
                        if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            label = acc[KEY_ACC_PRODUCT_NAME]
                            if not label:
                                label = acc[KEY_ACC_ACCOUNT_NUMBER]
                            label = ' '.join(
                                [MENU_TEXT['Holding'], label])
                            account_menu.add_command(
                                label=label,
                                command=lambda x=bank_code, y=acc: self._show_holdings(x, y))
                            label = label + '%'
                            account_menu.add_command(
                                label=label,
                                command=lambda x=bank_code, y=acc: self._show_holdings_perc(x, y))
                        if 'HKWDU' in acc[KEY_ACC_ALLOWED_TRANSACTIONS] or \
                                'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            label = acc[KEY_ACC_PRODUCT_NAME]
                            if not label:
                                label = acc[KEY_ACC_ACCOUNT_NUMBER]
                            label = ' '.join(
                                [MENU_TEXT['Holding'], label, TRANSACTION.upper()])
                            account_menu.add_command(
                                label=label,
                                command=(lambda x=bank_code, y=acc: self._show_transactions(x, y)))
                show_menu.add_cascade(
                    label=bank_name, menu=account_menu, underline=0)
            """
            DOWNLOAD Menu
            """
            download_menu = Menu(
                menu, tearoff=0, font=menu_font, bg='Lightblue')
            menu.add_cascade(label=MENU_TEXT['Download'], menu=download_menu)
            download_menu.add_command(
                label=MENU_TEXT['All_Banks'], command=self._all_banks)
            download_menu.add_separator()
            download_menu.add_command(
                label=MENU_TEXT['Prices'], command=self._import_prices)
            download_menu.add_separator()
            for bank_name in self.bank_names.values():
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                download_menu.add_cascade(
                    label=bank_name,
                    command=lambda x=bank_code: self._all_accounts(x))
                accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                if accounts:
                    for acc in accounts:
                        if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            download_menu.add_cascade(
                                label=' '.join(
                                    [bank_name, MENU_TEXT['Holding']]),
                                command=lambda x=bank_code: self._all_holdings(x))
                download_menu.add_separator()
            '''
            TRANSFER Menu
            '''
            transfer_menu = Menu(
                menu, tearoff=0, font=menu_font, bg='Lightblue')
            menu.add_cascade(label=MENU_TEXT['Transfer'], menu=transfer_menu)
            bank_names = {}
            for bank_name in self.bank_names.values():
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                if accounts:
                    for acc in accounts:
                        if 'HKCCS' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            bank_names[bank_code] = bank_name
            for bank_name in bank_names.values():
                bank_code = dict_get_first_key(bank_names, bank_name)
                accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                account_menu = Menu(transfer_menu, tearoff=0,
                                    font=menu_font, bg='Lightblue')
                if accounts:
                    for acc in accounts:
                        if 'HKCCS' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            label = acc[KEY_ACC_PRODUCT_NAME]
                            if not label:
                                label = acc[KEY_ACC_ACCOUNT_NUMBER]
                            label = ' '.join([MENU_TEXT['Statement'], label])
                            account_menu.add_command(
                                label=label,
                                command=(lambda x=bank_code,
                                         y=acc: self._sepa_credit_transfer(x, y)))
                transfer_menu.add_cascade(
                    label=bank_name, menu=account_menu, underline=0)
        if MariaDBname != UNKNOWN:
            """
            DATABASE Menu
            """
            database_menu = Menu(
                menu, tearoff=0, font=menu_font, bg='Lightblue')
            menu.add_cascade(label=MENU_TEXT['Database'], menu=database_menu)
            bank_names = {}
            for bank_name in self.bank_names.values():
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                if accounts:
                    for acc in accounts:
                        if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                            bank_names[bank_code] = bank_name
            if bank_names != {}:
                all_banks_menu = Menu(
                    database_menu, tearoff=0, font=menu_font, bg='Lightblue')
                database_menu.add_cascade(
                    label=MENU_TEXT['All_Banks'], menu=all_banks_menu, underline=0)
                all_banks_menu.add_command(
                    label=MENU_TEXT['Holding Performance'],
                    command=(lambda x=FN_ALL_BANKS, y='':
                             self._data_holding_performance(x, y)))
                all_banks_menu.add_command(
                    label=MENU_TEXT['Holding ISIN Comparision'],
                    command=(lambda x=FN_ALL_BANKS, y='', z=EURO: self._data_holding_isin_comparision(x, y, z)))
                all_banks_menu.add_command(
                    label=MENU_TEXT['Holding ISIN Comparision'] + '%',
                    command=(lambda x=FN_ALL_BANKS, y='', z=PERCENT: self._data_holding_isin_comparision(x, y, z)))
                all_banks_menu.add_command(label=MENU_TEXT['Balances'],
                                           command=self._data_balances)

                all_banks_menu.add_command(
                    label=MENU_TEXT['Transaction Detail'],
                    command=(lambda x=FN_ALL_BANKS,
                             y=None: self._data_transaction_detail(x, y)))

                for bank_name in bank_names.values():
                    bank_code = dict_get_first_key(bank_names, bank_name)
                    accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                    account_menu = Menu(
                        database_menu, tearoff=0, font=menu_font, bg='Lightblue')
                    if accounts:
                        for acc in accounts:
                            if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                                account_menu.add_command(
                                    label=MENU_TEXT['Holding Performance'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._data_holding_performance(x, y)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Holding ISIN Comparision'],
                                    command=(lambda x=bank_name, y=acc[KEY_ACC_IBAN],
                                             z=EURO: self._data_holding_isin_comparision(x, y, z)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Holding ISIN Comparision'] + '%',
                                    command=(lambda x=bank_name, y=acc[KEY_ACC_IBAN],
                                             z=PERCENT: self._data_holding_isin_comparision(x, y, z)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Transaction Detail'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._data_transaction_detail(x, y)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Profit of closed Transactions'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._transactions_profit(x, y)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Profit Transactions incl. current Depot Positions'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._transactions_profit_all(x, y)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Prices ISINs'],
                                    command=(lambda x=None: self._data_prices(x)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Prices ISINs'] + '%',
                                    command=(lambda x=PERCENT: self._data_prices(x)))

                                account_menu.add_separator()
                                account_menu.add_command(
                                    label=MENU_TEXT['Acquisition Amount Table'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._acquisition_table(x, y)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Transactions Table'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._transactions_table(x, y)))
                                account_menu.add_command(
                                    label=MENU_TEXT['Holding_T'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._data_holding_t(x, y)))
                                account_menu.add_separator()
                                extra_menu = Menu(account_menu, tearoff=0, font=menu_font,
                                                  bg='Lightblue')
                                account_menu.add_cascade(label=MENU_TEXT['Extras'],
                                                         menu=extra_menu, underline=0)
                                extra_menu.add_command(
                                    label=MENU_TEXT['Import MS_Access Data'],
                                    command=(lambda x=self.mariadb,
                                             y=acc[KEY_ACC_IBAN]: import_holding_from_access(x, y)))
                                extra_menu.add_command(
                                    label=MENU_TEXT['Update Portfolio Total Amount'],
                                    command=(lambda x=self.mariadb,
                                             y=acc[KEY_ACC_IBAN]:
                                             update_holding_total_amount_portfolio(x, y)))
                                transaction_menu = Menu(account_menu, tearoff=0, font=menu_font,
                                                        bg='Lightblue')
                                extra_menu.add_cascade(label=MENU_TEXT['Transactions'],
                                                       menu=transaction_menu, underline=0)
                                transaction_menu.add_command(
                                    label=MENU_TEXT['Import Transactions'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._import_transaction(x, y)))
                                transaction_menu.add_command(
                                    label=MENU_TEXT['Check Transactions Pieces'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._transactions_pieces(x, y)))
                                transaction_menu.add_command(
                                    label=MENU_TEXT['Synchronize Transactions'],
                                    command=(lambda x=bank_name,
                                             y=acc[KEY_ACC_IBAN]: self._transactions_sync(x, y)))
                    database_menu.add_cascade(
                        label=bank_name, menu=account_menu, underline=0)
                database_menu.add_separator()
            database_menu.add_command(
                label=MENU_TEXT['ISIN Table'], command=self._isin_table)
            database_menu.add_command(
                label=MENU_TEXT['Prices ISINs'],
                command=(lambda x=None: self._data_prices(x)))
            database_menu.add_command(
                label=MENU_TEXT['Prices ISINs'] + '%',
                command=(lambda x=PERCENT: self._data_prices(x)))
            database_menu.add_command(
                label=MENU_TEXT['Historical Prices'],  command=self._import_prices_histclose)

        """
        CUSTOMIZE Menu
        """
        customize_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Customize'], menu=customize_menu)
        customize_menu.add_command(label=MENU_TEXT['Application INI File'],
                                   command=self._appcustomizing)
        if self.shelve_app:
            customize_menu.add_separator()
            customize_menu.add_command(label=MENU_TEXT['Import Bankidentifier CSV-File'],
                                       command=self._import_bankidentifier)
            customize_menu.add_command(label=MENU_TEXT['Import Server CSV-File'],
                                       command=self._import_server)
            customize_menu.add_separator()
            if self.shelve_app[KEY_ALPHA_VANTAGE]:
                customize_menu.add_command(label=MENU_TEXT['Refresh Alpha Vantage'],
                                           command=self._alpha_vantage_refresh)
                customize_menu.add_separator()
            if MariaDBname != UNKNOWN:
                if self.mariadb.select_server:
                    customize_menu.add_command(label=MENU_TEXT['New Bank'],
                                               command=self._bank_data_new)
                    customize_menu.add_command(label=MENU_TEXT['Delete Bank'],
                                               command=self._bank_data_delete)
                else:
                    MessageBoxInfo(message=MESSAGE_TEXT['PRODUCT_ID'])
            if self.bank_names:
                customize_menu.add_separator()
                for bank_name in self.bank_names.values():
                    bank_code = dict_get_first_key(self.bank_names, bank_name)
                    cust_bank_menu = Menu(customize_menu, tearoff=0,
                                          font=menu_font, bg='Lightblue')
                    cust_bank_menu.add_command(label=MENU_TEXT['Change Login Data'],
                                               command=lambda x=bank_code: self._bank_data_change(x))
                    if bank_code not in list(SCRAPER_BANKDATA.keys()):
                        cust_bank_menu.add_command(label=MENU_TEXT['Synchronize'],
                                                   command=lambda x=bank_code: self._bank_sync(x))
                        cust_bank_menu.add_command(label=MENU_TEXT['Change Security Function'],
                                                   command=lambda
                                                   x=bank_code: self._bank_security_function(x, False))
                        cust_bank_menu.add_command(label=MENU_TEXT['Refresh BankParameterData'],
                                                   command=lambda
                                                   x=bank_code: self._bank_refresh_bpd(x))
                        cust_bank_menu.add_command(label=MENU_TEXT['Change FinTS Transaction Version'],
                                                   command=lambda
                                                   x=bank_code: self._bank_version_transaction(x))
                    cust_bank_menu.add_command(label=MENU_TEXT['Show Data'],
                                               command=lambda x=bank_code: self._bank_show_shelve(x))
                    customize_menu.add_cascade(
                        label=bank_name, menu=cust_bank_menu, underline=0)

    def _def_styles(self):

        style = ttk.Style()
        style.theme_use(style.theme_names()[0])
        style.configure('TLabel', font=('Arial', 8, 'bold'))
        style.configure('OPT.TLabel', font=(
            'Arial', 8, 'bold'), foreground='Grey')
        style.configure('HDR.TLabel', font=('Courier', 8), foreground='Grey')
        style.configure('TButton', font=('Arial', 8, 'bold'), relief=GROOVE,
                        highlightcolor='blue', highlightthickness=5, shiftrelief=3)
        style.configure('TText', font=('Courier', 8))

    def _alpha_vantage_refresh(self):

        self._footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_REFRESH_RUN'])
        self.progress.start()
        refresh = self.alpha_vantage.refresh()
        if refresh:
            self._footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_REFRESH'])
        else:
            self._footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
        self.progress.stop()

    def _bank_data_change(self, bank_code):

        self._delete_footer()
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change Login Data']])
        try:
            login_data = shelve_get_key(bank_code, [KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC,
                                                    KEY_SERVER, KEY_IDENTIFIER_DELIMITER])
        except KeyError as key_error:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
            delete_shelve_files(bank_code)
            MessageBoxInfo(title=title,
                           message=MESSAGE_TEXT['BANK_DELETED'].format(bank_code))
            return
        bank_data_box = BankDataChange(
            title, self.mariadb, bank_code, login_data)
        if bank_data_box.button_state == WM_DELETE_WINDOW:
            return
        try:
            data = [(KEY_BANK_CODE, bank_code),
                    (KEY_BANK_NAME, bank_data_box.field_dict[KEY_BANK_NAME]),
                    (KEY_USER_ID,  bank_data_box.field_dict[KEY_USER_ID]),
                    (KEY_PIN,  bank_data_box.field_dict[KEY_PIN]),
                    (KEY_BIC,  bank_data_box.field_dict[KEY_BIC]),
                    (KEY_SERVER,  bank_data_box.field_dict[KEY_SERVER]),
                    (KEY_IDENTIFIER_DELIMITER,
                     bank_data_box.field_dict[KEY_IDENTIFIER_DELIMITER])
                    ]
            shelve_put_key(bank_code, data)
        except KeyError as key_error:
            exception_error(
                message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
            return
        self._delete_footer()
        if bank_code in list(SCRAPER_BANKDATA.keys()):
            self._bank_data_scraper(bank_code)
        else:
            self._bank_security_function(bank_code, False)

    def _bank_data_new(self):

        self._delete_footer()
        bankidentifier = self.mariadb.select_table(
            BANKIDENTIFIER, [DB_code], order=DB_code)
        bank_codes = self.mariadb.select_server_code()
        title = ' '.join([MENU_TEXT['Customize'], MENU_TEXT['New Bank']])
        if not bankidentifier:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(BANKIDENTIFIER.upper()))
        elif not bank_codes:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(SERVER.upper()))
        else:
            bank_data_box = BankDataNew(
                title, self.mariadb, bank_codes=bank_codes)
            if bank_data_box.button_state == WM_DELETE_WINDOW:
                return
            bank_code = bank_data_box.field_dict[KEY_BANK_CODE]
            try:
                data = [(KEY_BANK_CODE, bank_data_box.field_dict[KEY_BANK_CODE]),
                        (KEY_BANK_NAME,
                         bank_data_box.field_dict[KEY_BANK_NAME]),
                        (KEY_USER_ID,  bank_data_box.field_dict[KEY_USER_ID]),
                        (KEY_PIN,  bank_data_box.field_dict[KEY_PIN]),
                        (KEY_BIC,  bank_data_box.field_dict[KEY_BIC]),
                        (KEY_SERVER,  bank_data_box.field_dict[KEY_SERVER]),
                        (KEY_IDENTIFIER_DELIMITER,
                         bank_data_box.field_dict[KEY_IDENTIFIER_DELIMITER])
                        ]
                shelve_put_key(bank_code, data, flag='c')
            except KeyError as key_error:
                exception_error()
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
                return
            self._delete_footer()
            bank_name = shelve_get_key(bank_code, KEY_BANK_NAME)
            if bank_code in list(SCRAPER_BANKDATA.keys()):
                if bank_code == BMW_BANK_CODE:
                    self._bank_data_scraper(BMW_BANK_CODE)
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DATA_NEW_SCRAPER'].format(
                    bank_name, bank_code))
            else:
                self._bank_security_function(bank_code, True)
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DATA_NEW'].format(
                    bank_name, bank_code))
            try:
                self.window.destroy()
            except Exception:
                pass

    def _bank_data_delete(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Customize'], MENU_TEXT['Delete Bank']])
        deletebank = BankDelete(title)
        if deletebank.button_state == WM_DELETE_WINDOW:
            return
        bank_code = deletebank.field_dict[KEY_BANK_CODE]
        bank_name = deletebank.field_dict[KEY_BANK_NAME]
        delete_shelve_files(bank_code)
        MessageBoxInfo(
            title=title,
            message=MESSAGE_TEXT['BANK_DELETED'].format(bank_name, bank_code))
        self.window.destroy()

    def _bank_data_scraper(self, bank_code):

        bank = self._bank_init(bank_code)
        get_accounts = bank.get_accounts(bank)
        accounts = []
        for account in get_accounts:
            acc = {}
            account_product_name, iban, account_number = account
            acc[KEY_ACC_IBAN] = iban
            acc[KEY_ACC_ACCOUNT_NUMBER] = account_number
            acc[KEY_ACC_SUBACCOUNT_NUMBER] = None
            acc[KEY_ACC_BANK_CODE] = bank_code
            acc[KEY_ACC_OWNER_NAME] = None
            acc[KEY_ACC_PRODUCT_NAME] = account_product_name
            acc[KEY_ACC_ALLOWED_TRANSACTIONS] = ['HKKAZ']
            accounts.append(acc)
        data = [(KEY_ACCOUNTS, accounts),
                (KEY_STORAGE_PERIOD, bank.storage_period)]
        shelve_put_key(bank_code, data, flag='w')

    def _bank_init(self, bank_code):

        if bank_code in list(SCRAPER_BANKDATA.keys()):
            if bank_code == BMW_BANK_CODE:
                bank = BmwBank()
        else:
            bank = InitBank(bank_code, self.mariadb)
        return bank

    def _bank_refresh_bpd(self, bank_code):

        self._delete_footer()
        bank = InitBankAnonymous(bank_code, self.mariadb)
        bank.dialogs.anonymous(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join([bank_name, MENU_TEXT['Customize'],
                            MENU_TEXT['Refresh BankParameterData']])
        self._show_message(bank, message=message)

    def _bank_show_shelve(self, bank_code):

        self._delete_footer()
        shelve_data = shelve_get_key(bank_code, SHELVE_KEYS)
        shelve_text = MESSAGE_TEXT['SHELVE'].format(bank_code)
        for key in SHELVE_KEYS:
            if shelve_data[key]:
                if key == KEY_ACCOUNTS:
                    shelve_text = shelve_text + '{:20}  \n'.format(key)
                    for account in shelve_data[key]:
                        shelve_text = shelve_text + \
                            '{:5} {:80} \n'.format(' ', 80 * '_')
                        for item in account.keys():
                            if isinstance(account[item], list):
                                description = item
                                for value_ in account[item]:
                                    shelve_text = shelve_text + '{:5} {:20} {} \n'.format(
                                        ' ', description, value_)
                                    description = len(description) * ' '
                            else:
                                shelve_text = shelve_text + '{:5} {:20} {}\n'.format(
                                    ' ', item, account[item])
                else:
                    if isinstance(shelve_data[key], list) or isinstance(shelve_data[key],
                                                                        ValueList):
                        description = key
                        for item in shelve_data[key]:
                            shelve_text = shelve_text + \
                                '{:20} {} \n'.format(description, item)
                            description = len(description) * ' '
                    elif isinstance(shelve_data[key], dict):
                        description = key
                        for _key in list(shelve_data[key].keys()):
                            shelve_text = shelve_text + \
                                '{:20} {} \n'.format(description, _key)
                            description = len(description) * ' '
                            shelve_text = (shelve_text + '{:20} {} \n'.format(
                                description, shelve_data[key][_key]))
                    else:
                        shelve_text = shelve_text + \
                            '{:20} {} \n'.format(key, shelve_data[key])
            else:
                shelve_text = shelve_text + '{:20} {} \n'.format(key, 'None')
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Show Data']])
        PrintList(title=title, text=shelve_text)

    def _bank_sync(self, bank_code):

        self._delete_footer()
        bank = InitBankSync(bank_code, self.mariadb)
        bank.dialogs.sync(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join(
            [bank_name, MENU_TEXT['Customize'], MENU_TEXT['Synchronize']])
        self._show_message(bank, message=message)

    def _bank_version_transaction(self, bank_code):

        self._delete_footer()
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change FinTS Transaction Version']])
        transaction_versions = shelve_get_key(
            bank_code, KEY_VERSION_TRANSACTION)
        try:
            transaction_version_box = VersionTransaction(
                title, bank_code, transaction_versions)
            if transaction_version_box.button_state == WM_DELETE_WINDOW:
                return
            for key in transaction_version_box.field_dict.keys():
                transaction_versions[key[2:5]
                                     ] = transaction_version_box.field_dict[key]
            data = (KEY_VERSION_TRANSACTION, transaction_versions)
            shelve_put_key(bank_code, data)
        except KeyError as key_error:
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['LOGIN'].format(
                bank_name, key_error))

    def _date_init(self, iban, timedelta_days=1):

        to_date = date.today()
        while int(to_date.strftime('%w')) in [6, 0]:
            to_date = to_date - timedelta(days=1)
        if iban == '':
            from_date = self.mariadb.select_max_price_date(
                HOLDING, period=(date(2000, 1, 1), to_date - timedelta(days=timedelta_days)))
        else:
            from_date = self.mariadb.select_max_price_date(
                HOLDING, iban=iban, period=(date(2000, 1, 1), to_date - timedelta(days=timedelta_days)))
        if not from_date:
            return None, None
        while int(from_date.strftime('%w')) in [6, 0]:
            from_date = from_date - timedelta(days=1)
        if to_date < from_date:
            to_date = from_date
        return from_date, to_date

    def _data_holding_performance(self, bank_name, iban):

        self._delete_footer()
        _data_holding_performance = None
        period = (date.today() - timedelta(days=360), date.today())
        title = ' '.join([bank_name, MENU_TEXT['Holding Performance']])
        while True:
            from_date, to_date = period
            input_date = InputDate(title=title,
                                   from_date=from_date, to_date=to_date)
            if isinstance(_data_holding_performance, BuiltPandasBox):
                destroy_widget(_data_holding_performance.dataframe_window)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            if bank_name == FN_ALL_BANKS:
                select_holding_total = self.mariadb.select_holding_all_total(
                    period=(from_date, to_date))
            else:
                select_holding_total = self.mariadb.select_holding_total(
                    iban=iban, period=(from_date, to_date))
            if select_holding_total:
                title = ' '.join([title, ' ',
                                  MESSAGE_TEXT['Period'].format(from_date, to_date)])
                _data_holding_performance = PandasBoxHoldingPortfolios(
                    title=title, dataframe=select_holding_total)
            else:
                self._footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_holding_isin_comparision(self, bank_name, iban, mode):

        self._delete_footer()
        percent = ''
        if mode == PERCENT:
            percent = '%'
        from_date, to_date = self._date_init(iban, timedelta_days=90)
        title = ' '.join(
            [bank_name, MENU_TEXT['Holding ISIN Comparision'], percent])
        if iban:
            select_holding_all_isin = self.mariadb.select_dict(
                HOLDING_VIEW, DB_name, DB_ISIN, iban=iban)
        else:
            select_holding_all_isin = self.mariadb.select_dict(
                HOLDING_VIEW, DB_name, DB_ISIN, period=(from_date, to_date))
        if not select_holding_all_isin:
            MessageBoxInfo(title=title, message=(
                MESSAGE_TEXT['DATA_NO'].format('', '')))
            return
        default_texts = []

        while True:
            date_field_list = InputDateFieldlist(
                title=title,
                from_date=from_date, standard=title,
                default_texts=default_texts,
                field_list=list(select_holding_all_isin.keys()))
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            default_texts = date_field_list.field_list
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            title1 = ' '.join([
                title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
            while True:
                selected_fields = BuiltRadioButtons(
                    title=title1,
                    button1_text=BUTTON_OK, button2_text=None,
                    button3_text=None, button4_text=None, button5_text=None,
                    default_value=None,
                    radiobutton_dict={DB_pieces: ' ',
                                      DB_market_price: ' ',
                                      DB_total_amount: ' ',
                                      DB_acquisition_amount: ' ',
                                      FN_PROFIT_LOSS: ' '}
                )
                if selected_fields.button_state == WM_DELETE_WINDOW:
                    break
                else:
                    db_field = selected_fields.field
                if db_field == FN_PROFIT_LOSS:
                    db_fields = [DB_name, DB_price_date,
                                 DB_total_amount, DB_acquisition_amount]
                else:
                    db_fields = [DB_name, DB_price_date, db_field]
                if iban:
                    select_holding_data = self.mariadb.select_holding_data(
                        field_list=db_fields, iban=iban, name=date_field_list.field_list,
                        period=(from_date, to_date))
                else:
                    select_holding_data = self.mariadb.select_holding_data(
                        field_list=db_fields, name=date_field_list.field_list, period=(from_date, to_date))
                if select_holding_data:
                    self._footer.set('')
                    title2 = ' '.join([title1, db_field.upper()])
                    PandasBoxIsins(title=title2,
                                   dataframe=(db_field, select_holding_data, mode,
                                              date_field_list.field_list),
                                   )
                else:
                    self._footer.set(
                        MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_holding_t(self, bank_name, iban):
        '''
        Generate Holding Data (pieces, acquisition_amount) of Transaction Data
        Store result in table holding_t
        '''
        self._delete_footer()
        select_name_isin = self.mariadb.select_table_distinct(
            TRANSACTION_VIEW, [DB_name, DB_ISIN], DB_name, iban=iban)
        name_isin_dict = dict(select_name_isin)
        name_list = list(map(lambda x: x[0], select_name_isin))
        title = ' '.join([bank_name, MENU_TEXT['Holding_T']])
        default_texts_holding_t = shelve_get_key(
            BANK_MARIADB_INI, title + HOLDING_T)
        if not default_texts_holding_t:
            default_texts_holding_t = []
        while True:
            selected_fields = SelectCreateHolding_t(
                title=title,  checkbutton_texts=name_list)
            if selected_fields.button_state == WM_DELETE_WINDOW:
                break
            else:
                selected_name_list = selected_fields.field_list
            if selected_name_list:
                for selected_name in selected_name_list:
                    isin = name_isin_dict[selected_name]
                    if selected_fields.button_state == BUTTON_REPLACE:
                        # delete isin from holding_t
                        self.mariadb.execute_delete(
                            HOLDING_T, iban=iban, isin=isin)
                    self._data_holding_t_create(
                        title, iban, isin, selected_name)
            else:
                self._footer.set(MESSAGE_TEXT['SELECT'])
        self._show_informations()

    def _data_holding_t_create(self, title, iban, isin, name):

        result = self.mariadb.select_table(
            ISIN, [DB_symbol, DB_name], ISIN=isin, result_dict=True)
        if result:
            symbol = result[0][DB_symbol]
            name_ = result[0][DB_name]
            if symbol == NOT_ASSIGNED:
                message = MESSAGE_TEXT['SYMBOL_MISSING'].format(isin, name_)
                Informations.holding_t_informations = Informations.holding_t_informations + \
                    ' '.join(['\n', WARNING, message.replace('\n', ' / ')])
            elif symbol:
                transactions = self.mariadb.select_table(
                    TRANSACTION, [DB_price_date, DB_counter,
                                  DB_transaction_type, DB_pieces, DB_price],
                    result_dict=True, order=[DB_iban, DB_ISIN, DB_price_date, DB_counter],
                    iban=iban, isin=isin)
                if transactions:
                    # create dataframe of all transactions of isin
                    dataframe_transactions = DataFrame(transactions)
                    receipt = dataframe_transactions[DB_transaction_type] == TRANSACTION_RECEIPT
                    dataframe_transactions[DB_pieces].where(
                        receipt, other=-dataframe_transactions[DB_pieces], inplace=True)
                    dataframe_transactions = dataframe_transactions.groupby(
                        # condense multiple transaction of same date
                        by=DB_price_date, as_index=False).sum()
                    dataframe_transactions[FN_SOLD_PIECES] = dataframe_transactions[DB_pieces].cumsum(
                    )

                    dataframe_transactions[DB_acquisition_amount] = dataframe_transactions[DB_pieces] * \
                        dataframe_transactions[DB_price]
                    dataframe_transactions[DB_acquisition_amount] = dataframe_transactions[DB_acquisition_amount].cumsum(
                    )
                    dataframe_transactions[DB_price] = dataframe_transactions[[DB_acquisition_amount, FN_SOLD_PIECES]].apply(
                        lambda x: x.acquisition_amount / x.sold_pieces if x.sold_pieces != 0 else 0, axis=1)
                    start_price_date = dataframe_transactions[DB_price_date].iloc[0]
                    _date = dataframe_transactions[DB_price_date].iloc[-1]
                    end_price_date = dat.subtract(_date, 1)
                    result = self.mariadb.select_table(PRICES_ISIN_VIEW, [DB_price_date, DB_close], result_dict=True,
                                                       name=name_, period=(start_price_date, end_price_date))
                    if result:
                        dataframe_prices = DataFrame(result)
                        if dataframe_prices[DB_price_date].iloc[0] > start_price_date or dataframe_prices[DB_price_date].iloc[-1] < end_price_date:
                            message = MESSAGE_TEXT['PRICES_PERIOD'].format(
                                name_, isin, symbol, start_price_date, end_price_date)
                            Informations.holding_t_informations = Informations.holding_t_informations + \
                                ' '.join(
                                    ['\n', WARNING, message.replace('\n', ' / ')])
                        else:
                            dataframe_transactions.rename(
                                columns={DB_close: DB_market_price, DB_price: DB_acquisition_price}, inplace=True)
                            dataframe = dataframe_prices.merge(
                                # union dataframe of prices with dataframe of transactions, result dataframe with filled gaps betweeen transactions
                                dataframe_transactions, how='outer', on=DB_price_date)
                            dataframe[FN_SOLD_PIECES].ffill(inplace=True)
                            dataframe[DB_acquisition_price].ffill(inplace=True)
                            dataframe[DB_acquisition_amount].ffill(
                                inplace=True)
                            # delete all rows where FN_SOLD_PIECES = 0
                            dataframe.query(FN_SOLD_PIECES +
                                            ' != 0', inplace=True)
                            dataframe.drop(
                                columns=[DB_counter, DB_pieces, DB_transaction_type], inplace=True)
                            dataframe.rename(
                                columns={DB_close: DB_market_price, FN_SOLD_PIECES: DB_pieces}, inplace=True)
                            dataframe[DB_total_amount] = dataframe[DB_market_price] * \
                                dataframe[DB_pieces]
                            dataframe[DB_iban] = iban
                            dataframe[DB_ISIN] = isin
                            # delete existing holding_t from dataframe
                            max_price_date = self.mariadb.select_max_price_date(
                                HOLDING_T, iban=iban, isin=isin)
                            if max_price_date:
                                start_price_date = max_price_date
                                dataframe = dataframe[dataframe.price_date >
                                                      start_price_date]
                            # create isin in holding_t
                            self.mariadb.import_holding_t('Title', dataframe)
                            message = MESSAGE_TEXT['HOLDING_T'].format(
                                name_, isin, start_price_date, end_price_date)
                            Informations.holding_t_informations = Informations.holding_t_informations + \
                                ' '.join(
                                    ['\n', INFORMATION, message.replace('\n', ' / ')])
                    else:
                        message = MESSAGE_TEXT['PRICES_NO'].format(
                            name_, symbol, isin, start_price_date)
                        Informations.holding_t_informations = Informations.holding_t_informations + \
                            ' '.join(
                                ['\n', WARNING, message.replace('\n', ' / ')])
            else:
                message = MESSAGE_TEXT['SYMBOL_MISSING'].format(isin, name_)
                Informations.holding_t_informations = Informations.holding_t_informations + \
                    ' '.join(['\n', WARNING,
                              message.replace('\n', ' / ')])
        else:
            message = ' '.join([isin, MESSAGE_TEXT['ISIN_DATA']])
            Informations.holding_t_informations = Informations.holding_t_informations + \
                ' '.join(['\n', WARNING, message.replace('\n', ' / ')])

    def _data_transaction_detail(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Transaction Detail']])
        Transaction = DataTransactionDetail(
            title=title, mariadb=self.mariadb, table=TRANSACTION_VIEW,
            bank_name=bank_name, iban=iban)
        self._footer.set(Transaction.footer)

    def _data_profit_delivery_negative(self, dict_):
        """ set delivery pieces negative """
        if dict_[DB_transaction_type] == TRANSACTION_DELIVERY:
            dict_[DB_pieces] = - dict_[DB_pieces]

        return dict_

    def _data_profit_pieces_cumulate(self, previous_dict, dict_):
        """ accumulate pieces"""
        dict_[FN_PIECES_CUM] = dict_[DB_pieces]
        dict_[FN_PIECES_CUM] = dict_[FN_PIECES_CUM] + \
            previous_dict[FN_PIECES_CUM]
        if dict_[FN_PIECES_CUM] < 0:
            MessageBoxInfo(message=MESSAGE_TEXT['TRANSACTION_PIECES_NEGATIVE'].format(
                dict_[DB_price_date]))
        return dict_

    def _data_prices(self, mode):

        self._delete_footer()
        if mode:
            title = MENU_TEXT['Prices ISINs'] + ' %'
        else:
            title = MENU_TEXT['Prices ISINs']
        select_isin_ticker = self.mariadb.select_isin_with_ticker(
            [DB_name, DB_symbol], order=DB_name)
        if not select_isin_ticker:
            MessageBoxInfo(title=title, message=(
                MESSAGE_TEXT['DATA_NO'].format(ISIN.upper(), DB_symbol.upper())))
            return
        name_symbol = dict(select_isin_ticker)
        from_date = '1950-01-01'
        to_date = date.today()
        default_texts = []
        default_texts_prices = shelve_get_key(BANK_MARIADB_INI, title + PRICES)
        if not default_texts_prices:
            default_texts_prices = []
        while True:
            date_field_list = InputDateFieldlistPrices(
                title=title,
                from_date=from_date, standard=None,
                default_texts=default_texts,
                field_list=list(name_symbol.keys()))
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            if not date_field_list.field_list:
                self._footer.set(MESSAGE_TEXT['DATA_NO'].format(
                    ', '.join(date_field_list.field_list), ''))
                break
            # selected names e.g. Amazon, ...
            default_texts = date_field_list.field_list
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            if mode == PERCENT:
                symbol_list = list(map(name_symbol.get, default_texts))
                from_date = self.mariadb.select_first_price_date_of_prices(
                    symbol_list, period=(from_date, to_date))
                if not from_date:
                    self._footer.set(MESSAGE_TEXT['DATA_NO'].format(
                        ', '.join(date_field_list.field_list), ''))
                    break
            selected_fields = SelectFields(
                title=title, standard=title + PRICES,
                default_texts=default_texts_prices,
                checkbutton_texts=[DB_open, DB_low, DB_high, DB_close, DB_adjclose, DB_volume,
                                   DB_dividends, DB_splits])
            if selected_fields.button_state == WM_DELETE_WINDOW:
                break
            else:
                # selected data fields e.g. close, ..
                field_list = selected_fields.field_list
            db_fields = [DB_name, DB_price_date, *field_list]
            select_data = self.mariadb.select_table(PRICES_ISIN_VIEW, db_fields, order=DB_name, result_dict=True,
                                                    name=date_field_list.field_list, period=(from_date, to_date))
            select_origin_dict = dict(self.mariadb.select_table(
                ISIN, [DB_name, DB_origin_symbol], name=date_field_list.field_list))
            if select_data:
                self._footer.set('')
                PandasBoxPrices(
                    title=title, dataframe=(field_list, select_data, select_origin_dict, mode))
            else:
                self._footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(', '.join(date_field_list.field_list), ''))

    def _data_balances(self):

        self._delete_footer()
        to_date = date.today()
        from_date = date(2021, 10, 3)
        title = ' '.join(
            [MENU_TEXT['All_Banks'], MENU_TEXT['Balances']])
        while True:
            input_date = InputDate(title=title,
                                   header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date
                                   )
            if input_date.button_state == WM_DELETE_WINDOW:
                return input_date.button_state, None, None
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            data_total_amounts = self.mariadb.select_total_amounts(
                period=(from_date, to_date))
            title = ' '.join([title, MESSAGE_TEXT['Period'].format(
                from_date, to_date)])
            if data_total_amounts:
                PandasBoxTotals(title=title, dataframe=data_total_amounts, )
            else:
                MessageBoxInfo(title=title, message=(
                    MESSAGE_TEXT['DATA_NO'].format('', '')))

    def _import_bankidentifier(self):

        MessageBoxInfo(message=MESSAGE_TEXT['IMPORT_CSV'].format(
            BANKIDENTIFIER.upper()))
        webbrowser.open(BUNDESBANK_BLZ_MERKBLATT)
        webbrowser.open(BUNDEBANK_BLZ_DOWNLOAD)
        file_dialogue = FileDialogue()
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_bankidentifier(
                file_dialogue.filename)
            MessageBoxInfo(title=MESSAGE_TEXT['TABLE'].format(BANKIDENTIFIER.upper()),
                           message=MESSAGE_TEXT['LOAD_DATA'].format(file_dialogue.filename))

    def _import_prices(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Download'], MENU_TEXT['Prices']])
        select_isin_ticker = self.mariadb.select_isin_with_ticker(
            [DB_name], order=DB_name)
        if select_isin_ticker:
            select_isin_ticker = list(map(lambda x: x[0], select_isin_ticker))
            download_prices = None
            while True:
                select_isins = SelectDownloadPrices(
                    title=title, checkbutton_texts=select_isin_ticker)
                if select_isins.button_state == WM_DELETE_WINDOW:
                    self._show_informations()
                    if isinstance(download_prices, Thread):
                        if download_prices.is_alive:
                            MessageBoxInfo(
                                title=title, message=MESSAGE_TEXT['THREAD_RUNNING'])
                    return
                state = select_isins.button_state
                field_list = select_isins.field_list
                if self.shelve_app[KEY_THREADING] == TRUE:
                    download_prices = Thread(target=self._import_prices_run,
                                             args=(self.mariadb, title, field_list, state))
                    download_prices.start()
                else:
                    self._import_prices_run(
                        self.mariadb, title, field_list, state)
        else:
            self._footer.set(MESSAGE_TEXT['SYMBOL_MISSING_ALL'].format(title))

    def _import_prices_histclose(self):
        '''
        download of historical prices may contain adjusted close prices
        e.g. extra dividends, splits, ... are represented by multiplication with a factor (r-factor)
        Such close prices generate faulty total_amount of holding positions in the past  (table holding_t)
        To get the historical precise close prices in table holding_t close prices must be readjusted (see Isin table)
        '''
        self._delete_footer()
        names, names_symbol, names_adjustments = self.mariadb.select_isin_adjustments()
        title = ' '.join([MENU_TEXT['Historical Prices']])
        while True:
            select_isins = SelectDownloadPrices(
                title=title, checkbutton_texts=names,
                button1_text=BUTTON_UPDATE, button2_text=None, button3_text=None,)
            if select_isins.button_state == WM_DELETE_WINDOW:
                self._show_informations()
                return
            field_list = select_isins.field_list
            for name in field_list:
                self.mariadb.update_prices_histclose(
                    name, names_symbol[name], names_adjustments[name])

    def _import_prices_run(self, mariadb, title, field_list, state):

        for name in field_list:
            select_isin_data = self.mariadb.select_table(
                ISIN, [DB_ISIN, DB_symbol, DB_origin_symbol], name=name, result_dict=True)
            if select_isin_data:
                select_isin_data = select_isin_data[0]
                symbol = select_isin_data[DB_symbol]
                origin_symbol = select_isin_data[DB_origin_symbol]
                message_symbol = symbol + '/' + origin_symbol
                isin = select_isin_data[DB_ISIN]
                if state == BUTTON_DELETE:
                    self.mariadb.execute_delete(PRICES, symbol=symbol)
                    MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                   message=MESSAGE_TEXT['PRICES_DELETED'].format(
                                       name, message_symbol, isin))
                else:
                    if symbol == NOT_ASSIGNED:
                        MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                       message=MESSAGE_TEXT['SYMBOL_MISSING'].format(isin, name))
                    else:
                        from_date = datetime.strptime(
                            FROM_BEGINNING_DATE, "%Y-%m-%d").date()
                        from_beginning_date = from_date
                        if state == BUTTON_APPEND:
                            max_price_date = self.mariadb.select_max_price_date(
                                PRICES, symbol=symbol)
                            if max_price_date:
                                from_date = max_price_date + timedelta(days=1)
                        if origin_symbol == YAHOO:
                            tickers = Ticker(symbol)
                            f = io.StringIO()
                            with redirect_stdout(f):
                                dataframe = tickers.history(auto_adjust=False,
                                                            period=None, start=from_date, end=date.today())
                            Informations.prices_informations = ' '.join(
                                [Informations.prices_informations, '\n' + INFORMATION, f.getvalue()])
                            columns = {"Date": DB_price_date, 'Open': DB_open, 'High': DB_high,
                                       'Low': DB_low, 'Close': DB_close, 'Adj Close': DB_adjclose,
                                       'Dividends': DB_dividends, 'Stock Splits': DB_splits,
                                       'Volume': DB_volume}
                        elif origin_symbol == ALPHA_VANTAGE:
                            function = self.shelve_app[KEY_ALPHA_VANTAGE_PRICE_PERIOD]
                            '''
                            By default, outputsize=compact. Strings compact and full are accepted with the following specifications:
                            compact returns only the latest 100 data points;
                            full returns the full-length time series of 20+ years of historical data
                            '''
                            url = 'https://www.alphavantage.co/query?function=' + function + '&symbol=' + \
                                symbol + '&outputsize='
                            if from_date == from_beginning_date:
                                url = url + OUTPUTSIZE_FULL + '&apikey=' + \
                                    self.shelve_app[KEY_ALPHA_VANTAGE]
                            else:
                                url = url + OUTPUTSIZE_COMPACT + '&apikey=' + \
                                    self.shelve_app[KEY_ALPHA_VANTAGE]
                            data = requests.get(url).json()
                            keys = [*data]  # list of keys of dictionary data
                            dataframe = None
                            if len(keys) == 2:
                                try:
                                    '''
                                    2. item of dict data contains Time Series as a dict ( *data[1})
                                    example: TIME_SERIES_DAILY                                                                {
                                                "Meta Data": {
                                                    "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                                                    "2. Symbol": "IBM",
                                                    "3. Last Refreshed": "2023-07-26",
                                                    "4. Output Size": "Compact",
                                                    "5. Time Zone": "US/Eastern"
                                                },
                                                "Time Series (Daily)": {
                                                    "2023-07-26": {
                                                        "1. open": "140.4400",
                                                        "2. high": "141.2500",
                                                        "3. low": "139.8800",
                                                        "4. close": "141.0700",
                                                        "5. volume": "4046441"
                                                    },
                                                    "2023-07-25": {
                                                        "1. open": "139.4200",
                                                        "2. high": "140.4300",
                                    '''
                                    data = data[keys[1]]
                                    dataframe = DataFrame(data)
                                    dataframe = dataframe.T
                                    if 'ADJUSTED' in function:
                                        columns = {"index": DB_price_date, '1. open': DB_open,
                                                   '2. high': DB_high, '3. low': DB_low, '4. close': DB_close,
                                                   '5. adjusted close': DB_adjclose, '6. volume': DB_volume,
                                                   '7. dividend amount': DB_dividends,
                                                   '8. split coefficient': DB_splits}
                                    else:
                                        columns = {"index": DB_price_date, '1. open': DB_open,
                                                   '2. high': DB_high, '3. low': DB_low, '4. close': DB_close,
                                                   '5. volume': DB_volume}
                                except Exception:
                                    Informations.prices_informations = ' '.join(
                                        [Informations.prices_informations, '\n' + ERROR, data])
                                    MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                                   message=MESSAGE_TEXT['ALPHA_VANTAGE'].format(isin, name))
                                    return
                            else:
                                try:
                                    data = data['Information']
                                except Exception:
                                    pass
                                Informations.prices_informations = ' '.join(
                                    [Informations.prices_informations, '\n' + ERROR, data])
                                MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                               message=MESSAGE_TEXT['ALPHA_VANTAGE'].format(isin, name))
                                return
                        if dataframe.empty:
                            MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                           message=MESSAGE_TEXT['PRICES_NO'].format(
                                               name, message_symbol, isin, ''))
                        else:
                            dataframe = dataframe.reset_index()
                            dataframe[DB_symbol] = symbol
                            dataframe.rename(columns=columns, inplace=True)
                            if origin_symbol == YAHOO:
                                dataframe[DB_origin] = YAHOO
                            elif origin_symbol == ALPHA_VANTAGE:
                                dataframe[DB_origin] = ALPHA_VANTAGE
                            try:
                                dataframe[DB_price_date] = dataframe[DB_price_date].apply(
                                    lambda x: x.date())
                            except Exception:
                                pass
                            dataframe = dataframe.set_index(
                                [DB_symbol, DB_price_date])
                            dataframe.sort_index(inplace=True)
                            period = (
                                dataframe.index[0][1], dataframe.index[-1][1])
                            self.mariadb.execute_delete(
                                PRICES, symbol=symbol, period=period)
                            if mariadb.import_prices(title, dataframe):
                                MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                               message=MESSAGE_TEXT['PRICES_LOADED'].format(
                                                   name, period, message_symbol, isin))

    def _import_server(self):

        MessageBoxInfo(message=MESSAGE_TEXT['IMPORT_CSV'].format(
            SERVER.upper()) + FINTS_SERVER)
        self._websites(FINTS_SERVER_ADDRESS)
        file_dialogue = FileDialogue()
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_server(
                file_dialogue.filename)
            MessageBoxInfo(title=MESSAGE_TEXT['TABLE'].format(SERVER.upper()),
                           message=MESSAGE_TEXT['LOAD_DATA'].format(file_dialogue.filename))

    def _import_transaction(self, bank_name, iban):
        """
        import transactions from CSV_File.
        CSV File Columns ((price_date, ISIN, name, pieces, transaction_type, price)
        price_date: YYYY-MM-DD
        decimals: decimal_point
        """
        _text = ("\n\nStructure of CSV_File: \n"
                 "\nColumns: \n price_date, ISIN, name, pieces, price\n"
                 "\n         PriceDate Format: YYYY-MM-DD"
                 "\n         Pieces and Price DecimalPoint"
                 "\n         Pieces NEGATIVE for Deliveries \n"
                 "\nHeader_line will be ignored"
                 )
        MessageBoxInfo(
            message=MESSAGE_TEXT['IMPORT_CSV'].format(TRANSACTION.upper()) + _text)
        file_dialogue = FileDialogue()
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_transaction(iban, file_dialogue.filename)
            MessageBoxInfo(title=MESSAGE_TEXT['TABLE'].format(TRANSACTION),
                           message=MESSAGE_TEXT['LOAD_DATA'].format(file_dialogue.filename))

    def _isin_table(self):

        self._delete_footer()
        isin_name = ''
        title = ' '.join([MENU_TEXT['Database'], MENU_TEXT['ISIN Table']])
        while True:
            isin = Isin(title, self.mariadb,
                        self.shelve_app[KEY_ALPHA_VANTAGE], isin_name=isin_name)
            if isin.button_state == WM_DELETE_WINDOW:
                return
            if isin.button_state == MENU_TEXT['Prices']:
                self._import_prices()
            if isin.button_state == FORMS_TEXT['Adjust Prices']:
                while True:
                    adjustments = Adjustments(
                        self.mariadb, isin.field_dict[DB_ISIN])
                    if adjustments.button_state == WM_DELETE_WINDOW:
                        break
            if isin.field_dict:
                isin_name = isin.field_dict[DB_name]

    def _sepa_credit_transfer(self, bank_code, account):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Transfer'], bank_name, label])
        bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
        bank.iban = account[KEY_ACC_IBAN]
        bank.subaccount_number = account[KEY_ACC_SUBACCOUNT_NUMBER]
        sepa_credit_box = SepaCreditBox(
            bank, self.mariadb, account, title=title)
        if sepa_credit_box.button_state == WM_DELETE_WINDOW:
            return
        transfer_data = {}
        account_data = dictaccount(bank_code,
                                   bank.account_number)
        transfer_data[SEPA_CREDITOR_NAME] = sepa_credit_box.field_dict[SEPA_CREDITOR_NAME]
        transfer_data[SEPA_CREDITOR_IBAN] = sepa_credit_box.field_dict[SEPA_CREDITOR_IBAN].upper()
        transfer_data[SEPA_CREDITOR_BIC] = sepa_credit_box.field_dict[SEPA_CREDITOR_BIC].upper()
        transfer_data[SEPA_AMOUNT] = sepa_credit_box.field_dict[SEPA_AMOUNT].replace(
            ',', '.')
        transfer_data[SEPA_PURPOSE] = sepa_credit_box.field_dict[
            SEPA_PURPOSE_1] + ' ' + sepa_credit_box.field_dict[SEPA_PURPOSE_2]
        transfer_data[SEPA_REFERENCE] = sepa_credit_box.field_dict[SEPA_REFERENCE]
        if 'HKCSE' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
            if sepa_credit_box.field_dict[SEPA_EXECUTION_DATE] == str(date.today()):
                transfer_data[SEPA_EXECUTION_DATE] = '1999-01-01'
            else:
                transfer_data[SEPA_EXECUTION_DATE] = sepa_credit_box.field_dict[SEPA_EXECUTION_DATE]
        else:
            transfer_data[SEPA_EXECUTION_DATE] = '1999-01-01'
        SepaCreditTransfer(bank, account_data, transfer_data)
        if transfer_data[SEPA_EXECUTION_DATE] == '1999-01-01':
            bank.dialogs.transfer(bank)
        else:
            bank.dialogs.date_transfer(bank)
        self._show_message(bank)

    def _bank_security_function(self, bank_code, new):

        self._delete_footer()
        bank = InitBankAnonymous(bank_code, self.mariadb)
        bank.dialogs.anonymous(bank)
        security_function_dict = {}
        default_value = None
        for twostep in bank.twostep_parameters:
            security_function, security_function_name = twostep
            security_function_dict[security_function] = security_function_name
            if (shelve_get_key(bank_code, KEY_SECURITY_FUNCTION) and shelve_get_key(
                    bank_code, KEY_SECURITY_FUNCTION)[0:3] == security_function[0:3]):
                default_value = security_function
        bank_name = self._bank_name(bank.bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change Security Function']])
        if new:
            security_function_box = BuiltRadioButtons(
                title=title,
                header=MESSAGE_TEXT['TWOSTEP'], default_value=default_value,
                button2_text=None, radiobutton_dict=security_function_dict)
        else:
            security_function_box = BuiltRadioButtons(
                title=title,
                header=MESSAGE_TEXT['TWOSTEP'], default_value=default_value,
                radiobutton_dict=security_function_dict)
        if security_function_box.button_state == WM_DELETE_WINDOW:
            return
        if security_function_box.button_state == BUTTON_SAVE:
            data = (KEY_SECURITY_FUNCTION, security_function_box.field[0:3])
            shelve_put_key(bank_code, data)
        self._footer.set(MESSAGE_TEXT['SYNC_START'].format(bank_name))

    def _show_alpha_vantage(self):

        self._delete_footer()
        title = MENU_TEXT['Alpha Vantage']
        alpha_vantage_symbols = self.mariadb.select_dict(
            ISIN, DB_name, DB_symbol, origin_symbol=ALPHA_VANTAGE)
        alpha_vantage_names = list(alpha_vantage_symbols.keys())
        field_list = []
        while True:
            checkbutton = SelectFields(
                title=title,
                button2_text=None, button3_text=None, button4_text=None, default_texts=field_list,
                checkbutton_texts=self.alpha_vantage.function_list)
            if checkbutton.button_state == WM_DELETE_WINDOW:
                return
            field_list = checkbutton.field_list
            dataframe = None
            for function in checkbutton.field_list:
                default_values = []
                while True:
                    title_function = ' '.join([title, function])
                    parameters = AlphaVantageParameter(
                        title_function, function, self.shelve_app[KEY_ALPHA_VANTAGE],
                        self.alpha_vantage.parameter_dict[function], default_values,
                        alpha_vantage_names)
                    if parameters.button_state == WM_DELETE_WINDOW:
                        break
                    elif parameters.button_state == MENU_TEXT['ISIN Table']:
                        self._isin_table()
                        return
                    elif parameters.button_state == BUTTON_ALPHA_VANTAGE:
                        self._websites(ALPHA_VANTAGE_DOCUMENTATION)
                    else:
                        default_values = list(parameters.field_dict.values())
                        url = 'https://www.alphavantage.co/query?function=' + function
                        for key, value in parameters.field_dict.items():
                            if value:
                                if key.lower() == DB_symbol:
                                    value = alpha_vantage_symbols[value]
                                api_parameter = ''.join(
                                    ['&', key.lower(), '=', value])
                                url = url + api_parameter
                        try:
                            data_json = requests.get(url).json()
                        except Exception:
                            exception_error(
                                message=MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
                            break
                        key_list = list(data_json.keys())
                        if JSON_KEY_META_DATA in data_json.keys():
                            if isinstance(dataframe, DataFrame):
                                dataframe_next = DataFrame(
                                    data_json[key_list[1]]).T
                                dataframe = dataframe.join(dataframe_next)
                            else:
                                dataframe = DataFrame(
                                    data_json[key_list[1]]).T
                        elif JSON_KEY_ERROR_MESSAGE in data_json.keys():
                            MessageBoxInfo(title=title_function, message=MESSAGE_TEXT[
                                'ALPHA_VANTAGE_ERROR_MSG'].format(data_json[JSON_KEY_ERROR_MESSAGE], url))
                        elif data_json == {}:
                            MessageBoxInfo(title=title_function, message=MESSAGE_TEXT[
                                'ALPHA_VANTAGE_NO_DATA'].format(url))
                        else:
                            self._websites(url)
                        break
            if isinstance(dataframe, DataFrame):
                title_function = ' '.join([title_function, url])
                BuiltPandasBox(title=title_function, dataframe=dataframe)

    def _show_alpha_vantage_search_symbol(self):

        function = 'SYMBOL_SEARCH'
        title = MENU_TEXT['Alpha Vantage Symbol Search']
        while True:
            while True:
                parameters = AlphaVantageParameter(
                    title, function, self.shelve_app[KEY_ALPHA_VANTAGE],
                    self.alpha_vantage.parameter_dict[function], [], [])
                if parameters.button_state == WM_DELETE_WINDOW:
                    break
                elif parameters.button_state == MENU_TEXT['ISIN Table']:
                    self._isin_table()
                    return
                elif parameters.button_state == BUTTON_ALPHA_VANTAGE:
                    self._websites(ALPHA_VANTAGE_DOCUMENTATION)
                else:
                    url = 'https://www.alphavantage.co/query?function=' + function
                    for key, value in parameters.field_dict.items():
                        if value:
                            api_parameter = ''.join(
                                ['&', key.lower(), '=', value])
                            url = url + api_parameter
                    try:
                        data_json = requests.get(url).json()
                    except Exception:
                        exception_error(
                            message=MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
                        break
                    if JSON_KEY_ERROR_MESSAGE in data_json.keys():
                        MessageBoxInfo(title=title, message=MESSAGE_TEXT[
                            'ALPHA_VANTAGE_ERROR_MSG'].format(data_json[JSON_KEY_ERROR_MESSAGE], url))
                    elif data_json == {}:
                        MessageBoxInfo(title=title, message=MESSAGE_TEXT[
                            'ALPHA_VANTAGE_NO_DATA'].format(url))
                    else:
                        self._websites(url)

    def _show_balances_all_banks(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Show'], MENU_TEXT['Balances']])
        message = title
        total_df = []
        if self.bank_names != {}:
            for bank_name in self.bank_names.values():
                message = message + '\n' + bank_name
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                bank_balances = self._show_balances_get(bank_code)
                if bank_balances:
                    dataframe = DataFrame(bank_balances, columns=[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                                                  KEY_ACC_PRODUCT_NAME, DB_entry_date,
                                                                  DB_closing_status, DB_closing_balance, DB_closing_currency,
                                                                  DB_opening_status, DB_opening_balance, DB_opening_currency])
                    total_df.append(dataframe)
            if total_df:
                PandasBoxBalancesAllBanks(title=title, dataframe=total_df)
                self._footer.set(
                    ' '.join([message, '\n', MESSAGE_TEXT['TASK_DONE']]))
            else:
                self._footer.set(
                    ' '.join([message, MESSAGE_TEXT['DATA_NO'].format('', '')]))

    def _show_balances(self, bank_code, bank_name):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Show'], MENU_TEXT['Balances']])
        bank_balances = self._show_balances_get(bank_code)
        if bank_balances:
            dataframe = DataFrame(bank_balances, columns=[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                                          KEY_ACC_PRODUCT_NAME, DB_entry_date,
                                                          DB_closing_status, DB_closing_balance, DB_closing_currency,
                                                          DB_opening_status, DB_opening_balance, DB_opening_currency])
            title = ' '.join(
                [MENU_TEXT['Show'], bank_name, MENU_TEXT['Balances']])
            PandasBoxBalances(title=title, dataframe=dataframe,
                              dataframe_sum=[DB_closing_balance, DB_opening_balance])
        else:
            self._footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _show_balances_get(self, bank_code):

        accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
        balances = []
        if accounts:
            for acc in accounts:
                iban = acc[KEY_ACC_IBAN]
                max_entry_date = self.mariadb.select_max_price_date(
                    STATEMENT, field_name_date=DB_entry_date, iban=iban)
                if max_entry_date:
                    fields = [DB_counter,
                              DB_closing_status, DB_closing_balance, DB_closing_currency,
                              DB_opening_status, DB_opening_balance, DB_opening_currency]
                    balance = self.mariadb.select_table(
                        STATEMENT, fields, result_dict=True, iban=iban, entry_date=max_entry_date, order=DB_counter)
                    if balance:
                        # STATEMENT Account contains 1-n records per day
                        balances.append(Balance(bank_code,
                                                acc[KEY_ACC_ACCOUNT_NUMBER],
                                                acc[KEY_ACC_PRODUCT_NAME],
                                                max_entry_date,
                                                balance[-1][DB_closing_status],
                                                balance[-1][DB_closing_balance],
                                                balance[-1][DB_closing_currency],
                                                balance[0][DB_opening_status],
                                                balance[0][DB_opening_balance],
                                                balance[0][DB_opening_currency],
                                                ))
                else:
                    # HOLDING Account
                    max_price_date = self.mariadb.select_max_price_date(
                        HOLDING, iban=iban)
                    if max_price_date:

                        fields = [DB_total_amount_portfolio,
                                  DB_amount_currency]
                        balance = self.mariadb.select_table(
                            HOLDING, fields, result_dict=True, iban=iban, price_date=max_price_date)
                        if balance:
                            # HOLDING Account contains only 1 record per day
                            balance = balance[0]
                            # HOLDING previous entry
                            clause = ' ' + DB_price_date + ' < ' + \
                                '"' + max_price_date.strftime("%Y-%m-%d") + '"'
                            max_price_date_previous = self.mariadb.select_max_price_date(
                                HOLDING, iban=iban, clause=clause)
                            balance_previous = self.mariadb.select_table(
                                HOLDING, fields, result_dict=True, iban=iban, price_date=max_price_date_previous)
                            if balance_previous:
                                balance_previous = balance_previous[0]
                            else:
                                balance_previous = balance
                            balances.append(Balance(bank_code,
                                                    acc[KEY_ACC_ACCOUNT_NUMBER],
                                                    acc[KEY_ACC_PRODUCT_NAME],
                                                    max_price_date,
                                                    '',
                                                    balance[DB_total_amount_portfolio],
                                                    balance[DB_amount_currency],
                                                    '',
                                                    balance_previous[DB_total_amount_portfolio],
                                                    balance_previous[DB_amount_currency]
                                                    ))
        return balances

    def _show_statements(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join([MENU_TEXT['Show'], bank_name,
                          MENU_TEXT['Statement'], label])
        date_field_list = InputDateFieldlist(title=title,
                                             from_date=date.today() - timedelta(days=30),
                                             standard=MENU_TEXT['Show'] +
                                             MENU_TEXT['Statement'],
                                             field_list=self.mariadb.table_fields[STATEMENT])
        if date_field_list.button_state == WM_DELETE_WINDOW:
            return

        from_date = date_field_list.field_dict[FN_FROM_DATE]
        to_date = date_field_list.field_dict[FN_TO_DATE]
        statements = self.mariadb.select_table(STATEMENT, date_field_list.field_list,
                                               iban=iban,
                                               period=(from_date, to_date))
        if statements:
            title = ' '.join(
                [title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
            PandasBoxStatement(dataframe=(
                statements, date_field_list.field_list), title=title)
            return
        else:
            self._footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _show_transactions(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        field_list = self.mariadb.table_fields[TRANSACTION_VIEW]
        from_date = date(2000, 1, 1)
        to_date = date.today()
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        default_texts = []
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'], label, TRANSACTION.upper()])
        while True:
            date_field_list = InputDateFieldlist(title=title,
                                                 from_date=from_date, to_date=to_date,
                                                 default_texts=default_texts,
                                                 standard=MENU_TEXT['Prices ISINs'], field_list=field_list)
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            default_texts = date_field_list.field_list
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            data_list = self.mariadb.select_table(
                TRANSACTION_VIEW, date_field_list.field_list, result_dict=True,
                iban=iban, period=(from_date, to_date))

            title = ' '.join(
                [title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
            if data_list:
                PandasBoxHoldingTransaction(title=title, dataframe=data_list,
                                            dataframe_sum=[DB_posted_amount, DB_acquisition_amount])
            else:
                self._footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _show_holdings(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        field_list = self.mariadb.table_fields[HOLDING_VIEW]

        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'], label])
        max_price_date, _ = self._date_init(iban, timedelta_days=0)
        if not max_price_date:
            self._footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))
            return
        date_ = max_price_date
        default_texts = []
        while True:
            date_field_list = InputDateFieldlistHolding(title=title, date=date_,
                                                        field_list=field_list,
                                                        default_texts=default_texts,
                                                        mariadb=self.mariadb, iban=iban)
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            default_texts = date_field_list.field_list
            date_ = date_field_list.field_dict[FN_DATE]
            data_date_ = self.mariadb.select_holding_data(
                field_list=date_field_list.field_list, iban=iban, price_date=date_)
            if data_date_:
                data_list = sorted(data_date_,
                                   key=lambda i: (i[DB_name]))
                title_period = ' '.join(
                    [title, MESSAGE_TEXT['Period'].format(date_, date_)])
                PandasBoxHolding(title=title_period,
                                 dataframe=(
                                     data_list, date_field_list.field_list),
                                 dataframe_sum=[DB_total_amount,
                                                DB_acquisition_amount, FN_PROFIT],
                                 )

    def _show_holdings_perc(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'] + '%', label])
        from_date = (date.today() - timedelta(days=1))
        to_date = date.today()
        while True:
            input_date = InputDateHoldingPerc(title=title, from_date=from_date,
                                              to_date=to_date,
                                              mariadb=self.mariadb, iban=iban)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            data_from_date = self.mariadb.select_holding_data(
                iban=iban, price_date=from_date)
            to_date = input_date.field_dict[FN_TO_DATE]
            data_to_date = self.mariadb.select_holding_data(
                iban=iban, price_date=to_date)
            title1 = ' '.join(
                [title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
            PandasBoxHoldingPercent(
                title=title1, dataframe=(data_to_date, data_from_date))

    def _transactions_pieces(self, bank_name, iban):

        self._delete_footer()
        from_date = date(2000, 1, 1)
        to_date = date.today()
        title = ' '.join([bank_name, MENU_TEXT['Check Transactions Pieces']])
        while True:
            input_date = InputDate(title=title, header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            result = self.mariadb.transaction_portfolio(
                iban=iban, period=(from_date, to_date))
            if result:
                dataframe = DataFrame(list(result), columns=['ORIGIN',
                                                             DB_ISIN, DB_name, DB_pieces])
                BuiltPandasBox(
                    dataframe=dataframe, title=title
                    + MESSAGE_TEXT['TRANSACTION_PIECES_PORTFOLIO'])
            else:
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['TRANSACTION_CHECK'].format('NO '))

    def _transactions_profit(self, bank_name, iban):

        self._delete_footer()
        from_date = date(2000, 1, 1)
        to_date = date.today()
        while True:
            title = ' '.join(
                [bank_name, MENU_TEXT['Profit of closed Transactions']])
            input_date = InputDate(title=title,
                                   header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            self._transactions_profit_closed(title, iban, from_date, to_date)

    def _transactions_profit_closed(self, title, iban, from_date, to_date):

        self._delete_footer()
        result = self.mariadb.transaction_profit_closed(
            iban=iban, period=(from_date, to_date))
        if result:
            title = ' '.join(
                [title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
            PandasBoxTransactionProfit(title=title, dataframe=list(result))
        else:
            MessageBoxInfo(title=title,
                           message=MESSAGE_TEXT['TRANSACTION_CLOSED_EMPTY'].format(from_date, to_date))

    def _transactions_profit_all(self, bank_name, iban):

        self._delete_footer()
        from_date = date(2000, 1, 1)
        to_date = date.today()
        title = ' '.join(
            [bank_name, MENU_TEXT['Profit Transactions incl. current Depot Positions']])
        while True:
            title = ' '.join(
                [bank_name, MENU_TEXT['Profit Transactions incl. current Depot Positions']])
            input_date = InputDate(title=title,
                                   header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            result = self.mariadb.transaction_profit_all(
                iban=iban, period=(from_date, to_date))
            if result:
                title = ' '.join(
                    [title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
                PandasBoxTransactionProfit(title=title, dataframe=list(result))
            else:
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['TRANSACTION_NO'].format(from_date, to_date))
                self._transactions_profit_closed(
                    bank_name, iban, from_date, to_date)

    def _transactions_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Transactions Table']])
        transaction_table = TransactionTable(
            title=title, mariadb=self.mariadb, table=TRANSACTION_VIEW,
            button2_text=BUTTON_NEW,
            bank_name=bank_name, iban=iban)
        self._footer.set(transaction_table.footer)

    def _transactions_sync(self, bank_name, iban):

        self._delete_footer()
        select_isins = self.mariadb.select_dict(
            HOLDING_VIEW, DB_name, DB_ISIN, iban=iban)
        if select_isins == {}:
            self._footer.set(MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))
            return
        price_dates = self.mariadb.select_holding_fields(iban=iban)
        sync_table = []
        name = list(select_isins.keys())[0]
        isin = select_isins[name]
        while True:
            input_isin = InputISIN(
                title=MESSAGE_TEXT['TRANSACTION_TITLE'].format(bank_name, ''),
                header=MESSAGE_TEXT['TRANSACTION_HEADER_SYNC_TABLE'],
                names=select_isins, period=False, default_values=(name, isin))
            if isinstance(sync_table, TransactionSync):
                destroy_widget(sync_table.dataframe_window)
            if input_isin.button_state == WM_DELETE_WINDOW:
                return
            isin = input_isin.field_dict[DB_ISIN]
            name = input_isin.field_dict[DB_name]
            max_price_date = self.mariadb.select_max_price_date(
                TRANSACTION, iban=iban, isin=isin)
            if max_price_date:
                from_date = max_price_date
                result = self.mariadb.select_holding_acquisition(
                    iban=iban, isin=isin, period=(from_date, date.today()))
            else:
                result = self.mariadb.select_holding_acquisition(
                    iban=iban, isin=isin)
            data = []
            transactions = []
            for row in result:
                if len(data) == 2:
                    data.pop(0)
                data.append(row)
                if not max_price_date or data[-1].price_date != max_price_date:
                    if ((price_dates.index(data[-1].price_date) -
                         # all pieces sold
                         price_dates.index(data[0].price_date)) > 1):
                        sell_off_data = [data[0]]
                        transactions = (transactions + self.mariadb.transaction_sell_off(
                            iban, isin, name, sell_off_data))
                        data.pop(0)
                    if (data[0].acquisition_amount == data[-1].acquisition_amount
                            and len(data) == 2):
                        # skip, nothing sold or bought
                        if data[0].pieces != data[-1].pieces:
                            # show split, must be adjusted manually
                            transaction_fields = {
                                DB_ISIN: isin,
                                DB_price_date: data[-1].price_date,
                                DB_name: name,
                                DB_price_currency: data[-1].price_currency,
                                DB_price: data[-1].market_price,
                                DB_pieces: data[-1].pieces,
                                DB_transaction_type: 'SPLIT'
                            }
                            transactions.append(transaction_fields)
                    elif self.mariadb.row_exists(TRANSACTION, iban=iban, isin=isin,
                                                 price_date=data[-1].price_date, counter=0):
                        # skip, transaction already generated
                        pass
                    else:  # generate transaction; check posted amount manually
                        transactions = transactions + self.mariadb.transaction_sync(
                            iban, isin, name, data)
            max_price_date = self.mariadb.select_max_price_date(
                HOLDING, iban=iban)
            if (not self.mariadb.row_exists(
                    TRANSACTION, iban=iban, isin=isin, price_date=max_price_date)
                    and transactions):
                transactions = transactions + self.mariadb.transaction_sell_off(
                    iban, isin, name, data)
            if transactions:
                if isinstance(sync_table, TransactionSync):
                    destroy_widget(sync_table.dataframe_window)
                sync_table = TransactionSync(
                    self.mariadb, iban,
                    title=MESSAGE_TEXT['TRANSACTION_TITLE'].format(
                        bank_name, name),
                    header=MESSAGE_TEXT['TRANSACTION_HEADER_SYNC'],
                    transactions=transactions)

    def _websites(self, site):

        webbrowser.open(site)


class Data_ISIN_Period(object):
    """
    Get ISIN and period for table query
    ARGS
            title        message-key of title
            header       message-key header text
            table        MARIA DB table/view
            mariadb      MARIA DB connector
    """

    def __init__(self, title=MESSAGE_TITLE, header_key='SELECT', mariadb=None, table=TRANSACTION_VIEW,
                 bank_name='', iban=None, button2_text=None):

        self.header_key = header_key
        self.mariadb = mariadb
        self.table = table
        self.bank_name = bank_name
        self.iban = iban
        self.footer = ''
        if button2_text == BUTTON_NEW:
            transaction_isin = self.mariadb.select_dict(ISIN, DB_name, DB_ISIN)
        elif not iban:
            transaction_isin = self.mariadb.select_dict(
                self.table, DB_name, DB_ISIN, )
        else:
            transaction_isin = self.mariadb.select_dict(
                self.table, DB_name, DB_ISIN, iban=self.iban)
        if transaction_isin == {}:
            self.footer = MESSAGE_TEXT['DATA_NO'].format(
                self.bank_name, self.iban)
        else:
            names_list = list(transaction_isin.keys())
            name_ = names_list[0]
            from_date = date(2000, 1, 1)
            to_date = date.today()
            while True:
                self.title = title
                input_isin = InputISIN(
                    title=self.title, header=MESSAGE_TEXT[self.header_key],
                    default_values=(name_, transaction_isin[name_], from_date,
                                    to_date),
                    names=transaction_isin)
                if input_isin.button_state == WM_DELETE_WINDOW:
                    return
                self.name_, self.isin, from_date, to_date = tuple(
                    list(input_isin.field_dict.values()))
                name_ = self.name_
                self.period = (from_date, to_date)
                self.title = ' '.join([title, self.name_])
                self._data_processing()

    def _data_processing(self):

        pass


class AcquisitionTable(Data_ISIN_Period):
    """
    TOP-LEVEL-WINDOW        Maintain Holding Acquisition Values

    PARAMETER:
        data        Array of HoldingAcquisition() instances
    """

    def _data_processing(self):

        while True:
            from_date, to_date = self.period
            acquisition_data = self._get_acquisition()
            if isinstance(acquisition_data, list):
                header = MESSAGE_TEXT['ACQUISITION_HEADER_TABLE'].format(
                    from_date, to_date)
                acquisition_table = PandasBoxAcquisitionTable(
                    self.title, header, self.bank_name, self.iban, self.isin, self.name_,
                    self.period, acquisition_data, self.mariadb)
                if acquisition_table.button_state == WM_DELETE_WINDOW:
                    break
            else:
                break

    def _get_acquisition(self):

        select_holding_acquisition_data = self.mariadb.select_holding_acquisition(
            iban=self.iban, isin=self.isin, period=self.period)
        if select_holding_acquisition_data:
            return select_holding_acquisition_data
        else:
            MessageBoxInfo(
                message=MESSAGE_TEXT['DATA_NO'].format(self.bank_name, self.iban))
            return None


class TransactionTable(Data_ISIN_Period):
    """
    Maintain transactions of ISIN in period
    """

    def _data_processing(self):

        while True:
            from_date, to_date = self.period
            transactions_data = self._get_transactions()
            if isinstance(transactions_data, list):
                self.title = ' '.join(
                    [self.bank_name, MENU_TEXT['Transactions Table'], self.name_])
                header = MESSAGE_TEXT['TRANSACTION_HEADER_TABLE'].format(
                    from_date, to_date)
                transaction_table = PandasBoxTransactionTable(
                    self.title, header, self.bank_name, self.iban, self.isin, self.name_, self.period, transactions_data, self.mariadb)
                if transaction_table.button_state == WM_DELETE_WINDOW:
                    break
            else:
                break

    def _get_transactions(self):

        select_transactions_data = self.mariadb.select_transactions_data(
            iban=self.iban, isin=self.isin, period=self.period)
        if select_transactions_data:
            return select_transactions_data
        else:
            TransactionNew(MESSAGE_TEXT['TRANSACTION_TITLE'].format(self.bank_name, self.name_),
                           self.iban, self.isin, self.name_, 0, select_transactions_data, self.mariadb)
            return None


class DataTransactionDetail(Data_ISIN_Period):
    """
    Show transactions of ISIN in period
    """

    def _data_processing(self):

        field_list = 'price_date, counter, transaction_type, price, pieces, posted_amount'

        if self.iban:
            select_isin_transaction = self.mariadb.select_transactions_data(
                field_list=field_list, iban=self.iban, isin=self.isin, period=self.period)
        else:
            select_isin_transaction = self.mariadb.select_transactions_data(
                field_list=field_list, isin=self.isin, period=self.period)
        if select_isin_transaction:
            count_transactions = len(select_isin_transaction)
            if self.iban:
                select_holding_ibans = [self.iban]
            else:
                select_holding_ibans = self.mariadb.select_holding_fields(
                    field_list=DB_iban)
            for iban in select_holding_ibans:
                select_isin_transaction = self._data_transaction_add_portfolio(
                    iban, select_isin_transaction)
            from_date, to_date = self.period
            title = ' '.join(
                [self.title, MESSAGE_TEXT['Period'].format(from_date, to_date)])
            PandasBoxTransactionDetail(title=title, dataframe=(count_transactions, select_isin_transaction),
                                       )
        else:
            self.footer = MESSAGE_TEXT['DATA_NO'].format(
                self.bank_name, self.iban)

    def _data_transaction_add_portfolio(self, iban, select_isin_transaction):

        # add portfolio position, adds not realized profit/loss to transactions
        select_holding_last = self.mariadb.select_holding_last(
            iban, self.isin, self.period, field_list='price_date, market_price, pieces, total_amount')
        if select_holding_last:
            if select_holding_last[0] < select_isin_transaction[-1][0]:
                return select_isin_transaction
            self.period = (self.period[0], select_holding_last[0])
            select_holding_last = (
                select_holding_last[0], 0, TRANSACTION_DELIVERY,  *select_holding_last[1:])
            select_isin_transaction.append(select_holding_last)
        return select_isin_transaction


class Download(Thread):
    """
    Download all Accounts of Bank
    """

    def __init__(self, mariadb, bank):
        super().__init__(name=bank.bank_name)
        self.bank = bank
        self.mariadb = mariadb

    def run(self):

        self.mariadb.all_accounts(self.bank)
