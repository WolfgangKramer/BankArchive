"""
Created on 09.12.2019
__updated__ = "2026-06-02"
Author: Wolfang Kramer
"""
import requests
import webbrowser

from time import sleep
from datetime import date, timedelta, datetime
from threading import Thread
from pandas import DataFrame

import banking.declarations as decl
import banking.declarations_mariadb as declm
import banking.message_handler as msg

from banking.services_file import PDFService
from banking.formatters import ShelveFormatter
from banking.connect_data import connectionresult
from banking.bank import InitBank, InitBankSync, InitBankAnonymous
from banking.formbuilts import (
    BuiltPandasBox, BuiltRadioButtons,
    destroy_widget,
    FileDialogue,
)
from banking.forms import (
    AlphaVantageParameter, AppCustomizing,
    BankDataChange, BankDataNew, BankDelete,
    InputISIN,
    InputDate, InputPeriod, InputDateHolding,
    InputIsins, InputDateTable, InputDateTransactions, InputDatePrices,
    PandasBoxLedgerCoaTable, PandasBoxLedgerTable,
    PandasBoxIsinComparision, PandasBoxIsinComparisionPercent,
    PandasBoxStatementTable, PandasBoxHoldingTable, PandasBoxIsinTable,
    PandasBoxStatementNoLedgerTable,
    PandasBoxHoldingPercent, PandasBoxTotals, PandasBoxTransactionDetail,
    PandasBoxHoldingPortfolios, PandasBoxBalanceAll, PandasBoxBalance,
    PandasBoxTransactionTable, PandasBoxTransactionTableShow, PandasBoxTransactionProfit,
    PandasBoxPrices, PandasBoxLedgerAccountCategory, PandasBoxPiecesConsistency,
    LedgerTableSearchRowBox, StatementTableSearchRowBox,
    PrintMessageCode,
    SelectFields, SelectLedgerAccount, SelectLedgerAccountCategory,
    SelectLedgerDailyBalanceAccounts, SelectDownloadPrices, SelectBuildHoldings,
    TechnicalIndicator,
    VersionTransaction,
)
from banking.scraper import AlphaVantage, BmwBank
from banking.services_file import FileService
from banking.trading_calendar import xetra_cls
from banking.utils import (
    application_store,
    date_days, dec2,
    dict_get_first_key,
    get_menu_text,
)

from functools import wraps


def _wrapper(before=None, after=None):
    """
    A decorator factory that allows executing functions (or methods)
    before and/or after the decorated method is called.

    Parameters:
        before (str or callable, optional):
            - If str: name of a method on `self` to call before execution.
            - If callable: a function that takes `self` and is executed before.
        after (str or callable, optional):
            - If str: name of a method on `self` to call after execution.
            - If callable: a function that takes `self` and is executed after.
    """

    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Execute the "before" hook if provided
            if isinstance(before, str):
                # Call method on the instance by name
                getattr(self, before)()
            elif callable(before):
                # Call the provided function with self
                before(self)

            # Execute the original method
            result = method(self, *args, **kwargs)

            # Execute the "after" hook if provided
            if isinstance(after, str):
                # Call method on the instance by name
                getattr(self, after)()
            elif callable(after):
                # Call the provided function with self
                after(self)

            # Return the original method's result
            return result

        return wrapper

    return decorator


def websites(site):

    webbrowser.open(site)


class BankProcessor:
    """
        Example
        processor = BankProcessor()

        processor.process("sparkasse")
        processor.process("ing")
    """

    def process_consors(self, title, iban, filename, repo):

        if filename:
            result = repo.import_transaction_consors(iban, filename)
            return result
        else:
            msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_TEXT_TRANSACTION_BANK_CSV'))

    def process_flatex(self, title, iban, filename, repo):

        if filename:
            result = repo.import_transaction_flatex(iban, filename)
            return result
        else:
            msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_TEXT_TRANSACTION_BANK_CSV'))

    def process_default(self, title, iban, filename, repo):

        if filename:
            result = repo.import_transaction(iban, filename)
            return result
        else:
            msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_TEXT_TRANSACTION'))

    def process(self, bank_name, title, iban, filename, repo):
        methods = {
            "Consors": self.process_consors,
            "BIW": self.process_flatex,
        }
        methods.get(bank_name, self.process_default)(title, iban, filename, repo)


class BaseWorkflow:

    def __init__(self,  title, repo, service, footer, progress):

        self.title = title
        self.repo = repo
        self.srv = service
        self.footer = footer
        self.progress = progress
        self.bank_names = self.repo.dictbank_names()
        self.bank_processor = BankProcessor()

    def _bank_data_scraper(self, bank_code):

        bank = self._bank_init(bank_code)
        get_accounts = bank.get_accounts()
        accounts = []
        for account in get_accounts:
            acc = {}
            account_product_name, owner_name, iban, account_number = account
            acc[decl.KEY_ACC_IBAN] = iban
            acc[decl.KEY_ACC_ACCOUNT_NUMBER] = account_number
            acc[decl.KEY_ACC_SUBACCOUNT_NUMBER] = None
            acc[decl.KEY_ACC_BANK_CODE] = bank_code
            acc[decl.KEY_ACC_OWNER_NAME] = owner_name
            acc[decl.KEY_ACC_PRODUCT_NAME] = account_product_name
            acc[decl.KEY_ACC_ALLOWED_TRANSACTIONS] = ['HKKAZ']
            accounts.append(acc)
        if get_accounts:
            data = [(decl.KEY_ACCOUNTS, accounts),
                    (decl.KEY_STORAGE_PERIOD, bank.storage_period),
                    (decl.KEY_MIN_PIN_LENGTH, 6),
                    (decl.KEY_MAX_PIN_LENGTH, 16)]
            self.repo.shelve_put_key(bank_code, data)

    def _bank_name(self, bank_code):

        bank_name = bank_code
        if bank_code in self.bank_names:
            bank_name = self.bank_names[bank_code]
        return bank_name

    def _bank_init(self, bank_code):

        if bank_code in list(decl.SCRAPER_BANKDATA.keys()):
            if bank_code == decl.BMW_BANK_CODE:
                bank = BmwBank()
        else:
            bank = InitBank(bank_code)
        return bank

    def _show_informations(self):
        """
        show informations of threads, if exist
        """
        # download transaction
        title = ' '.join([get_menu_text("Download"), get_menu_text("Transaction")])
        PrintMessageCode(title=title, header=msg.Informations.TRANSACTION_INFORMATIONS,
                         text=msg.Informations.transaction_informations)
        # downloaad prices
        title = ' '.join([get_menu_text("Download"), get_menu_text("Prices")])
        PrintMessageCode(title=title, header=msg.Informations.PRICES_INFORMATIONS,
                         text=msg.Informations.prices_informations)
        # download bankdata
        title = ' '.join([get_menu_text("Download"), get_menu_text("All_Banks")])
        PrintMessageCode(title=title, header=msg.Informations.BANKDATA_INFORMATIONS,
                         text=msg.Informations.bankdata_informations)
        # update market_price in holding
        title = ' '.join([get_menu_text("Update"), get_menu_text("Holding")])
        PrintMessageCode(title=title, header=msg.Informations.HOLDING_INFORMATIONS,
                         text=msg.Informations.holding_informations)

    def _delete_footer(self):

        try:
            self.footer.set('')
        except Exception:
            pass
        self._show_informations()

    def _show_message(self, bank, message=None):
        """
        show messages of FINTS dialogue
        """
        if msg.Informations.bankdata_informations:
            PrintMessageCode(text=msg.Informations.bankdata_informations)
            msg.Informations.bankdata_informations = ''
        if bank.warning_message:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'TASK_WARNING'))
        else:
            bank_name = self._bank_name(bank.bank_code)
            if message:
                self.footer.set(
                    ' '.join([message, '\n', msg.get_message(msg.MESSAGE_TEXT, 'TASK_DONE')]))
            else:
                self.footer.set(
                    ' '.join([bank_name, '\n', msg.get_message(msg.MESSAGE_TEXT, 'TASK_DONE')]))

        bank.warning_message = False


