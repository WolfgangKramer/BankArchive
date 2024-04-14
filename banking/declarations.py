#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 09.12.2019
__updated__ = "2024-03-28"
@author: Wolfgang Kramer
"""

from _datetime import date
from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal


PNS = {}
"""
-------------------------- Alpha Vantage Prices Constants -----------------------------------------------

"""
OUTPUTSIZE_COMPACT = 'compact'
OUTPUTSIZE_FULL = 'full'
"""
-------------------------- Constants -----------------------------------------------
"""
NOT_ASSIGNED = 'NA'
VALIDITY_DEFAULT = '9999-01-01'
FROM_BEGINNING_DATE = '1990-01-01'
PRICE_ADJUSTMENT_LIMIT = 3  # % threshold price in tables TRANSACTION/PRICES
"""
--------------------------- WebSites --------------------------------------------------
"""
BUNDESBANK_BLZ_MERKBLATT = b"https://www.bundesbank.de/resource/blob/602848/50cba8afda2b0b1442016101cfd7e084/mL/merkblatt-bankleitzahlendatei-data.pdf"
BUNDEBANK_BLZ_DOWNLOAD = b"https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592"
MSEDGE_DRIVER_DOWNLOAD = b"https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver"
FINTS_SERVER_ADDRESS = b"https://www.hbci-zka.de/register/prod_register.htm"

FRANKFURTER_BOERSE = b"https://www.boerse-frankfurt.de/aktien/suche"
BNPPARIBAS = b"https://www.derivate.bnpparibas.com/realtime"
ONVISTA = b"https://www.onvista.de/"
WWW_YAHOO = b"https://de.finance.yahoo.com/lookup"
ALPHA_VANTAGE_DOCUMENTATION = 'https://www.alphavantage.co/documentation/'
WEBSITES = {'Frankfurter Boerse': FRANKFURTER_BOERSE,
            'BNP Paribas': BNPPARIBAS,
            'onvista': ONVISTA,
            'YAHOO!': WWW_YAHOO,
            'AlphaVantage': ALPHA_VANTAGE_DOCUMENTATION}

FINTS_SERVER = " \n\nContains German Bank FINTS Server Address \nRegistrate to get CSV Files  with PIN/TAN-Bank Access URL from FINTS\n\nCSV File contains 28 Columns\nColumn B: CODE\nColumn Y: PIN/TAN URL in CSV-File "
"""
--------------------------- Messages --------------------------------------------------
"""
MESSAGE_TITLE = 'BANK ARCHIVE'
FORMS_TEXT = {
    'Adjust Prices': 'Adjustments'
}
MENU_TEXT = {
    'Show': 'Show',
    'WebSites': 'WebSites',
    'Alpha Vantage': 'Alpha Vantage Query',
    'Alpha Vantage Symbol Search': 'Alpha Vantage Symbol Search',
    'Frankfurter Boerse': 'Frankfurter Boerse',
    'Onvista': 'Onvista',
    'Boerse.de': 'Boerse.de',

    'Balances': 'Balances',

    'Statement': 'Statement',
    'Holding': 'Holding',

    'Download': 'Download',
    'All_Banks': 'All_Banks',
    'Prices': 'Prices',

    'Transfer': 'Transfer',

    'Database': 'Database',

    'Balances': 'Balances',
    'Holding Performance': 'Holding Performance',
    'Holding ISIN Comparision': 'Holding ISIN Comparision',
    'Prices ISINs': 'Prices',
    'Historical Prices': 'Historical Close Price',
    'Transaction Detail': 'Transaction Detail',
    'Profit Transactions incl. current Depot Positions': 'Profit Transactions incl. current Depot Positions',
    'Profit of closed Transactions': 'Profit of closed Transactions',

    'Acquisition Amount Table': 'Acquisition Amount Table',
    'ISIN Table': 'ISIN Table',
    'Holding_T': 'Holding_of_Transactions',
    'Transactions Table': 'Transactions Table',
    'Import Transactions': 'Transaction CSV_File',
    'Import Bankidentifier CSV-File': 'Bankidentifier CSV-File',
    'Import Server CSV-File': 'Server CSV-File',
    'Import Ticker Symbols': 'Ticker CSV-File',

    'Extras': "Extras",
    'Import MS_Access Data': 'Import MS_Access Data',
    'Update Portfolio Total Amount': 'Update Portfolio Total Amount',
    'Transactions': 'Transactions',
    'Check Transactions Pieces': 'Check Transactions Pieces',
    'Synchronize Transactions': 'Synchronize Transactions',

    'Customize': 'Customize',

    'New Bank': 'New Bank',
    'Delete Bank': 'Delete Bank',
    'Change Login Data': 'Change Login Data',
    'Synchronize': 'Synchronize',
    'Change Security Function': 'Change Security Function',
    'Refresh BankParameterData': 'Refresh BankParameterData',
    'Change FinTS Transaction Version': 'Change FinTS Transaction Version',
    'Show Data': 'Show Data',
    'Application INI File': 'Application INI File',
    'Refresh Alpha Vantage': 'Create Alpha Vantage Query Selection',
}

CODE_3010 = '3010'  # Download bank data,    no entries exist'
CODE_3040 = '3040'  # Download partially executed
CODE_0030 = '0030'  # Download not executed

MESSAGE_TEXT = {
    CODE_0030: 'Bank: {} \n Bank Account: {}  {}       \n     Download not executed,    use single downloading bank data',
    CODE_3040: 'Bank: {} \n Bank Account: {}  {}       \n     Download partially executed',
    'ACQUISITION_HEADER': '{}  ACQUISITION AMOUNT CHANGE {} in Period {} - {}',
    'ACQUISITION_HEADER_TABLE': 'ACQUISITION AMOUNT CHANGE in Period {} - {},  Click RowNumber',
    'ACQUISITION_AMOUNT': 'Bank: {} \n Bank Account: {}  {}  {}      \n     Acquisition Amount must be adjusted manually',
    'ALPHA_VANTAGE': 'DOWNLOAD Prices from ALPHA_VANTAGE ({}/{}) failed (see ERROR Message before)',
    'ALPHA_VANTAGE_REFRESH_RUN': 'AlphaVantage Functions Creation started',
    'ALPHA_VANTAGE_REFRESH': 'AlphaVantage Functions successfully created',
    'ALPHA_VANTAGE_ERROR': 'API Parameter Information not created',
    'ALPHA_VANTAGE_ERROR_MSG': 'AlphaVantage Error Message: \n{} \n\n Generated URl: \n{}',
    'ALPHA_VANTAGE_NO_DATA': 'AlphaVantage API returns no Data \n {}',
    'APP': 'APPLICATION and MARIDB Customizing Installation',
    'BANK_CODE_EXIST': 'Bank Code exists',
    'BANK_DATA_NEW': 'Created {} ({}. Next Step: SYNCHRONIZE Bank',
    'BANK_DATA_NEW_SCRAPER': 'Created {} ({})',
    'BANK_DELETED': 'DELETE BANK LOGIN DATA \nBankcode: {}',
    'BANK_LOGIN': 'Bank Scraper Login failed \nException: {} \nURL: {}\nPassword: {}\nUserName: {}',
    'CREDENTIALS': '{} Login failed',
    'CREDENTIALS_CHECK': '{} Checking Credentials',
    'CHECKBOX': 'Select at least one of the Check Box Icons',
    'CONN': 'Database Connection failed  \nMariaDBuser: {} \nMariaDBname: {}',
    'DATA_NO': '{} \n{} \nData not available',
    'DATA_SAVED': 'Data successfully saved',
    'DATA_SELECTION_PRICES': 'Prices Data Selection {} - {}',
    'DATABASE': 'D A T A B A S E:  {}',
    'DATABASE_REFRESH': 'Database Credentials changed \n You must restart Banking',
    'DATE': '{} invalid or missing (Format e.g. 2020-12-12)',
    'DATE_ADJUSTED': 'Price_Date not in Table Holding \n Adjusted by existing previous Date',
    'DATE_TODAY': '{} Less todays date',
    'DBLOGIN': 'Database Connection failed! \n Check Database LOGIN Parameter in CUSTOMIZINDG Application/MariaDB',
    'DECIMAL': 'Invalid Decimal Format Field {} e.g. 12345.00',
    'DELETE_ORIGINS': 'Cancel Insert in {}. Otherwise old Records with Origin {} will be deleted',
    'DOWNLOAD_BANK':  'BANK: {}    Download Bank Data started',
    'DOWNLOAD_ACCOUNT': 'Bank: {} \n Bank Account: {}  {}       \n     Download Bank Data of Account {}',
    'DOWNLOAD_DONE': 'BANK: {}   Data downloading finished',
    'DOWNLOAD_HOLDING': 'If BUY/SELL Transaction done after Download RUN\nStart Download Holding once more! \n',
    'DOWNLOAD_NOT_DONE': 'BANK: {}   Data downloading finished with E R R O R ',
    'DOWNLOAD_REPEAT': 'Download {} canceled by User! \n\nStart Download once more!',
    'DOWNLOAD_RUNNING': '{} Data Download running',
    'ENTRY': 'Enter Data',
    'FIXED': '{} MUST HAVE {} Characters ',
    'SEGMENT': '{} Account {}   Error_Code: {}   HIKAZ segment not received from Bank',
    'HITAN6': 'Bank: {} \n Bank Account: {}  {}       \n     Could not find HITAN6 task_reference',
    'HIUPD_EXTENSION': 'Bank: {} \n Bank Account: {}  {}       \n     IBAN {} received Bank Information: \n     {}',
    'HOLDING_T': '{} / {} HOLDING_T data created in period ({} - {})',
    'HOLDING_USE_TRANSACTION': 'Table TRANSACTION and Table PRICES used to show holding data',
    'HTTP': 'Server not connected! HTTP Status Code: {}\nBank: {}  Server: {}',
    'HTTP_INPUT': 'Server not valid or not available! HTTP Status Code: {}',
    'IBAN': 'IBAN invalid',
    'IMPORT_CSV': 'Import CSV_File into Table {}',
    'ISIN_DATA': 'Enter ISIN Data',
    'LENGTH': '{} Exceeds Length OF {} Characters',
    'LOAD_DATA': 'Data imported (Duplicates ignored) \nfrom File {}',
    'LOGGING_FILE': 'OS Error Logging_file',
    'LOGIN': 'LOGIN Data incomplete.   \nCustomizing e.g. synchronization LOGIN Data must be done \nBank_Code: {} (Key Error: {})',
    'LOGIN_SCRAPER': 'LOGIN Data incomplete.   \nCustomizing LOGIN Data/Scraping must be done \nBank: {} ({})',
    'MANDATORY': '{} is mandatory',
    'MARIADB_DUPLICATE': 'Duplicate Entry ignored\nSQL Statement: \n{} \n Error: \n{} \n Vars: \n{}',
    'MARIADB_ERROR_SQL': 'SQL_Statement\n {} \n\nVars\n {}',
    'MARIADB_ERROR': 'MariaDB Error\n{} \n {}',
    'MIN_LENGTH': '{} Must have a Length OF {} Characters',
    'NAME_INPUT': 'Enter Query Name (Name of Stored Procedure, allowed Chars [alphanumeric and _): ',
    'NAMING': 'Fix Naming. Allowed Characters: A-Z, a-z, 0-9, _',
    'NO_TURNOVER': 'Bank: {} \n Bank Account: {}  {}       \n     No new turnover',
    'NOTALLOWED': '{} is not allowed {}',
    'ORIGIN_SYMBOL_MISSING': 'No origin for symbol found. \n ISIN: {}  /  {} \n\n You must add origin symbol in Table ISIN',
    'OS_ERROR': 'Shelve File  {} not found',
    'OVERVIEW': 'BANK {}: OVERVIEW ALL ACOUNT BALANCES',
    'PAIN': 'SEPA Format pain.001.001.03 not found/allowed\nBank: {}',
    'Period':               'Period ({}, {})',
    'PERIOD': '{} ({}) \n Bank Account: {} {}      \n Account Postings only available from {} onwards',
    'PIN': 'PIN missing! \nBank: {} ({})',
    'PIN_INPUT': 'Enter PIN   {} ({}) ',
    'PRICES_ADJUSTED': '{} ISIN: {} Transaction Date: {} \n Price in tables TRANSACTION and PRICES  differs by {}%',
    'PRICES_DELETED': '{}:  Prices deleted\n\n Used Ticker Symbol {} \n ISIN: {}',
    'PRICES_LOADED': '{}:  Price loaded for Period {}\n\n Used Ticker Symbol {} \n ISIN: {}',
    'PRICES_NO': '{}:  No new Prices found\n\n Used Ticker Symbol {} \n ISIN: {}  {}',
    'PRICES_PERIOD': '{} / {} /{} Prices missing in Period ({} - {})',
    'PRODUCT_ID': 'Product_ID missing, No Bank Access possible\n Get your Product_Id: https://www.hbci-zka.de/register/prod_register.htm',
    'RADIOBUTTON': 'Select one of SELECT the RadioButtons',
    'RESPONSE': 'Got unvalid response from bank',
    'SCROLL': 'Scroll forward: CTRL+RIGHT   Scroll backwards: CTRL+LEFT',
    'SEGMENT': '{} Account {}   Segment {} not received from Bank, ERRORCODE: {}',
    'SEGMENT_VERSION': 'Segment {}{} Version {} not implemented',
    'SELECT': 'Enter your Selection',
    'SELECT_ACCESS_DB': 'Select MS ACCESS Database File',
    'SELENIUM_DRIVER': 'Select Driver of choosen Explorer',
    'SEPA_CRDT_TRANSFER': 'SEPA Credit Transfer \nBank:    {}  \nAccount:    {} ({})',
    'SQLALCHEMY_ERROR': "Error Calling SQLAlchemy {}:    {}",
    'SHELVE': '\n LOGON Data, Synchronization Data >>>>> BANK: {}\n\n',
    'STACK': 'Method\n {} \n\nLine\n {} \n\nModule\n {}',
    'SYMBOL_MISSING_ALL': '{} \n \n No ticker/symbol found in Table ISIN. \n You must add ticker symbols in Table ISIN',
    'SYMBOL_MISSING': 'No ticker/symbol found. \n ISIN: {}  /  {} \n\n You must add ticker symbol in Table ISIN',
    'SYMBOL_USED': 'Symbol already used in {}',
    'SYNC': 'Synchronization Data incomplete    \nSynchronization must be done \nBank: {} ',
    'SYNC_START': 'Next Stepp: You must start Synchronization Bank: {} ',
    'TABLE': ' Table {}',
    'TASK_DONE': 'Task finished.',
    'TASK_WARNING': 'Finished with Warnings',
    'TAN_INPUT': 'Enter TAN  {} ({}): ',
    'TAN_CANCEL': 'Input TAN canceled, request aborted',
    'TERMINATION': 'FinTS MariaDB Banking Termination',
    'THREAD': 'Task {} aborted. No Dialogue. Its no mainthread',
    'THREAD_RUNNING': 'Background Job still running',
    'TRANSACTION_CHECK': '{} Difference Pieces of Transactions / Pieces of Portfolio',
    'TRANSACTION_CLOSED_EMPTY': ' No Closed Transactions in Period {} - {}',
    'TRANSACTION_HEADER_CHG': 'CHANGE TRANSACTIONS',
    'TRANSACTION_HEADER_DEL_MESSAGE': 'DELETE TRANSACTION\n{}  Price_Date {}  Counter {}',
    'TRANSACTION_HEADER_NEW': 'NEW TRANSACTION',
    'TRANSACTION_HEADER_SYNC_TABLE': 'SYNCHRONIZE TRANSACTIONS',
    'TRANSACTION_HEADER_TABLE': 'TRANSACTIONS  CHANGE in Period {} - {},  Click RowNumber',
    'TRANSACTION_NO': ' No Transactions in Period {} - {}',
    'TRANSACTION_PIECES_NEGATIVE': 'Transactions faulty! On {} cumulated Pieces negative!',
    'TRANSACTION_PIECES_PORTFOLIO': ' Difference Pieces of Transactions / Pieces of Portfolio',
    'TRANSACTION_TITLE': '{}  TRANSACTIONS  {} ',
    'TWOSTEP': 'Select one of the Security Functions \n Only Two-Step TAN Procedure \n SCA Strong Customer Authentication',
    'UNEXCEPTED_ERROR': 'E X C E P T I O N    E R R O R  !\n\nMODULE: {}\n\nLINE  of EXCEPTION ERROR Call: {}\n\nMETHOD: {}\n\nTYPE:\n {} \n\nVALUE:  {} \n\nTRACEBACK:\n {}',
    'VERSION_TRANSACTION': 'TRANSACTION HK{}{} not available',
    'WEBDRIVER': 'Installing {} WEB Driver failed\n\n{}',
    'WEBDRIVER_INSTALL': '{} WEB Driver installed to project.root/.wdm'
}
"""
--------------------------- FinTS --------------------------------------------------
"""
SYSTEM_ID_UNASSIGNED = '0'
CUSTOMER_ID_ANONYMOUS = '9999999999'
DIALOG_ID_UNASSIGNED = '0'
PRODUCT_ID = 'Not Valid'
VERSION_TRANSACTION = ['HKAKZ6', 'HKAKZ7',
                       'HKSAL6', 'HKSAL7', 'HKWPD5', 'HKWPD6']
"""
-------------------------------- MariaDB Tables ----------------------------------
"""
DATABASES = []
BANKIDENTIFIER = 'bankidentifier'
HOLDING = 'holding'
HOLDING_T = 'holding_t'  # Source is table TRANSACTION and PRICES
HOLDING_VIEW = 'holding_view'
HOLDING_T_VIEW = 'holding_t_view'
HOLDING_SYMBOL = 'holding_symbol'
SERVER = 'server'
STATEMENT = 'statement'
TRANSACTION = 'transaction'
TRANSACTION_VIEW = 'transaction_view'
ISIN = 'isin'
ISIN_NAME = 'isin_name'
ISIN_WITH_TICKER = 'isin_with_ticker'
PRICES = 'prices'
PRICES_ISIN_VIEW = 'prices_isin_view'
"""
 ------------------Shelve_Files------------------------------------------------
