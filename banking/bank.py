"""
Created on 18.11.2019
__updated__ = "2026-06-13"
@author: Wolfgang Kramer
"""

import webbrowser
from datetime import date
from random import randint

import banking.declarations as decl
import banking.declarations_mariadb as declm
import banking.message_handler as msg

from banking.repository import Repository

from banking.fints_dialog import Dialogs
from banking.forms import InputPIN
from banking.utils import application_store, http_error_code


class InitBank(object):
    """
    Data Bank Dialogue
    """

    def __init__(self, bank_code):

        repo = Repository()
        self.scraper = False
        self.bank_code = bank_code
        shelve_file = repo.shelve_get_keys(bank_code)
        try:
            self.user_id = shelve_file[decl.KEY_USER_ID]
            if decl.KEY_PIN in shelve_file.keys() and shelve_file[decl.KEY_PIN] not in ['', None]:
                decl.PNS[bank_code] = shelve_file[decl.KEY_PIN]
            self.bic = shelve_file[decl.KEY_BIC]
            self.server = shelve_file[decl.KEY_SERVER]
            self.bank_name = shelve_file[decl.KEY_BANK_NAME]
            self.accounts = shelve_file[decl.KEY_ACCOUNTS]
        except KeyError as key_error:
            msg.MessageBoxError(
                message=msg.get_message(msg.MESSAGE_TEXT, 'LOGIN', self.bank_code, key_error))
            return None  # thread checking
        http_code = http_error_code(self.server)
        if http_code not in decl.HTTP_CODE_OK:
            msg.MessageBoxError(
                title=self.bank_name,                
                message=msg.get_message(
                msg.MESSAGE_TEXT,
                'HTTP',
                http_code,
                self.bank_code,
                self.server
                )
            )
            webbrowser.open(self.server)
            return None  # thread checking
        if bank_code in list(decl.SCRAPER_BANKDATA.keys()):
            msg.MessageBoxError(
                title=self.bank_name,
                message=msg.get_message(msg.MESSAGE_TEXT, 'LOGIN_SCRAPER', '', self.bank_code))
            return None  # thread checking
        else:
            self.dialogs = Dialogs()
            try:
                self.security_function = shelve_file[decl.KEY_SECURITY_FUNCTION]
            except KeyError as key_error:
                msg.MessageBoxError(
                    title=self.bank_name,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'LOGIN', self.bank_code, key_error))
                return None  # thread checking
            # Checking / Installing FINTS server connection
            # register product:
            # https://www.hbci-zka.de/register/prod_register.htm
            self.product_id = application_store.get(declm.DB_product_id)
            if self.product_id == '':
                msg.MessageBoxInfo(
                    title=self.bank_name,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'decl.PRODUCT_ID'))
                self.product_id = decl.PRODUCT_ID
            # Getting Sychronisation Data
            try:
                #    Bank Parameter Data BPD
                self.system_id = shelve_file[decl.KEY_SYSTEM_ID]
                try:
                    self.supported_camt_messages = shelve_file[decl.KEY_SUPPORTED_CAMT_MESSAGE]
                except KeyError:
                    self.supported_camt_messages = None
                self.security_identifier = shelve_file[decl.KEY_SYSTEM_ID]
                self.bpd_version = shelve_file[decl.KEY_BPD]
                self.transaction_versions = shelve_file[decl.KEY_VERSION_TRANSACTION]
                self.storage_period = shelve_file[decl.KEY_STORAGE_PERIOD]
                self.twostep_parameters = shelve_file[decl.KEY_TWOSTEP]
                #    User Parameter Data UPD
                self.upd_version = shelve_file[decl.KEY_UPD]
            except KeyError:
                msg.MessageBoxError(
                    title=self.bank_name,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'SYNC', self.bank_code))
                return None  # thread checking
            # Setting Dialog Variables
            self.message_number = 1
            self.task_reference = None
            self.tan_process = 4
            self.security_reference = randint(10000, 99999)
            self.dialog_id = decl.DIALOG_ID_UNASSIGNED
            self.opened_bank_code = None

        self.sepa_credit_transfer_data = None
        self.sca = True
        self.challenge_hhduc = None
        self.challenge = ''
        self.warning_message = False
        self.iban = None
        self.account_number = None
        self.account_product_name = ''
        self.subaccount_number = None
        self.statement_mt940 = False  # Download Format of Statements  MT940 (Segment HKKAZ allowed)
        self.statement_camt = False  # Download Format of Statements   CAMT (Segment HKCAZ allowed)
        self.owner_name = ''
        self.period_message = False  # true if period message was displayed (segment.py)
        self.from_date = date.today()
        self.to_date = date.today()