class DownloadWorkFlow(BaseWorkflow):

    def __init__(self, title, repo, service, footer, progress):

        super().__init__(title, repo, service, footer, progress)

    @_wrapper(before="_delete_footer", after="_show_informations")
    def all_banks(self):

        CANCELED = ''
        if application_store.get(declm.DB_threading):
            banks_credentials = self.repo.listbank_codes()
            banks_download = []
            for bank_code in banks_credentials:
                if self.repo.shelve_get_download_activated(bank_code):
                    # PIN input outside of Thread
                    bank = self._bank_init(bank_code)
                    if bank.scraper:
                        self.footer.set(
                            msg.get_message(
                                msg.MESSAGE_TEXT, 'CREDENTIALS_CHECK', self.bank_names[bank_code]
                                )
                            )
                        if bank.credentials():
                            banks_download.append(bank_code)
                        else:
                            msg.MessageBoxInfo(
                                msg.get_message(
                                    msg.MESSAGE_TEXT, 'CREDENTIALS', self.bank_names[bank_code]
                                    )
                                )
                        bank.logoff()
                    else:
                        self.footer.set(
                            msg.get_message(
                                msg.MESSAGE_TEXT, 'CREDENTIALS_CHECK', self.bank_names[bank_code]
                                )
                            )
                        if bank.dialogs._start_dialog(bank) not in decl.START_DIALOG_FAILED:
                            banks_download.append(bank_code)
                        else:
                            msg.MessageBoxInfo(
                                msg.get_message(
                                    msg.MESSAGE_TEXT, 'CREDENTIALS', self.bank_names[bank_code]
                                    )
                                )
            bank.opened_bank_code = None  # triggers bank opening messages
            self.progress.start()
            for bank_code in banks_download:
                bank = self._bank_init(bank_code)
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'DOWNLOAD_RUNNING', bank.bank_name))
                download_thread = Thread(
                    name=bank.bank_name, target=self.srv.all_accounts, args=(bank,))
                download_thread.start()
                seconds = 0
                while download_thread.is_alive() and seconds < 60:
                    sleep(1)
                    seconds += 1
                    self.progress.update_progressbar()
                if bank.scraper:
                    bank.logoff()
            self.progress.stop()
            self.footer.set(
                msg.get_message(msg.MESSAGE_TEXT, 'DOWNLOAD_DONE', CANCELED, 10 * '!'))
        else:
            for bank_code in self.repo.listbank_codes():
                if self.repo.shelve_get_download_activated(bank_code):
                    self._all_accounts(bank_code)
        self._show_informations()

    @_wrapper(before="_delete_footer", after="_show_informations")
    def all_accounts(self, bank_code):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        if bank:
            self.footer.set(
                msg.get_message(msg.MESSAGE_TEXT, 'DOWNLOAD_RUNNING', bank.bank_name))
            self.progress.start()
            self.srv.all_accounts(bank)
            if bank.scraper:
                bank.logoff()
            self.progress.stop()
            self.footer.set(
                msg.get_message(msg.MESSAGE_TEXT, 'DOWNLOAD_DONE', bank.bank_name, 10 * '!'))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def all_holdings(self, bank_code):

        bank = self._bank_init(bank_code)
        if bank:
            self.footer.set(
                msg.get_message(msg.MESSAGE_TEXT, 'DOWNLOAD_RUNNING', bank.bank_name))
            self.srv.all_holdings(bank)
            self.footer.set(
                msg.get_message(msg.MESSAGE_TEXT, 'DOWNLOAD_DONE', bank.bank_name, 10 * '!'))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def import_prices(self):

        title = ' '.join([get_menu_text("Download"), get_menu_text("Prices")])
        names = self.repo.isin_names_with_ticker()
        if names:
            download_prices = None
            while True:
                select_isins = SelectDownloadPrices(
                    title=title, checkbutton_texts=names)
                if select_isins.button_state == decl.WM_DELETE_WINDOW:
                    self._show_informations()
                    return
                state = select_isins.button_state
                field_list = select_isins.field_list
                if application_store.get(declm.DB_threading):
                    download_prices = Thread(name=get_menu_text("Prices"),
                                             target=self.srv.import_prices_and_corporate_actions,
                                             args=(title, field_list), kwargs={"state": state})
                    download_prices.start()
                else:
                    self.srv.import_prices_and_corporate_actions(title, field_list, state=state)
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'SYMBOL_MISSING_ALL', title))