"""
DIRECTORY = 'C:/TEMP/PYTHON'
BANK_MARIADB_INI = 'BANKING'
UNKNOWN = 'UNKNOWN'
KEY_PRODUCT_ID = 'PRODUCT_ID'
KEY_ALPHA_VANTAGE = 'ALPHA_VANTAGE'
KEY_DIRECTORY = 'DIRECTORY'
KEY_DRIVER = 'DRIVER'
KEY_EXPLORER = 'EXPLORER'
KEY_MARIADB_NAME = 'MARIADB_NAME'
KEY_MARIADB_USER = 'MARIADB_USER'
KEY_MARIADB_PASSWORD = 'MARIADB_PASSWORD'
KEY_ALPHA_VANTAGE_PRICE_PERIOD = 'ALPHA_VANTAGE_PRICE_PERIOD'
KEY_SHOW_MESSAGE = 'SHOW_MESSAGE'
KEY_LOGGING = 'LOGGING'
KEY_THREADING = 'THREADING'
KEY_MS_ACCESS = 'MS_ACCESS'
KEY_GEOMETRY = 'GEOMETRY'
KEY_ALPHA_VANTAGE_FUNCTION = 'ALPHA_VANTAGE_FUNCTION'
KEY_ALPHA_VANTAGE_PARAMETER = 'ALPHA_VANTAGE_PARAMETER'
# True: Table HOLDING in Use else Table HOLDING_T
KEY_HOLDING_SWITCH = 'HOLDING_SWITCH'
APP_SHELVE_KEYS = [
    KEY_PRODUCT_ID, KEY_ALPHA_VANTAGE, KEY_DIRECTORY, KEY_LOGGING, KEY_MS_ACCESS,
    KEY_MARIADB_NAME, KEY_MARIADB_USER, KEY_MARIADB_PASSWORD,
    KEY_EXPLORER, KEY_DRIVER, KEY_SHOW_MESSAGE, KEY_THREADING, KEY_ALPHA_VANTAGE_PRICE_PERIOD,
    KEY_ALPHA_VANTAGE_FUNCTION, KEY_ALPHA_VANTAGE_PARAMETER, KEY_HOLDING_SWITCH
]
TRUE = 'ON'
FALSE = 'OFF'
SWITCH = [TRUE, FALSE]
# FALSE: HOLDING uses Table PRICES   TRUE: HOLDING uses TABLE HOLDING,
HOLDING_SWITCH = [HOLDING, HOLDING_T]
KEY_ACCOUNTS = 'ACCOUNTS'
KEY_BANK_CODE = 'BANK_CODE'
KEY_BANK_NAME = 'BANK_NAME'
KEY_BPD = 'BPD_VERSION'
KEY_PIN = 'PIN'
KEY_BIC = 'BIC'
KEY_SECURITY_FUNCTION = 'SECURITY_FUNCTION'
KEY_VERSION_TRANSACTION = 'VERSION_TRANSACTION'
KEY_VERSION_TRANSACTION_ALLOWED = 'VERSION_TRANSACTION_ALLOWED'
KEY_SEPA_FORMATS = 'SUPPORTED_SEPA_FORMATS'
KEY_SERVER = 'SERVER'
KEY_IDENTIFIER_DELIMITER = 'KEY_IDENTIFIER_DELIMITER'
KEY_STORAGE_PERIOD = 'STORAGE_PERIOD'
KEY_SYSTEM_ID = 'SYSTEM_ID'
KEY_TAN = 'TAN'
KEY_TWOSTEP = 'TWOSTEP_PARAMETERS'
KEY_UPD = 'UPD_VERSION'
KEY_USER_ID = 'USER_ID'
KEY_MIN_PIN_LENGTH = 'MIN_PIN_LENGTH'
KEY_MAX_PIN_LENGTH = 'MAX_PIN_LENGTH'
KEY_MAX_TAN_LENGTH = 'MAX_TAN_LENGTH'
KEY_TAN_REQUIRED = 'TRANSACTION_TANS_REQUIRED'
SHELVE_KEYS = [
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC,
    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_SECURITY_FUNCTION, KEY_VERSION_TRANSACTION,
    KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_SEPA_FORMATS, KEY_SYSTEM_ID,
    KEY_TWOSTEP, KEY_ACCOUNTS, KEY_UPD, KEY_BPD, KEY_STORAGE_PERIOD,
    KEY_MIN_PIN_LENGTH, KEY_MAX_PIN_LENGTH, KEY_MAX_TAN_LENGTH, KEY_TAN_REQUIRED,
]
MIN_PIN_LENGTH = 3
MAX_PIN_LENGTH = 20
MAX_TAN_LENGTH = 20
MIN_TAN_LENGTH = 1
"""
 ------------------ACCOUNTS Field Keys in Shelve_Files------------------------------------------------
