'''
Created on 21.12.2025

@author: Wolfg
'''
import inspect
import sys
import traceback
import logging
from contextlib import contextmanager
from tkinter import Tk, messagebox, TclError
from dataclasses import dataclass
from threading import current_thread, main_thread

import banking.declarations as decl


MESSAGE_TITLE = 'BANK ARCHIVE'
MESSAGE_TEXT = {
    decl.CODE_0030: 'Bank: {} \n Bank Account: {}  {}       \n     Download not executed,    use single downloading bank data',
    decl.CODE_3040: 'Bank: {} \n Bank Account: {}  {}       \n     Download partially executed',
    'ACCOUNT_IBAN_MISSED': 'Check TABLE LEDGER_COA: {}, \n Assign valid IBAN to ledger account: {}, {}',
    'ACQUISITION_HEADER': '{}  ACQUISITION AMOUNT CHANGE {} in Period {} - {}',
    'ACQUISITION_AMOUNT': 'Bank: {} \n Bank Account: {}  {}  {}      \n     Acquisition Amount must be adjusted manually',
    'ALPHA_VANTAGE': 'DOWNLOAD Prices from ALPHA_VANTAGE ({}/{}) failed (see ERROR Message before)',
    'ALPHA_VANTAGE_REFRESH_RUN': 'AlphaVantage Functions Creation started',
    'ALPHA_VANTAGE_REFRESH': 'AlphaVantage Functions successfully created\ntest\ntest\ntest\ntest\ntest\ntest\ntest\ntest\ntest\ntest',
    'ALPHA_VANTAGE_ERROR': 'API Parameter Information not created',
    'ALPHA_VANTAGE_ERROR_MSG': 'AlphaVantage Error Message: \n{} \n\n Generated URl: \n{}',
    'ALPHA_VANTAGE_NO_DATA': 'AlphaVantage API returns no Data \n {}',
    'APP': 'APPLICATION and MARIDB Customizing Installation',
    'ASSINGNABLE_STATEMENTS': 'Assignable Statements for ledger in period {} to {}',
    'BALANCE_DIFFERENCE':   'Difference LEDGER ./. STATEMENTS \n Bank Account {} {}:  {}  \n Ledger Account {} {}:  {}  \n Balance Difference: {}',
    'BANK_BALANCE_DIFFERENCE':   'Difference: BANK ./. DOWNLOADED STATEMENTS \n Bank Account {} {}:  {} \n Balance of downloaded Statements: {} \n Balance Difference: {}',
    'BANK_CHALLENGE': '{} ({}) \n Bank Account: {} {}      \n Challenge_Text:\n  {}',
    'BANK_CONSORS_TRANSFER': '\n\n Open Consors Secure Plus \nGenerate QR-TAN with Secure Plus',
    'BANK_CODE_EXIST': 'Bank Code exists',
    'BANK_DATA_ACCOUNTS_MISSED': 'Accounts missed in Customizing: {}',
    'BANK_DATA_NEW': 'Created {} ({}. Next Step: SYNCHRONIZE Bank \n\n Then restart application',
    'BANK_DATA_NEW_SCRAPER': 'Created {} ({})',
    'BANK_DELETED': 'DELETE BANK LOGIN DATA \nBankcode: {}',
    'BANK_DELETE_failed': 'DELETE BANK {} failed!! \n IBAN of bank exists in table {}',
    'BANK_LOGIN': 'Bank Scraper Login failed \nException: {} \nURL: {}\nPassword: {}\nUserName: {}',
    'BANK_PERIOD': '{} ({}) \n Bank Account: {} {}      \n Account Postings only available from {} onwards',
    'BMW_ZFA2': 'Please confirm the login process with your BMW Bank 2FA app',
    'BMW_ZFA2_REJECTED': 'login process not confirmed with your BMW Bank 2FA app; Login rejected',
    'CONNECT_IMAGE_ERROR': 'Image error, Could not load background image:\n {}',
    'CONNECT_MARIADB_ERROR': 'MariaDB connection error: {}',
    'CONNECT_MARIADB': 'MariaDB connected: {}',
    'CONNECT_SELECT_DB': 'Please select or specify a database.',
    'CONNECT_CREATE_DB': 'New database? \n The database {} does not exist.\n  Do you want to create it?',
    'CONNECT_DB_CREATED': 'Database {} created.',
    'CONNECT_CREATE_DB_ABORTED': 'Database creation aborted.',
    'CONNECT_DB_CONNECTED': 'Connected to database {}',
    'CREDENTIALS': '{} Login failed',
    'CREDENTIALS_CHECK': '{} Checking Credentials',
    'CHECKBOX': 'Select at least one of the Check Box Icons',
    'CONN': 'Database Connection failed  \nMariaDBuser: {} \nMariaDBname: {}',
    'CORPORATE_ACTIONS_IS_EMPTY': 'Corporate_Actions table is empty',
    'DATA_INSERTED': '{}       Data inserted',
    'DATA_CHANGED': '{}       Data changed',
    'DATA_DELETED': '{}       Data deleted',
    'DATA_ROW_EXIST': '{}       Data Row exists',
    'DATA_NO': '{} \n{} \nData not available',
    'DATABASE': 'D A T A B A S E:  {}',
    'DATABASE_REFRESH': 'Database Credentials changed \n You must restart Banking',
    'DATE': '{} invalid or missing (Format e.g. 2020-12-12)',
    'DATE_ADJUSTED': 'Price_Date not in Table Holding \n Adjusted by existing previous Date',
    'DATE_TODAY': '{} Less todays date',
    'DATE_NO_WORKDAY': '{} is no  working day',
    'DATE_NO_XETRA': 'No valid XETRA trading period',
    'DBLOGIN': 'Database Connection failed! \n Check Database LOGIN Parameter in CUSTOMIZINDG Application/MariaDB',
    'DECIMAL': 'Invalid Decimal Format Field {} e.g. 12345.00',
    'DOWNLOAD_BANK':  'BANK: {}    Download Bank Data started',
    'DOWNLOAD_ACCOUNT': 'Bank: {} {}\n Bank Account: {}  {}       \n     Download Bank Data of Iban {}',
    'DOWNLOAD_ACCOUNT_NOT_ACTIVATED': 'Bank: {} {}\n Bank Account: {}  {}       \n     Download Bank Data of Iban {} not activated in LEDGER_COA',
    'DOWNLOAD_DONE': 'BANK: {}   Data downloading finished',
    'DOWNLOAD_NOT_DONE': 'BANK: {}   Data downloading finished with E R R O R ',
    'DOWNLOAD_REPEAT': 'Download {} canceled by User! \n\nStart Download once more!',
    'DOWNLOAD_RUNNING': '{} Data Download running',
    'EXCEL': 'Excel File {} created, sheet added',
    'ENTRY': 'Enter Data',
    'ENTRY_DATE': 'Entry_date missed',
    'FIELDLIST_MIN': 'Select at least {} positions in fieldlist',
    'FIELDLIST_INTERSECTION_EMPTY': 'Intersection of the data in the selected period of all selected isin_codes is empty',
    'FIXED': '{} MUST HAVE {} Characters ',
    'FINTS_UPDATE_BPD_VERSION': 'Bank: {} \n Version of the bank parameter data updated.\n  New version: {}',
    'FINTS_UPDATE_UPD_VERSION': 'Bank: {} \n Version of the user parameter data updated.\n  New version: {}',
    'HELP_PANDASTABLE': 'Show Row Menu: \n          Select row\n          Click on row number with the right mouse button',
    'HELP_CHECK_UPLOAD': 'Start with FIRST row to be checked\n\n Show Row Menu: \n          Select row\n          Click on row number with the right mouse button\n          Then select Update Selected Row and UPDATE if the row and all previous rows are OK',
    'HITAN6': 'Bank: {} \n Bank sync: {}  {}       \n     Could not find HITAN6/7 task_reference',
    'HIKAZ':  'Response {} missing: bank_name {}, account_number {}, account_product_name {}',
    'HITAN': 'Security clearance is provided via another channel\n{}',
    'HITAN_MISSED': 'Response HITAN missing: bank_name {}, account_number {}, account_product_name {}',
    'HIUPD_EXTENSION': 'Bank: {} \n Bank Account: {}  {}       \n     IBAN {} received Bank Information: \n     {}',
    'HKKAZ CONSOR': 'Consors currently supports only version 6 for FINTS HKKAZ Segment.',
    'HOLDING_INSERT': 'Holding data for date {} does not exist. Insert?',
    'HOLDING_TRANSACTION_ERROR': 'Holding not created: {}',
    'HOLDING_TRANSACTION_CREATED': 'Holding row {} {} inserted',
    'HTTP': 'Server not connected! HTTP Status Code: {}\nBank: {}  Server: {}',
    'HTTP_INPUT': 'Server not valid or not available! HTTP Status Code: {}',
    'IBAN': 'IBAN invalid',
    'IBAN_MISSED': 'IBAN {} has no account assignment (see LEDGER_COA)',
    'IBAN_USED': 'IBAN is already assigned to another account',
    'IMPORT_ERROR': """
        CSV import failed.
        File : {}
        Error: {}
        """,
    'IMPORT_ALREADY': 'Rows of CSV-File {} already imported',
    'IMPORT_TEXT_TICKER': f"""
        ZIP format
        ----------
        The ZIP file is converted into the following CSV file during import.

        CSV format
        ----------
        - Encoding: utf8
        - Delimiter: ,
        - Quote character: "
        - Line ending: CRLF (\\r\\n)

        Expected columns
        ----------------
        1. symbol
        2. company_name
        3. exchange

        Additional values
        -----------------
        - ISIN is automatically set to 'NA'

        Notes
        -----
        Download Spreadsheet of Companies Traded on German Stock Exchanges

        {decl.TICKER_ADDRESS}
    """,
    'IMPORT_TEXT_SERVER': f"""
        CSV format
        ----------
        The CSV file must use the following structure:

        - Encoding: latin1
        - Delimiter: ;
        - Optional quote character: "
        - Line ending: CRLF (\r\n)
        - First row: header (ignored)

        Expected columns
        ----------------
        The CSV file contains 28 columns in total.

        Only the following columns are imported:

        1. code      : Bank / institute code
        2. server    : HBCI / FinTS server address

        All remaining columns are ignored during import.

        Additional processing
        ---------------------
        - Existing entries are deleted before import.
        - Placeholder server entries ('\\r') are removed.
        - Additional known servers from
          ``decl.SCRAPER_BANKDATA`` are inserted after import.

        Notes
        -----
        Registration to get CSV File:

        {decl.FINTS_SERVER_ADDRESS}
    """,
    'IMPORT_TEXT_BANKIDENTIFIER': f"""
         CSV format
        ----------
        The CSV file must use the following structure:

        - Encoding: latin1
        - Delimiter: ;
        - Optional quote character: "
        - Line ending: CRLF (\r\n)
        - First row: header (ignored)

        Expected columns
        ----------------
        1. code                      : Bank code (BLZ)
        2. payment_provider          : Payment provider type
        3. payment_provider_name     : Name of the payment provider
        4. postal_code               : Postal code
        5. location                  : City / location
        6. name                      : Bank name
        7. pan                       : PAN identifier
        8. bic                       : BIC code
        9. check_digit_calculation   : Check digit calculation method
        10. record_number            : Record number
        11. change_indicator         : Change indicator
        12. code_deletion            : Deletion flag
        13. follow_code              : Follow-up bank code

        Additional processing
        ---------------------
        - Existing entries are deleted before import.
        - Payment providers with provider code '2'

        Notes
        -----
        Informations

        {decl.BUNDESBANK_BLZ_MERKBLATT}

        Download

        {decl.BUNDEBANK_BLZ_DOWNLOAD}
    """,
    'IMPORT_TEXT_TRANSACTION_BANK_CONSORS': """
        Import transaction data via CSV File

            Download CSV File via Bank App Menu Tab:
                                "ORDERÜBERSICHT"
    """,   
    'IMPORT_TEXT_TRANSACTION_BANK_BIW': """
        Import transaction data via CSV File

            Download CSV File via Bank App Menu Tab:
                                "DEPOTUMSÄTZE"
    """,   
    'IMPORT_TEXT_TRANSACTION': """
        CSV format
        ----------
        The CSV file must use the following structure:

        - Encoding: latin1
        - Delimiter: ;
        - Optional quote character: "
        - Line ending: CRLF (\n)
        - First row: header (ignored)

        Expected columns:
        -----------------
        1. price_date     : Booking or valuation date
        2. isin           : ISIN of the security
        3. counter        : Number of transactions
        4. pieces         : Quantity of shares / units
        5. price          : Price per unit (decimal point!)

        Additional values are automatically added during import:
        --------------------------------------------------------
        - iban
        - transaction_type
        - currencies
        - posted_amount
        - origin filename

        Negative transactions are automatically converted into
        delivery transactions after import.
    """,
    'IMPORT_CSV': 'Import CSV_File into Table {}\n\n Source: \n{}',
    'IMPORT_CSV_MISSED': 'Customizing: Import CSV_File into Table {} ',
    'ISIN_ALPHABETIC': 'Isin_code must start with an alphabetic character',
    'ISIN_DATA': 'Enter ISIN Data',
    'ISIN_IN_HOLDING': 'No deletion allowed \n {} ({}) \n Used in holding or transaction table',
    'ISIN_SYMBOL_MISSED': '{} symbol/ticker missing',
    'ISDIGIT': 'Invalid Integer Field {}',
    'LEDGER_ACTIVATE': 'Ledger activated',
    'LEDGER_ALREADY_ASSIGNED': 'Selected STATEMEnt row is already assigned to LEDGER id_no {} ',
    'LEDGER_BALANCE_ERROR': 'Iban: {} The balance cannot determined without ledger data.',
    'LEDGER_CREATE': 'Inserting a new LEDGER row for the selected STATEMENT row',
    'LEDGER_ROW': 'No additional statement data available for table row ',
    'LEDGER_STATEMENT_ASSIGMENT_EMPTY': 'There are no assignment statements for ledger IdNo {} and Ledger Account {}',
    'LEDGER_STATEMENT_ASSIGMENT_MISSED': 'Update and select new assignment (statement) of credit/debit accounts marked in red !',
    'LEDGER_DAILY_BALANCE_RESET': 'Select account from which the daily balances should be deleted.',
    'LENGTH': '{} Exceeds Length OF {} Characters',
    'LOAD_DATA': 'Data imported if no message was displayed previously \nfrom File {}',
    'LOGGING_ACTIVE': 'Logging activated',
    'LOGGING_FILE': 'OS Error Logging_file',
    'LOGIN': 'LOGIN Data incomplete.   \nCustomizing e.g. synchronization LOGIN Data must be done \nBank_Code: {} (Key Error: {})',
    'LOGIN_SCRAPER': 'LOGIN Data incomplete.   \nCustomizing LOGIN Data/Scraping must be done \nBank: {} ({})',
    'MANDATORY': '{} is mandatory',
    'MARIADB_ERROR_SQL': 'SQL_Statement\n {} \n\nVars\n {}',
    'MARIADB_ERROR': 'MariaDB Error\n{} \n {}',
    'MIN_LENGTH': '{} Must have a Length OF {} Characters',
    'NAME_INPUT': 'Enter Query Name (Name of Stored Procedure, allowed Chars [alphanumeric and _): ',
    'NAMING': 'Fix Naming. Allowed Characters: A-Z, a-z, 0-9, _',
    'NO_TURNOVER': 'Bank: {} \n Bank Account: {}  {}       \n     No new turnover',
    'NOTALLOWED': '{} Value not allowed, select from list \n {}',
    'NOT_FOUND': 'MESSAGE_TEXT not found',
    'SHELVE_NAME_MISSED': 'Shelve name  {} not found',
    'OPENING_ACCOUNT_MISSED': 'Opening balance account is missing/multiple in Chart of Accounts',
    'OPENING_LEDGER_MISSED': 'Opening balances missed in {}. Account: {}',
    'PAIN': 'SEPA Format pain.001.001.03 not found/allowed\nBank: {}',
    'PERIOD': 'Period ({}, {})',
    'PIN_EMPTY': 'PIN must not be empty.',
    'PIN_DIGITS': 'PIN must contain digits only.',
    'PIN_INVALID': 'Invalid PIN.',
    'PIN': 'PIN missing! \nBank: {} ({})',
    'PIN_INPUT': 'Enter PIN   {} ({}) ',
    'PRICES_DELETED': '{}:  Prices deleted\n\n Used Ticker Symbol {} \n ISIN: {}',
    'PRICES_CLOSE_ZERO': '{} has not yet updated ClosePrice: {} {}',
    'PRICES_EMPTY': 'Price table is empty',
    'PRICES_ERROR': 'Prices Download Error {} ({}): {}',
    'PRICES_DOWNLOAD': 'Download Prices {}: {} → {}',
    'PRICES_NO_DOWNLOAD': 'Download: No Prices found {}: Ticker: {} Origin: {}',
    'PRICES_CORPORATE': '{}: imported {} corporate actions',
    'PRICES_LOADED': '{}: Prices imported {}  rows',
    'PRICES_ALREADY': '{} Prices up to date',
    'PRICES_NO': '{}:  No new Prices found\n\n Used Ticker Symbol {} {}\n ISIN: {}  {}',
    'PRODUCT_ID': 'Product_ID missing, No Bank Access possible\n Get your Product_Id: https://www.hbci-zka.de/register/prod_register.htm',
    'RADIOBUTTON': 'Select one of SELECT the RadioButtons',
    'RESPONSE': 'Got invalid response from bank',
    'SCRAPER_BALANCE': 'Last closing balance from database: {} \n Opening balance from the transaction overview: {}',
    'SCRAPER_NO_TRANSACTION_TO_STORE': '{} {} All transactions already saved in database',
    'SCRAPER_PAGE_ERROR': 'Connection interrupted!',
    'SCRAPER_SELENIUM_EXCEPTION': 'An error occurred:\n  Error type: {}\n  Error message: {}',
    'SCRAPER_TIMEOUT': 'Connection TimeOut',
    'SCROLL': 'Scroll forward: CTRL+RIGHT   Scroll backwards: CTRL+LEFT',
    'SEGMENT_VERSION': 'Segment {}{} Version {} not implemented',
    'SELECT_DATA': 'Selection incomplete',
    'SELECT_INCOMPLETE': 'Enter your Selection',
    'SELECT_NO_RESULTS': 'Query with {} no results',
    'SELECT_ROW': 'Select row, then right clicking on row number',
    'SEPA_CRDT_TRANSFER': 'SEPA Credit Transfer \nBank:    {}  \nAccount:    {} ({})',
    'SQLALCHEMY_ERROR': "Error Calling SQLAlchemy {}:    {}",
    'SHELVE': '\n LOGON Data, Synchronization Data >>>>> BANK: {}\n\n',
    'STACK': '\n\n LINE\n {} \n        MODULE  {}\n        METHOD {}',
    'SYMBOL_MISSING_ALL': '{} \n \n No ticker/symbol found in Table ISIN. \n You must add ticker symbols in Table ISIN',
    'SYMBOL_MISSING': 'No ticker/symbol (symbol_origin) found. \n ISIN: {}  /  {} \n\n You must add ticker symbol in Table ISIN',
    'SYMBOL_USED': 'Symbol already used in {}',
    'SYNC': 'Synchronization Data incomplete    \nSynchronization must be done \nBank: {} ',
    'SYNC_START': 'Next Step: You must start Synchronization Bank: {} ',
    'SUPPORTED_CAMT_MESSAGES': 'Refresh Bank_parameter: Supported camt_message_name missed',
    'TA_OTHER_PARAMETER': 'function contains additional parameters: \n  {}',
    'TA_NO_RESULT': 'Technical Analysis no result!\n Category: {}  Indicator: {}',
    'TA_METHOD_ERROR': 'Indicator {}: Name creation of the calling method not successful',
    'TA_CLASS_NO_METHOD': 'Category: {} \nMethods in class {} not found',
    'TA_NO_OHLC': 'Category: {} \n No OHCL Series parameter of Class {}',
    'TA_ADD_CHART': 'Add Charts',
    'TASK_DONE': 'Task finished.',
    'TASK_WARNING': 'Finished with Warnings',
    'TASK_STARTED': '{}: Task started.',
    'TAN_INPUT': 'Enter TAN  {} ({}): ',
    'TAN_CANCEL': 'Input TAN canceled, request aborted',
    'TERMINATION': 'FinTS MariaDB Banking Termination',
    'THREAD': 'Task {} aborted. No Dialogue. Its no mainthread',
    'THREADING_ACTIVE': 'Threading activated',
    'TRANSACTION_CHECK': '{} Difference Pieces of Transactions / Pieces of Portfolio',
    'TRANSACTION_CLOSED_EMPTY': ' No Closed Transactions in Period {} - {}',
    'TRANSACTION_HEADER_SYNC_TABLE': 'SYNCHRONIZE TRANSACTIONS',
    'TRANSACTION_NO': ' No Transactions in Period {} - {}',
    'TRANSACTION_PIECES_NEGATIVE': 'Transactions faulty! On {} cumulated Pieces negative!',
    'TRANSACTION_PIECES_PORTFOLIO': ' Difference Pieces of Transactions / Pieces of Portfolio',
    'TRANSACTION_TITLE': '{}  TRANSACTIONS  {} ',
    'TWOSTEP': 'Select one of the Security Functions \n Only Two-Step TAN Procedure \n SCA Strong Customer Authentication',
    'UNEXCEPTED_ERROR': 'E X C E P T I O N    E R R O R  !\n\nMODULE: {}\n\nLINE  of EXCEPTION ERROR Call: {}\n\nMETHOD: {}\n\nTYPE:\n {} \n\nVALUE:  {} \n\nTRACEBACK:\n {}',
    'VERSION_TRANSACTION': 'TRANSACTION HK{}{} not available',
    'VOP_HHDUC': 'Verification of Payee: No PNG header found in challenge_hhduc',
    'VOP_FAILED': 'Verification of Payee failed',
    'WEBDRIVER': 'Installing {} WEB Driver failed\n\n{}',
    'WEBDRIVER_INSTALL': '{} WEB Driver installed to project.root/.wdm'
}


