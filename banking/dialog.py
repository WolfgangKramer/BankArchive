"""
Created on 18.11.2019
__updated__ = "2024-03-25"
@author: Wolfgang Kramer
"""

import base64
import io
import json
import logging
import re
import requests

from datetime import date, datetime
from operator import itemgetter
from threading import current_thread, main_thread
from fints.message import FinTSInstituteMessage
from fints.segments.accounts import HISPAS1
from fints.segments.auth import (
    HITAN6, HITANS1, HITANS2, HITANS3, HITANS4, HITANS5, HITANS6, HIPINS1
)
from fints.segments.bank import HIBPA3, HIUPA4, HIUPD6
from fints.segments.depot import HIWPD5, HIWPD6
from fints.segments.dialog import HISYN4, HIRMG2, HIRMS2
from fints.segments.message import HNHBK3
from fints.segments.statement import HIKAZ6, HIKAZ7
from fints.utils import Password
from mt940.models import Transactions

from banking.declarations import (
    BANK_MARIADB_INI,
    CODE_0030, CODE_3010, CODE_3040,
    DIALOG_ID_UNASSIGNED,
    ERROR,
    Informations, INFORMATION, IDENTIFIER,
    PERCENT,
    MESSAGE_TEXT,
    KEY_IDENTIFIER_DELIMITER, KEY_SYSTEM_ID,
    KEY_BPD, KEY_UPD, KEY_BANK_NAME, KEY_STORAGE_PERIOD, KEY_TWOSTEP, KEY_ACCOUNTS,
    KEY_MIN_PIN_LENGTH, KEY_MAX_PIN_LENGTH, KEY_MAX_TAN_LENGTH,
    KEY_VERSION_TRANSACTION, KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_SEPA_FORMATS, KEY_SHOW_MESSAGE, KEY_TAN_REQUIRED,
    KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS,
    KEY_ACC_BANK_CODE, KEY_ACC_CURRENCY, KEY_ACC_CUSTOMER_ID, KEY_ACC_OWNER_NAME,
    KEY_ACC_PRODUCT_NAME, KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_TYPE,
    PNS,
    STATEMENT,
    WARNING, KEY_LOGGING)
from banking.fints_extension import HIKAZS6, HIKAZS7,  HIWPDS5, HIWPDS6
from banking.formbuilts import (
    MessageBoxTermination, MessageBoxInfo, WM_DELETE_WINDOW)
from banking.forms import PrintMessageCode, InputPIN
from banking.message import Messages
from banking.utils import (
    Amount,
    Calculate,
    create_iban,
    exception_error,
    shelve_get_key, shelve_put_key)


re_identification = re.compile(r'^:35B:ISIN\s(.*)\|(.*)\|(.*)$')
re_marketprice = re.compile(
    r'^:90B::MRKT\/\/ACTU\/([A-Z]{3})(\d*),{1}(\d*)$')
re_marketprice01 = re.compile(r'^:90A::MRKT\/\/PRCT\/(\d*),{1}(\d*)$')
re_pricedate01 = re.compile(r'^:98A::PRIC\/\/(\d{8})')
re_pricedate02 = re.compile(r'^:98C::PRIC\/\/(\d{8})')
re_pricedate03 = re.compile(r'^:98A::STAT\/\/(\d{8})')
re_pricedate04 = re.compile(r'^:98C::STAT\/\/(\d{8})')
re_exchange_rate = re.compile(
    r'^:92B::EXCH\/\/([A-Z]{3})\/([A-Z]{3})\/(\d*),{1}(\d*)$')
re_pieces = re.compile(r'^:93B::AGGR\/\/UNIT\/(\d*),(\d*)$')
re_pieces01 = re.compile(r'^:93B::AGGR\/\/FAMT\/(\d*),(\d*)$')
re_total_amount = re.compile(r'^:19A::HOLD\/\/([A-Z]{3})(\d*),{1}(\d*)$')
re_acquisitionprice = re.compile(
    r'^:70E::HOLD\/\/\d*[A-Z]{3}\|2(\d*?),{1}(\d*?)\+([A-Z]{3})$')
re_total_amountportfolio = re.compile(
    r'^:19A::HOLP\/\/([A-Z]{3})(\d*),{1}(\d*)$')
logger = logging.getLogger(__name__)
log_target = logger.info


