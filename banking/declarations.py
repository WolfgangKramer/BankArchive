#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 09.12.2019
__updated__ = "2026-07-12"
@author: Wolfgang Kramer
"""

from _datetime import date
from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal

import banking.declarations_mariadb as declm
import banking.services_file as srvf

"""
------------------------- Globals ---------------------------------------------------
"""
temp_file_manager = srvf.TempFileManager()

technical_indicator_counter = 0

PNS = {}
"""
-------------------------- Date Constants -----------------------------------------------
"""
# Start Currency EUR
START_CURRENCY_EUR = '2002-01-01'
# Start date  download in MariaDB database
# e.g. start www download of prices e.g. from https://www.alphavantage.co
START_DATE_PRICES = '2000-01-01'
# start download of statements from bank; attention check storage_period of your bank
START_DATE_STATEMENTS = date(2000, 1, 1)
# start date transaction date
START_DATE_TRANSACTIONS = date(2000, 1, 1)
# start date holding_data
START_DATE_HOLDING = date(2010, 1, 1)
# start date transfer statements to ledger
START_DATE_LEDGER = date(1990, 1, 1)
# Submission of scheduled SEPA transfers (HKCSE)
TRANSFER_DATA_SEPA_EXECUTION_DATE = '1999-01-01'
# Maria DB initialzing date fields
MARIADB_STANDARD_DATE = '2000-01-01'

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
CONSORS_BANK_CODE = '76030080'
"""
--------------------------- WebSites --------------------------------------------------
"""
BUNDESBANK_BLZ_MERKBLATT = b"https://www.bundesbank.de/resource/blob/602848/50cba8afda2b0b1442016101cfd7e084/mL/merkblatt-bankleitzahlendatei-data.pdf"
BUNDEBANK_BLZ_DOWNLOAD = b"https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592"
MSEDGE_DRIVER_DOWNLOAD = b"https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver"
FINTS_SERVER_ADDRESS = b"https://www.fints.org/de/hersteller/produktregistrierung"
TICKER_ADDRESS = b"https://investexcel.net/stocks-traded-german-exchanges/?utm_source=chatgpt.com"

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
MENU_TEXT = {
    'Connect DB': 'Connect DB',
    'Ledger': 'Ledger',
    'Show': 'Show',
    'Download': 'Download',
    'Transfer': 'Transfer',
    'Database': 'Database',
    'Customize': 'Customize',

    'Account': 'Account',
    'Account Category': 'Account Category',
    'Close Volume': 'Close Volume',
    'Currency Table':'Currency Table',
    'All_Banks': 'All_Banks',
    'Alpha Vantage': 'Alpha Vantage Query',
    'Alpha Vantage Symbol Search': 'Alpha Vantage Symbol Search',
    'Application INI File': 'Application INI File',
    'Assets': 'Assets',
    'Balances': 'Balances',
    'Bond_Master Table': 'Bond_Master Table',
    'Change FinTS Transaction Version': 'Check FinTS Transaction Version',
    'Change Security Function': 'Check Security Function',
    'Change Login Data': 'Change Login Data',
    'Chart of Accounts': 'Chart of Accounts',
    'Check Transactions Pieces': 'Check Transactions Pieces',
    'Check Upload': 'Check Upload',
    'Check Bank Statement': 'Check Bank Statement',
    'Corporate Actions': 'Corporate Actions',
    'Corporate Dividends': 'Corporate Dividends',
    'Delete Bank': 'Delete Bank',
    'Holding': 'Holding',
    'Holding Missing Trading Day': 'Holding Missing Trading Day',
    'Holding Performance': 'Holding Performance',
    'Holding ISIN Comparision': 'Holding ISIN Comparision',
    'Holding ISIN Comparision %': 'Holding ISIN Comparision %',
    'Holding Table': 'Holding Table',
    'Import Bankidentifier CSV-File': 'Bankidentifier CSV-File',
    'Import Server CSV-File': 'Server CSV-File',
    'Import Ticker Symbols': 'Ticker CSV-File',
    'Import Transactions': 'Import Transactions',
    'Insert Holding Positions from Transactions': 'Insert Holding Positions from Transactions',
    'ISIN Table': 'ISIN Table',
    'Journal': 'Journal',
    'Login Online Banking': 'Login Online Banking',
    'New Bank': 'New Bank',
    'Prices': 'Prices',
    'Prices ISINs': 'Prices',
    'Profit Transactions incl. current Depot Positions': 'Profit Transactions incl. current Depot Positions',
    'Profit of closed Transactions': 'Profit of closed Transactions',
    'Refresh Alpha Vantage': 'Create Alpha Vantage Query Selection',
    'Refresh BankParameterData': 'Refresh BankParameterData',
    'Reset Screen Positions': 'Reset Screen Positions',
    'Reset Ledger_daily_balance': 'Reset Ledger_daily_balance',
    'Search': 'Search',
    'Search via Statement': 'Search via Statement',
    'Show Data': 'Show Data',
    'Show All Data': 'Show All Data',
    'Show Data BPD/UPD': 'Show Data BPD/UPD',
    'Statement': 'Statement',
    'Statement_wo': 'Statement without Ledger Assignment',
    'Synchronize': 'Synchronize',
    'Synchronize Transactions': 'Synchronize Transactions',
    'Technical Indicators': 'Technical Indicators',
    'Transactions': 'Transactions',
    'Transaction Detail': 'Transaction Detail',
    'Transactions Table': 'Transactions Table',
    'Update': 'Update',
    'Update Holding Market Price by Closing Price': 'Insert/Change Holding using Closing Price',
    'Update Portfolio Total Amount': 'Update Portfolio Total Amount',
    'WebSites': 'WebSites',
    'Frankfurter Boerse': 'Frankfurter Boerse',
    'Onvista': 'Onvista',
    'Boerse.de': 'Boerse.de',
}

POPUP_MENU_TEXT = {
    'Show Holding': 'Show_Holding',
    'Show selected Row': 'Show selected Row',
    'Show credit data': 'Show selected Row credit data',
    'Show debit data': 'Show selected Row debit data',
    'New Row': 'New Row',
    'Update selected Row': 'Update selected Row',
    'Delete selected Row': 'Delete selected Row',
    'Export to Excel': 'Export to Excel',
    # specials
    'Show Holding Changed': 'Show Holding Changed',    
    'Show Holding Daily': 'Show_Holding Daily',    
}

CODE_3010 = '3010'  # Download bank data,    no entries exist'
CODE_3040 = '3040'  # Download partially executed
CODE_0030 = '0030'  # Download not executed
CODE_3955 = '3955'  # Security clearance is provided via another channel


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
 ------------------Shelve_Files------------------------------------------------
"""
KEY_DIRECTORY = 'DIRECTORY'
KEY_DRIVER = 'DRIVER'
MARIADB_NAME = 'MARIADB_NAME'
MARIADB_USER = 'MARIADB_USER'
MARIADB_PASSWORD = 'MARIADB_PASSWORD'
MARIADB_HOST = 'MARIADB_HOST'
KEY_ALPHA_VANTAGE_PRICE_PERIOD = 'ALPHA_VANTAGE_PRICE_PERIOD'
KEY_SHOW_MESSAGE = 'SHOW_MESSAGE'
KEY_LOGGING = 'LOGGING'
KEY_THREADING = 'THREADING'