class CustomizingWorkFlow(BaseWorkflow):

    def __init__(self,  title, repo, service, footer, progress):

        super().__init__(title, repo, service, footer, progress)

    @_wrapper(before="_delete_footer")
    def appcustomizing(self):
        """Handle application customization dialog loop."""
        field_dict = application_store.get(None)
        while True:
            app_data_box = AppCustomizing(field_dict)
            # Window closed
            if app_data_box.button_state == decl.WM_DELETE_WINDOW:
                return
            field_dict = app_data_box.field_dict
            if app_data_box.button_state == decl.BUTTON_SAVE:
                # Save changes to database
                field_dict[declm.DB_row_id] = 1
                self.repo.replace_application(field_dict)
                msg.MessageBoxInfo(
                    message=msg.get_message(msg.MESSAGE_TEXT, 'DATABASE_REFRESH')
                )
                raise msg.ExitBankMenu()
            elif app_data_box.button_state == decl.BUTTON_RESTORE:
                # Restore original values
                field_dict = application_store.get(None)
            elif app_data_box.button_state == decl.WM_DELETE_WINDOW:
                break

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_data_change(self, bank_code):

        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, get_menu_text("Customize"),
                          get_menu_text("Change Login Data")])
        login_data = self.repo.shelve_get_login_data(bank_code)
        bank_data_box = BankDataChange(
            title, bank_code, login_data)
        if bank_data_box.button_state == decl.WM_DELETE_WINDOW:
            return
        try:
            self.repo.shelve_put_bank_data(bank_code, bank_data_box.field_dict)
        except KeyError as key_error:
            msg.MessageBoxException(title, msg.get_message(msg.MESSAGE_TEXT, 'LOGIN', bank_code, key_error))
            return
        if bank_code in list(decl.SCRAPER_BANKDATA.keys()):
            self._bank_data_scraper(bank_code)
        else:
            self.bank_security_function(bank_code, False)

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_data_new(self):

        bank_codes = self.repo.get_server_codes()
        title = ' '.join([get_menu_text("Customize"), get_menu_text("New Bank")])
        if not self.repo.count_bankidentifier():
            msg.MessageBoxInfo(
                title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_CSV', declm.BANKIDENTIFIER.upper(), decl.NOT_ASSIGNED))
        elif not bank_codes:
            msg.MessageBoxInfo(
                title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_CSV', declm.SERVER.upper(), decl.NOT_ASSIGNED))
        else:
            bank_data_box = BankDataNew(
                title, bank_codes=bank_codes)
            if bank_data_box.button_state == decl.WM_DELETE_WINDOW:
                return
            bank_code = bank_data_box.field_dict[decl.KEY_BANK_CODE]
            try:
                self.repo.shelve_put_bank_data(bank_code, bank_data_box.field_dict)
            except KeyError as key_error:
                msg.MessageBoxException(
                    title,
                    msg.get_message(
                        msg.MESSAGE_TEXT, 'LOGIN', bank_code, key_error
                        )
                    )
                return
            bank_name = self.repo.shelve_get_bank_name(bank_code)
            if bank_code in list(decl.SCRAPER_BANKDATA.keys()):
                if bank_code == decl.BMW_BANK_CODE:
                    self._bank_data_scraper(decl.BMW_BANK_CODE)
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'BANK_DATA_NEW_SCRAPER', bank_name, bank_code
                        )
                    )
            else:
                self.bank_security_function(bank_code, True)
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'BANK_DATA_NEW', bank_name, bank_code
                        )
                    )
            raise msg.ExitBankMenu()  # to show new bank in menu after restart

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_data_delete(self):

        title = ' '.join([get_menu_text("Customize"), get_menu_text("Delete Bank")])
        deletebank = BankDelete(title)
        if deletebank.button_state == decl.WM_DELETE_WINDOW:
            return
        bank_code = deletebank.field_dict[decl.KEY_BANK_CODE]
        bank_name = deletebank.field_dict[decl.KEY_BANK_NAME]
        for table in [declm.STATEMENT, declm.LEDGER_STATEMENT, declm.HOLDING, declm.TRANSACTION]:
            if self.repo.iban_exists(table, bank_code):
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'BANK_DELETE_failed', bank_name, table.upper()
                        )
                    )
                return
        self.repo.shelve_delete(bank_code)
        self.bank_names.pop(bank_code, None)
        msg.MessageBoxInfo(
            title=title,
            message=msg.get_message(msg.MESSAGE_TEXT, 'BANK_DELETED', bank_name, bank_code))
        raise msg.ExitBankMenu()  # not show deleted bank in menu after restart

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_refresh_bpd(self, bank_code):

        bank = InitBankAnonymous(bank_code)
        bank.dialogs.anonymous(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join([bank_name, get_menu_text("Customize"),
                            get_menu_text("Refresh BankParameterData")])
        self._show_message(bank, message=message)

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_show_shelve(self, bank_code):

        title = f"{connectionresult.database.upper()} {self.bank_names[bank_code]} {get_menu_text('Customize')} {get_menu_text('Show Data')}"
        pdf = PDFService()
        pdf.add_page()
        pdf.add_heading(title, level=1)
        header = msg.get_message(msg.MESSAGE_TEXT, 'SHELVE', bank_code)
        pdf.add_heading(header, level=2)
        shelve_data = self.repo.shelve_get_shelve_keys(bank_code)
        formatter = ShelveFormatter(shelve_data, decl.SHELVE_KEYS)
        pdf.add_text(formatter.format())
        pdf.add_page()
        pdf.save()
        pdf.show()

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_show_all_shelve(self):

        title = f"{connectionresult.database.upper()} {get_menu_text('Customize')} {get_menu_text('Show All Data')}"
        pdf = PDFService()
        pdf.add_page()
        pdf.add_heading(title, level=1)
        shelve_keys = [
            decl.KEY_BANK_CODE, decl.KEY_BANK_NAME,
            decl.KEY_USER_ID, decl.KEY_PIN, decl.KEY_BIC,
            decl.KEY_SERVER, decl.KEY_ACCOUNTS
            ]
        for bank_code in self.bank_names:

            shelve_data = self.repo.shelve_get_shelve_keys(bank_code)
            header = msg.get_message(msg.MESSAGE_TEXT, 'SHELVE', bank_code)
            formatter = ShelveFormatter(shelve_data, shelve_keys,
                                        account_fields=[decl.KEY_ACC_IBAN, decl.KEY_ACC_OWNER_NAME, decl.KEY_ACC_PRODUCT_NAME])
            header = f"{connectionresult.database.upper()} {self.bank_names[bank_code]}"
            pdf.add_heading(header, level=2)
            pdf.add_text(formatter.format())
            pdf.add_page()
        pdf.save()
        pdf.show()

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_sync(self, bank_code):

        bank = InitBankSync(bank_code)
        bank.dialogs.sync(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join(
            [bank_name, get_menu_text("Customize"), get_menu_text("Synchronize")])
        self._show_message(bank, message=message)

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_version_transaction(self, bank_code):

        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, get_menu_text("Customize"),
                          get_menu_text("Change FinTS Transaction Version")])
        transaction_versions = self.repo.shelve_get_version_transaction(bank_code)
        transaction_version_box = VersionTransaction(
            title, bank_code, transaction_versions)
        if transaction_version_box.button_state == decl.WM_DELETE_WINDOW:
            return
        transaction_versions = {}
        for key in transaction_version_box.field_dict.keys():
            transaction_versions[key[2:5]
                                 ] = transaction_version_box.field_dict[key]
        data = (decl.KEY_VERSION_TRANSACTION, transaction_versions)
        self.repo.shelve_put_key(bank_code, data)

    @_wrapper(before="_delete_footer", after="_show_informations")
    def import_bankidentifier(self):

        title = get_menu_text("Import Bankidentifier CSV-File")
        msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_TEXT_BANKIDENTIFIER'))
        webbrowser.open(decl.BUNDESBANK_BLZ_MERKBLATT)
        webbrowser.open(decl.BUNDEBANK_BLZ_DOWNLOAD)
        file_dialogue = FileDialogue(title=title, filetypes='csv')
        if file_dialogue.filename not in ['', None]:
            result = self.repo.import_bankidentifier(file_dialogue.filename)
            if result is None:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'LOAD_DATA', file_dialogue.filename)
                    )
                data = self.repo.get_bankidentifier_data()
                dataframe = DataFrame(data)
                BuiltPandasBox(title=title, dataframe=dataframe)
            else:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_ERROR', file_dialogue.filename, result)
                    )

    @_wrapper(before="_delete_footer", after="_show_informations")
    def import_server(self):

        title = get_menu_text("Import Server CSV-File")
        msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_TEXT_SERVER'))
        webbrowser.open(decl.FINTS_SERVER_ADDRESS)
        file_dialogue = FileDialogue(title=title, filetypes='csv')
        if file_dialogue.filename not in ['', None]:
            result = self.repo.import_server(file_dialogue.filename)
            if result is None:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'LOAD_DATA', file_dialogue.filename)
                    )
                data = self.repo.get_server_data()
                dataframe = DataFrame(data)
                BuiltPandasBox(title=title, dataframe=dataframe)
            else:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_ERROR', file_dialogue.filename, result)
                    )

    @_wrapper(before="_delete_footer", after="_show_informations")
    def import_tickers(self):

        title = get_menu_text("Import Ticker Symbols")
        msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_TEXT_TICKER'))
        webbrowser.open(decl.TICKER_ADDRESS)
        file_dialogue = FileDialogue(title=title, filetypes='zip')  # zip file
        if file_dialogue.filename not in ['', None]:
            csv_file = FileService.spreadsheet_zip_to_csv(file_dialogue.filename)  # convert to csv file
            result = self.repo.import_tickers(csv_file)
            if result is None:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'LOAD_DATA', file_dialogue.filename)
                    )
                data = self.repo.get_tickers_data()
                dataframe = DataFrame(data)
                BuiltPandasBox(title=title, dataframe=dataframe)
            else:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_ERROR', file_dialogue.filename, result)
                    )

    @_wrapper(before="_delete_footer", after="_show_informations")
    def bank_security_function(self, bank_code, new):
        """
        Parameter: new ... create bpd data of new bank
        """
        if new:
            bank = InitBankAnonymous(bank_code)
            bank.dialogs.anonymous(bank)
        security_function_dict = {}
        default_value = None

        for twostep in self.repo.shelve_get_twostep(bank_code):
            security_function, security_function_name = twostep
            security_function_dict[security_function] = security_function_name
            if (self.repo.shelve_get_security_function(bank_code) and self.repo.shelve_get_key(bank_code, decl.KEY_SECURITY_FUNCTION)[0:3] == security_function[0:3]):
                default_value = security_function
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, get_menu_text("Customize"),
                          get_menu_text("Change Security Function")])
        if new:
            security_function_box = BuiltRadioButtons(
                title=title,
                header=msg.get_message(msg.MESSAGE_TEXT, 'TWOSTEP'),
                default_value=default_value,
                button2_text=None,
                radiobutton_dict=security_function_dict)
        else:
            security_function_box = BuiltRadioButtons(
                title=title,
                header=msg.get_message(msg.MESSAGE_TEXT, 'TWOSTEP'),
                default_value=default_value,
                radiobutton_dict=security_function_dict)
        if security_function_box.button_state == decl.WM_DELETE_WINDOW:
            return
        if security_function_box.button_state == decl.BUTTON_SAVE:
            data = (decl.KEY_SECURITY_FUNCTION, security_function_box.field[0:3])
            self.repo.shelve_put_key(bank_code, data)
        self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'SYNC_START', bank_name))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def reset(self):

        self.repo.reset_geometry()
        self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'TASK_DONE'))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def alpha_vantage_refresh(self):

        self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_REFRESH_RUN'))
        refresh = self.alpha_vantage.refresh()
        if refresh:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_REFRESH'))
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_ERROR'))