@contextmanager
def capture_yfinance_logs(level=logging.DEBUG):
    logger = logging.getLogger("yfinance")

    log_stream = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            log_stream.append(self.format(record))

    handler = ListHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    # alten Zustand sichern
    old_level = logger.level
    old_handlers = logger.handlers[:]

    logger.setLevel(level)
    logger.handlers = [handler]

    try:
        yield log_stream
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        handler.close()


def get_message(message_dict, key, *format_args, **format_kwargs):
    """
    Retrieves a message from a dictionary and formats it.
    Errors are handled and an explanatory message is returned:
    - Key not found
    - Placeholders missing or incorrect variables used for formatting
    """
    # Key checking
    if key not in message_dict:
        return f"[MESSAGE ERROR] Key '{key}' not present in the MESSAGE_TEXT dictionary."

    template = message_dict[key]

    # If no formatting is necessary
    if not format_args and not format_kwargs:
        return template

    # If no formatting is necessary
    try:
        return template.format(*format_args, **format_kwargs)
    except IndexError as e:
        return (f"[FORMAT ERROR] Too few positional arguments for Key '{key}'. "
                f"Template: '{template}'. Fehler: {e}")
    except KeyError as e:
        return (f"[FORMAT ERROR] Named placeholder {e} is missing for key '{key}'. "
                f"Template: '{template}'")
    except Exception as e:
        return (f"[FORMAT ERROR] Unexpected error while formatting key '{key}': {e}")