class InitBankSync(object):
    """
    Data Bank Synchronization
    """

    def __init__(self, bank_code):

        repo = Repository()
        self.bank_code = bank_code
        self.scraper = False
        shelve_file = repo.shelve_get_keys(bank_code)
        try:
            self.user_id = shelve_file[decl.KEY_USER_ID]
            if decl.KEY_PIN in shelve_file.keys() and shelve_file[decl.KEY_PIN] not in ['', None]:
                decl.PNS[bank_code] = shelve_file[decl.KEY_PIN]
            self.bic = shelve_file[decl.KEY_BIC]
            self.server = shelve_file[decl.KEY_SERVER]
            self.security_function = shelve_file[decl.KEY_SECURITY_FUNCTION]
            self.bpd_version = shelve_file[decl.KEY_BPD]
        except KeyError as key_error:
            msg.MessageBoxError(
                message=msg.get_message(msg.MESSAGE_TEXT, 'LOGIN', self.bank_code, key_error))
            return None  # thread checking
        if bank_code not in decl.PNS.keys():
            try:
                inputpin = InputPIN(bank_code)
                decl.PNS[bank_code] = inputpin.pin
            except TypeError:
                msg.MessageBoxError(
                    message=msg.get_message(msg.MESSAGE_TEXT, 'PIN', '', self.bank_code))
                return None  # thread checking
        # register product: https://www.hbci-zka.de/register/prod_register.htm
        self.product_id = application_store.get(declm.DB_product_id)
        if self.product_id == '':
            msg.MessageBoxInfo(message=msg.get_message(msg.MESSAGE_TEXT, 'decl.PRODUCT_ID'))
            self.product_id = decl.PRODUCT_ID
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in decl.HTTP_CODE_OK:
            msg.MessageBoxError(message=msg.get_message(
                msg.MESSAGE_TEXT,
                'HTTP',
                http_code,
                self.bank_code,
                self.server
                )
            )
            webbrowser.open(self.server)
            return None  # thread checking
        # Init Sychronization Data
        self.system_id = decl.SYSTEM_ID_UNASSIGNED
        self.security_identifier = '0'
        self.bank_name = None
        self.transaction_versions = shelve_file[decl.KEY_VERSION_TRANSACTION]
        self.storage_period = 90
        self.twostep_parameters = []
        self.upd_version = repo.shelve_get_upd(bank_code)
        if not self.upd_version:
            self.upd_version = 0
            self.accounts = []
        else:
            self.accounts = repo.shelve_get_accounts(bank_code)
        # Setting Dialog Variables
        self.message_number = 1
        self.task_reference = None
        self.tan_process = 4
        self.security_reference = randint(10000, 99999)
        self.iban = None
        self.account_number = None
        self.account_product_name = ''
        self.subaccount_number = None
        self.from_date = date.today()
        self.dialog_id = decl.DIALOG_ID_UNASSIGNED
        self.warning_message = False
        self.dialogs = Dialogs()


class InitBankAnonymous(object):
    """
    Data Bank Anonymous Dialogue
    """

    def __init__(self, bank_code):

        repo = Repository()
        # Dialog Identification
        self.bank_code = bank_code
        self.scraper = False
        self.user_id = decl.CUSTOMER_ID_ANONYMOUS
        self.server = repo.shelve_get_server(bank_code)
        if self.server in [None, '']:
            msg.MessageBoxError(
                message=msg.get_message(msg.MESSAGE_TEXT, 'LOGIN', self.bank_code, decl.KEY_SERVER))
            return None  # thread checking
        # register product: https://www.hbci-zka.de/register/prod_register.htm
        self.product_id = application_store.get(declm.DB_product_id)
        if self.product_id in [None, '']:
            msg.MessageBoxInfo(message=msg.get_message(msg.MESSAGE_TEXT, 'decl.PRODUCT_ID'))
            self.product_id = decl.PRODUCT_ID
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in decl.HTTP_CODE_OK:
            msg.MessageBoxError(message=msg.get_message(
                msg.MESSAGE_TEXT,
                'HTTP',
                http_code,
                self.bank_code,
                self.server
                )
            )
            webbrowser.open(self.server)
            return None  # thread checking
        # Init Sychronization Data
        self.system_id = decl.SYSTEM_ID_UNASSIGNED
        self.security_identifier = '0'
        self.security_function = None
        self.bpd_version = 0
        self.bank_name = None
        self.twostep_parameters = []
        self.upd_version = repo.shelve_get_upd(bank_code)
        if not self.upd_version:
            self.upd_version = 0
            self.accounts = []
        else:
            self.accounts = repo.shelve_get_accounts(bank_code)
        # Setting Dialog Variables
        self.message_number = 1
        self.task_reference = None
        self.tan_process = 4
        self.security_reference = randint(10000, 99999)
        self.warning_message = False
        self.dialogs = Dialogs()