class DatabaseWorkFlow(BaseWorkflow):

    def __init__(self,  title, repo, service, footer, progress):

        super().__init__(title, repo, service, footer, progress)

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_holding_performance(self, bank_name, iban):

        _data_holding_performance = None
        title = ' '.join([bank_name, get_menu_text("Holding Performance")])
        data_dict = {}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if isinstance(_data_holding_performance, BuiltPandasBox):
                destroy_widget(_data_holding_performance.dataframe_window)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            if bank_name == decl.FN_ALL_BANKS:
                select_holding_total = self.repo.select_holding_total(
                    period=(data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE]))
            else:
                select_holding_total = self.repo.select_holding_total_of_iban(
                    iban=iban, period=(data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE]))
            if select_holding_total:
                title_period = ' '.join([title, ' ',
                                         msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])])
                while True:
                    table = PandasBoxHoldingPortfolios(
                        title=title_period, dataframe=select_holding_total, mode=decl.NUMERIC)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', bank_name, iban))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_holding_isin_comparision(self, bank_name, iban):

        title = ' '.join([bank_name, get_menu_text("Holding ISIN Comparision")])
        data_dict = {}
        data_dict_isins = {}
        while True:
            input_period = InputPeriod(
                title=title, data_dict=data_dict, selection_name=title + 'A')
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict_period = input_period.field_dict
            period = (data_dict_period[decl.FN_FROM_DATE],
                      data_dict_period[decl.FN_TO_DATE])
            if iban:
                isin_dict = self.repo.get_isin_dict_of_iban(iban=iban, period=period)
            else:
                isin_dict = self.repo.get_isin_dict(period=period)
            if isin_dict:
                input_isins = InputIsins(table=isin_dict, selection_name=title + 'B',
                                         title=title, data_dict=data_dict_isins, separator=[decl.FN_COMPARATIVE])
                if input_isins.button_state == decl.WM_DELETE_WINDOW:
                    return
                data_dict_isins = input_isins.field_dict
                selected_isins = list(
                    filter(lambda x: data_dict_isins[x] == 1, list(data_dict_isins.keys())))
                # more than one isin selected
                if len(selected_isins) > 1:
                    if data_dict_isins[decl.FN_COMPARATIVE] == decl.FN_PROFIT_LOSS:
                        db_fields = [declm.DB_name, declm.DB_price_date,
                                     ''.join([declm.DB_total_amount, '-', declm.DB_acquisition_amount, ' AS ', decl.FN_PROFIT_LOSS])]
                    else:
                        db_fields = [declm.DB_name, declm.DB_price_date,
                                     data_dict_isins[decl.FN_COMPARATIVE]]
                    if iban:
                        selected_holding_data = self.repo.select_holding_data_of_iban(
                            field_list=db_fields, iban=iban, selected_isins=selected_isins,
                            period=period)
                    else:
                        selected_holding_data = self.repo.select_holding_data(
                            field_list=db_fields, selected_isins=selected_isins, period=period)
                    if selected_holding_data:
                        self.footer.set('')
                        title_period = ' '.join(
                            [title,
                             data_dict_isins[decl.FN_COMPARATIVE].upper(),
                             msg.get_message(
                                 msg.MESSAGE_TEXT, 'PERIOD', period[0], period[1]
                                 )
                             ]
                            )
                        while True:
                            table = PandasBoxIsinComparision(title=title_period, dataframe=(
                                data_dict_isins[decl.FN_COMPARATIVE], selected_holding_data),
                                dataframe_typ=decl.TYP_DECIMAL, mode=decl.NUMERIC)
                            if table.button_state == decl.WM_DELETE_WINDOW:
                                break
                    else:
                        self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'FIELDLIST_INTERSECTION_EMPTY'))
                else:
                    self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'FIELDLIST_MIN', "2"))
            else:
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', bank_name, iban))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_holding_isin_comparision_percent(self, bank_name, iban):
        """
        Name, price_date, comparision_field of isins
        in their maximum common time interval in a given period
        """
        title = ' '.join([bank_name, get_menu_text("Holding ISIN Comparision %")])
        data_dict = {}
        data_dict_isins = {}
        while True:
            input_period = InputPeriod(
                title=title, data_dict=data_dict, selection_name=title + 'A')
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            if iban:
                isin_dict = self.repo.get_isin_dict_of_iban(iban=iban, period=period)
            else:
                isin_dict = self.repo.get_isin_dict(period=period)
            if isin_dict:
                input_isins = InputIsins(table=isin_dict, selection_name=title + 'B',
                                         title=title, data_dict=data_dict_isins, separator=[decl.FN_COMPARATIVE])
                if input_isins.button_state == decl.WM_DELETE_WINDOW:
                    return
                data_dict_isins = input_isins.field_dict
                selected_isins = list(
                    filter(lambda x: data_dict_isins[x] == 1, list(data_dict_isins.keys())))
                # more than one isin selected
                if len(selected_isins) > 1:
                    from_date, to_date, data = self.repo.select_holding_isins_interval(
                        iban, data_dict_isins[decl.FN_COMPARATIVE], selected_isins, period=period)
                    if data:
                        self.footer.set('')
                        title_period = ' '.join(
                            [title,
                             data_dict_isins[decl.FN_COMPARATIVE].upper(),
                             msg.get_message(
                                 msg.MESSAGE_TEXT, 'PERIOD', from_date, to_date
                                 )
                             ]
                            )
                        while True:
                            table = PandasBoxIsinComparisionPercent(title=title_period, dataframe=(
                                data_dict_isins[decl.FN_COMPARATIVE], data),
                                dataframe_typ=decl.TYP_DECIMAL, mode=decl.NUMERIC)
                            if table.button_state == decl.WM_DELETE_WINDOW:
                                break
                    else:
                        self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'FIELDLIST_INTERSECTION_EMPTY'))
                else:
                    self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'FIELDLIST_MIN', "2"))
            else:
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', bank_name, iban))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_isin_table(self):

        title = ' '.join([get_menu_text("Database"), get_menu_text("ISIN Table")])
        selected_row = 0
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        while True:
            data = self.repo.select_isin_table()
            isin_table = PandasBoxIsinTable(
                title, data, message, mode=decl.EDIT_ROW, selected_row=selected_row)
            selected_row = isin_table.selected_row
            message = isin_table.message
            if isin_table.button_state == decl.WM_DELETE_WINDOW:
                break
            if isin_table.button_state == decl.BUTTON_PRICES_IMPORT:
                self.srv.import_prices_and_corporate_actions(title, [isin_table.selected_row_dict[declm.DB_name]], state=decl.BUTTON_REPLACE)
            self._show_informations()

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_holding_table(self, bank_name, iban):

        title = ' '.join([bank_name,
                          get_menu_text("Holding Table")])
        data_dict = {}
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        while True:
            date_holding_view = InputDateTable(
                title=title, data_dict=data_dict, table=declm.HOLDING_VIEW)
            if date_holding_view.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = date_holding_view.field_dict
            selected_check_button = list(
                filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
            period = ' '.join(
                [data_dict[decl.FN_FROM_DATE], '-', data_dict[decl.FN_TO_DATE]])
            title_period = ' '.join([title, period])

            data = self.repo.select_holding_view_table_of_iban(
                field_list=[declm.DB_iban, declm.DB_price_date, declm.DB_ISIN] + selected_check_button,
                iban=iban, period=(data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE]))
            if data:
                while True:
                    holding_table = PandasBoxHoldingTable(
                        title_period, data, message, iban, mode=decl.EDIT_ROW)
                    message = holding_table.message
                    if holding_table.button_state == decl.WM_DELETE_WINDOW:
                        break


    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_insert_holding_from_transaction(self, bank_name, iban):
        title = ' '.join(
            [bank_name, get_menu_text("Insert Holding Positions from Transactions")])
        name_isin_code = self.repo.get_transactions_name_isin_of_iban(iban)
        if name_isin_code:
            names = list(name_isin_code.keys())
            while True:
                select_isins = SelectBuildHoldings(title=title, checkbutton_texts=names)
                if select_isins.button_state == decl.WM_DELETE_WINDOW:
                    self._show_informations()
                    return
                field_list = select_isins.field_list
                for seleted_isin_name in field_list:
                    isin_code = name_isin_code[seleted_isin_name]
                    self.srv.build_holdings(title, select_isins.button_state, iban, isin_code)
     

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_update_holding_and_prices(self, bank_name, iban):
        """
        For a working day:
        Replaces market_price (table declm.HOLDING) by close price (table declm.PRICES)
        If not existing: creates holding positions
        """
        title = ' '.join(
            [bank_name, get_menu_text("Update Holding Market Price by Closing Price")])
        while True:
            input_date = InputDate(title=title)
            if input_date.button_state == decl.WM_DELETE_WINDOW:
                return
            if input_date:
                date_day = input_date.field_dict[decl.FN_DATE]
            if date_days.isweekend(date_day):
                msg.MessageBoxInfo(
                    title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'DATE_NO_WORKDAY', date_day))
            break
        holdings = self.repo.select_holding_view_table_of_iban(
                field_list='*', iban=iban, period=(date_day, date_day))
        if not holdings:  # duplicate holding positions
            message_box_ask = msg.MessageBoxAsk(
                title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'HOLDING_INSERT', date_day))
            if message_box_ask.result:
                price_date = self.repo.holding_max_date(to_date=date_day)
                holdings = self.repo.select_holding_table_of_iban(
                    field_list='*', period=(price_date, price_date), iban=iban)
                for holding_dict in holdings:
                    holding_dict[declm.DB_price_date] = date_day
                    holding_dict[declm.DB_origin] = decl.ORIGIN_INSERTED
                    self.repo.insert_holding(holding_dict)

                    msg.holding_informations_append(
                        decl.INFORMATION,
                        ' '.join(
                            ['\n',
                             bank_name,
                             msg.get_message(
                                 msg.MESSAGE_TEXT, 'HOLDING_INSERT', date_day
                                 ),
                             '\n',
                             holding_dict[declm.DB_ISIN],
                             '\n']
                            )
                        )
            else:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'DATA_NO',
                        declm.HOLDING.upper(),
                        (date_days.convert_to_str(decl.START_DATE_HOLDING), date_day)
                        )
                    )
                return
            holdings = self.repo.select_holding_view_table_of_iban(
                    field_list='*', iban=iban, period=(date_day, date_day))
        if holdings:  # update holding positions
            for holding_dict in holdings:
                title_download = ' '.join(
                    [title, get_menu_text("Download"), get_menu_text("Prices")])
                result = self._data_update_holding_price(
                    title_download, bank_name, iban, holding_dict)
                if not result:
                    origin_symbol = self.repo.select_isin_scalar(declm.DB_origin_symbol, isin_code=holding_dict[declm.DB_ISIN])
                    msg.holding_informations_append(
                        decl.WARNING,
                        msg.get_message(
                            msg.MESSAGE_TEXT, 'PRICES_NO',
                            ' '.join(
                                [
                                    '\n', bank_name, declm.HOLDING.upper(),
                                    declm.DB_price_date.upper(),
                                    date_days.convert(holding_dict[declm.DB_price_date])
                                    ]
                                ),
                            holding_dict[declm.DB_symbol],
                            origin_symbol,
                            holding_dict[declm.DB_ISIN],
                            holding_dict[declm.DB_name]
                            )
                        )
            self.repo.update_total_holding_amount(
                iban=iban, period=(date_day, date_day))

    def _data_update_holding_price(self, title, bank_name, iban, holding_dict):
        """
        Imports prices
        Updates market_price, total_amount
        """
        price = self.repo.get_close_price(holding_dict[declm.DB_ISIN], holding_dict[declm.DB_price_date])
        if not price:
            # import price data
            self.srv.import_prices_and_corporate_actions(title, [holding_dict[declm.DB_name]], state=decl.BUTTON_APPEND)
        price_close = self.repo.get_close_price(holding_dict[declm.DB_ISIN], holding_dict[declm.DB_price_date])
        if price_close:
            # update holding market price
            field_dict = {}
            field_dict[declm.DB_market_price] = price_close
            field_dict[declm.DB_total_amount] = dec2.multiply(
                field_dict[declm.DB_market_price], holding_dict[declm.DB_pieces])
            field_dict[declm.DB_origin] = decl.ORIGIN_PRICES
            self.repo.update_holding(iban, holding_dict[declm.DB_price_date], holding_dict[declm.DB_ISIN], field_dict)
            msg.holding_informations_append(
                decl.INFORMATION, ' '.join([
                    '\n',
                    bank_name,
                    declm.DB_ISIN.upper(),
                    holding_dict[declm.DB_ISIN],
                    holding_dict[declm.DB_name],
                    '\n          ',
                    declm.DB_price_date.upper(),
                    date_days.convert_to_str(holding_dict[declm.DB_price_date]),
                    '\n'
                    ])
                )
            return True
        return False

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_technical_indicators(self):
        """
        def destroy_withdrawn():
            for widget in root.winfo_children():
                if isinstance(widget, Toplevel):
                    if not widget.winfo_viewable():  # = withdrawn oder iconified
                        widget.destroy()
        """
        title = get_menu_text("Technical Indicators")
        data_dict = {decl.FN_FROM_DATE: date_days.subtract(date.today(), 360),
                     decl.FN_TO_DATE: date.today()}
        names = self.repo.isin_names_with_ticker()
        while True:
            ta_data = TechnicalIndicator(
                title=title, data_dict=data_dict, selection_name=title, container=names)
            if ta_data.button_state == decl.WM_DELETE_WINDOW:
                break
            data_dict[declm.DB_ISIN] = ta_data.field_dict[declm.DB_ISIN]
            data_dict[declm.DB_name] = ta_data.field_dict[declm.DB_name]
            data_dict[decl.FN_FROM_DATE] = ta_data.field_dict[decl.FN_FROM_DATE]
            data_dict[decl.FN_TO_DATE] = ta_data.field_dict[decl.FN_TO_DATE]

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_transaction_detail(self, bank_name, iban):

        title = ' '.join([bank_name,
                          get_menu_text("Transaction Detail")])
        data_dict = {}  # If empty, then the last input will be used.
        while True:
            date_transations = InputDateTransactions(
                title=title, data_dict=data_dict, upper=[declm.DB_name])
            if date_transations.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = date_transations.field_dict
            if not data_dict or decl.FN_FROM_DATE not in data_dict:  # when the menu is accessed multiple times
                break
            title_period = ' '.join(
                [title, data_dict[decl.FN_FROM_DATE], '-', data_dict[decl.FN_TO_DATE]])
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            isin_code = self.repo.get_isin_of_name(data_dict[declm.DB_name])
            if iban:
                select_isin_transaction = self.srv.get_transaction_overview(
                    isin_code, period, iban, data_dict[decl.FN_COST_METHOD])
            else:
                select_holding_ibans = self.repo.get_iban_of_transactions(period)
                select_isin_transaction = []
                for _iban in select_holding_ibans:
                    _iban = _iban[0]
                    result = self.srv.get_transaction_overview(
                        isin_code, period, _iban, data_dict[decl.FN_COST_METHOD])
                    select_isin_transaction.extend(result)
            if select_isin_transaction:
                title_period = '   '.join(
                    [title, data_dict[declm.DB_name], data_dict[decl.FN_COST_METHOD], msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])])
                while True:

                    table = PandasBoxTransactionDetail(title=title_period, dataframe=select_isin_transaction, mode=decl.NO_CURRENCY_SIGN)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
                    else:
                        self.footer.set(
                            msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', bank_name, iban))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_transaction_table(self, bank_name, iban):

        title = ' '.join([bank_name,
                          get_menu_text("Transactions T able")])
        names = self.repo.isin_names()
        data_dict = {}
        while True:
            input_isin = InputISIN(title=title, data_dict=data_dict, container=names)
            if input_isin.button_state == decl.WM_DELETE_WINDOW:
                return
            isin = data_dict[declm.DB_ISIN] = input_isin.field_dict[declm.DB_ISIN]
            name = data_dict[declm.DB_name] = input_isin.field_dict[declm.DB_name]
            from_date = data_dict[decl.FN_FROM_DATE] = input_isin.field_dict[decl.FN_FROM_DATE]
            to_date = data_dict[decl.FN_TO_DATE] = input_isin.field_dict[decl.FN_TO_DATE]
            title_period = ' '.join(
                [title, name, isin, from_date, '-', to_date])
            message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
            while True:
                data = self.repo.get_transactions_of_iban_isin_code(iban, isin, (from_date, to_date))
                transaction_table = PandasBoxTransactionTable(
                    title_period, data, message, iban, isin, name, mode=decl.EDIT_ROW)
                message = transaction_table.message
                if transaction_table.button_state == decl.WM_DELETE_WINDOW:
                    break

    @_wrapper(before="_delete_footer", after="_show_informations")
    def data_prices(self, sign):

        if sign:
            title = get_menu_text("Prices ISINs") + ' %'
        else:
            title = get_menu_text("Prices ISINs")
        data_dict = {}
        if not self.repo.count_prices():
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'PRICES_EMPTY'))
            return
        while True:
            while True:
                date_prices = InputDatePrices(title=title, data_dict=data_dict)
                if date_prices.button_state == decl.WM_DELETE_WINDOW:
                    return
                data_dict = date_prices.field_dict
                selected_check_button = list(
                    filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
                db_fields = list(declm.TABLE_FIELDS_PROPERTIES[declm.PRICES].keys())
                # intersection: price fields of table declm.PRICES
                selected_fields = list(set(db_fields) & set(selected_check_button))
                selected_isins = list(set(db_fields) ^ set(
                    selected_check_button))  # symetric_difference: selected isin_codes
                if selected_fields and selected_isins:
                    isin_name = self.repo.get_name_of_isin_code(selected_isins)
                    if isin_name:
                        self.srv.import_prices_and_corporate_actions(title, [isin_name], state=decl.BUTTON_APPEND)
                    break
                else:
                    msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'SELECT_INCOMPLETE'))
            select_data = self.repo.get_selected_price_data(
                selected_fields,
                selected_isins,
                (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
                )
            select_origin_dict = self.repo.get_name_origin_symbol(selected_isins)
            if select_data:
                self.footer.set('')
                period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
                while True:
                    price_table = PandasBoxPrices(title=f"""{title} {str(period)}""", dataframe=(
                        selected_fields, select_data, select_origin_dict, sign), dataframe_typ=decl.TYP_DECIMAL, mode=decl.NUMERIC)
                    if price_table.button_state == decl.WM_DELETE_WINDOW:
                        break
            else:
                msg.MessageBoxInfo(title=title, message=msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', ', '.join(selected_isins), ''))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def import_transaction(self, bank_name, iban):
        """
        import transactions from CSV_File.
        """
        title = ' '.join([bank_name, get_menu_text("Import Transactions")])
        self.bank_processor.process(bank_name, title, iban, None, None)
        file_dialogue = FileDialogue(title=title)
        if file_dialogue.filename not in ['', None]:
            last_price_date = self.repo.get_max_price_date_of_transaction(iban)
            if not last_price_date:
                last_price_date = decl.START_DATE_TRANSACTIONS
            result = self.bank_processor.process(bank_name, title, iban, file_dialogue.filename, self.repo)
            if result is None:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'LOAD_DATA', file_dialogue.filename)
                    )
                data = self.repo.get_transaction_data_of_iban_from_date(iban, last_price_date)
                if data:
                    dataframe = DataFrame(data)
                    BuiltPandasBox(title=title, dataframe=dataframe)
                else:
                    msg.MessageBoxInfo(
                        title=title,
                        message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_ALREADY', file_dialogue.filename)
                        )
            else:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_ERROR', file_dialogue.filename, result)
                    )

    @_wrapper(before="_delete_footer", after="_show_informations")
    def transactions_pieces(self, bank_name, iban):

        title = ' '.join([bank_name, get_menu_text("Check Transactions Pieces")])
        price_dates = self.repo.get_price_dates_of_transactions(iban=iban)
        if price_dates:
            for price_date in price_dates:
                price_date = date_days.convert_to_str(price_date[0])
                result = self.repo.check_pieces_consistency_for_iban(
                    iban, price_date)
                if result:
                    title_period = ' '.join(
                        [title, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', decl.START_DATE_TRANSACTIONS, price_date)])
                    table = PandasBoxPiecesConsistency(
                        dataframe=result, title=title_period, cellwidth_resizeable=False, mode=decl.EDIT_ROW)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
        else:
            msg.MessageBoxInfo(title=title,
                               message=msg.get_message(
                                   msg.MESSAGE_TEXT,
                                   'TRANSACTION_CHECK',
                                   'NO '
                                   )
                               )
    @_wrapper(before="_delete_footer", after="_show_informations")
    def transactions_profit(self, bank_name, iban):

        title = ' '.join(
            [bank_name, get_menu_text("Profit of closed Transactions")])
        data_dict = {}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            self.transactions_profit_closed(
                title, iban, data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
    @_wrapper(before="_delete_footer", after="_show_informations")
    def transactions_profit_closed(self, title, iban, from_date, to_date):

        result = self.repo.transaction_profit_closed(iban, (from_date, to_date))
        if result:
            title_period = ' '.join(
                [title, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', from_date, to_date)])
            while True:
                table = PandasBoxTransactionProfit(
                    title=title_period, dataframe=list(result), mode=decl.NO_CURRENCY_SIGN,
                    cellwidth_resizeable=False)
                if table.button_state == decl.WM_DELETE_WINDOW:
                    break

        else:
            msg.MessageBoxInfo(title=title,
                               message=msg.get_message(
                                   msg.MESSAGE_TEXT,
                                   'TRANSACTION_CLOSED_EMPTY',
                                   from_date,
                                   to_date
                                   )
                               )
    @_wrapper(before="_delete_footer", after="_show_informations")
    def transactions_profit_all(self, bank_name, iban):

        title = ' '.join(
            [bank_name, get_menu_text("Profit Transactions incl. current Depot Positions")])
        data_dict = {}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            result = self.repo.transaction_profit_all(iban, (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE]))
            if result:
                title_period = ' '.join(
                    [title, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])])
                while True:
                    table = PandasBoxTransactionProfit(
                        title=title_period, dataframe=list(result), mode=decl.NO_CURRENCY_SIGN,
                        cellwidth_resizeable=False)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
            else:
                msg.MessageBoxInfo(
                    title=title,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'TRANSACTION_NO', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE]
                        )
                    )
                self._transactions_profit_closed(
                    bank_name, iban, data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
    @_wrapper(before="_delete_footer", after="_show_informations")
    def update_holding_total_amount_portfolio(self, bank_name, iban):
        """
        Update Table holding total_amount_portfolio
        """
        title = ' '.join(
            [bank_name, iban, get_menu_text("Update Portfolio Total Amount")])
        data_dict = {decl.FN_FROM_DATE:  date.today(), decl.FN_TO_DATE: date.today()}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            self.repo.update_total_holding_amount(iban=iban, period=period)
            self.footer.set(' '.join(
                [msg.get_message(msg.MESSAGE_TEXT, 'TASK_DONE'),  "\n", get_menu_text('Update Portfolio Total Amount'),
                 "\n", bank_name, iban,   msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])]
                )
            )