def is_main_thread() -> bool:

    return current_thread() is main_thread()


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


def bankdata_informations_append(information, message):

    message = str(message)
    Informations.bankdata_informations = ' '.join(
        [Informations.bankdata_informations, '\n' + information, message])


def prices_informations_append(information, message):

    message = str(message)
    Informations.prices_informations = ' '.join(
        [Informations.prices_informations, '\n' + information, message])


def transaction_informations_append(information, message):

    message = str(message)
    Informations.transaction_informations = ' '.join(
        [Informations.transaction_informations, '\n' + information, message])


def holding_informations_append(information, message):

    message = str(message)
    Informations.holding_informations = ' '.join(
        [Informations.holding_informations, '\n' + information, message])


class Informations(object):
    """
    Threading
    Downloading Bankdata using FinTS
    Container of messages, responses of banks, errors
    """
    bankdata_informations = ''
    BANKDATA_INFORMATIONS = 'BANKDATA INFORMATIONS'

    """
    Threading
    Download prices from Yahoo! or Alpha Vantage
    Container of messages, errors
    """
    prices_informations = ' '
    PRICES_INFORMATIONS = 'PRICES_INFORMATIONS'

    """
    Upload transactions from bank
    Container of messages, errors
    """
    transaction_informations = ' '
    TRANSACTION_INFORMATIONS = 'TRANSACTION_INFORMATIONS'

    """
    Update prices in holding from Yahoo! or Alpha Vantage
    Container of messages, errors
    """
    holding_informations = ' '
    HOLDING_INFORMATIONS = 'HOLDING_INFORMATIONS'


