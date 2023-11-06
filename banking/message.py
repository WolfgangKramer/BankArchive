"""
Created on 18.11.2019
__updated__ = "2023-08-27"
@author: Wolfgang Kramer
"""
import inspect
import logging

from fints.client import FinTS3Serializer

from banking.declarations import CUSTOMER_ID_ANONYMOUS, KEY_TAN_REQUIRED
from banking.segment import Segments
from banking.utils import shelve_get_key


def _serialize(message):

    fints3serializer = FinTS3Serializer()
    byte_message = fints3serializer.serialize_message(message).split(b"'")
    logging.getLogger(__name__).debug('\n\n>>>>> START' + 80 * '>' + '\n')
    logging.getLogger(__name__).debug(inspect.stack()[1])
    for item in byte_message:
        logging.getLogger(__name__).debug(item)


def _get_tan_required(bank, segment_type):

    tan_required = True
    transactions_tan_required = shelve_get_key(
        bank.bank_code, KEY_TAN_REQUIRED)
    for item in transactions_tan_required:
        transaction, tan_required = item
        if transaction == segment_type:
            break
    return tan_required


class Messages():
    """
    FinTS Message Structures

    Documentation:
    https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf
    """

    def msg_dialog_init(self, bank, seg=Segments()):
        """
        (For more Information Chapter  C.3 Page 41)
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKIND(bank, message)
        message = seg.segHKVVB(bank, message)
        message = seg.segHKTAN(bank, message)
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_dialog_anonymous(self, bank, seg=Segments()):
        """
        (For more Information Chapter  C.5 Page 55)
        """
        message = seg.segHNHBK(bank)
        message = seg.segHKIND(bank, message, user_id=CUSTOMER_ID_ANONYMOUS)
        message = seg.segHKVVB(bank, message)
        message = seg.segHKTAN(bank, message)
        message = seg.segHNHBSnoencrypt(bank, message)
        _serialize(message)
        return message

    def msg_dialog_syn(self, bank, seg=Segments()):
        """
        (For more Information Chapter  C.8 Page 66)
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKIND(bank, message)
        message = seg.segHKVVB(bank, message)
        message = seg.segHKTAN(bank, message)
        message = seg.segHKSYN(bank, message)
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_tan(self, bank, seg=Segments()):
        """
        FinTS Message TAN challenge
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKTAN(bank, message)
        message = seg.segHNSHA_TAN(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_statements(self, bank, seg=Segments()):
        """
        FinTS Message Request of account turnovers
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKKAZ(bank, message)
        if _get_tan_required(bank, 'HKKAZ'):
            message = seg.segHKTAN(bank, message, segment_name='HKKAZ')
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_holdings(self, bank, seg=Segments()):
        """
        FinTS Message Request of Portfolio
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKWPD(bank, message)
        if _get_tan_required(bank, 'HKWPD'):
            message = seg.segHKTAN(bank, message, segment_name='HKWPD')
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_trading(self, bank, seg=Segments()):
        """
        FinTS Message Request of movements in portfolio (untested!!)
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKWDU(bank, message)
        if _get_tan_required(bank, 'HKWDU'):
            message = seg.segHKTAN(bank, message, segment_name='HKWDU')
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_transfer(self, bank, seg=Segments()):
        """
        FinTS Message Execution of a SEPA credit transfer
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKCCS1(bank, message)
        if _get_tan_required(bank, 'HKCCS'):
            message = seg.segHKTAN(bank, message, segment_name='HKCCS')
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_date_transfer(self, bank, seg=Segments()):
        """
        FinTS Message Execution of a SEPA date credit transfer
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKCSE1(bank, message)
        if _get_tan_required(bank, 'HKCSE'):
            message = seg.segHKTAN(bank, message, segment_name='HKCSE')
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_dialog_end(self, bank, seg=Segments()):
        """
        (For more Information Chapter  C.4 Page 53)
        """
        message = seg.segHNHBK(bank)
        message = seg.segHNSHK(bank, message)
        message = seg.segHKEND(bank, message)
        message = seg.segHNSHA(bank, message)
        message = seg.segHNHBS(bank, message)
        _serialize(message)
        return message