KEY_ALPHA_VANTAGE_FUNCTION = 'ALPHA_VANTAGE_FUNCTION'
KEY_ALPHA_VANTAGE_PARAMETER = 'ALPHA_VANTAGE_PARAMETER'
KEY_LEDGER = 'LEDGER'
KEY_RESET_SCREENSIZE = 'KEY_RESET_SCREENSIZE'


TRUE = 1
FALSE = 0
"""
SWITCH = [TRUE, FALSE]
"""
KEY_ACCOUNTS = 'ACCOUNTS'
KEY_BANK_CODE = 'BANK_CODE'
KEY_BANK_NAME = 'BANK_NAME'
KEY_BPD = 'BPD_VERSION'
KEY_PIN = 'PIN'
KEY_BIC = 'BIC'
KEY_LOGIN_ONLINE_BANKING = 'LOGIN_ONLINE_BANKING'
KEY_SECURITY_FUNCTION = 'SECURITY_FUNCTION'
KEY_VERSION_TRANSACTION = 'VERSION_TRANSACTION'
KEY_VERSION_TRANSACTION_ALLOWED = 'VERSION_TRANSACTION_ALLOWED'
KEY_SERVER = 'SERVER'
KEY_IDENTIFIER_DELIMITER = 'KEY_IDENTIFIER_DELIMITER'
KEY_DOWNLOAD_ACTIVATED = 'DOWNLOAD_ACTIVATED'
KEY_STORAGE_PERIOD = 'STORAGE_PERIOD'
KEY_SYSTEM_ID = 'SYSTEM_ID'
KEY_TAN = 'TAN'
KEY_TWOSTEP = 'TWOSTEP_PARAMETERS'
KEY_SUPPORTED_SEPA_FORMATS = 'SUPPORTED_SEPA_FORMATS'
KEY_SUPPORTED_CAMT_MESSAGE = 'SUPPORTED_CAMT_MESSAGE'
KEY_UPD = 'UPD_VERSION'
KEY_USER_ID = 'USER_ID'
KEY_MIN_PIN_LENGTH = 'MIN_PIN_LENGTH'
KEY_MAX_PIN_LENGTH = 'MAX_PIN_LENGTH'
KEY_MAX_TAN_LENGTH = 'MAX_TAN_LENGTH'
KEY_TAN_REQUIRED = 'TRANSACTION_TANS_REQUIRED'
SHELVE_KEYS = [
    KEY_LOGIN_ONLINE_BANKING, KEY_BANK_CODE, KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC,
    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_DOWNLOAD_ACTIVATED, KEY_SECURITY_FUNCTION, KEY_VERSION_TRANSACTION,
    KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_SYSTEM_ID,
    KEY_TWOSTEP, KEY_SUPPORTED_CAMT_MESSAGE, KEY_ACCOUNTS, KEY_UPD, KEY_BPD, KEY_STORAGE_PERIOD,
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
ORIGIN_LEDGER = '_LEDGER_'  # data source: ledger database
# data source: update market_price, total_amount and total_amount_portfolio in table holding  from table prices
ORIGIN_PRICES = '_PRICES_'
# data source: inserted if holding position is missing during update from prices
ORIGIN_INSERTED = '_INSERTED_'
# data source: inserted using transaction data
ORIGIN_TRANSACTION = '_TRANSACTION_'
ORIGIN_BANKDATA_CHANGED = '_BANKDATA_CHANGED_'
ORIGINS = [ORIGIN, ORIGIN_LEDGER, ORIGIN_INSERTED]
DEBIT = 'D'
CREDIT = 'C'
PERCENT = 'PCT'
EURO = 'EUR'
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
ORIGIN_SYMBOLS = [NOT_ASSIGNED, YAHOO]
EXCHANGE_CODES = {
    "DE": "XETRA",
    "F": "FRA",
    "SG": "STUTTGART",
    "BE": "BERLIN",
    "HM": "HAMBURG",
    "MU": "MUNICH",
    "DU": "DUESSELDORF"
}

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
ALPHA_VANTAGE_OPTIONAL_COMBO = {'outputsize': ['compact', 'full']}

"""
-------------------------- Formbuilts -----------------------------------------------
"""
ENTRY = 'Entry'
COMBO = 'ComboBox'
CHECK = 'CheckButton'
TEXT = 'Text'

BUTTON_ALPHA_VANTAGE = 'ALPHA_VANTAGE'
BUTTON_APPEND = 'APPEND'
BUTTON_ADD_CHART = 'ADD CHART'
BUTTON_CREDIT = 'SHOW CREDIT'
BUTTON_CREATE = 'CREATE'
BUTTON_COPY = 'COPY'
BUTTON_DEBIT = 'SHOW DEBIT'
BUTTON_DELETE = 'DELETE'
BUTTON_DELETE_ALL = 'DELETE ALL'
BUTTON_DATA = 'DATA'
BUTTON_INIT = 'INIT'
BUTTON_INSERT = 'INSERT'
BUTTON_INDICATOR = 'SELECT INDICATOR'
BUTTON_PRICES_IMPORT = 'IMPORT PRICES'
BUTTON_NEXT = 'NEXT'
BUTTON_NEW = 'NEW'
BUTTON_OK = 'OK'
BUTTON_PRINT = 'PRINT'
BUTTON_PREVIOUS = 'PREVIOUS'
BUTTON_QUIT = 'QUIT'
BUTTON_QUIT_ALL = 'QUIT ALL'
BUTTON_REPLACE = 'REPLACE'
BUTTON_RESTORE = 'RESTORE'
BUTTON_SAVE = 'SAVE'
BUTTON_SAVE_STANDARD = 'SAVE as Standard'
BUTTON_SELECT_ALL = 'SELECT All'
BUTTON_SELECT = 'SELECT'
BUTTON_STANDARD = 'STANDARD'
BUTTON_STORE = 'STORE'
BUTTON_UPDATE = 'UPDATE'

COLOR_ERROR = 'red'
COLOR_NOT_ASSIGNED = 'cyan'
COLOR_NEGATIVE = 'darkorange'
COLOR_HOLDING = 'yellow'
COLUMN_FORMATS_LEFT = 'LEFT'
COLUMN_FORMATS_RIGHT = 'RIGHT'
COLUMN_FORMATS_CURRENCY = 'CURRENCY'
COLUMN_FORMATS_COLOR_NEGATIVE = 'COLOR_NEGATIVE'
STANDARD = 'STANDARD'
FORMAT_FIXED = 'F'
FORMAT_VARIABLE = 'V'
TYP_ALPHANUMERIC = 'X'
TYP_DECIMAL = 'D'
TYP_DATE = 'DAT'

LIGHTBLUE = 'LIGHTBLUE'
MAX_FIELD_LENGTH = 65

"""
-------------------------- Forms -----------------------------------------------
"""
WM_DELETE_WINDOW = 'WM_DELETE_WINDOW'
START_DIALOG_FAILED = [None, WM_DELETE_WINDOW]

WIDTH_TEXT = 170
HEIGHT_TEXT = 60
HEADER = 'HEADER'
INFORMATION = 'INFORMATION '
WARNING = 'WARNING     '
ERROR = 'ERROR       '
SHOW_MESSAGE = [INFORMATION, WARNING, ERROR]
FN_ACCOUNT_NAME = 'ACCOUNT_NAME'
FN_ACCOUNT_NUMBER = 'ACCOUNT_NUMBER_'
FN_COMPARATIVE = 'COMPARATIVE_VALUE'
COST_FIFO = "FIFO"
COST_LIFO = "LIFO"
COST_AVERAGE = "AVERAGE"
COST_METHOD = [COST_FIFO, COST_LIFO, COST_AVERAGE]
FN_COST_METHOD = 'COST_METHOD'
FN_DATE = 'DATE'
FN_TO_DATE = 'TO_DATE'
FN_FROM_DATE = 'FROM_DATE'
FN_BANK_NAME = 'BANK_NAME'
FN_FIELD_NAME = 'Field_Name'
FN_PROCUDURE_NAME = 'Procedure_Name'
FN_PERCENTAGE = 'Percentage'
FN_DATA_MODE = 'DATA_MODE'
FN_PROPORTIONAL = 'PROPORTIONAL'
FN_ABSOLUTE = 'ABSOLUTE'
FN_TOTAL = 'TOTAL'
FN_TOTAL_PERCENT = '% TOTAL'
FN_PERIOD_PERCENT = 'PERIOD'
FN_DAILY_PERCENT = 'Day'
FN_PROFIT = 'Profit'
FN_PROFIT_LOSS = 'PROFIT_LOSS'
FN_PROFIT_CUM = 'PERFORMANCE'
FN_PIECES_CUM = 'CUM_PIECES'
FN_SOLD_PIECES = 'sold_pieces'
FN_ALL_BANKS = 'ALL BANKS '
FN_CREDIT = 'CREDIT'
FN_DEBIT = 'DEBIT'
FN_BALANCE = 'BALANCE'
FN_COLUMNS_EURO = [FN_TOTAL, FN_PROFIT,
                   FN_PROFIT_LOSS, FN_PROFIT_CUM,
                   FN_BALANCE, FN_CREDIT, FN_DEBIT]
FN_COLUMNS_PERCENT = [FN_TOTAL_PERCENT,
                      FN_PERIOD_PERCENT, FN_DAILY_PERCENT]
NOTPROVIDED = 'NOTPROVIDED'
"""
-------------------------- BuilPandasBox param mode
"""
EDIT_ROW = 'EDIT_ROW'
CURRENCY_SIGN = 'CURRENCY_SIGN'
NUMERIC = 'NUMERIC'
NO_CURRENCY_SIGN = 'NO_CURRENCY_SIGN'
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
    'DEBT': 'debitor_id',
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

SEPA_FIELD86_CHECK = {
declm.DB_exchange_rate: "PandasBoxStatementTable"
}
"""

----------------------------- Scraper ------------

    Adding new bank scraper routines or changing login Link -->  reload server table:

            CUSTOMIZINGG
                Import Server CSV-File
"""
BMW_BANK_CODE = '70220300'
# value: [>login Link<, >identifier_delimiter<, >storage_period<]
SCRAPER_BANKDATA = {BMW_BANK_CODE: [
    'https://ebanking.bmwbank.de/eBankingClient', '+', 360]}
"""
----------------------------- Named Tuples ------------
"""
Balance = namedtuple(
    'Balance', ' '.join([KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_PRODUCT_NAME, declm.DB_entry_date.upper(),
                         declm.DB_closing_status, declm.DB_closing_balance, declm.DB_closing_currency,
                         declm.DB_opening_status, declm.DB_opening_balance, declm.DB_opening_currency]))
"""
----------------------------- DataClasses ------------
"""


@dataclass
class BpdUpdVersion:
    """
    BPD:
        Die Bankparameterdaten dienen zum einen der automatisierten kreditinstitutsspezifischen
        Konfiguration von Kundensystemen und zum anderen der dynamischen Anpassung
        an institutsseitige Vorgaben hinsichtlich der Auftragsgenerierung.
        Des Weiteren ist es mit Hilfe der BPD moeglich, bestimmte Fehler bereits auf der
        Kundenseite zu erkennen, was sich wiederum positiv auf die institutsseitige
        Verarbeitung der Auftragsdaten auswirkt.

    UPD:
        Die Userparameterdaten, die kreditinstitutsseitig benutzerbezogen generiert und
        vorgehalten werden, erlauben eine automatisierte und dynamische Konfiguration
        von Kundensystemen. In Abgrenzung zu den BPD enthalten die UPD ausschließlich
        kunden- und kontenspezifische Informationen und sind somit haeufigeren Modifikationen unterworfen.
        Waehrend die Bankparameterdaten die grundsaetzlich vom Kreditinstitut angebotenen
        Geschaeftsvorfaelle angeben, gestatten die Userparameterdaten kontenbezogene
        Berechtigungspruefungen im Kundenprodukt. So kann das Kundenprodukt mit Hilfe der
        Userparameterdaten pruefen, ob der Kunde fuer die Ausfuehrung eines der in den
        Bankparameterdaten angegebenen Geschaeftsvorfaelle in Verbindung mit einem
        bestimmten Konto berechtigt ist.
        Das Konto, das im jeweiligen Geschaeftsvorfall fuer die Berechtigungspruefung heran
        zuziehen ist, ist im Regelfall entweder das Auftraggeberkonto oder das Depotkonto
        bei Wertpapierauftraegen oder das Anlagekonto bei Festgeldanlagen. In den Faellen,
        in denen es sich um ein hiervon abweichendes Konto handelt, ist dies in der
        Geschaeftsvorfallbeschreibung vermerkt. Bei Geschaeftsvorfaellen ohne Kontenbezug
        (z.B. Informationsbestellung) findet keine Berechtigungspruefung statt.
        Bei Aenderungen werden die Userparameterdaten im Rahmen der Dialoginitialisierung
        fuer den sich anmeldenden Benutzer automatisch aktualisiert. Die aktualisierten
        UPD werden sofort aktiv (s. hierzu die Ausfuehrungen zu den BPD).

    Source:
        Financial Transaction Services (FinTS)
        Dokument: Formals
        Kapitel:  Bankparameterdaten (BPD)
        Kapitel:  Userparameterdaten (UPD)
    """
    bpd: int  # stored Version of bank parameter data (MariaDB table shelves)
    upd: int  # stored Version of user parameter data (MariaDB table shelves)


@dataclass
class ToolbarSwitch:
    """
    Switch Toolbar True/False

    See class ToolBarBanking

    True: Show Banking Toolbar
        Used to suppress formatting amounts with currency sign
        (see formbuilt.py  Class BuiltPandasBox)

    False: Hidden Banking Toolbar
    """
    toolbar_switch = True


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


class TechnicalIndicatorData(object):
    """
    Controlling the display of indicator charts
    """
    TA_CLOSE = []  # charts close added to plot of technical indicator
    # TA_LINES inserts y-line into chart (line_name, y_value)
    TA_LINES = {'RSIIndicator': [('OVERSOLD', 30), ('OVERBOUGHT', 70)],
                'StochRSIIndicator': [('OVERSOLD', 0.2), ('OVERBOUGHT', 0.8)], }
    """
    1. Volume Indicators
        Accumulation/Distribution Index (ADI) > AccDistIndexIndicator
        On-Balance Volume (OBV) > OnBalanceVolumeIndicator
        Money Flow Index (MFI) > MFIIndicator
        Chaikin Money Flow (CMF) > ChaikinMoneyFlowIndicator
        Force Index (FI) > ForceIndexIndicator
        Ease of Movement (EoM, EMV) > EaseOfMovementIndicator (also sma_ease_of_movement)
        Volume-price Trend (VPT) > VolumePriceTrendIndicator
        Negative Volume Index (NVI) > NegativeVolumeIndexIndicator
        Volume Weighted Average Price (VWAP) > VolumeWeightedAveragePriceIndicator

    2. Volatility Indicators
        Average True Range (ATR) > AverageTrueRange
        Bollinger Bands (BB) > BollingerBands with methods like bollinger_hband, bollinger_lband, bollinger_mavg, etc.
        Keltner Channel (KC) > KeltnerChannel with methods like keltner_channel_hband, mband, etc.
        Donchian Channel (DC) > DonchianChannel with similar band methods.
        Ulcer Index (UI) > UlcerIndex

    3. Trend Indicators
        Simple Moving Average (SMA) > SMAIndicator
        Exponential Moving Average (EMA) > EMAIndicator
        Weighted Moving Average (WMA) > WMAIndicator
        Moving Average Convergence Divergence (MACD) > MACD (includes macd_diff, macd_signal)
        Average Directional Movement Index (ADX) > ADXIndicator with adx_neg, adx_pos
        Vortex Indicator (VI) > VortexIndicator with vortex_indicator_neg, vortex_indicator_pos
        Trix (TRIX) > TRIXIndicator
        Mass Index (MI) > MassIndex
        Commodity Channel Index (CCI) > CCIIndicator
        Detrended Price Oscillator (DPO) > DPOIndicator
        KST Oscillator (KST) > KSTIndicator with kst_sig
        Ichimoku Kinko Hyo (Ichimoku) > IchimokuIndicator (includes lines like conversion line, base line, ichimoku_a, ichimoku_b)
        Parabolic Stop and Reverse (Parabolic SAR) > PSARIndicator with down/up indicators
        Schaff Trend Cycle (STC) > STCIndicator
        Aroon Indicator > AroonIndicator with aroon_down, aroon_up

    4. Momentum Indicators
        Relative Strength Index (RSI) > RSIIndicator
        Stochastic RSI (SRSI) > StochRSIIndicator, with stochrsi_d, stochrsi_k
        True Strength Index (TSI) > TSIIndicator
        Ultimate Oscillator (UO) > UltimateOscillator
        Stochastic Oscillator > StochasticOscillator with stoch, stoch_signal
        Williams %R (WR) > WilliamsRIndicator
        Awesome Oscillator (AO) > AwesomeOscillatorIndicator
        Kaufmans Adaptive Moving Average (KAMA) > KAMAIndicator
        Rate of Change (ROC) > ROCIndicator
        Percentage Price Oscillator (PPO) > PercentagePriceOscillator, with ppo_hist, ppo_signal
        Percentage Volume Oscillator (PVO) > PercentageVolumeOscillator, with pvo_hist, pvo_signal

    5. Other Indicators
        Daily Return (DR) > DailyReturnIndicator
        Daily Log Return (DLR) > DailyLogReturnIndicator
        Cumulative Return (CR) > CumulativeReturnIndicator
    """
    # indicator columns of dataframe created by ta.add_all_ta_features
    TA_VOLUME = {
        'AccDistIndexIndicator': ['volume_adi'],
        'OnBalanceVolumeIndicator': ['volume_obv'],
        'ChaikinMoneyFlowIndicator': ['volume_cmf'],
        'ForceIndexIndicator': ['volume_fi'],
        'EaseOfMovementIndicator': ['volume_em', 'volume_sma_em'],
        'VolumePriceTrendIndicator': ['volume_vpt'],
        'VolumeWeightedAveragePrice': ['volume_vwap'],
        'MFIIndicator': ['volume_mfi'],
        'NegativeVolumeIndexIndicator': ['volume_nvi']
        }
    TA_VOLATILITY = {
        'BollingerBands': ['volatility_bbm', 'volatility_bbh', 'volatility_bbl', 'volatility_bbw',
                           'volatility_bbp', 'volatility_bbhi', 'volatility_bbli'],
        'KeltnerChannel': ['volatility_kch', 'volatility_kcl', 'volatility_kcw', 'volatility_kcp',
                           'volatility_kchi', 'volatility_kcli'],
        'DonchianChannel': ['volatility_dcl', 'volatility_dch', 'volatility_dcm', 'volatility_dcw',
                            'volatility_dcp'],
        'AverageTrueRange': ['volatility_atr'],
        'UlcerIndex': ['volatility_ui']
        }
    TA_TREND = {
        'MACD': ['trend_macd', 'trend_macd_signal', 'trend_macd_diff'],
        'SMAIndicator': ['trend_sma_fast', 'trend_sma_slow'],
        'EMAIndicator': ['trend_ema_fast', 'trend_ema_slow'],
        'VortexIndicator': ['trend_vortex_ind_pos', 'trend_vortex_ind_neg', 'trend_vortex_ind_diff'],
        'TRIXIndicator': ['trend_trix'],
        'MassIndex': ['trend_mass_index'],
        'DPOIndicator': ['trend_dpo'],
        'KSTIndicator': ['trend_kst', 'trend_kst_sig' 'trend_kst_diff'],
        'IchimokuIndicator': ['trend_ichimoku_conv', 'trend_ichimoku_base', 'trend_ichimoku_a', 'trend_ichimoku_b'],
        'STCIndicator': ['trend_stc'],
        'ADXIndicator': ['trend_adx', 'trend_adx_pos', 'trend_adx_neg'],
        'CCIIndicator': ['trend_cci'],
        'IchimokuIndicator_visual': ['trend_visual_ichimoku_a', 'trend_visual_ichimoku_b'],
        'AroonIndicator': ['trend_aroon_up', 'trend_aroon_down', 'trend_aroon_ind'],
        'PSARIndicator': ['trend_psar_up', 'trend_psar_down', 'trend_psar_up_indicator', 'trend_psar_down_indicator'],
        }
    TA_MOMENTUM = {
        'RSIIndicator': ['momentum_rsi'],
        'StochRSIIndicator': ['momentum_stoch_rsi', 'momentum_stoch_rsi_k', 'momentum_stoch_rsi_d'],
        'TSIIndicator': ['momentum_tsi'],
        'UltimateOscillator': ['momentum_uo'],
        'StochasticOscillator': ['momentum_stoch', 'momentum_stoch_signal'],
        'WilliamsRIndicator': ['momentum_wr'],
        'AwesomeOscillatorIndicator': ['momentum_ao'],
        'ROCIndicator': ['momentum_roc'],
        'PercentagePriceOscillator': ['momentum_ppo', 'momentum_ppo_signal', 'momentum_ppo_hist'],
        'PercentageVolumeOscillator': ['momentum_pvo', 'momentum_pvo_signal', 'momentum_pvo_hist'],
        'KAMAIndicator': ['momentum_kama']
        }
    TA_OTHERS = {
        'DailyReturnIndicator': ['others_dr'],
        'DailyLogReturnIndicator': ['others_dlr'],
        'CumulativeReturnIndicator': ['others_cr']
        }