class Level():
    """
    severity level of the message
    """
    INFORMATION = decl.INFORMATION
    WARNING = decl.WARNING
    ERROR = decl.ERROR


class InfoStorage():
    """
    Message Storage Place
    """
    BANK = Informations.BANKDATA_INFORMATIONS
    PRICES = Informations.PRICES_INFORMATIONS
    TRANSACTION = Informations.TRANSACTION_INFORMATIONS
    HOLDING = Informations.HOLDING_INFORMATIONS


@dataclass()
class Message:
    """
    Message – reines Datenobjekt (keine Logik)
    """
    title: str
    text: str
    level: Level
    info_storage: InfoStorage


class StackTraceFormatter:
    """
    Stacktrace-Formatter (kein Copy & Paste mehr)
    """

    @staticmethod
    def format(skip: int = 2) -> str:
        lines = []
        for frame in inspect.stack()[skip:]:
            lines.append(

                f"LINE: {frame.lineno} METHOD: {frame.function}\n"
                f"{frame.filename}\n"
            )
        return "\n".join(lines)


class InformationMessageFactory:
    """
    Message Builder Information
    """
    @staticmethod
    def create(
        message: str = "",
        title: str = MESSAGE_TITLE,
        information: str = decl.INFORMATION,
        info_store: str = "",
    ) -> Message:

        return Message(
            title=title,
            text=message,
            level=information,
            info_storage=info_store
        )