"""
KEY_ACC_IBAN = 'IBAN'
KEY_ACC_ACCOUNT_NUMBER = 'ACCOUNT_NUMBER'
KEY_ACC_SUBACCOUNT_NUMBER = 'SUBACCOUNT_NUMBER'
KEY_ACC_BANK_CODE = 'BANK_CODE'
KEY_ACC_CUSTOMER_ID = 'CUSTOMER_ID'
KEY_ACC_TYPE = 'TYPE'
KEY_ACC_CURRENCY = 'CURRENCY'
KEY_ACC_OWNER_NAME = 'OWNER_NAME'
KEY_ACC_PRODUCT_NAME = 'PRODUCT_NAME'
KEY_ACC_ALLOWED_TRANSACTIONS = 'ALLOWED_TRANSACTIONS'
KEY_ACC_KEYS = [
    KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS,
    KEY_ACC_BANK_CODE, KEY_ACC_CURRENCY, KEY_ACC_CUSTOMER_ID, KEY_ACC_OWNER_NAME,
    KEY_ACC_PRODUCT_NAME, KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_TYPE
]
"""
-------------------HBCI Server ---------------------------------------------------
"""
HTTP_CODE_OK = [200, 405]
"""
---------------------------- S.W.I.F.T. Formats MT940, MT535, MT536 -------------
"""
ORIGIN = '_BANKDATA_'
DEBIT = 'D'
CREDIT = 'C'
PERCENT = 'PCT'
EURO = 'EUR'
CURRENCY = [EURO]  # table statement and holding (prices see below)
CURRENCY_EXTENDED = CURRENCY
# table statement and holding (prices see below) exteneded by PCT (bonds)
CURRENCY_EXTENDED.append(PERCENT)
FAMT = 'FAMT'
UNIT = 'UNIT'
TYPES = [FAMT, UNIT]
TRANSACTION_RECEIPT = 'RECE'
TRANSACTION_DELIVERY = 'DELI'
TRANSACTION_TYPES = [TRANSACTION_RECEIPT, TRANSACTION_DELIVERY]
"""
--------------- ISIN field values -------------
"""
YAHOO = 'Yahoo!'
ALPHA_VANTAGE = 'AlphaVantage'
ONVISTA = 'Onvista'
ORIGIN_SYMBOLS = [NOT_ASSIGNED, ALPHA_VANTAGE, YAHOO]
CURRENCIES = [EURO, 'USD', 'AUD', 'CAD', 'CHF',
              'GBP', 'JPY']  # ISIN currency of prices
"""
--------------- Alpha Vantage field values -------------
"""
JSON_KEY_ERROR_MESSAGE = 'Error Message'
JSON_KEY_META_DATA = 'Meta Data'
TIME_SERIES_DAILY = 'TIME_SERIES_DAILY'
TIME_SERIES_DAILY_ADJUSTED = 'TIME_SERIES_DAILY_ADJUSTED'
TIME_SERIES_INTRADAY = 'TIME_SERIES_INTRADAY'
TIME_SERIES_WEEKLY = 'TIME_SERIES_WEEKLY'
TIME_SERIES_WEEKLY_ADJUSTED = 'TIME_SERIES_WEEKLY_ADJUSTED'
TIME_SERIES_MONTHLY = 'TIME_SERIES_MONTHLY'
TIME_SERIES_WEEKLY_ADJUSTED = 'TIME_SERIES_WEEKLY_ADJUSTED'
ALPHA_VANTAGE_PRICE_PERIOD = [TIME_SERIES_INTRADAY,
                              TIME_SERIES_DAILY, TIME_SERIES_DAILY_ADJUSTED,
                              TIME_SERIES_WEEKLY, TIME_SERIES_WEEKLY_ADJUSTED,
                              TIME_SERIES_MONTHLY, TIME_SERIES_WEEKLY_ADJUSTED]
ALPHA_VANTAGE_REQUIRED = ['symbol', 'interval', 'keywords', 'from_currency', 'to_currency', 'from_symbol',
                          'to_symbol', 'market', 'time_period', 'series_type']
ALPHA_VANTAGE_REQUIRED_COMBO = {'interval': ['1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly'],
                                'time_period': [60, 200],
                                'series_type': ['close', 'open', 'high', 'low']
                                }
ALPHA_VANTAGE_OPTIONAL_COMBO = {'outputsize': ['compact', 'full']
                                }
"""
-------------------------- Forms -----------------------------------------------
"""
WIDTH_TEXT = 170
HEIGHT_TEXT = 60
HEADER = 'HEADER'
INFORMATION = 'INFORMATION: '
WARNING = 'WARNING:     '
ERROR = 'ERROR:       '
LIGHTBLUE = 'LIGHTBLUE'
SHOW_MESSAGE = [INFORMATION, WARNING, ERROR]
FN_DATE = 'DATE'
FN_TO_DATE = 'TO_Date'
FN_FROM_DATE = 'FROM_Date'
# FN_GET_METHOD = 'Getting_Method'
FN_BANK_NAME = 'BANK_NAME'
FN_FIELD_NAME = 'Field_Name'
FN_PROCUDURE_NAME = 'Procedure_Name'
FN_PERCENTAGE = 'Percentage'
FN_Y_AXE = 'Y_AXE'
FN_DATA_MODE = 'DATA_MODE'
FN_SHARE = 'SHARE'
FN_PROPORTIONAL = 'PROPORTIONAL'
FN_ABSOLUTE = 'ABSOLUTE'
FN_TOTAL = 'TOTAL'
FN_TOTAL_PERCENT = '% Total'
FN_PERIOD_PERCENT = 'Period'
FN_DAILY_PERCENT = 'Day'
FN_PROFIT = 'Profit'
FN_PROFIT_LOSS = 'Profit&Loss'
FN_PROFIT_CUM = 'Performance'
FN_PIECES_CUM = 'cumPieces'
FN_SOLD_PIECES = 'sold_pieces'
FN_ALL_BANKS = 'ALL BANKS '
FN_COLUMNS_EURO = [FN_TOTAL, FN_PROFIT,
                   FN_PROFIT_LOSS, FN_PROFIT_CUM]
FN_COLUMNS_PERCENT = [FN_TOTAL_PERCENT,
                      FN_PERIOD_PERCENT, FN_DAILY_PERCENT]
Y_AXE_PROFIT = 'profit'
Y_AXE = ['market_price', 'acquisition_price', 'pieces',
         'total_amount', 'acquisition_amount', Y_AXE_PROFIT]
SEPA_CREDITOR_NAME = 'Creditor_Name'
SEPA_CREDITOR_IBAN = 'Creditor_IBAN'
SEPA_CREDITOR_BIC = 'Creditor_BIC'
SEPA_CREDITOR_BANK_NAME = 'Creditor_Bank_Name'
SEPA_CREDITOR_BANK_LOCATION = 'CREDITOR_Bank_Location'
SEPA_AMOUNT = 'Amount'
SEPA_PURPOSE = 'Purpose'
SEPA_PURPOSE_1 = 'Purpose_1'
SEPA_PURPOSE_2 = 'Purpose_2'
SEPA_REFERENCE = 'Reference'
SEPA_EXECUTION_DATE = 'Execution_Date'
NOTPROVIDED = 'NOTPROVIDED'
"""
-------------------------- Forms: Select ... ----------------------------------------
"""
EQUAL = 'EQUAL'
CONTAINS = 'CONTAINS'
START_WITH = 'START_WITH'
END_WITH = 'END_WITH'
GREATER = 'GREATER'
LESS = 'LESS'
OPERATORS = [EQUAL, CONTAINS, START_WITH, END_WITH, GREATER, LESS]
"""
-------------------------------- MariaDB Tables --------------------------------------------------------
"""
# CREATE_...   copied from HEIDI SQL Create-Tab and IF NOT EXISTS added
# additionally with VIEWs: ALTER ALGORITHM changed to CREATE ALGORITHM
CREATE_BANKIDENTIFIER = "CREATE TABLE IF NOT EXISTS `bankidentifier` (\
    `code` CHAR(8) NOT NULL COMMENT 'Bank_Code (BLZ)' COLLATE 'latin1_swedish_ci',\
    `payment_provider` CHAR(1) NOT NULL COMMENT 'Merkmal, ob bankleitzahlführender Zahlungsdienstleister >1< oder nicht >2<. Maßgeblich sind nur Datensätze mit dem Merkmal >1<' COLLATE 'latin1_swedish_ci',\
    `payment_provider_name` VARCHAR(70) NOT NULL COLLATE 'latin1_swedish_ci',\
    `postal_code` CHAR(5) NOT NULL COLLATE 'latin1_swedish_ci',\
    `location` VARCHAR(70) NOT NULL DEFAULT '' COMMENT 'Bank Location' COLLATE 'latin1_swedish_ci',\
    `name` VARCHAR(70) NOT NULL DEFAULT '' COMMENT 'Bank Name' COLLATE 'latin1_swedish_ci',\
    `pan` CHAR(5) NOT NULL COMMENT ' Primary Account Number' COLLATE 'latin1_swedish_ci',\
    `bic` VARCHAR(11) NOT NULL DEFAULT '' COMMENT 'Bank Identifier Code (BIC) (S.W.I.F.T.)' COLLATE 'latin1_swedish_ci',\
    `check_digit_calculation` CHAR(2) NOT NULL COMMENT 'Kennzeichen für Prüfzifferberechnungsmethode ' COLLATE 'latin1_swedish_ci',\
    `record_number` CHAR(6) NOT NULL COLLATE 'latin1_swedish_ci',\
    `change_indicator` CHAR(1) NOT NULL COMMENT 'Merkmal, ob bankleitzahlführender Zahlungsdienstleister >1< oder nicht >2<). Maßgeblich sind nur Datensätze mit dem Merkmal >1<' COLLATE 'latin1_swedish_ci',\
    `code_deletion` CHAR(50) NOT NULL COMMENT 'Hinweis auf eine beabsichtigte Bankleitzahllöschung Das Feld enthält das Merkmal >0< (keine Angabe) oder >1< (Bankleitzahl im Feld 1 ist zur' COLLATE 'latin1_swedish_ci',\
    `follow_code` CHAR(8) NOT NULL COMMENT 'Hinweis auf Nachfolge-Bankleitzahl' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`code`, `payment_provider`) USING BTREE,\
    INDEX `BIC` (`bic`) USING BTREE\
)\
COMMENT='Contains German Banks\r\n\r\nSource: https://www.bundesbank.de/resource/blob/602848/50cba8afda2b0b1442016101cfd7e084/mL/merkblatt-bankleitzahlendatei-data.pdf\r\n\r\nDownload CSV: https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_HOLDING = "CREATE TABLE IF NOT EXISTS `holding` (\
    `iban` CHAR(22) NOT NULL COMMENT ':97A:: DepotKonto' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL DEFAULT '2019-01-01' COMMENT ':98A:: M Datum (und Uhrzeit), auf dem/der die Aufstellung basiert',\
    `ISIN` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN-Kennung' COLLATE 'latin1_swedish_ci',\
    `price_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':90B:: ISO 4217-Währungscode' COLLATE 'latin1_swedish_ci',\
    `market_price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':90A:: Marktpreis (Prozentsatz)  :90B:: Markpreis (Börsenkurs)',\
    `acquisition_price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':70E:: Einstandspreis',\
    `pieces` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT ':93B:: Stückzahl oder Nennbetrag',\
    `amount_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':19A:: ISO 4217-Währungscode Depotwert' COLLATE 'latin1_swedish_ci',\
    `total_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':19A:: Depotwert',\
    `total_amount_portfolio` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Deportwert Gesamt',\
    `acquisition_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Einstandswert',\
    `exchange_rate` DECIMAL(14,6) NULL DEFAULT '0.000000' COMMENT ':92B:: Kurs/Satz',\
    `exchange_currency_1` CHAR(3) NULL DEFAULT NULL COMMENT ':92B:: Erste Währung' COLLATE 'latin1_swedish_ci',\
    `exchange_currency_2` CHAR(3) NULL DEFAULT NULL COMMENT ':92B:: Zweite Wöhrung' COLLATE 'latin1_swedish_ci',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'Datensatz Herkunft:  _BANKDATA_  Download Bank' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`iban`, `price_date`, `ISIN`) USING BTREE,\
    INDEX `ISIN_KEY` (`ISIN`) USING BTREE\
)\
COMMENT='MT 535\r\nVersion: SRG 1998\r\nStatement of Holdings; basiert auf S.W.I.F.T. Standards Release Guide 1998\r\n\r\nKapitel:\r\nB\r\nVersion:\r\nV3.0, Final Version\r\nFinancial Transaction Services (FinTS)\r\nDokument: Messages - Finanzdatenformate\r\nSeite:\r\n150\r\nStand:\r\n06.08.2010\r\nKapitel: S.W.I.F.T.-Formate\r\nAbschnitt: 13BMT 53'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_HOLDING_T = "CREATE TABLE IF NOT EXISTS `holding_t` (\
    `iban` CHAR(22) NOT NULL COMMENT ':97A:: DepotKonto' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL DEFAULT '2019-01-01' COMMENT ':98A:: M Datum (und Uhrzeit), auf dem/der die Aufstellung basiert',\
    `ISIN` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN-Kennung' COLLATE 'latin1_swedish_ci',\
    `price_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':90B:: ISO 4217-Währungscode' COLLATE 'latin1_swedish_ci',\
    `market_price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':90A:: Marktpreis (Prozentsatz)  :90B:: Markpreis (Börsenkurs)',\
    `acquisition_price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':70E:: Einstandspreis',\
    `pieces` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':93B:: Stückzahl oder Nennbetrag',\
    `amount_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':19A:: ISO 4217-Währungscode Depotwert' COLLATE 'latin1_swedish_ci',\
    `total_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':19A:: Depotwert',\
    `total_amount_portfolio` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Deportwert Gesamt',\
    `acquisition_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Einstandswert',\
    `exchange_rate` DECIMAL(14,6) NULL DEFAULT '0.000000' COMMENT ':92B:: Kurs/Satz',\
    `exchange_currency_1` CHAR(3) NULL DEFAULT NULL COMMENT ':92B:: Erste Währung' COLLATE 'latin1_swedish_ci',\
    `exchange_currency_2` CHAR(3) NULL DEFAULT NULL COMMENT ':92B:: Zweite Wöhrung' COLLATE 'latin1_swedish_ci',\
    `origin` VARCHAR(50) NULL DEFAULT '_TRANSACTION_' COMMENT 'Datensatz Herkunft: TRANSACTION  generated using tables prices and transaction' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`iban`, `price_date`, `ISIN`) USING BTREE,\
    INDEX `ISIN_KEY` (`ISIN`) USING BTREE\
)\
COMMENT='Holdings generated using Transactions'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_HOLDING__T_VIEW = "CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW IF NOT EXISTS `holding_t_view` AS SELECT * FROM  holding_t INNER JOIN isin_name USING(isin)  ;"
CREATE_HOLDING_VIEW = "CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW IF NOT EXISTS  `holding_view` AS SELECT * FROM holding INNER JOIN isin_name USING(isin)  ;"
CREATE_ISIN = "CREATE TABLE  IF NOT EXISTS   `isin` (\
    `name` VARCHAR(35) NOT NULL DEFAULT 'NA' COMMENT ':35B:: Wertpapierbezeichnung' COLLATE 'latin1_swedish_ci',\
    `ISIN` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN-Kennung' COLLATE 'latin1_swedish_ci',\
    `type` VARCHAR(50) NOT NULL DEFAULT 'SHARE' COMMENT 'SHARE, BOND, SUBSCRIPTION RIGHT' COLLATE 'latin1_swedish_ci',\
    `validity` DATE NOT NULL DEFAULT '9999-01-01' COMMENT 'Isin valid to this date',\
    `wkn` CHAR(6) NOT NULL DEFAULT 'NA' COMMENT 'Die Wertpapierkennnummer (WKN, vereinzelt auch WPKN oder WPK abgekürzt) ist eine in Deutschland verwendete sechsstellige Ziffern- und Buchstabenkombination zur Identifizierung von Wertpapieren (Finanzinstrumenten). Setzt man drei Nullen vor die WKN, so erhält man die neunstellige deutsche National Securities Identifying Number (NSIN) des jeweiligen Wertpapiers.' COLLATE 'latin1_swedish_ci',\
    `symbol` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'ticker symbol' COLLATE 'latin1_swedish_ci',\
    `origin_symbol` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'origin of symbol: Yahoo or AlphaVantage' COLLATE 'latin1_swedish_ci',\
    `adjustments` VARCHAR(500) NOT NULL DEFAULT '{}' COMMENT 'Json String (contains adjustment factors e.g. splits, special dividends, ...) in  json format{symbol: {date_to: (r-factor,used) ...., }}' COLLATE 'latin1_swedish_ci',\
    `currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT 'Currency Code' COLLATE 'latin1_swedish_ci',\
    `comment` TEXT NULL DEFAULT NULL COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`name`) USING BTREE,\
    UNIQUE INDEX `ISIN` (`ISIN`) USING BTREE\
)\
COMMENT='ISIN informations'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_ISIN_NAME = "CREATE ALGORITHM  = UNDEFINED SQL SECURITY DEFINER VIEW IF NOT EXISTS  `isin_name` AS SELECT isin, name FROM  isin WHERE validity = (SELECT MAX(validity) FROM isin)  ;"
CREATE_PRICES = "CREATE TABLE IF NOT EXISTS `prices` (\
    `symbol` VARCHAR(50) NOT NULL DEFAULT 'NA' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL DEFAULT '2000-01-01',\
    `open` DECIMAL(14,6) NULL DEFAULT '0.000000',\
    `high` DECIMAL(14,6) NULL DEFAULT '0.000000',\
    `low` DECIMAL(14,6) NULL DEFAULT '0.000000',\
    `close` DECIMAL(14,6) NULL DEFAULT '0.000000',\
    `volume` DECIMAL(14,2) NULL DEFAULT '0.00',\
    `adjclose` DECIMAL(14,6) NULL DEFAULT '0.000000',\
    `histclose` DECIMAL(14,6) NULL DEFAULT '0.000000' COMMENT 'historical value without adjustments',\
    `dividends` DECIMAL(14,2) NULL DEFAULT '0.00',\
    `splits` DECIMAL(14,2) UNSIGNED NULL DEFAULT '0.00',\
    `origin` VARCHAR(50) NULL DEFAULT 'NA' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`symbol`, `price_date`) USING BTREE\
)\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_PRICES_ISIN_VIEW = "CREATE ALGORITHM  = UNDEFINED SQL SECURITY DEFINER VIEW IF NOT EXISTS  `prices_isin_view` AS SELECT * FROM prices INNER JOIN isin USING (symbol);"
CREATE_SERVER = "CREATE TABLE IF NOT EXISTS `server` (\
    `code` CHAR(8) NOT NULL COMMENT 'Bankleitzahl' COLLATE 'latin1_swedish_ci',\
    `server` VARCHAR(100) NULL DEFAULT NULL COMMENT 'PIN/TAN-Access URL' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`code`) USING BTREE\
)\
COMMENT='German Bank PIN/TAN-Access URL'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_STATEMENT = "CREATE TABLE IF NOT EXISTS `statement` (\
    `iban` CHAR(22) NOT NULL COMMENT 'IBAN' COLLATE 'latin1_swedish_ci',\
    `entry_date` DATE NOT NULL COMMENT ':61: Buchungsdatum MMTT',\
    `counter` SMALLINT(5) NOT NULL DEFAULT '0',\
    `date` DATE NOT NULL COMMENT ':61: UMSATZ Valuta Datum',\
    `guessed_entry_date` DATE NULL DEFAULT NULL COMMENT ':61: Buchungsdatum MMTT',\
    `status` CHAR(2) NOT NULL COMMENT ':61:Soll/Habenkennung C,D,RC,RD' COLLATE 'latin1_swedish_ci',\
    `currency_type` CHAR(1) NULL DEFAULT NULL COMMENT ':61:Waehrungsart' COLLATE 'latin1_swedish_ci',\
    `currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':60F:Waehrung' COLLATE 'latin1_swedish_ci',\
    `amount` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00',\
    `id` CHAR(4) NOT NULL DEFAULT 'NMSC' COMMENT ':61:Buchungsschluessel' COLLATE 'latin1_swedish_ci',\
    `customer_reference` VARCHAR(65) NOT NULL DEFAULT 'NONREF' COMMENT ':61:Kundenreferenz (oder Feld :86:20-29 KREF oder CREF (Bezeichner Subfeld) Kundenreferenz Customer Reference' COLLATE 'latin1_swedish_ci',\
    `bank_reference` VARCHAR(16) NULL DEFAULT NULL COMMENT ':61:Bankreferenz (oder Feld :86:20-29 BREF (Bezeichner Subfeld) Bankreferenz, Instruction ID' COLLATE 'latin1_swedish_ci',\
    `extra_details` VARCHAR(34) NULL DEFAULT NULL COMMENT ':61:Waehrungsart und Umsatzbetrag in Ursprungswaehrung' COLLATE 'latin1_swedish_ci',\
    `transaction_code` INT(3) UNSIGNED NOT NULL DEFAULT '0' COMMENT ':86:Geschaeftsvorfall-Code',\
    `posting_text` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 00 Buchungstext' COLLATE 'latin1_swedish_ci',\
    `prima_nota` VARCHAR(10) NULL DEFAULT NULL COMMENT ':86: 10 Primanoten-Nr.' COLLATE 'latin1_swedish_ci',\
    `purpose` VARCHAR(390) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck' COLLATE 'latin1_swedish_ci',\
    `purpose_wo_identifier` VARCHAR(390) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ohne Identifier' COLLATE 'latin1_swedish_ci',\
    `applicant_bic` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 30 BLZ Auftraggeber oder BIC (oder Feld :86:20-29 BIC(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `applicant_iban` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 31 KontoNr des Ueberweisenden/Zahlungsempfaengers (oder Feld :86:20-29 IBAN(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `applicant_name` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 32-33 Name des Ueberweisenden / Zahlungsempfaengers (oder Feld :86:20-29 ANAM(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `return_debit_notes` INT(3) NULL DEFAULT '0' COMMENT ':86: 34 SEPA-Rueckgabe Codes',\
    `end_to_end_reference` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck EREF (Bezeichner Subfeld) SEPA End to End-Referenz' COLLATE 'latin1_swedish_ci',\
    `mandate_id` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck MREF(Bezeichner Subfeld) SEPA Mandatsreferenz' COLLATE 'latin1_swedish_ci',\
    `payment_reference` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck PREF(Bezeichner Subfeld) Retourenreferenz' COLLATE 'latin1_swedish_ci',\
    `creditor_id` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck CRED(Bezeichner Subfeld) SEPA Creditor Identifier' COLLATE 'latin1_swedish_ci',\
    `debtor_id` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck DEBT(Bezeichner Subfeld) Originator Identifier' COLLATE 'latin1_swedish_ci',\
    `ordering_party` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ORDP(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `beneficiary` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck BENM(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `ultimate_creditor` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ULTC(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `ultimate_debtor` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ULTD(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `remittance_information` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck REMI(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `purpose_code` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck PURP(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `return_reason` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck RTRN(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `return_reference` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck RREF(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `counterparty_account` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ACCW(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `intermediary_bank` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck IBK(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `exchange_rate` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck EXCH(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `original_amount` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck OCMT oder OAMT (Bezeichner Subfeld) Ursprünglicher Umsatzbetrag' COLLATE 'latin1_swedish_ci',\
    `compensation_amount` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck COAM(Bezeichner Subfeld) Zinskompensationsbetrag' COLLATE 'latin1_swedish_ci',\
    `charges` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck CHGS(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `different_client` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ABWA(Bezeichner Subfeld) Abweichender SEPA Auftraggeber' COLLATE 'latin1_swedish_ci',\
    `different_receiver` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ABWE(Bezeichner Subfeld) Abweichender SEPA Empfänger' COLLATE 'latin1_swedish_ci',\
    `sepa_purpose` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck SVWZ(Bezeichner Subfeld) Abweichender SEPA Verwendungszweck' COLLATE 'latin1_swedish_ci',\
    `additional_purpose` VARCHAR(108) NULL DEFAULT NULL COMMENT ':86: 60-63 Verwendungszweck Fortführung aus :86:20-29' COLLATE 'latin1_swedish_ci',\
    `opening_status` CHAR(1) NOT NULL COMMENT ':60F:Anfangssaldo Soll/Haben-Kennung C,D ' COLLATE 'latin1_swedish_ci',\
    `opening_entry_date` DATE NOT NULL COMMENT ':60F:Buchungsdatum ',\
    `opening_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':60F:Waehrung' COLLATE 'latin1_swedish_ci',\
    `opening_balance` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00',\
    `closing_status` CHAR(1) NOT NULL COMMENT ':62F:Schlusssaldo Soll/Haben-Kennung C,D ' COLLATE 'latin1_swedish_ci',\
    `closing_entry_date` DATE NOT NULL COMMENT ':62F:Buchungsdatum ',\
    `closing_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':62F:Waehrung' COLLATE 'latin1_swedish_ci',\
    `closing_balance` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT ':62F:Betrag',\
    `reference` VARCHAR(16) NULL DEFAULT NULL COMMENT ':21: BEZUGSREFERENZNUMMER oder NONREF' COLLATE 'latin1_swedish_ci',\
    `order_reference` VARCHAR(16) NULL DEFAULT NULL COMMENT ':20: AUFTRAGSREFERENZNUMMER' COLLATE 'latin1_swedish_ci',\
    `statement_no_page` INT(5) UNSIGNED NOT NULL DEFAULT '0',\
    `statement_no` INT(5) UNSIGNED NOT NULL DEFAULT '0',\
    PRIMARY KEY (`iban`, `entry_date`, `counter`) USING BTREE\
)\
COMMENT='Konto'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_TRANSACTION = "CREATE TABLE IF NOT EXISTS `transaction` (\
    `iban` CHAR(22) NOT NULL COMMENT ':97A:: DepotKonto' COLLATE 'latin1_swedish_ci',\
    `ISIN` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN Kennung' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL COMMENT ':98C::PREP// Erstellungsdatum',\
    `counter` SMALLINT(5) NOT NULL DEFAULT '0',\
    `transaction_type` CHAR(4) NOT NULL DEFAULT 'RECE' COMMENT ':22H:: Indikator für Eingang/Lieferung DELI=Lieferung(Belastung) RECE=Eingang(Gutschrift)' COLLATE 'latin1_swedish_ci',\
    `price_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':90A:: ISO 4217-Waehrungscode oder  :90B:: PCT  Preis als Prozentsatz' COLLATE 'latin1_swedish_ci',\
    `price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':90A::  Preis als Prozentsatz oder  :90B:: Abrechnungskurs',\
    `pieces` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':36B:: Gebuchte Stueckzahl',\
    `amount_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':19A:: Gebuchter Betrag,  ISO 4217-Waehrungscode' COLLATE 'latin1_swedish_ci',\
    `posted_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':19A:: Gebuchter Betrag, Kurswert',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'Datensatz Herkunft:  _BANKDATA_  Download Bank' COLLATE 'latin1_swedish_ci',\
    `comments` VARCHAR(200) NULL DEFAULT NULL COMMENT 'Comments' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`iban`, `ISIN`, `price_date`, `counter`) USING BTREE\
)\
COMMENT='Statement of Transactions based on S.W.I.F.T Standard Release Guide 1998\r\nMT 536 fields '\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"
CREATE_TRANSACTION_VIEW = "CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW IF NOT EXISTS  `transaction_view` AS SELECT * FROM transaction INNER JOIN isin_name USING(ISIN)  ;"
CREATE_TABLES = [CREATE_BANKIDENTIFIER,
                 CREATE_ISIN,
                 CREATE_ISIN_NAME,
                 CREATE_HOLDING,
                 CREATE_HOLDING_T,
                 CREATE_HOLDING_VIEW,
                 CREATE_PRICES,
                 CREATE_PRICES_ISIN_VIEW,
                 CREATE_SERVER,
                 CREATE_STATEMENT,
                 CREATE_TRANSACTION,
                 CREATE_TRANSACTION_VIEW
                 ]
"""
-------------------------------- MariaDB Table Fields --------------------------------------------------------
"""
DB_acquisition_amount = 'acquisition_amount'
DB_acquisition_price = 'acquisition_price'
DB_additional_purpose = 'additional_purpose'
DB_adjustments = 'adjustments'
DB_open = 'open'
DB_low = 'low'
DB_high = 'high'
DB_close = 'close'
DB_dividends = 'dividends'
DB_adjclose = 'adjclose'
DB_amount = 'amount'
DB_amount_currency = 'amount_currency'
DB_applicant_bic = 'applicant_bic'
DB_applicant_iban = 'applicant_iban'
DB_applicant_name = 'applicant_name'
DB_bank_reference = 'bank_reference'
DB_beneficiary = 'beneficiary'
DB_bic = 'bic'
DB_category_name = 'category_name'
DB_change_indicator = 'change_indicator'
DB_charges = 'charges'
DB_check_digit_calculation = 'check_digit_calculation'
DB_closing_balance = 'closing_balance'
DB_closing_currency = 'closing_currency'
DB_closing_entry_date = 'closing_entry_date'
DB_closing_status = 'closing_status'
DB_code = 'code'
DB_code_deletion = 'code_deletion'
DB_comments = 'comments'
DB_compensation_amount = 'compensation_amount'
DB_counter = 'counter'
DB_counterparty_account = 'counterparty_account'
DB_country = 'country'
DB_creditor_id = 'creditor_id'
DB_currency = 'currency'
DB_currency_type = 'currency_type'
DB_customer_reference = 'customer_reference'
DB_date = 'date'
DB_debtor_id = 'debtor_id'
DB_different_client = 'different_client'
DB_different_receiver = 'different_receiver'
DB_end_to_end_reference = 'end_to_end_reference'
DB_entry_date = 'entry_date'
DB_exchange = 'exchange'
DB_exchange_currency_1 = 'exchange_currency_1'
DB_exchange_currency_2 = 'exchange_currency_2'
DB_exchange_rate = 'exchange_rate'
DB_extra_details = 'extra_details'
DB_follow_code = 'follow_code'
DB_guessed_entry_date = 'guessed_entry_date'
DB_high_price = 'high_price'
DB_iban = 'iban'
DB_id = 'id'
DB_intermediary_bank = 'intermediary_bank'
DB_ISIN = 'ISIN'
DB_last_price = 'last_price'
DB_low_price = 'low_price'
DB_location = 'location'
DB_mandate_id = 'mandate_id'
DB_market_price = 'market_price'
DB_name = 'name'
DB_opening_balance = 'opening_balance'
DB_opening_currency = 'opening_currency'
DB_opening_entry_date = 'opening_entry_date'
DB_opening_status = 'opening_status'
DB_order_reference = 'order_reference'
DB_ordering_party = 'ordering_party'
DB_origin = 'origin'
DB_origin_symbol = 'origin_symbol'
DB_original_amount = 'original_amount'
DB_pan = 'pan'
DB_payment_provider = 'payment_provider'
DB_payment_provider_name = 'payment_provider_name'
DB_payment_reference = 'payment_reference'
DB_pieces = 'pieces'
DB_pieces_cum = 'pieces_cum'
DB_postal_code = 'postal_code'
DB_posted_amount = 'posted_amount'
DB_posting_text = 'posting_text'
DB_price = 'price'
DB_price_currency = 'price_currency'
DB_price_date = 'price_date'
DB_prima_nota = 'prima_nota'
DB_purpose = 'purpose'
DB_purpose_code = 'purpose_code'
DB_purpose_wo_identifier = 'purpose_wo_identifier'
DB_ratio_price = 'ratio_price'
DB_record_number = 'record_number'
DB_reference = 'reference'
DB_remittance_information = 'remittance_information'
DB_return_debit_notes = 'return_debit_notes'
DB_return_reason = 'return_reason'
DB_return_reference = 'return_reference'
DB_sepa_purpose = 'sepa_purpose'
DB_server = 'server'
DB_statement_no = 'statement_no'
DB_statement_no_page = 'statement_no_page'
DB_status = 'status'
DB_splits = 'splits'
DB_symbol = 'symbol'
DB_total_amount = 'total_amount'
DB_total_amount_portfolio = 'total_amount_portfolio'
DB_transaction_code = 'transaction_code'
DB_transaction_type = 'transaction_type'
DB_type = 'type'
DB_ultimate_creditor = 'ultimate_creditor'
DB_ultimate_debtor = 'ultimate_debtor'
DB_validity = 'validity'
DB_volume = 'volume'
DB_wkn = 'wkn'
DB_TYPES = ['SHARE', 'BOND', 'SUBSCRIPTION RIGHT']
"""
---------------  MT940 Field 86 identifiers in element PURPOSE (>identifier sub-field< :  >MARIADB column name<)-----------------------------------------------------
"""
IDENTIFIER = {
    'EREF': 'end_to_end_reference',
    'BREF': 'bank_reference',
    'KREF': 'customer_reference',
    'CREF': 'customer_reference',
    'MREF': 'mandate_id',
    'PREF': 'payment_reference',
    'CRED': 'creditor_id',
    'DEBT': 'debtor_id',
    'ORDP': 'ordering_party',
    'BENM': 'beneficiary',
    'ULTC': 'ultimate_creditor',
    'ULTD': 'ultimate_debtor',
    'REMI': 'remittance_information',
    'PURP': 'purpose_code',
    'RTRN': 'return_reason',
    'RREF': 'return_reference',
    'ACCW': 'counterparty_account',
    'IBK': 'intermediary_bank',
    'OCMT': 'original_amount',
    'OAMT': 'original_amount',
    'COAM': 'compensation_amount',
    'CHGS': 'charges',
    'EXCH': 'exchange_rate',
    'IBAN': 'applicant_iban',
    'BIC': 'applicant_bic',
    'ABWA': 'different_client',
    'ABWE': 'different_receiver',
    'ANAM': 'applicant_name',
    'SVWZ': 'sepa_purpose'
}
"""
----------------------------- Transactions (Holding) ------------
"""
COUNTER_PORTFOLIO = '000'  # transactions from portfolio_data (counter_values 0-9
COUNTER_MANUAL = '010'  # manual insertion of transactions (counter 10-99)
COUNTER_MT536 = '100'  # downloaded transactions, Format MT 536
"""
----------------------------- Scraper ------------

    Adding new bank scraper routines or changing login Link -->  reload server table:
   
            CUSTOMIZINGG
                Import Server CSV-File