class ShowWorkFlow(BaseWorkflow):

    def __init__(self,  title, repo, service, footer, progress):

        super().__init__(title, repo, service, footer, progress)
        if application_store.get(declm.DB_alpha_vantage):
            self.alpha_vantage_function = self.repo.get_alpha_vantage_functions()
            self.alpha_vantage_parameter = self.repo.get_alpha_vantage_parameters()
            self.alpha_vantage = AlphaVantage(progress, self.alpha_vantage_function, self.alpha_vantage_parameter)
        self.bank_owner_account = self.repo.get_bank_owner_accounts()
    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_alpha_vantage(self):

        title = get_menu_text("Alpha Vantage")
        alpha_vantage_symbols = self.repo.get_alpha_vantage_tickers()
        alpha_vantage_names = list(alpha_vantage_symbols.keys())
        function_list = self.repo.get_alpha_vantage_functions()
        parameter_dict = self.repo.get_alpha_vantage_parameters()
        field_list = []
        while True:
            checkbutton = SelectFields(
                title=title,
                button2_text=None, button3_text=None, button4_text=None, default_texts=field_list,
                checkbutton_texts=function_list)
            if checkbutton.button_state == decl.WM_DELETE_WINDOW:
                return
            field_list = checkbutton.field_list
            dataframe = None
            for function in checkbutton.field_list:
                default_values = []
                while True:
                    title_function = ' '.join([title, function])
                    parameters = AlphaVantageParameter(
                        title_function, function, application_store.get(declm.DB_alpha_vantage),
                        parameter_dict[function], default_values,
                        alpha_vantage_names)
                    if parameters.button_state == decl.WM_DELETE_WINDOW:
                        break
                    elif parameters.button_state == get_menu_text("ISIN Table"):
                        self._data_isin_table()
                        return
                    elif parameters.button_state == decl.BUTTON_ALPHA_VANTAGE:
                        websites(decl.ALPHA_VANTAGE_DOCUMENTATION)
                    else:
                        default_values = list(parameters.field_dict.values())
                        url = 'https://www.alphavantage.co/query?function=' + function
                        for key, value in parameters.field_dict.items():
                            if value:
                                if key.lower() == declm.DB_symbol:
                                    value = alpha_vantage_symbols[value]
                                api_parameter = ''.join(
                                    ['&', key.lower(), '=', value])
                                url = url + api_parameter
                        try:
                            data_json = requests.get(url).json()
                        except Exception:
                            msg.MessageBoxException(title, msg.get_message(msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_ERROR'))
                            break
                        key_list = list(data_json.keys())
                        if decl.JSON_KEY_META_DATA in data_json.keys():
                            if isinstance(dataframe, DataFrame):
                                dataframe_next = DataFrame(
                                    data_json[key_list[1]]).T
                                dataframe = dataframe.join(dataframe_next)
                            else:
                                dataframe = DataFrame(
                                    data_json[key_list[1]]).T
                        elif decl.JSON_KEY_ERROR_MESSAGE in data_json.keys():
                            msg.MessageBoxInfo(
                                title=title_function,
                                message=msg.get_message(
                                    msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_ERROR_MSG',
                                    data_json[decl.JSON_KEY_ERROR_MESSAGE], url
                                    )
                                )
                        elif data_json == {}:
                            msg.MessageBoxInfo(
                                title=title_function,
                                message=msg.get_message(
                                    msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_NO_DATA', url
                                    )
                                )
                        else:
                            websites(url)
                        break
            if isinstance(dataframe, DataFrame):
                title_function = ' '.join([title_function, url])
                while True:
                    table = BuiltPandasBox(
                        title=title_function, dataframe=dataframe,
                        mode=decl.NUMERIC)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_alpha_vantage_search_symbol(self):

        function = 'SYMBOL_SEARCH'
        title = get_menu_text("Alpha Vantage Symbol Search")
        while True:
            parameters = AlphaVantageParameter(
                title, function, application_store.get(declm.DB_alpha_vantage),
                self.alpha_vantage.parameter_dict[function], [], [])
            if parameters.button_state == decl.WM_DELETE_WINDOW:
                break
            elif parameters.button_state == get_menu_text("ISIN Table"):
                self._data_isin_table()
            elif parameters.button_state == decl.BUTTON_ALPHA_VANTAGE:
                websites(decl.ALPHA_VANTAGE_DOCUMENTATION)
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
                    msg.MessageBoxException(title, msg.get_message(msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_ERROR'))
                    break
                if decl.JSON_KEY_ERROR_MESSAGE in data_json.keys():
                    msg.MessageBoxInfo(
                        title=title,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_ERROR_MSG', data_json[decl.JSON_KEY_ERROR_MESSAGE], url
                            )
                        )
                elif data_json == {}:
                    msg.MessageBoxInfo(
                        title=title,
                        message=msg.get_message(msg.MESSAGE_TEXT, 'ALPHA_VANTAGE_NO_DATA', url)
                        )
                else:
                    websites(url)
    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_balances_all_banks(self):

        title = ' '.join([get_menu_text("Show"), get_menu_text("Balances")])
        total_df = []
        if self.bank_names != {}:
            bank_accounts_missed = ''
            for bank_name in self.bank_names.values():
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                balance_accounts = self.repo.shelve_get_accounts(bank_code)
                if not balance_accounts:
                    bank_accounts_missed = f"{bank_accounts_missed} ({bank_name})  "
                    message = msg.get_message(msg.MESSAGE_TEXT, 'BANK_DATA_ACCOUNTS_MISSED', bank_accounts_missed)
                    self.footer.set(message)
                else:
                    bank_balances = self.srv.get_balances(balance_accounts)
                    if bank_balances:
                        dataframe = DataFrame(bank_balances)
                        dataframe.insert(0, decl.KEY_BANK_NAME, bank_name)
                        dataframe = dataframe.sort_values(by=[decl.KEY_BANK_NAME, decl.KEY_ACC_OWNER_NAME])
                        total_df.append(dataframe)
            if total_df:
                title = f"""{title} {date_days.today()}"""
                PandasBoxBalanceAll(title=title, dataframe=total_df,
                                    mode=decl.CURRENCY_SIGN,
                                    cellwidth_resizeable=False)
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, ''))
    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_balances(self, bank_code, bank_name, owner_name=None):

        title = ' '.join([bank_name, get_menu_text("Show"), get_menu_text("Balances")])
        balance_accounts = self.repo.shelve_get_accounts(bank_code)
        if not balance_accounts:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, ''))
            return
        bank_balances = self.srv.get_balances(balance_accounts)
        if bank_balances:
            if owner_name:
                bank_balances = [d for d in bank_balances if d.get(decl.KEY_ACC_OWNER_NAME) == owner_name]
                title = f"""{title}  date_days.today()"""
            dataframe = DataFrame(bank_balances)
            dataframe = dataframe.sort_values(by=decl.KEY_ACC_OWNER_NAME)
            title = f"""{title} {date_days.today()}"""
            PandasBoxBalance(title=title, dataframe=dataframe, dataframe_sum=[
                             decl.FN_BALANCE, declm.DB_opening_balance], mode=decl.CURRENCY_SIGN,
                             cellwidth_resizeable=False)
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, ''))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_statements(self, bank_code, account):

        iban = account[decl.KEY_ACC_IBAN]
        bank_name = self._bank_name(bank_code)
        selection_name = ' '.join(
            [get_menu_text("Show"), bank_name, get_menu_text("Statement")])
        label = account[decl.KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[decl.KEY_ACC_ACCOUNT_NUMBER]
        title = ' '.join([selection_name, label])
        data_dict = {}
        while True:
            date_statement = InputDateTable(
                title=title, data_dict=data_dict, table=declm.STATEMENT, selection_name=selection_name)
            if date_statement.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = date_statement.field_dict
            self.repo.selection_put(title, data_dict)
            if declm.DB_amount in data_dict:
                data_dict[declm.DB_status] = 1
            if declm.DB_opening_balance in data_dict:
                data_dict[declm.DB_closing_status] = 1
            if declm.DB_opening_balance in data_dict:
                data_dict[declm.DB_opening_status] = 1
            selected_check_button = list(
                filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
            message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            data = self.repo.get_statements(selected_check_button, iban, period)
            title_period = ' '.join([title, str(period)])
            if data:
                while True:
                    table = PandasBoxStatementTable(
                        title_period, data, message, mode=decl.EDIT_ROW)
                    message = table.message
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title_period, selected_check_button))
                break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_transactions(self, bank_code, account):

        iban = account[decl.KEY_ACC_IBAN]
        label = account[decl.KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[decl.KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join([get_menu_text("Show"), bank_name,
                          get_menu_text("Transactions"), label])
        data_dict = {}
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        while True:
            date_transaction_view = InputDateTable(
                title=title, data_dict=data_dict, table=declm.TRANSACTION_VIEW)
            if date_transaction_view.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = date_transaction_view.field_dict
            selected_check_button = list(
                filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            data = self.repo.get_transaction_view_data_of_iban_period(selected_check_button, iban, period)
            title_period = ' '.join([title, str(period)])
            if data:
                while True:
                    table = PandasBoxTransactionTableShow(
                        title_period, data, iban, message, mode=decl.EDIT_ROW)
                    message = table.message
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title_period, selected_check_button))
                break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_holdings(self, bank_code, account):

        iban = account[decl.KEY_ACC_IBAN]
        label = account[decl.KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[decl.KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [get_menu_text("Show"), bank_name, get_menu_text("Holding") + '%', label])
        data_dict = {decl.FN_FROM_DATE: date.today() - timedelta(days=1), decl.FN_TO_DATE: date.today()}
        while True:
            input_period = InputDateHolding(title=title, data_dict=data_dict,
                                            container=iban)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            data_from_date = self.repo.get_holding_of_iban_date(iban, data_dict[decl.FN_FROM_DATE])
            data_to_date = self.repo.get_holding_of_iban_date(iban, data_dict[decl.FN_TO_DATE])
            title_period = ' '.join(
                [title, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])])
            while True:
                table = PandasBoxHoldingPercent(title=title_period, dataframe=(
                    data_to_date, data_from_date), mode=decl.CURRENCY_SIGN,
                    cellwidth_resizeable=False)
                if table.button_state == decl.WM_DELETE_WINDOW:
                    break
    def websites(self, site):

        webbrowser.open(site)