class ExceptionMessageFactory:
    """
    Message Builder Exception Error
    """
    @staticmethod
    def from_current_exception(
        message: str = "",
        title: str = MESSAGE_TITLE,
        info_store: str = "",
    ) -> Message:
        exc_type, exc_value, exc_tb = sys.exc_info()

        if exc_type is None:
            raise RuntimeError("Keine aktive Exception vorhanden")

        tb_list = traceback.extract_tb(exc_tb)

        caller = inspect.stack()[1]

        formatted = get_message(
            MESSAGE_TEXT,
            "UNEXCEPTED_ERROR",
            caller.filename,
            caller.lineno,
            caller.function,
            exc_type.__name__,
            exc_value,
            tb_list
            )

        full_message = "\n\n".join(filter(None, [message, formatted]))

        return Message(
            title=title,
            text=full_message,
            level=Level.ERROR,
            info_storage=info_store
        )


class TerminationMessageFactory:
    """
    Message Builder Terminatiom
    """
    @staticmethod
    def create(
        info: str = "",
        info_store: str = "",
    ) -> Message:
        base = get_message(MESSAGE_TEXT, "TERMINATION")

        parts = [base]
        if info:
            parts.append(info)

        parts.append(StackTraceFormatter.format())

        return Message(
            title=MESSAGE_TITLE,
            text="\n\n".join(parts),
            level=Level.ERROR,
            info_storage=info_store
        )