class Dialogs:
    """
    Dialogues: Customer - Bank
    """

    def __init__(self, mariadb):

        self.mariadb = mariadb
        self._show_message = shelve_get_key(BANK_MARIADB_INI, KEY_SHOW_MESSAGE)
        self._logging = shelve_get_key(BANK_MARIADB_INI, KEY_LOGGING)
        if not self._show_message:
            self._show_message = ERROR

    def _start_dialog(self, bank, msg=Messages()):

        if bank.opened_bank_code != bank.bank_code:
            bank.opened_bank_code = None
            bank.dialog_id = DIALOG_ID_UNASSIGNED
            bank.tan_process = 4
            bank.sca = True
            response = None
            while not response:
                bank.message_number = 1
                if bank.bank_code not in PNS.keys():
                    input_pin = InputPIN(
                        bank.bank_code, bank_name=bank.bank_name)
                    if input_pin.button_state == WM_DELETE_WINDOW:
                        return None
                    PNS[bank.bank_code] = input_pin.pin
                response, _ = self._send_msg(
                    bank, msg.msg_dialog_init(bank), dialog_init=True)
                if response is not None:
                    for seg in response.find_segments(HIUPD6):
                        if bank.iban == seg.iban and seg.extension:
                            formatted_string = json.dumps(
                                seg.extension, indent=4)
                            MessageBoxInfo(message=MESSAGE_TEXT['HIUPD_EXTENSION'].format(
                                bank.bank_name, bank.account_number, bank.account_product_name, bank.iban, formatted_string),
                                bank=bank, information_storage=Informations.BANKDATA_INFORMATIONS)
                    seg = response.find_segment_first(HNHBK3)
                    if seg:
                        break
                Informations.bankdata_informations = ''
                PNS.pop(bank.bank_code, None)
                response = None
            bank.dialog_id = seg.dialog_id
            seg = response.find_segment_first(HITAN6)
            if not seg:
                MessageBoxInfo(message=MESSAGE_TEXT['HITAN6'].format(
                    bank.bank_name, bank.account_number, bank.account_product_name), bank=bank)
            bank.task_reference = seg.task_reference
            response, _ = self._get_tan(bank, msg, response)
            if response:
                bank.opened_bank_code = bank.bank_code
                return response
            else:
                return None  # input of Tan canceled
        else:
            return True  # thread checking

    def _end_dialog(self, bank, msg=Messages()):

        self._send_msg(bank, msg.msg_dialog_end(bank))
        bank.message_number = 1
        bank.opened_bank_code = None

    def _get_tan(self, bank, msg, response):

        hirms_codes = []
        for seg in response.find_segments(HIRMS2):
            for hirms in seg.responses:
                if hirms.code == CODE_0030:
                    bank.tan_process = 2
                    message = msg.msg_tan(bank)
                    if message:
                        response, hirms_codes = self._send_msg(bank, message)
                    else:
                        MessageBoxInfo(message=MESSAGE_TEXT['TAN_CANCEL'].format(
                            bank.bank_name, bank.account_number), bank=bank, information=ERROR)
                    return None, []  # input of tan canceled
        return response, hirms_codes

    def _get_segment(self, bank, segment_type):

        for seg in [HIKAZ6, HIKAZ7, HIWPD5, HIWPD6]:
            if (seg.__name__[2:5] == segment_type and
                    seg.__name__[5:6] == str(bank.transaction_versions[segment_type])):
                return seg
        MessageBoxTermination(info=MESSAGE_TEXT['SEGMENT_VERSION'].format(
            'HI', segment_type, bank.transaction_versions[segment_type]), bank=bank)

    def _store_bpd_shelve(self, bank, response):

        seg = response.find_segment_first(HIBPA3)
        if seg is not None:
            bank.bpd_version = seg.bpd_version
            bank.bank_name = seg.bank_name
            shelve_put_key(bank.bank_code, [
                           (KEY_BPD, bank.bpd_version), (KEY_BANK_NAME, bank.bank_name)])
        else:
            return
        for hitans in [HITANS6, HITANS5, HITANS4, HITANS3, HITANS2, HITANS1]:
            seg = response.find_segment_first(hitans)
            if seg is not None:
                bank.twostep_parameters = []
                for par in seg.parameter.twostep_parameters:
                    if par.tan_process == '2':
                        bank.twostep_parameters.append(
                            (par.security_function, par.name))
                shelve_put_key(
                    bank.bank_code, (KEY_TWOSTEP, bank.twostep_parameters))
                break
        transaction_versions_allowed = {}
        transaction_versions_allowed['KAZ'] = []
        seg = response.find_segment_first(HIKAZS6)
        if seg is not None:
            transaction_versions_allowed['KAZ'].append(seg.header.version)
        seg = response.find_segment_first(HIKAZS7)
        if seg is not None:
            transaction_versions_allowed['KAZ'].append(seg.header.version)
        transaction_versions_allowed['WPD'] = []
        seg = response.find_segment_first(HIWPDS5)
        if seg is not None:
            transaction_versions_allowed['WPD'].append(seg.header.version)
        seg = response.find_segment_first(HIWPDS6)
        if seg is not None:
            transaction_versions_allowed['WPD'].append(seg.header.version)
        shelve_put_key(bank.bank_code, (KEY_VERSION_TRANSACTION_ALLOWED,
                       transaction_versions_allowed))
        if shelve_get_key(bank.bank_code, KEY_VERSION_TRANSACTION):
            bank.transaction_versions = shelve_get_key(
                bank.bank_code, KEY_VERSION_TRANSACTION)
        else:
            # use lowest version
            bank.transaction_versions = {}
            bank.transaction_versions['KAZ'] = 7
            seg = response.find_segment_first(HIKAZS6)
            if seg is not None:
                bank.transaction_versions['KAZ'] = seg.header.version
            bank.transaction_versions['WPD'] = 6
            seg = response.find_segment_first(HIWPDS5)
            if seg is not None:
                bank.transaction_versions['WPD'] = seg.header.version
            shelve_put_key(
                bank.bank_code, (KEY_VERSION_TRANSACTION, bank.transaction_versions))
        seg = response.find_segment_first(HISPAS1)
        bank.sepa_formats = []
        if seg is not None:
            bank.sepa_formats = seg.parameter.supported_sepa_formats
        shelve_put_key(bank.bank_code, (KEY_SEPA_FORMATS, bank.sepa_formats))
        seg = response.find_segment_first(HIPINS1)
        if seg is not None:
            tans_required = []
            for item in seg.parameter.transaction_tans_required:
                tans_required.append((item.transaction, item.tan_required))
            shelve_put_key(bank.bank_code, [(KEY_MIN_PIN_LENGTH, seg.parameter.min_pin_length),
                                            (KEY_MAX_PIN_LENGTH,
                                            seg.parameter.max_pin_length),
                                            (KEY_MAX_TAN_LENGTH,
                                            seg.parameter.max_tan_length),
                                            (KEY_TAN_REQUIRED, tans_required)])
        else:
            MessageBoxInfo(message=MESSAGE_TEXT['HIPINS1'], bank=bank)
            shelve_put_key(bank.bank_code, [(KEY_MIN_PIN_LENGTH, 3),
                                            (KEY_MAX_PIN_LENGTH, 20),
                                            (KEY_MAX_TAN_LENGTH, 10)])
        seg = response.find_segment_first(HIKAZS7)
        if seg is not None:
            bank.storage_period = seg.parameter.storage_period
        else:
            seg = response.find_segment_first(HIKAZS6)
            if seg is not None:
                bank.storage_period = seg.parameter.storage_period
            else:
                bank.storage_period = 90
        shelve_put_key(
            bank.bank_code, (KEY_STORAGE_PERIOD, bank.storage_period))

    def _store_sync_shelve(self, bank, response):

        seg = response.find_segment_first(HNHBK3)
        if seg is not None:
            bank.dialog_id = seg.dialog_id
        else:
            MessageBoxTermination(info=MESSAGE_TEXT['HNHBK3'], bank=bank)
        seg = response.find_segment_first(HISYN4)
        if seg is not None:
            bank.system_id = seg.system_id
            bank.security_identifier = seg.system_id
            shelve_put_key(bank.bank_code, (KEY_SYSTEM_ID, seg.system_id))
        else:
            MessageBoxTermination(info=MESSAGE_TEXT['HISYN4'], bank=bank)
        seg = response.find_segment_first(HISPAS1)
        if seg is not None:
            bank.sepa_formats = seg.parameter.supported_sepa_formats
            shelve_put_key(
                bank.bank_code, (KEY_SEPA_FORMATS, bank.sepa_formats))
        self._store_upd_shelve(bank, response)

    def _store_upd_shelve(self, bank, response):
        ' If Bank not provide User Parameter Data during Synchronization'
        seg = response.find_segment_first(HIUPA4)
        if seg is not None:
            bank.upd_version = seg.upd_version
            shelve_put_key(bank.bank_code, (KEY_UPD, bank.upd_version))
        else:
            return
        seg = response.find_segment_first(HIUPD6)
        if seg is not None:
            bank.accounts = []
            for upd in response.find_segments(HIUPD6):
                if upd.account_information.account_number:
                    acc = {}
                    if upd.iban:
                        acc[KEY_ACC_IBAN] = upd.iban
                    else:
                        acc[KEY_ACC_IBAN] = create_iban(
                            bank_code=upd.account_information.bank_identifier.bank_code,
                            account_number=upd.account_information.account_number)
                    acc[KEY_ACC_ACCOUNT_NUMBER] = upd.account_information.account_number
                    acc[KEY_ACC_SUBACCOUNT_NUMBER] = upd.account_information.subaccount_number
                    acc[KEY_ACC_BANK_CODE] = upd.account_information.bank_identifier.bank_code
                    acc[KEY_ACC_CUSTOMER_ID] = upd.customer_id
                    acc[KEY_ACC_TYPE] = upd.account_type
                    acc[KEY_ACC_CURRENCY] = upd.account_currency
                    if upd.name_account_owner_1:
                        acc[KEY_ACC_OWNER_NAME] = upd.name_account_owner_1
                    if upd.name_account_owner_2:
                        acc[KEY_ACC_OWNER_NAME] = (acc[KEY_ACC_OWNER_NAME]
                                                   + upd.name_account_owner_2)
                    acc[KEY_ACC_PRODUCT_NAME] = upd.account_product_name
                    acc[KEY_ACC_ALLOWED_TRANSACTIONS] = []
                    for allowed_transaction in upd.allowed_transactions:
                        if allowed_transaction.transaction is not None:
                            acc[KEY_ACC_ALLOWED_TRANSACTIONS].append(
                                allowed_transaction.transaction)
                    bank.accounts.append(acc)
            shelve_put_key(bank.bank_code, (KEY_ACCOUNTS, bank.accounts))

    def _receive_msg(self, bank, msg, response, hirms_codes):

        if CODE_0030 in hirms_codes:
            seg = response.find_segment_first(HITAN6)
            if not seg:
                MessageBoxInfo(message=MESSAGE_TEXT[CODE_0030].format(
                    bank.bank_name, bank.account_number, bank.account_product_name), bank=bank, information=WARNING)
                return [], hirms_codes
            if current_thread() is main_thread():
                bank.task_reference = seg.task_reference
                response, hirms_codes = self._get_tan(bank, msg, response)
            else:
                MessageBoxInfo(message=MESSAGE_TEXT[CODE_0030].format(
                    bank.bank_name, bank.account_number, bank.account_product_name), bank=bank, information=WARNING)
        return response, hirms_codes

    def _send_msg(self, bank, message, dialog_init=False):

        if self._logging:
            log_out = io.StringIO()
            with Password.protect():
                message.print_nested(stream=log_out, prefix="\t")
                logger.debug(('Sending ' + 30 * '>' + '\n{}\n' + 40 * '>' + '\n').format
                             (log_out.getvalue()))
                log_out.truncate(0)
        r = requests.post(bank.server,
                          headers={b'Content-Type': 'text/plain;charset=UTF-8'},
                          data=base64.b64encode(message.render_bytes()))
        if r.status_code < 200 or r.status_code > 299:
            MessageBoxTermination(info=MESSAGE_TEXT(
                'SEND_ERROR').format(r.status_code), bank=bank)
        try:
            response = FinTSInstituteMessage(
                segments=base64.b64decode(r.content.decode('latin1')))
        except Exception:
            exception_error(
                message=MESSAGE_TEXT['RESPONSE'])
            PrintMessageCode(text=Informations.bankdata_informations)
            if dialog_init:
                return None,  []
            else:
                MessageBoxTermination(bank=bank)
        bank.response = response
        if self._logging:
            with Password.protect():
                response.print_nested(stream=log_out, prefix="\t")
                logger.debug(('Received ' + 30 * '>' + '\n{}\n' + 40 * '>' + '\n').format
                             (log_out.getvalue()))
        seg = response.find_segment_first(HIRMG2)
        # bank feedback message
        error, fints_codes = self._fints_code(bank, seg)
        if error:
            PrintMessageCode(text=Informations.bankdata_informations)
            if dialog_init:
                return None,  fints_codes
            else:
                MessageBoxTermination(bank=bank)
        # bank feedback segments of message
        for seg in response.find_segments(HIRMS2):
            error, hirms_codes = self._fints_code(bank, seg)
            fints_codes = fints_codes + hirms_codes
            if error:
                PrintMessageCode(text=Informations.bankdata_informations)
                if dialog_init:
                    return None,  fints_codes
                else:
                    MessageBoxTermination(bank=bank)
        return response, fints_codes

    def _fints_code(self, bank, segment):

        codes = []
        error = False
        for response in segment.responses:
            codes.append(response.code)
            if response.code == '3076':      # SCA not required
                bank.sca = False
            if response.code[0] in ['0', '1']:
                if self._show_message == INFORMATION:
                    Informations.bankdata_informations = Informations.bankdata_informations + '\n{} Code {} {} '.format(
                        INFORMATION, response.code, response.text)
            elif response.code[0] == '3':
                if response.code == '3010':    # no entries found
                    MessageBoxInfo(message=MESSAGE_TEXT['NO_TURNOVER'].format(
                        bank.bank_name, bank.account_number, bank.account_product_name), bank=bank)
                if self._show_message in [INFORMATION, WARNING]:
                    Informations.bankdata_informations = Informations.bankdata_informations + '\n{} Code {} {} '.format(
                        WARNING, response.code, response.text)
                    bank.warning_message = True
            else:
                error = True
                Informations.bankdata_informations = Informations.bankdata_informations + '\n{} Code {} - Bezugssegment ({}) '.format(
                    ERROR, response.code, response.reference_element)
                Informations.bankdata_informations = Informations.bankdata_informations + '\n{} {} Parameters {}'.format(
                    ERROR, response.text, response.parameters)
        return error, codes

    def _mt535_listdict(self, data):
        """
        documentation:
         https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Finanzdatenformate_2010-08-06_final_version.pdf
        (For more Information Chapter  B.4 page 150)

        Modified Coding copied from
            Pure-python FinTS (formerly known as HBCI) implementation https://pypi.python.org/pypi/fints
        """
        dec2 = Calculate(places=2)
        dec6 = Calculate(places=6)
        mt535_lines = str.splitlines(data)
        # The first line is empty.
        del mt535_lines[0]
        # First: Collapse multiline clauses into one clause
        clauses = self._collapse_multilines(mt535_lines)
        # Check price_date header information
        for clause in clauses:
            m = re_pricedate04.match(clause)
            if m:
                _price_date = m.group(1)
            m = re_pricedate03.match(clause)
            if m:
                _price_date = m.group(1)
            m = re_total_amountportfolio.match(clause)
            if m:
                _total_amount_portfolio = dec2.convert(
                    float(m.group(2) + '.' + m.group(3)))
        # Second: Scan sequence of clauses for financial instrument
        finsegs = self._grab_financial_instrument_segments(clauses)
        # Third: Extract financial instrument data
        mt535 = []
        for idx, finseg in enumerate(finsegs):
            mt535.append({})
            mt535[idx]['price_date'] = _price_date
            for clause in finseg:
                # identification of instrument
                # e.g. ':35B:ISIN LU0635178014|/DE/ETF127|COMS.-MSCI
                # EM.M.T.U.ETF I'
                m = re_identification.match(clause)
                if m:
                    mt535[idx]['ISIN'] = m.group(1)
                    mt535[idx]['name'] = m.group(3)
                # current market price
                # e.g. ':90B::MRKT//ACTU/EUR38,82'
                m = re_marketprice.match(clause)
                if m:
                    mt535[idx]['price_currency'] = m.group(1)
                    mt535[idx]['market_price'] = dec6.convert(
                        float(m.group(2) + '.' + m.group(3)))
                else:
                    m = re_marketprice01.match(clause)
                    if m:
                        mt535[idx]['price_currency'] = PERCENT
                        mt535[idx]['market_price'] = dec6.convert(
                            float(m.group(1) + '.' + m.group(2)))
                # date of market price
                # e.g. ':98A::PRIC//20170428'
                m = re_pricedate02.match(clause)
                if m:
                    mt535[idx]['price_date'] = m.group(1)
                elif not m:
                    m = re_pricedate01.match(clause)
                    if m:
                        mt535[idx]['price_date'] = m.group(1)
                # number of pieces
                # e.g. ':93B::AGGR//UNIT/16,8211'
                m = re_pieces.match(clause)
                if m:
                    mt535[idx]['pieces'] = dec2.convert(
                        float(m.group(1) + '.' + m.group(2)))
                else:
                    m = re_pieces01.match(clause)
                    if m:
                        mt535[idx]['pieces'] = dec2.convert(
                            float(m.group(1) + '.' + m.group(2)))
                # total value of holding
                # e.g. ':19A::HOLD//EUR970,17'
                m = re_total_amount.match(clause)
                if m:
                    mt535[idx]['amount_currency'] = m.group(1)
                    mt535[idx]['total_amount'] = dec2.convert(
                        float(m.group(2) + '.' + m.group(3)))
                # Acquisition price
                # e.g ':70E::HOLD//1STK23,968293+EUR'
                m = re_acquisitionprice.match(clause)
                if m:
                    mt535[idx]['acquisition_price'] = dec6.convert(
                        float(m.group(1) + '.' + m.group(2)))
                # Exchange_rate
                # e.g ':92B::EXCH//EUR/TRY/6,3926'
                m = re_exchange_rate.match(clause)
                if m:
                    mt535[idx]['exchange_currency_1'] = m.group(1)
                    mt535[idx]['exchange_currency_2'] = m.group(2)
                    mt535[idx]['exchange_rate'] = float(
                        m.group(3) + '.' + m.group(4))
                    if mt535[idx]['exchange_rate'] != 0:
                        if mt535[idx]['exchange_currency_2'] == mt535[idx]['amount_currency']:
                            mt535[idx]['amount_currency'] = mt535[idx]['exchange_currency_1']
                            mt535[idx]['total_amount'] = dec2.divide(
                                mt535[idx]['total_amount'], mt535[idx]['exchange_rate'])
                        if mt535[idx]['exchange_currency_2'] == mt535[idx]['price_currency']:
                            mt535[idx]['price_currency'] = mt535[idx]['exchange_currency_1']
                            mt535[idx]['market_price'] = dec6.divide(
                                mt535[idx]['market_price'], mt535[idx]['exchange_rate'])
            mt535[idx]['total_amount_portfolio'] = _total_amount_portfolio
        return mt535

    def _collapse_multilines(self, lines):

        clauses = []
        prevline = ""
        for line in lines:
            if line.startswith(":"):
                if prevline != "":
                    clauses.append(prevline)
                prevline = line
            elif line.startswith("-"):
                # last line
                clauses.append(prevline)
                clauses.append(line)
            else:
                prevline += "|{}".format(line)
        return clauses

    def _grab_financial_instrument_segments(self, clauses):
        retval = []
        stack = []
        within_financial_instrument = False
        for clause in clauses:
            if clause.startswith(":16R:FIN"):
                # start of financial instrument
                within_financial_instrument = True
            elif clause.startswith(":16S:FIN"):
                # end of financial instrument - move stack over to
                # return value
                retval.append(stack)
                stack = []
                within_financial_instrument = False
            else:
                if within_financial_instrument:
                    stack.append(clause)
        return retval

    def _mt940_listdict(self, data, bank_code):
        """
        documentation:
        https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Finanzdatenformate_2010-08-06_final_version.pdf
        (For more Information Chapter  B.8 page 174)
        """

        transactions = Transactions()
        dec2 = Calculate(places=2)
        mt940 = []
        identifier_delimiter = shelve_get_key(
            bank_code, KEY_IDENTIFIER_DELIMITER)
        # bank: CONSORS
        # transactions.parse returns duplicate customer_reference value separated
        # by <LF>
        keys_not_used = []
        for mt940_statement in transactions.parse(data):
            for key_ in mt940_statement.data.keys():
                if key_ not in self.mariadb.table_fields[STATEMENT] or mt940_statement.data[key_] is None:
                    keys_not_used.append(key_)
                else:
                    value = mt940_statement.data[key_]
                    if value is not None and isinstance(value, str):
                        mt940_statement.data[key_] = value.replace('\n', ' ')
                    if isinstance(value, date):
                        mt940_statement.data[key_] = str(value)
            for key_ in keys_not_used:
                del mt940_statement.data[key_]
            keys_not_used = []
            mt940.append(mt940_statement.data)
        idx_mt940 = 0
        clauses = data.splitlines()
        tags = Transactions.defaultTags().copy()
        for clause in clauses:
            m = tags['60F'].re.match(clause[5:])  # opening balance data
            if clause[0:5] == ':60F:' and m:
                _opening_status = m.group('status')
                _entry_date = datetime.strptime(
                    m.group('year') + m.group('month') + m.group('day'), '%y%m%d').date()
                _opening_entry_date = _entry_date
                _opening_currency = m.group('currency')
                _opening_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
                _closing_status = m.group('status')
                _closing_entry_date = _entry_date
                _closing_currency = m.group('currency')
                _closing_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
            m = tags['60M'].re.match(clause[5:])  # opening balance data
            if clause[0:5] == ':60M:' and m:
                _opening_status = m.group('status')
                _entry_date = datetime.strptime(
                    m.group('year') + m.group('month') + m.group('day'), '%y%m%d').date()
                _opening_entry_date = _entry_date
                _opening_currency = m.group('currency')
                _opening_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
                _closing_status = m.group('status')
                _closing_entry_date = _entry_date
                _closing_currency = m.group('currency')
                _closing_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
            m = tags[61].re.match(clause[4:])  # transaction data
            if clause[0:4] == ':61:' and m:
                _amount = dec2.convert(abs(Amount(m.group('amount'),
                                                  m.group('status')).amount))
                _status = m.group('status')
                try:
                    _entry_date = datetime.strptime(
                        m.group('entry_date'), '%y%m%d').date()
                except IndexError:
                    pass
                mt940[idx_mt940]['entry_date'] = _entry_date
                mt940[idx_mt940]['amount'] = _amount
                mt940[idx_mt940]['currency'] = _opening_currency
                mt940[idx_mt940].update({'opening_status': _opening_status})
                mt940[idx_mt940].update(
                    {'opening_entry_date': _opening_entry_date})
                mt940[idx_mt940].update(
                    {'opening_currency': _opening_currency})
                mt940[idx_mt940].update({'opening_balance': _opening_balance})
                x = _opening_balance
                if _opening_status == 'D':
                    x = -x
                y = _amount
                if _status == 'D':
                    y = -y
                _closing_balance = dec2.add(x, y)
                _closing_status = 'C' if (_closing_balance > 0) else 'D'
                mt940[idx_mt940].update({'closing_status': _closing_status})
                mt940[idx_mt940].update(
                    {'closing_entry_date': _closing_entry_date})
                mt940[idx_mt940].update(
                    {'closing_currency': _closing_currency})
                mt940[idx_mt940].update(
                    {'closing_balance': abs(_closing_balance)})
                _opening_balance = abs(_closing_balance)
                _opening_status = _closing_status
                mt940[idx_mt940] = self._create_identifiers(
                    mt940[idx_mt940], identifier_delimiter)
                idx_mt940 += 1
        return mt940

    def _create_identifiers(self, mt940, identifier_delimiter):

        if 'purpose' in mt940:
            identifiers = []
            purpose = mt940['purpose'].replace(' ', '')
            for identifier in IDENTIFIER.keys():
                identifier = identifier + identifier_delimiter
                m = re.compile(identifier).search(purpose)
                if m is not None:
                    identifiers.append((m.group(), m.start(), m.end()))
            identifiers = sorted(identifiers, key=itemgetter(1))
            purpose_all = purpose
            for idx, identifier in enumerate(identifiers):
                name, start, end = identifier
                name = name[:-1]
                if idx == 0:
                    purpose = purpose_all[0:start]
                    mt940.update({'purpose_wo_identifier': purpose})
                try:
                    _, next_start, _ = identifiers[idx + 1]
                except IndexError:
                    next_start = len(purpose_all)
                value = purpose_all[end:next_start]
                if len(value) > 65:
                    value = value[0:65]
                mt940.update({IDENTIFIER[name]: value})
            if 'purpose_wo_identifier' not in mt940:
                mt940['purpose_wo_identifier'] = mt940['purpose']
        return mt940

    def anonymous(self, bank, msg=Messages()):
        ' HITANS >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
        bank.message_number = 1
        bank.dialog_id = DIALOG_ID_UNASSIGNED
        response, _ = self._send_msg(
            bank, msg.msg_dialog_anonymous(bank))
        self._store_bpd_shelve(bank, response)

    def sync(self, bank, msg=Messages()):
        ' HISYN >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
        bank.message_number = 1
        bank.dialog_id = DIALOG_ID_UNASSIGNED
        response, _ = self._send_msg(bank, msg.msg_dialog_syn(bank))
        self._store_sync_shelve(bank, response)
        self._end_dialog(bank)

        ' HIUPD 2nd search >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
        seg = response.find_segment_first(HIUPD6)
        if not seg:
            response = self._start_dialog(bank)
            if response:
                self._store_upd_shelve(bank, response)
                self._end_dialog(bank)

    def holdings(self, bank, msg=Messages()):

        if self._start_dialog(bank):
            bank.tan_process = 4
            response, hirms_codes = self._send_msg(
                bank, msg.msg_holdings(bank))
            response, hirms_codes = self._receive_msg(
                bank, msg, response, hirms_codes)
            if not response:
                return False
            hiwpd = self._get_segment(bank, 'WPD')
            seg = response.find_segment_first(hiwpd)
            if not seg:
                MessageBoxTermination(
                    info=MESSAGE_TEXT['HIWPD'].format(hiwpd.__name__), bank=bank)
                return False  # thread checking
            if type(seg.holdings) is bytes:
                try:
                    holding_str = seg.holdings.decode('utf-8')
                except UnicodeDecodeError:
                    holding_str = seg.holdings.decode('latin1')
            else:
                holding_str = seg.holdings
            if self._logging:
                logger.debug('\n\n>>>>> START MT535 DATA ' + 40 * '>' + '\n')
                log_target(holding_str)
                logger.debug('\n\n>>>>> START MT535 DATA PARSING ' +
                             30 * '>' + '\n')
            self._end_dialog(bank)
            return self._mt535_listdict(holding_str)
        else:
            return None

    def statements(self, bank, msg=Messages()):

        if self._start_dialog(bank):
            statements = []
            bank.tan_process = 4
            response, hirms_codes = self._send_msg(
                bank, msg.msg_statements(bank))
            response, hirms_codes = self._receive_msg(
                bank, msg, response, hirms_codes)
            if not response:
                return []
            if CODE_3010 in hirms_codes:
                return statements
            if CODE_0030 not in hirms_codes:
                if CODE_3040 in hirms_codes:  # further turnovers exist
                    MessageBoxInfo(message=MESSAGE_TEXT[CODE_3040].format(
                        bank.bank_name, bank.account_number, bank.account_product_name), bank=bank, information=WARNING)
                hikaz = self._get_segment(bank, 'KAZ')
                seg = response.find_segment_first(hikaz)
                if not seg:
                    MessageBoxInfo(message=MESSAGE_TEXT['HIKAZ'].format(
                        bank.bank_name, bank.account_number, bank.account_product_name), bank=bank, information=ERROR)
                    return False  # thread checking
                try:
                    statement_booked_str = seg.statement_booked.decode('utf-8')
                except UnicodeDecodeError:
                    statement_booked_str = seg.statement_booked.decode(
                        'latin1')
                if self._logging:
                    logger.debug('\n\n>>>>> START MT940 DATA ' +
                                 40 * '>' + '\n')
                    log_target(statement_booked_str)
                    logging.getLogger(__name__).debug(
                        '\n\n>>>>> START MT940 DATA PARSING ' + 30 * '>' + '\n')
                statements = self._mt940_listdict(
                    statement_booked_str, bank.bank_code)
            self._end_dialog(bank)
            return statements
        else:
            return None

    def transfer(self, bank, msg=Messages()):

        if self._start_dialog(bank):
            bank.tan_process = 4
            response, _ = self._send_msg(
                bank, msg.msg_transfer(bank))
            seg = response.find_segment_first(HITAN6)
            if not seg:
                MessageBoxTermination(info=MESSAGE_TEXT['HITAN6'], bank=bank)
                return False  # thread checking
            bank.task_reference = seg.task_reference
            response, _ = self._get_tan(bank, msg, response)
            if response:
                self._end_dialog(bank)
            else:
                return None
        else:
            return None

    def date_transfer(self, bank, msg=Messages()):

        if self._start_dialog(bank):
            bank.tan_process = 4
            response, _ = self._send_msg(
                bank, msg.msg_date_transfer(bank))
            seg = response.find_segment_first(HITAN6)
            if not seg:
                MessageBoxTermination(info=MESSAGE_TEXT['HITAN6'], bank=bank)
                return False  # thread checking
            bank.task_reference = seg.task_reference
            response, _ = self._get_tan(bank, msg, response)
            if response:
                self._end_dialog(bank)
            else:
                return None  # input of Tan canceled
        else:
            return None
