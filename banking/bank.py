"""
Created on 18.11.2019
__updated__ = "2023-10-10"
@author: Wolfgang Kramer
"""
from datetime import date
from random import randint
import re
import webbrowser

from banking.declarations import (
    BANK_MARIADB_INI, BMW_BANK_CODE,
    CUSTOMER_ID_ANONYMOUS,
    DIALOG_ID_UNASSIGNED,
    HTTP_CODE_OK, MESSAGE_TEXT,
    KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_PRODUCT_ID, KEY_BANK_NAME, KEY_VERSION_TRANSACTION,
    KEY_SERVER, KEY_SECURITY_FUNCTION, KEY_SEPA_FORMATS, KEY_SYSTEM_ID,
    KEY_BPD, KEY_UPD, KEY_STORAGE_PERIOD, KEY_TWOSTEP, KEY_ACCOUNTS,
    PRODUCT_ID, PNS,
    SCRAPER_BANKDATA,
    SHELVE_KEYS, SYSTEM_ID_UNASSIGNED, KEY_LOGGING,
)
from banking.dialog import Dialogs
from banking.formbuilts import MessageBoxError, MessageBoxInfo
from banking.forms import InputPIN
from banking.scraper import BmwBank
from banking.utils import shelve_get_key, http_error_code


class InitBank:
    """
    Data Bank Dialogue
    """

    def __init__(self, bank_code, mariadb):

        self.message_texts = ''
        self.scraper = False
        self.bank_code = bank_code
        shelve_file = shelve_get_key(bank_code, SHELVE_KEYS, none=False)
        try:
            self.user_id = shelve_file[KEY_USER_ID]
            if KEY_PIN in shelve_file.keys() and shelve_file[KEY_PIN] not in ['', None]:
                PNS[bank_code] = shelve_file[KEY_PIN]
            self.bic = shelve_file[KEY_BIC]
            self.server = shelve_file[KEY_SERVER]
            self.bank_name = shelve_file[KEY_BANK_NAME]
            self.accounts = shelve_file[KEY_ACCOUNTS]
        except KeyError:
            MessageBoxError(
                message=MESSAGE_TEXT['LOGIN'].format('', self.bank_code))
            return None  # thread checking
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=MESSAGE_TEXT['HTTP'].format(http_code,
                                                                self.bank_code, self.server))
            webbrowser.open(self.server)
            return None  # thread checking
        if bank_code in list(SCRAPER_BANKDATA.keys()):
            if bank_code == BMW_BANK_CODE:
                self.dialogs = BmwBank(PNS[bank_code], shelve_get_key(
                    BANK_MARIADB_INI, KEY_LOGGING))
                self.scraper = True
            else:
                MessageBoxError(
                    message=MESSAGE_TEXT['LOGIN_SCRAPER'].format('', self.bank_code))
                return None  # thread checking
        else:
            self.dialogs = Dialogs(mariadb)
            try:
                self.security_function = shelve_file[KEY_SECURITY_FUNCTION]
            except KeyError:
                MessageBoxError(
                    message=MESSAGE_TEXT['LOGIN'].format('', self.bank_code))
                return None  # thread checking
            # Checking / Installing FINTS server connection
            # register product:
            # https://www.hbci-zka.de/register/prod_register.htm
            self.product_id = shelve_get_key(BANK_MARIADB_INI, KEY_PRODUCT_ID)
            if self.product_id == '':
                MessageBoxInfo(message=MESSAGE_TEXT['PRODUCT_ID'])
                self.product_id = PRODUCT_ID
            # Getting Sychronisation Data
            try:
                #    Bank Parameter Data BPD
                self.system_id = shelve_file[KEY_SYSTEM_ID]
                for sepa_format in shelve_file[KEY_SEPA_FORMATS]:
                    if re.search('pain.001.001.03', sepa_format):
                        self.sepa_descriptor = sepa_format
                        break
                if not self.sepa_descriptor:
                    MessageBoxError(
                        message=MESSAGE_TEXT['PAIN'].format(self.bank_code))
                    return None  # thread checking
                self.security_identifier = shelve_file[KEY_SYSTEM_ID]
                self.bpd_version = shelve_file[KEY_BPD]
                self.transaction_versions = shelve_file[KEY_VERSION_TRANSACTION]
                self.storage_period = shelve_file[KEY_STORAGE_PERIOD]
                self.twostep_parameters = shelve_file[KEY_TWOSTEP]
                #    User Parameter Data UPD
                self.upd_version = shelve_file[KEY_UPD]
            except KeyError:
                MessageBoxError(
                    message=MESSAGE_TEXT['SYNC'].format(self.bank_code))
                return None  # thread checking
            # Setting Dialog Variables
            self.message_number = 1
            self.task_reference = None
            self.tan_process = 4
            self.security_reference = randint(10000, 99999)
            self.dialog_id = DIALOG_ID_UNASSIGNED
            self.opened_bank_code = None

        self.sepa_credit_transfer_data = None
        self.warning_message = False
        self.iban = None
        self.account_number = None
        self.account_product_name = ''
        self.subaccount_number = None
        self.period_message = False
        self.from_date = date.today()
        self.to_date = date.today()