class MessageDispatcher:
    """
    Dispatches message
    """
    def dispatch(self, message: Message):
        raise NotImplementedError


class BankDispatcher(MessageDispatcher):

    def dispatch(self, message: Message):
        bankdata_informations_append(message.level, message.text)


class TransactionDispatcher(MessageDispatcher):

    def dispatch(self, message: Message):
        transaction_informations_append(message.level, message.text)


class PricesDispatcher(MessageDispatcher):

    def dispatch(self, message: Message):
        prices_informations_append(message.level, message.text)


class HoldingDispatcher(MessageDispatcher):

    def dispatch(self, message: Message):
        holding_informations_append(message.level, message.text)


class PrintDispatcher(MessageDispatcher):

    def dispatch(self, message: Message):
        print(message.text)


class GuiDispatcher(MessageDispatcher):

    def dispatch(self, message: Message):
        window = Tk()
        window.withdraw()
        window.title(message.title)

        try:
            if message.level == Level.ERROR:
                messagebox.showerror(
                    title=message.title,
                    message=self.extend_message_len(message),
                )
            else:
                if not message.info_storage:
                    messagebox.showinfo(
                        title=message.title,
                        message=self.extend_message_len(message),
                    )

        finally:
            destroy_widget(window)

    def extend_message_len(self,  message: Message):
        """
        returns possibly extended message
        """
        try:
            title_len = max(len(x) for x in list(message.title.splitlines()))
            message_len = max(len(x) for x in list(message.text.splitlines()))
            if title_len > message_len:
                return message.text + '\n' + ' ' * title_len
            else:
                return message.text
        except Exception:
            return message.text