"""
BMW_BANK_CODE = '70220300'
# value: [>login Link<, >identifier_delimiter<, >storage_period<]
SCRAPER_BANKDATA = {BMW_BANK_CODE: [
    'https://banking.bmwbank.de/privat/banking/', '+', 360]}
EXPLORER = ['Edge', ]
"""
----------------------------- Named Tuples ------------
"""
Balance = namedtuple(
    'Balance', ' '.join([KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_PRODUCT_NAME, DB_entry_date.upper(),
                         DB_closing_status, DB_closing_balance, DB_closing_currency,
                         DB_opening_status, DB_opening_balance, DB_opening_currency]))
TransactionNamedTuple = namedtuple(
    'TransactionNamedTuple', 'price_date counter transaction_type price_currency price pieces amount_currency posted_amount acquisition_amount, sold_pieces, comments')
"""
----------------------------- DataClasses ------------
"""


@dataclass
class Caller:
    """
    Used to remember window position
    (see formbuilt.py  methods geometry_get, geometry_put)
    Contains class name of calling Class)
    """
    caller: str


@dataclass
class HoldingAcquisition:
    price_date: date
    price_currency: str = field(default=EURO)
    market_price: Decimal = field(default=0)
    acquisition_price: Decimal = field(default=0)
    pieces: Decimal = field(default=0)
    amount_currency: str = field(default=EURO)
    total_amount: Decimal = field(default=0)
    acquisition_amount: Decimal = field(default=0)
    origin: str = field(default=0)


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
    Container öf messages, errors
    """
    prices_informations = ' '
    PRICES_INFORMATIONS = 'PRICES_INFORMATIONS'
    """
    Creaze HOLDING_T
    Container öf messages, errors
    """
    holding_t_informations = ' '
    HOLDING_T_INFORMATIONS = 'HOLDING_T_INFORMATIONS'