class LedgerWorkFlow(BaseWorkflow):

    def __init__(self,  title, repo, service, footer, progress):

        super().__init__(title, repo, service, footer, progress)
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_balances(self):
        """
        Show ledger balances
            date referred to entry_date field in Ledger
        """
        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Balances")])
        accounts = self.repo.get_balance_accounts()
        data_dict = {decl.FN_FROM_DATE: date(datetime.now().year, 1, 1), decl.FN_TO_DATE: date(datetime.now().year, 12, 31)}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            if input_period:
                from_date = input_period.field_dict[decl.FN_FROM_DATE]
                to_date = input_period.field_dict[decl.FN_TO_DATE]
                data_dict = input_period.field_dict
                data = self.srv.ledger_balance_account(to_date, accounts, from_date=from_date)
                if data:
                    title = ' '.join([title, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', from_date, to_date)])
                    BuiltPandasBox(
                        title=title, dataframe=DataFrame(data, columns=[declm.DB_account, declm.DB_name, decl.FN_BALANCE]),
                        mode=decl.NO_CURRENCY_SIGN, cellwidth_resizeable=False
                        )
            else:
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, ''))
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_assets(self):
        """
        Show ledger assets of period
            date referred to entry_date field in Ledger
        """
        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Assets")])
        asset_accounts = self.repo.get_balance_assets()
        data_dict = {decl.FN_FROM_DATE: date.today(), decl.FN_TO_DATE: date.today()}
        input_period = InputPeriod(title=title, data_dict=data_dict)
        if input_period.button_state == decl.WM_DELETE_WINDOW:
            return
        if input_period:
            from_date = input_period.field_dict[decl.FN_FROM_DATE]
            to_date = input_period.field_dict[decl.FN_TO_DATE]
            if date_days.convert_to_date(to_date) > date.today():
                to_date = date_days.today()
            data = []
            data_counter = 0
            trading_days = xetra_cls.trading_days(from_date, to_date, as_str=True)
            for asset_day in trading_days:
                asset_day_data = self.srv.ledger_balance_account(asset_day, asset_accounts)
                if asset_day_data:
                    data = [*data, *asset_day_data]
                    data_counter += 1
            self._show_informations()
            title = ' '.join(
                [title, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', from_date, to_date)])
            if data_counter == 0:
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, ''))
            elif data_counter == 1:
                BuiltPandasBox(
                    title=title,
                    dataframe=DataFrame(data, columns=[declm.DB_account, declm.DB_name, decl.FN_BALANCE]),
                    dataframe_sum=[decl.FN_BALANCE],
                    mode=decl.NO_CURRENCY_SIGN,
                    cellwidth_resizeable=False
                    )
            elif data_counter > 1:
                while True:
                    table = PandasBoxTotals(title, data)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
        else:
            self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, ''))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_upload_check(self):
        """
        Check (last upload ledger)
        """
        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Check Upload")])

        from_date = date(datetime.now().year - 1, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        period = (from_date, to_date)
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_CHECK_UPLOAD')
        while True:
            data = self.repo.get_ledger_upload_check(period)
            if data:
                table = PandasBoxLedgerTable(
                    title, data, message, period=period)
                message = table.message
                if table.button_state == decl.WM_DELETE_WINDOW:
                    break
            else:
                period = msg.get_message(
                    msg.MESSAGE_TEXT, 'PERIOD',
                    date_days.convert_to_str(from_date), date_days.convert_to_str(to_date)
                    )
                self.footer.set(msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title, period))
                break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_bank_statement_check(self):
        """
        Check (Bank Statement of an account)
        """
        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Check Bank Statement")])
        self.ledger_account(title=title, )
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_account_category(self):
        """
        Account grouped by category with sum Rows
        """
        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Account Category")])
        data_dict = self.repo.selection_get(title)
        if not data_dict:
            data_dict = {decl.FN_FROM_DATE: date(datetime.now().year, 1, 1), decl.FN_TO_DATE: date(
                datetime.now().year, 12, 31)}
        while True:
            select_ledger_account = SelectLedgerAccountCategory(
                title=title, data_dict=data_dict)
            if select_ledger_account.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = select_ledger_account.field_dict
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            account_name = data_dict[declm.DB_account][5:]
            account = data_dict[declm.DB_account][:4]
            field_list = [declm.DB_id_no, declm.DB_entry_date, declm.DB_date, declm.DB_purpose_wo_identifier, declm.DB_amount,
                          declm.DB_currency, declm.DB_category, declm.DB_credit_account, declm.DB_debit_account, declm.DB_applicant_name]
            while True:
                title_period = '  '.join(
                    [title, account, account_name, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])])
                data = self.repo.get_ledger_account(field_list, account, period)
                if data:
                    table = PandasBoxLedgerAccountCategory(
                        title=title_period, dataframe=data, mode=decl.NUMERIC)
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', ' ', title_period))
                    break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_account(self, title=None):

        if title is None:
            title = ' '.join([get_menu_text("Ledger"),
                             get_menu_text("Account")])
        data_dict = self.repo.selection_get(title)
        if not data_dict:
            data_dict = {decl.FN_FROM_DATE: date(datetime.now().year, 1, 1),
                         decl.FN_TO_DATE: date(datetime.now().year, 12, 31)}
        while True:
            select_ledger_account = SelectLedgerAccount(
                title=title, data_dict=data_dict)
            if select_ledger_account.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = select_ledger_account.field_dict
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            account_name = data_dict[declm.DB_account][5:]
            account = data_dict[declm.DB_account][:4]
            data_dict[declm.DB_id_no] = 1
            field_list = list(filter(lambda x: data_dict[x] == 1, list(
                data_dict.keys())))  # filter selected check_buttons
            selected_row = 0
            message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
            while True:
                title_period = '  '.join(
                    [title, account, account_name, msg.get_message(msg.MESSAGE_TEXT, 'PERIOD', data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])])
                if get_menu_text("Check Bank Statement") in title:
                    # caller is _ledger_statement_check
                    data = self.repo.get_ledger_bank_statement(field_list, account, period)
                else:
                    data = self.repo.get_ledger_account(field_list, account, period)

                if data:
                    table = PandasBoxLedgerTable(
                        title_period, data, message, mode=decl.EDIT_ROW, selected_row=selected_row, period=period)
                    message = table.message
                    selected_row = table.selected_row
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', ' ', title_period))
                    break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_journal(self):

        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Journal")])
        data_dict = {decl.FN_FROM_DATE: date(datetime.now().year, 1, 1), decl.FN_TO_DATE: date(datetime.now().year, 12, 31)}
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            title_period = ' '.join(
                [title, data_dict[decl.FN_FROM_DATE], '-', data_dict[decl.FN_TO_DATE]])
            selected_row = 0
            while True:
                period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
                data = self.repo.get_ledger_view_in_period(period)
                if data:
                    table = PandasBoxLedgerTable(
                        title_period, data, message, mode=decl.EDIT_ROW, selected_row=selected_row, period=period)
                    message = table.message
                    selected_row = table.selected_row
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', ' ', title_period))
                    break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_coa_table(self):

        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Chart of Accounts")])
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        selected_row = 0
        while True:
            data = self.repo.get_ledger_coa()
            ledger_coa_table = PandasBoxLedgerCoaTable(
                title, data, message, mode=decl.EDIT_ROW, selected_row=selected_row)
            message = ledger_coa_table.message
            selected_row = ledger_coa_table.selected_row
            if ledger_coa_table.button_state == decl.WM_DELETE_WINDOW:
                return
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_daily_balance(self):

        title = ' '.join([get_menu_text("Ledger"),
                         get_menu_text("Reset Ledger_daily_balance")])

        accounts = SelectLedgerDailyBalanceAccounts(title=title)
        if accounts.field_dict:
            accounts_to_delete = list(
                key.removeprefix(decl.FN_ACCOUNT_NUMBER) for key, value in accounts.field_dict.items() if value == 1
                )
            self.repo.delete_ledger_daily_balance(accounts_to_delete)
        else:
            self.footer.set(
                msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', declm.LEDGER_DAILY_BALANCE.upper(), ''))

    @_wrapper(before="_delete_footer", after="_show_informations")
    def show_statements_no_ledger(self):

        title = ' '.join(
            [get_menu_text("Ledger"), get_menu_text("Statement_wo")])
        data_dict = {}
        while True:
            date_statement = InputDateTable(
                title=title, data_dict=data_dict, table=declm.STATEMENT)
            if date_statement.button_state == decl.WM_DELETE_WINDOW:
                return
            data_dict = date_statement.field_dict
            selected_check_button = [
                x for x, v in (data_dict or {}).items() if v == 1
            ]
            message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
            period = (data_dict[decl.FN_FROM_DATE], data_dict[decl.FN_TO_DATE])
            while True:
                data = self.repo.get_statement_without_ledger(selected_check_button, period)
                title_period = ' '.join([title, str(period)])
                if data:
                    table = PandasBoxStatementNoLedgerTable(
                        title_period, data, message, mode=decl.EDIT_ROW)
                    message = table.message
                    if table.button_state == decl.WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        msg.get_message(msg.MESSAGE_TEXT, 'DATA_NO', title_period, selected_check_button))
                    break
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_search(self):
        """Handle ledger search workflow."""
        title = f"{get_menu_text('Ledger')} {get_menu_text('Search')}"
        # --- collect allowed accounts ---
        accounts = self.repo.get_all_accounts() or []
        accounts_list = [f"{acc[0]} {acc[1]}" for acc in accounts]
        # --- build combo dictionaries ---
        combo_sources = [
            declm.DB_origin,
            declm.DB_category,
            declm.DB_applicant_name
        ]
        combo_dict = {}
        for field in combo_sources:
            combo_dict.update(
                self._create_combo_list(
                    declm.LEDGER,
                    field,
                    date_name=declm.DB_entry_date
                )
            )
        combo_insert_value = combo_sources.copy()
        combo_positioning_dict = {
            **self._create_combo_list(declm.LEDGER, declm.DB_category, date_name=declm.DB_entry_date),
            **self._create_combo_list(declm.LEDGER, declm.DB_applicant_name, date_name=declm.DB_entry_date),
            declm.DB_currency: decl.CURRENCIES,
            declm.DB_credit_account: accounts_list,
            declm.DB_debit_account: accounts_list,
        }
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        selected_row = 0
        # --- main search loop ---
        while True:
            search = LedgerTableSearchRowBox(
                declm.LEDGER,
                declm.LEDGER_VIEW,
                {},
                title=self.title,
                button1_text=decl.BUTTON_SELECT,
                button2_text=None,
                protected=[declm.DB_upload_check, declm.DB_bank_statement_checked],
                combo_dict=combo_dict,
                combo_insert_value=combo_insert_value,
                combo_positioning_dict=combo_positioning_dict
            )
            if search.button_state == decl.WM_DELETE_WINDOW:
                break
            # filter out empty values
            search_dict = {
                k: v for k, v in search.field_dict.items()
                if v not in ['', '0']
            }
            title_search = f"{title} {search_dict}"
            while search_dict:
                data = self.repo.get_ledgers_of_search(search_dict)
                table = PandasBoxLedgerTable(
                    title_search,
                    data,
                    message,
                    mode=decl.EDIT_ROW,
                    selected_row=selected_row
                )
                message = table.message
                selected_row = table.selected_row
                if table.button_state == decl.WM_DELETE_WINDOW:
                    break

    def _create_combo_list(
        self,
        table,
        field_name,
        from_date=date.today() - timedelta(weeks=104),
        date_name=declm.DB_price_date
    ):
        """
        Return dict {field_name: sorted list of field values}
        filtered by optional date range.
        """
        # --- get data from repository ---
        if from_date:
            period = (from_date, date.today())
            values = self.repo.get_field_values_of_table_in_period(
                table, field_name, date_name, period
            )
        else:
            values = self.repo.get_field_values_of_table(table, field_name)
        if not values:
            return {field_name: []}
        # --- flatten + remove None ---
        # faster and cleaner than sum(...) and while-remove loop
        flat_values = [
            item
            for row in values
            for item in row
            if item is not None
        ]
        # --- return sorted result ---
        return {field_name: sorted(flat_values)}
    @_wrapper(before="_delete_footer", after="_show_informations")
    def ledger_search_of_statement(self):

        title = f"{get_menu_text('Ledger')} {get_menu_text('Search via Statement')}"
        combo_dict = self._create_combo_list(
            declm.STATEMENT,
            declm.DB_iban,
            date_name=declm.DB_entry_date,
        )
        combo_insert_value = [declm.DB_iban]
        message = msg.get_message(msg.MESSAGE_TEXT, 'HELP_PANDASTABLE')
        selected_row = 0
        header = None
        while True:
            search = StatementTableSearchRowBox(
                declm.STATEMENT,
                declm.STATEMENT,
                {},
                title=title,
                header=header,
                mandatory=[declm.DB_iban, declm.DB_entry_date],
                focus_out=[declm.DB_entry_date],
                focus_in=[declm.DB_entry_date],
                combo_dict=combo_dict,
                combo_insert_value=combo_insert_value,
                button1_text=decl.BUTTON_SELECT,
                button2_text=None,
            )
            if search.button_state == decl.WM_DELETE_WINDOW:
                break
            search_dict = {
                k: v
                for k, v in search.field_dict.items()
                if v not in ("", "0") or k in (declm.DB_iban, declm.DB_entry_date)
            }
            if not search_dict:
                continue
            title_search = f"{title} {search_dict}"
            while True:
                data = self.repo.get_ledgers_via_statement(search_dict)
                if not data:
                    header = msg.get_message(
                        msg.MESSAGE_TEXT, 'SELECT_NO_RESULTS', search_dict
                    )
                    break
                table = PandasBoxLedgerTable(
                    title_search,
                    data,
                    message,
                    mode=decl.EDIT_ROW,
                    selected_row=selected_row,
                )
                message = table.message
                selected_row = table.selected_row
                if table.button_state == decl.WM_DELETE_WINDOW:
                    break