class DispatcherRouter():
    """
    Central routing logic.
    """

    def __init__(self):
        self.gui = GuiDispatcher()
        self.print = PrintDispatcher()
        self.bank = BankDispatcher()
        self.prices = PricesDispatcher()
        self.transaction = TransactionDispatcher()
        self.holding = HoldingDispatcher()

    def route(self, message: Message):
        if is_main_thread():
            self.gui.dispatch(message)
        else:
            if not message.info_storage:
                message.info_storage = InfoStorage.BANK

        if message.info_storage == InfoStorage.BANK:
            self.bank.dispatch(message)
        elif message.info_storage == InfoStorage.PRICES:
            self.prices.dispatch(message)
        elif message.info_storage == InfoStorage.TRANSACTION:
            self.transaction.dispatch(message)
        elif message.info_storage == InfoStorage.HOLDING:
            self.holding.dispatch(message)
        elif not is_main_thread():
            self.print.dispatch(message)


class MessageBoxException:
    """
    Displays exceptions error message.
    """

    def __init__(
        self,
        message: str = "",
        title: str = MESSAGE_TITLE,
        info_storage=None,
    ):
        msg = ExceptionMessageFactory.from_current_exception(
            message=message,
            title=title,
        )
        DispatcherRouter().route(msg)


class MessageBoxInfo:
    """
    Displays an informational message.
    """

    def __init__(
        self,
        message: str = "",
        title: str = MESSAGE_TITLE,
        information=decl.INFORMATION,
        info_storage=None,
    ):
        msg = InformationMessageFactory.create(
            message=message,
            title=title,
            information=information,
            info_store=info_storage,
        )
        DispatcherRouter().route(msg)