class InitBankSync:
    """
    Data Bank Synchronization
    """

    def __init__(self, bank_code, mariadb):

        self.message_texts = ''
        self.bank_code = bank_code
        self.scraper = False
        shelve_keys = [KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_BPD, KEY_SERVER,
                       KEY_SECURITY_FUNCTION]
        shelve_file = shelve_get_key(bank_code, shelve_keys, none=False)
        try:
            self.user_id = shelve_file[KEY_USER_ID]
            if KEY_PIN in shelve_file.keys() and shelve_file[KEY_PIN] not in ['', None]:
                PNS[bank_code] = shelve_file[KEY_PIN]
            self.bic = shelve_file[KEY_BIC]
            self.server = shelve_file[KEY_SERVER]
            self.security_function = shelve_file[KEY_SECURITY_FUNCTION]
            self.bpd_version = shelve_file[KEY_BPD]
        except KeyError:
            MessageBoxError(
                message=MESSAGE_TEXT['LOGIN'].format('', self.bank_code))
            return None  # thread checking
        if bank_code not in PNS.keys():
            try:
                inputpin = InputPIN(bank_code)
                PNS[bank_code] = inputpin.pin
            except TypeError:
                MessageBoxError(
                    message=MESSAGE_TEXT['PIN'].format('', self.bank_code))
                return None  # thread checking
        # register product: https://www.hbci-zka.de/register/prod_register.htm
        self.product_id = shelve_get_key(BANK_MARIADB_INI, KEY_PRODUCT_ID)
        if self.product_id == '':
            MessageBoxInfo(message=MESSAGE_TEXT['PRODUCT_ID'])
            self.product_id = PRODUCT_ID
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=MESSAGE_TEXT['HTTP'].format(http_code,
                                                                self.bank_code, self.server))
            webbrowser.open(self.server)
            return None  # thread checking
        # Init Sychronization Data
        self.system_id = SYSTEM_ID_UNASSIGNED
        self.security_identifier = '0'
        self.bank_name = None
        self.storage_period = 90
        self.twostep_parameters = []
        self.upd_version = shelve_get_key(bank_code, KEY_UPD)
        if not self.upd_version:
            self.upd_version = 0
            self.accounts = []
        else:
            self.accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
        # Setting Dialog Variables
        self.message_number = 1
        self.task_reference = None
        self.tan_process = 4
        self.security_reference = randint(10000, 99999)
        self.iban = None
        self.from_date = date.today()
        self.dialog_id = DIALOG_ID_UNASSIGNED
        self.warning_message = False
        self.dialogs = Dialogs(mariadb)


class InitBankAnonymous:
    """
    Data Bank Anoymous Dialogue
    """

    def __init__(self, bank_code, mariadb):

        self.message_texts = ''
        # Dialog Identification
        self.bank_code = bank_code
        self.scraper = False
        self.user_id = CUSTOMER_ID_ANONYMOUS
        self.server = shelve_get_key(bank_code, KEY_SERVER)
        if self.server in [None, '']:
            MessageBoxError(
                message=MESSAGE_TEXT['LOGIN'].format('', self.bank_code))
            return None  # thread checking
        # register product: https://www.hbci-zka.de/register/prod_register.htm
        self.product_id = shelve_get_key(BANK_MARIADB_INI, KEY_PRODUCT_ID)
        if self.product_id in [None, '']:
            MessageBoxInfo(message=MESSAGE_TEXT['PRODUCT_ID'])
            self.product_id = PRODUCT_ID
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=MESSAGE_TEXT['HTTP'].format(http_code,
                                                                self.bank_code, self.server))
            webbrowser.open(self.server)
            return None  # thread checking
        # Init Sychronization Data
        self.system_id = SYSTEM_ID_UNASSIGNED
        self.security_identifier = '0'
        self.bpd_version = 0
        self.bank_name = None
        self.twostep_parameters = []
        self.upd_version = shelve_get_key(bank_code, KEY_UPD)
        if not self.upd_version:
            self.upd_version = 0
            self.accounts = []
        else:
            self.accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
        # Setting Dialog Variables
        self.message_number = 1
        self.task_reference = None
        self.tan_process = 4
        self.security_reference = randint(10000, 99999)
        self.warning_message = False
        self.dialogs = Dialogs(mariadb)
