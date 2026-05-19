"""
Created on 18.11.2019
__updated__ = "2026-05-19"
@author: Wolfgang Kramer
"""

import inspect
import logging

from fints.client import FinTS3Serializer

import banking.declarations as decl
import banking.declarations_mariadb as declm

from banking.repository import Repository
from banking.fints_segment import Segments
from banking.utils import application_store


def _serialize(message):

    if application_store.get(declm.DB_logging):
        fints3serializer = FinTS3Serializer()
        byte_message = fints3serializer.serialize_message(message).split(b"'")
        logging.getLogger(__name__).debug('\n\n>>>>> START' + 80 * '>' + '\n')
        logging.getLogger(__name__).debug(inspect.stack()[1])
        for item in byte_message:
            logging.getLogger(__name__).debug(item)


def _get_tan_required(bank, segment_type, repo):

    tan_required = True
    transactions_tan_required = repo.shelve_get_tan_required(bank.bank_code)
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

    def __init__(self):

        self.repo = Repository()
        self.segments = Segments(self.repo)

    def msg_dialog_init(self, bank):
        """
        (For more Information Chapter  C.3 Page 41)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKIND(bank, message)
        message = self.segments.segHKVVB(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_dialog_anonymous(self, bank):
        """
        (For more Information Chapter  C.5 Page 55)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHKIND(
            bank, message, user_id=decl.CUSTOMER_ID_ANONYMOUS)
        message = self.segments.segHKVVB(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHNHBSnoencrypt(bank, message)
        _serialize(message)
        return message

    def msg_dialog_syn(self, bank):
        """
        (For more Information Chapter  C.8 Page 66)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKIND(bank, message)
        message = self.segments.segHKVVB(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHKSYN(message)
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_tan_decoupled(self, bank):
        """
        FinTS Message TAN challenge decoupled
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKTAN_decoupled(bank, message)
        message = self.segments.segHNSHA_TAN(bank, message)
        if message:
            message = self.segments.segHNHBS(bank, message)
            _serialize(message)
            return message
        return None  # input of tan canceled

    def msg_tan(self, bank):
        """
        FinTS Message TAN challenge
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHNSHA_TAN(bank, message)
        if message:
            message = self.segments.segHNHBS(bank, message)
            _serialize(message)
            return message
        return None  # input of tan canceled

    def msg_statements(self, bank):
        """
        FinTS Message Request of account turnovers (MT940)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        if bank.statement_mt940:
            message = self.segments.segHKKAZ(bank, message)
            if _get_tan_required(bank, 'HKKAZ', self.repo):
                message = self.segments.segHKTAN(
                    bank, message, segment_name='HKKAZ')
        else:
            message = self.segments.segHKCAZ(bank, message)
            if _get_tan_required(bank, 'HKCAZ', self.repo):
                message = self.segments.segHKTAN(
                    bank, message, segment_name='HKCAZ')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_holdings(self, bank):
        """
        FinTS Message Request of Portfolio
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKWPD(bank, message)
        if _get_tan_required(bank, 'HKWPD', self.repo):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKWPD')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_trading(self, bank):
        """
        FinTS Message Request of movements in portfolio (untested!!)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKWDU(bank, message)
        if _get_tan_required(bank, 'HKWDU', self.repo):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKWDU')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_dialog_end(self, bank):
        """
        (For more Information Chapter  C.4 Page 53)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKEND(bank, message)
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message