class MessageBoxError:
    """
    Displays an error message.
    No termination if explicitly requested.
    """

    def __init__(
        self,
        message: str = "",
        title: str = MESSAGE_TITLE,
        terminate: bool = True,
        info_storage=InfoStorage.BANK,
    ):

        msg = Message(
            title=title,
            text=message,
            level=Level.ERROR,
            info_storage=info_storage,
        )
        if terminate:
            MessageBoxTermination(info=message, info_storage=info_storage)
        else:
            DispatcherRouter().route(msg)


class MessageBoxTermination:
    """
    Replacement for legacy MessageBoxTermination.
    Uses module factories and dispatchers.
    """

    def __init__(self, info: str = "", info_storage=InfoStorage.BANK, bank=None):
        try:
            # 1. Build termination message
            message = TerminationMessageFactory.create(
                info=info,
                info_store=info_storage,
            )

            # Prepare text: if a 'bank' object is supplied, prepend its name/iban
            new_text = message.text
            final_info_storage = message.info_storage

            if bank is not None:
                bank_name = getattr(bank, "bank_name", "") or ""
                bank_iban = getattr(bank, "iban", "") or ""
                bank_parts = " - ".join(p for p in (bank_name, bank_iban) if p)
                if bank_parts:
                    new_text = f"{bank_parts}\n\n{new_text}"
                final_info_storage = InfoStorage.BANK

            # If caller explicitly passed info_storage as InfoStorage, prefer it
            if isinstance(info_storage, InfoStorage):
                final_info_storage = info_storage

            # Message is frozen dataclass -> create a new Message with adjusted fields
            msg_with_bank = Message(
                title=message.title,
                text=new_text,
                level=Level.ERROR,
                info_storage=final_info_storage,
            )

            # 2. Dispatch message
            DispatcherRouter().route(msg_with_bank)

        finally:
            # 3. Hard termination only from main thread
            if is_main_thread():
                sys.exit()


class MessageBoxAsk:
    """
    Yes / No dialog.
    Returns True if YES.
    """

    def __init__(self, message: str = "", title: str = MESSAGE_TITLE):
        self.result = False

        if not is_main_thread():
            # No GUI possible → safe default
            return

        window = Tk()
        window.withdraw()
        window.title(title)

        try:
            self.result = messagebox.askyesno(
                title=title,
                message=message,
                default="no"
            )
        finally:
            destroy_widget(window)


class ExitBankMenu(Exception):
    """
    wrap command instruction of the menu to suppress raise output to console
    using method self._safe_callback
    e.g.
    323:command= self._safe_callback(self.w_cust.appcustomizing))
    """
    pass
