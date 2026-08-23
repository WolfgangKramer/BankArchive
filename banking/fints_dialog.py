"""
Created on 18.11.2019
__updated__ = "2026-08-07"
@author: Wolfgang Kramer
"""

import base64
import io
import json
import logging
import re
import requests
import xmltodict
import xml.dom.minidom as minidom

from decimal import Decimal
from typing import Any, List, Dict, Optional, Tuple
from datetime import date
from operator import itemgetter
from fints.message import FinTSInstituteMessage
from fints.segments.auth import (
    HITAN6, HITAN7, HITANS1, HITANS2, HITANS3, HITANS4, HITANS5, HITANS6, HITANS7, HIPINS1
)
from fints.segments.bank import HIBPA3, HIUPA4, HIUPD6
from fints.segments.depot import HIWPD5, HIWPD6
from fints.segments.dialog import HISYN4, HIRMG2, HIRMS2
from fints.segments.message import HNHBK3
from fints.segments.statement import HIKAZ6, HIKAZ7, HICAZ1, HICAZS1
from fints.utils import Password
from mt940.models import Transactions

import banking.declarations as decl
import banking.declarations_mariadb as declm
import banking.message_handler as msg

from banking.fints_extension import HIKAZS6, HIKAZS7, HIWPDS5, HIWPDS6
from banking.forms import InputPIN, ProtocolViewer
from banking.fints_message import Messages
from banking.utils import (
    Amount, application_store,
    dict_get_nested_value, dec2, dec6,
    create_iban,
    date_yymmdd,
    )
from banking.repository import Repository


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


class UPDService:

    def __init__(self, repo):
        self.repo = repo

    def process_response(self, bank, response):
        if not self._update_upd_version(bank, response):
            return
        accounts = self._extract_accounts(response)
        if accounts:
            bank.accounts = accounts
            self.repo.shelve_put_key(
                bank.bank_code, (decl.KEY_ACCOUNTS, accounts)
            )
        self._show_message(bank)

    def _update_upd_version(self, bank, response) -> bool:
        seg = response.find_segment_first(HIUPA4)
        if seg is None:
            return False
        if Dialogs.upd_updated:
            return False
        if seg.upd_version > 1 and bank.upd_version == seg.upd_version:
            return False
        bank.upd_version = seg.upd_version
        self.repo.shelve_put_key(
            bank.bank_code, (decl.KEY_UPD, bank.upd_version)
        )
        Dialogs.upd_updated = True
        return True

    def _extract_accounts(self, response):

        if response.find_segment_first(HIUPD6) is None:
            return []
        accounts = []
        for upd in response.find_segments(HIUPD6):
            if not upd.account_information.account_number:
                continue
            accounts.append(self._build_account(upd))
        return accounts

    def _build_account(self, upd):
        iban = upd.iban or create_iban(
            bank_code=upd.account_information.bank_identifier.bank_code,
            account_number=upd.account_information.account_number
        )
        acc = {
            decl.KEY_ACC_IBAN: iban,
            decl.KEY_ACC_ACCOUNT_NUMBER: upd.account_information.account_number,
            decl.KEY_ACC_SUBACCOUNT_NUMBER: upd.account_information.subaccount_number,
            decl.KEY_ACC_BANK_CODE: upd.account_information.bank_identifier.bank_code,
            decl.KEY_ACC_CUSTOMER_ID: upd.customer_id,
            decl.KEY_ACC_TYPE: upd.account_type,
            decl.KEY_ACC_CURRENCY: upd.account_currency,
            decl.KEY_ACC_PRODUCT_NAME: upd.account_product_name,
            decl.KEY_ACC_ALLOWED_TRANSACTIONS: [
                t.transaction
                for t in upd.allowed_transactions
                if t.transaction is not None
            ]
        }
        owner_name = (upd.name_account_owner_1 or "") + (upd.name_account_owner_2 or "")
        if owner_name:
            acc[decl.KEY_ACC_OWNER_NAME] = owner_name
        return acc

    def _show_message(self, bank):
        msg.MessageBoxInfo(
            message=msg.get_message(
                msg.MESSAGE_TEXT,
                'FINTS_UPDATE_UPD_VERSION',
                bank.bank_name,
                bank.upd_version
            ),
            information=decl.INFORMATION
        )


class BPDService:
    """
    Service responsible for extracting BPD-related data from a response
    and persisting it into the repository.
    """

    def __init__(self, repo: Any) -> None:
        self.repo = repo

    def update_bank(self, bank: Any, response: Any, update_bpd: bool = False) -> None:
        """Main entry point."""

        self.repo.shelve_del_key(bank.bank_code, decl.KEY_SUPPORTED_SEPA_FORMATS)  # deprecated key
        hibpa = self._get_segment(response, HIBPA3)
        if not hibpa:
            return
        if not self._should_update_bpd(bank, hibpa, update_bpd):
            return
        self._update_basic_bank_data(bank, hibpa)
        self._store_camt_messages(bank, response)
        self._store_twostep_parameters(bank, response)
        self._store_transaction_versions_allowed(bank, response)
        self._store_transaction_versions(bank, response)
        self._store_pin_tan_rules(bank, response)
        self._store_storage_period(bank, response)
        self._notify_bpd_update(bank)

    def _should_update_bpd(self, bank: Any, seg: Any, update_bpd: bool) -> bool:
        """Determine whether BPD update is required."""

        if update_bpd:
            return True
        if Dialogs.bpd_updated:
            return False
        if seg.bpd_version <= 1:
            return True
        if bank.bpd_version == seg.bpd_version:
            return False
        return True

    def _update_basic_bank_data(self, bank: Any, seg: Any) -> None:
        """Update basic bank attributes and persist them."""

        bank.bpd_version = seg.bpd_version
        bank.bank_name = seg.bank_name
        self.repo.shelve_put_key(
            bank.bank_code,
            [(decl.KEY_BPD, bank.bpd_version), (decl.KEY_BANK_NAME, bank.bank_name)]
        )
        Dialogs.bpd_updated = True

    def _get_segment(self, response: Any, segment_type: Any) -> Optional[Any]:
        """Safely fetch first segment."""
        return response.find_segment_first(segment_type)

    def _get_first_available_segment(
        self,
        response: Any,
        *segment_types: Any
    ) -> Optional[Any]:
        """Return first matching segment from a list."""
        for seg_type in segment_types:
            if seg := response.find_segment_first(seg_type):
                return seg
        return None

    def _get_version(self, response: Any, *segments: Any, default: int) -> int:
        """Extract version from first matching segment."""
        seg = self._get_first_available_segment(response, *segments)
        return seg.header.version if seg else default

    def _store_camt_messages(self, bank: Any, response: Any) -> None:
        seg = self._get_segment(response, "HICAZS")
        if not seg:
            return
        try:
            bank.supported_camt_messages = seg.parameter.supported_camt_formats
        except KeyError:
            bank.supported_camt_messages = None

        self.repo.shelve_put_key(
            bank.bank_code,
            (decl.KEY_SUPPORTED_CAMT_MESSAGE, bank.supported_camt_messages)
        )

    def _store_twostep_parameters(self, bank: Any, response: Any) -> None:
        for hitans in (HITANS7, HITANS6, HITANS5, HITANS4, HITANS3, HITANS2, HITANS1):
            seg = self._get_segment(response, hitans)
            if not seg:
                continue
            bank.twostep_parameters = [
                (par.security_function, par.name)
                for par in seg.parameter.twostep_parameters
                if par.tan_process == '2'
            ]
            self.repo.shelve_put_key(
                bank.bank_code,
                (decl.KEY_TWOSTEP, bank.twostep_parameters)
            )
            return

    def _store_transaction_versions_allowed(self, bank: Any, response: Any) -> None:

        result: Dict[str, List[int]] = {}

        def collect(key: str, segments: List[Any]) -> None:
            versions = [
                seg.header.version
                for s in segments
                if (seg := self._get_segment(response, s))
            ]
            if versions:
                result[key] = versions
        collect('KAZ', [HIKAZS7, HIKAZS6])
        collect('CAZ', [HICAZS1])
        collect('TAN', [HITANS7, HITANS6])
        collect('WPD', [HIWPDS6, HIWPDS5])
        self.repo.shelve_put_key(
            bank.bank_code,
            (decl.KEY_VERSION_TRANSACTION_ALLOWED, result)
        )

    def _store_transaction_versions(self, bank: Any, response: Any) -> None:

        stored = self.repo.shelve_get_version_transaction(bank.bank_code)
        if stored:
            bank.transaction_versions = stored
            return
        bank.transaction_versions = {
            'TAN': self._get_version(response, HITANS7, HITANS6, default=7),
            'KAZ': self._get_version(response, HIKAZS7, HIKAZS6, default=7),
            'WPD': self._get_version(response, HIWPDS6, HIWPDS5, default=6),
        }
        self.repo.shelve_put_key(
            bank.bank_code,
            (decl.KEY_VERSION_TRANSACTION, bank.transaction_versions)
        )

    def _store_pin_tan_rules(self, bank: Any, response: Any) -> None:

        seg = self._get_segment(response, HIPINS1)
        if seg:
            tans_required = [
                (item.transaction, item.tan_required)
                for item in seg.parameter.transaction_tans_required
            ]
            values = [
                (decl.KEY_MIN_PIN_LENGTH, seg.parameter.min_pin_length),
                (decl.KEY_MAX_PIN_LENGTH, seg.parameter.max_pin_length),
                (decl.KEY_MAX_TAN_LENGTH, seg.parameter.max_tan_length),
                (decl.KEY_TAN_REQUIRED, tans_required),
            ]
        else:
            msg.MessageBoxInfo(
                title=bank.bank_name,
                message=msg.get_message(msg.MESSAGE_TEXT, 'HIPINS1'))
            values = [
                (decl.KEY_MIN_PIN_LENGTH, 3),
                (decl.KEY_MAX_PIN_LENGTH, 20),
                (decl.KEY_MAX_TAN_LENGTH, 10),
            ]
        self.repo.shelve_put_key(bank.bank_code, values)

    def _store_storage_period(self, bank: Any, response: Any) -> None:

        seg = self._get_first_available_segment(response, HIKAZS7, HIKAZS6)
        bank.storage_period = seg.parameter.storage_period if seg else 90
        self.repo.shelve_put_key(
            bank.bank_code,
            (decl.KEY_STORAGE_PERIOD, bank.storage_period)
        )

    def _notify_bpd_update(self, bank: Any) -> None:
        msg.MessageBoxInfo(
            title=bank.bank_name,
            message=msg.get_message(
                msg.MESSAGE_TEXT,
                'FINTS_UPDATE_BPD_VERSION',
                bank.bank_name,
                bank.bpd_version
            ),
            information=decl.INFORMATION
        )


class IdentifierService:
    """
    Shared service for extracting SEPA identifiers from transaction purpose.
    """

    def create_identifiers(
        self,
        entry: Dict[str, Any],
        delimiter: str
    ) -> Dict[str, Any]:
        """
        Extract SEPA identifiers from 'purpose' field and enrich entry.
        """
        if "purpose" not in entry:
            return entry
        purpose = entry["purpose"]
        if isinstance(purpose, list):
            purpose = " ".join(purpose)
        compact = purpose.replace(" ", "")
        identifiers = []
        # Find identifiers in purpose string
        for key in decl.IDENTIFIER.keys():
            pattern = key + delimiter
            match = re.search(pattern, compact)
            if match:
                identifiers.append((match.group(), match.start(), match.end()))
        identifiers.sort(key=itemgetter(1))
        # Extract values between identifiers
        for i, (name, _, end) in enumerate(identifiers):
            clean_name = name[:-1]
            next_start = identifiers[i + 1][1] if i + 1 < len(identifiers) else None

            value = compact[end:next_start] if next_start else compact[end:]
            entry[decl.IDENTIFIER[clean_name]] = value[:65]
        # Store original purpose cleaned (optional refinement possible)
        entry.setdefault("purpose_wo_identifier", purpose)
        return entry


class MT940Service:
    """
    Service for parsing MT940 bank statement format.
    """

    def __init__(self, repo, identifier_service: IdentifierService):

        self.repo = repo
        self.identifier_service = identifier_service

    def parse(self, data: str, bank_code: str) -> List[Dict[str, Any]]:
        """
        Parse MT940 raw data into structured list of dictionaries.

        Documentation:
        https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Finanzdatenformate_2010-08-06_final_version.pdf
        (Chapter B.8, page 174)
        """
        transactions = Transactions()
        identifier_delimiter = self.repo.shelve_get_identifier_delimiter(bank_code)
        mt940_statements = transactions.parse(data)
        mt940: List[Dict[str, Any]] = []
        # Normalize parsed statements
        for stmt in mt940_statements:
            cleaned = self._clean_statement(stmt.data)
            mt940.append(cleaned)
        # Enrich with balances and transaction data
        self._enrich_with_balances(mt940, data, identifier_delimiter)
        return mt940

    def _clean_statement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove unused keys and normalize values.
        """
        cleaned = {}
        for key, value in data.items():
            if key not in declm.TABLE_FIELDS[declm.STATEMENT] or value is None:
                continue
            if isinstance(value, str):
                value = value.replace("\n", " ")
            if isinstance(value, date):
                value = str(value)
            cleaned[key] = value
        return cleaned

    def _enrich_with_balances(
        self,
        mt940: List[Dict[str, Any]],
        raw_data: str,
        identifier_delimiter: str
    ) -> None:
        """
        Parse raw MT940 clauses and enrich transactions with balances.
        """
        idx = 0
        clauses = raw_data.splitlines()
        tags = Transactions.defaultTags().copy()
        for clause in clauses:
            if clause.startswith(":60F:") or clause.startswith(":60M:"):
                self._handle_opening_balance(clause, tags)

            if clause.startswith(":61:"):
                idx = self._handle_transaction(
                    clause, tags, mt940, idx, identifier_delimiter
                )

    def _handle_opening_balance(self, clause: str, tags: Dict) -> None:
        """
        Extract opening balance information.
        """
        tag = '60F' if clause.startswith(":60F:") else '60M'
        m = tags[tag].re.match(clause[5:])
        if not m:
            return
        self._opening_status = m.group("status")
        self._entry_date = date_yymmdd.convert(
            m.group("year") + m.group("month") + m.group("day")
        )
        self._opening_entry_date = self._entry_date
        self._opening_currency = m.group("currency")
        self._opening_balance = dec2.convert(
            abs(Amount(m.group("amount"), m.group("status")).amount)
        )
        # Initialize closing same as opening
        self._closing_status = self._opening_status
        self._closing_entry_date = self._entry_date
        self._closing_currency = self._opening_currency
        self._closing_balance = self._opening_balance

    def _handle_transaction(
        self,
        clause: str,
        tags: Dict,
        mt940: List[Dict[str, Any]],
        idx: int,
        identifier_delimiter: str
    ) -> int:
        """
        Process transaction line (:61:)
        """
        m = tags[61].re.match(clause[4:])
        if not m:
            return idx
        amount = dec2.convert(
            abs(Amount(m.group("amount"), m.group("status")).amount)
        )
        status = m.group("status")
        try:
            entry_date = date_yymmdd.convert(m.group("entry_date"))
        except Exception:
            entry_date = self._entry_date
        entry = mt940[idx]
        entry.update({
            "entry_date": entry_date,
            "amount": amount,
            "currency": self._opening_currency,
            "opening_status": self._opening_status,
            "opening_entry_date": self._opening_entry_date,
            "opening_currency": self._opening_currency,
            "opening_balance": self._opening_balance,
        })
        # Calculate closing balance
        opening = -self._opening_balance if self._opening_status == "D" else self._opening_balance
        delta = -amount if status == "D" else amount
        closing_balance = dec2.add(opening, delta)
        closing_status = "C" if closing_balance > 0 else "D"

        entry.update({
            "closing_status": closing_status,
            "closing_entry_date": self._closing_entry_date,
            "closing_currency": self._closing_currency,
            "closing_balance": abs(closing_balance),
        })
        # Prepare next iteration
        self._opening_balance = abs(closing_balance)
        self._opening_status = closing_status
        mt940[idx] = self._create_identifiers(entry, identifier_delimiter)
        return idx + 1

    def _create_identifiers(self, mt940: Dict[str, Any], delimiter: str) -> Dict[str, Any]:
        """
        Delegate identifier extraction to shared service.
        """
        return self.identifier_service.create_identifiers(mt940, delimiter)


class CAMT052Service:
    """
    Service for parsing CAMT.052 XML bank statements.
    """

    def __init__(self, repo, identifier_service: IdentifierService):

        self.repo = repo
        self.identifier_service = identifier_service

    def parse(self, xml_string: str, bank) -> List[Dict[str, Any]]:

        def ensure_list(x):
            return x if isinstance(x, list) else ([x] if x else [])

        def convert_amount(amount, status):
            amount = amount if isinstance(amount, Decimal) else dec2.convert(amount)
            return amount if status == decl.CREDIT else -amount

        def normalize_amount(a):
            if isinstance(a, dict) and "#text" in a:
                amount = dec2.convert(a["#text"])
                currency = a.get("@Ccy", decl.EURO)
                return amount, currency
            return None, decl.EURO

        def get_date(node):
            if isinstance(node, dict):
                return node.get("Dt") or node.get("#text")
            return node

        def get_status(indicator):
            return decl.DEBIT if indicator == "DBIT" else decl.CREDIT

        def extract_balance(bal):
            tp = bal.get("Tp", {})
            cd = tp.get("Cd") or tp.get("CdOrPrtry")
            if isinstance(cd, dict):
                cd = cd.get("#text") or cd.get("Cd")
            amount, currency = normalize_amount(bal.get("Amt"))
            if amount is None:
                return None
            status = get_status(bal.get("CdtDbtInd"))
            amount = convert_amount(amount, status)
            date = get_date(bal.get("Dt") or bal.get("DtTm"))
            return cd, amount, currency, status, date

        identifier_delimiter = self.repo.shelve_get_identifier_delimiter(bank.bank_code)
        doc = xmltodict.parse(xml_string).get("Document", {})
        rpt = doc.get("BkToCstmrAcctRpt", {}).get("Rpt", {})
        opening_balance = closing_balance = None
        for bal in ensure_list(rpt.get("Bal")):
            parsed = extract_balance(bal)
            if not parsed:
                continue
            cd, amount, currency, status, date = parsed
            if cd == "OPBD":
                opening_balance = amount
                opening_currency = currency
                opening_status = status
                opening_date = date
            elif cd == "CLBD":
                closing_balance = amount
        entries_out = []
        running_balance = opening_balance
        for entry in ensure_list(rpt.get("Ntry")):
            entry_obj = {}
            if running_balance is not None:
                entry_obj.update({
                    declm.DB_opening_balance: abs(running_balance),
                    declm.DB_opening_status: opening_status,
                    declm.DB_opening_currency: opening_currency,
                    declm.DB_opening_entry_date: opening_date,
                })
            amount, currency = normalize_amount(entry.get("Amt"))
            status = get_status(entry.get("CdtDbtInd"))
            entry_obj.update({
                declm.DB_amount: amount,
                declm.DB_currency: currency,
                declm.DB_status: status,
                declm.DB_entry_date: get_date(entry.get("BookgDt")),
                declm.DB_date: get_date(entry.get("ValDt")),
                declm.DB_posting_text: entry.get("AddtlNtryInf"),
                declm.DB_bank_reference: entry.get("AcctSvcrRef"),
            })

            if running_balance is not None:
                running_balance = dec2.add(
                    running_balance,
                    convert_amount(amount, status)
                )
                opening_status = decl.CREDIT if running_balance > 0 else decl.DEBIT
                opening_date = entry_obj[declm.DB_entry_date]

                entry_obj.update({
                    declm.DB_closing_balance: abs(running_balance),
                    declm.DB_closing_status: opening_status,
                    declm.DB_closing_entry_date: opening_date,
                    declm.DB_closing_currency: opening_currency,
                })
            # --- BkTxCd ---
            bk = entry.get("BkTxCd", {})
            prtry = (bk.get("Prtry") or {}).get("Cd")
            if prtry:
                parts = prtry.split("+")
                entry_obj[declm.DB_id] = parts[0] if len(parts) > 0 else None
                entry_obj[declm.DB_transaction_code] = parts[1] if len(parts) > 1 else None
                entry_obj[declm.DB_prima_nota] = parts[2] if len(parts) > 2 else None
            # --- Tx Details ---
            for tx in ensure_list((entry.get("NtryDtls") or {}).get("TxDtls")):
                refs = tx.get("Refs", {})
                entry_obj.update({
                    declm.DB_remittance_information: refs.get("InstrId"),
                    declm.DB_end_to_end_reference: refs.get("EndToEndId"),
                    declm.DB_mandate_id: (tx.get("DrctDbtTx", {}).get("MndtRltdInf", {}).get("MndtId")),
                    declm.DB_purpose_code: (tx.get("Purp") or {}).get("Cd"),
                })
                if tx.get("RmtInf"):
                    entry_obj[declm.DB_purpose] = tx["RmtInf"].get("Ustrd", decl.NOT_ASSIGNED)
                else:
                    entry_obj[declm.DB_purpose] = decl.NOT_ASSIGNED   
                rltd = tx.get("RltdPties", {})
                if entry_obj[declm.DB_status] == decl.CREDIT:
                    party = rltd.get("Dbtr")
                    acct = rltd.get("DbtrAcct")
                else:
                    party = rltd.get("Cdtr")
                    acct = rltd.get("CdtrAcct")
                if party:
                    entry_obj[declm.DB_applicant_name] = dict_get_nested_value(party, ["Pty", "Nm"])
                if acct:
                    iban = (
                        dict_get_nested_value(acct, ["Id", "IBAN"])
                        or dict_get_nested_value(acct, ["Id", "Othr", "Id"])
                    )
                    entry_obj[declm.DB_applicant_iban] = iban
            if entry_obj[declm.DB_status] != decl.CREDIT:
                entry_obj = self._create_identifiers(entry_obj, identifier_delimiter)
            entry_obj[declm.DB_camt] = "052"
            entries_out.append(entry_obj)
        # --- Closing balance check ---
        if entries_out and closing_balance is not None:
            last = entries_out[-1]
            calc = convert_amount(
                last[declm.DB_closing_balance],
                last[declm.DB_closing_status]
            )
            if closing_balance != calc:
                msg.MessageBoxInfo(
                    title=bank.bank_name,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'BANK_BALANCE_DIFFERENCE',
                        bank.account_product_name,
                        bank.account_number,
                        closing_balance,
                        last[declm.DB_closing_balance],
                        calc,
                        str(dec2.subtract(closing_balance, calc))
                    ),
                    information=decl.WARNING
                )
        return entries_out

    def _create_identifiers(self, entry: Dict[str, Any], delimiter: str) -> Dict[str, Any]:
        """
        Delegate identifier extraction to shared service.
        """
        return self.identifier_service.create_identifiers(entry, delimiter)


class MT535Service:
    """
    Service class for parsing MT535 (SWIFT / FinTS) portfolio statements.
    """

    def parse(self, data: str) -> List[Dict[str, Any]]:
        """
        Parse MT535 message content into a list of dictionaries.

        Reference:
        FinTS 3.0 Specification (Chapter B.4, page 150)
        https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Finanzdatenformate_2010-08-06_final_version.pdf

        Based on:
        Pure-python FinTS implementation (formerly HBCI)
        https://pypi.python.org/pypi/fints

        :param data: Raw MT535 message as string
        :return: List of parsed financial instruments
        """

        def collapse_multilines(lines: List[str]) -> List[str]:
            """
            Merge multiline SWIFT clauses into single-line clauses.
            """
            clauses: List[str] = []
            prev_line = ""
            for line in lines:
                if line.startswith(":"):
                    if prev_line:
                        clauses.append(prev_line)
                    prev_line = line
                elif line.startswith("-"):
                    clauses.append(prev_line)
                    clauses.append(line)
                else:
                    prev_line += f"|{line}"
            return clauses

        def grab_financial_instrument_segments(clauses: List[str]) -> List[List[str]]:
            """
            Extract FIN segments (financial instruments) from clauses.
            """
            segments: List[List[str]] = []
            stack: List[str] = []
            inside_fin = False
            for clause in clauses:
                if clause.startswith(":16R:FIN"):
                    inside_fin = True
                elif clause.startswith(":16S:FIN"):
                    segments.append(stack)
                    stack = []
                    inside_fin = False
                elif inside_fin:
                    stack.append(clause)
            return segments
        # --- Preprocessing ---
        lines = data.splitlines()
        if lines:
            lines.pop(0)  # remove first empty line if present
        clauses = collapse_multilines(lines)
        price_date = None
        total_amount_portfolio = None
        # --- Header extraction ---
        for clause in clauses:
            if (m := re_pricedate04.match(clause)) or (m := re_pricedate03.match(clause)):
                price_date = m.group(1)

            if m := re_total_amountportfolio.match(clause):
                total_amount_portfolio = dec2.convert(
                    float(f"{m.group(2)}.{m.group(3)}")
                )
        # --- Extract financial instruments ---
        fin_segments = grab_financial_instrument_segments(clauses)
        results: List[Dict[str, Any]] = []
        for finseg in fin_segments:
            instrument: Dict[str, Any] = {
                "price_date": price_date,
            }
            for clause in finseg:
                # Identification (ISIN + name)
                if m := re_identification.match(clause):
                    instrument["isin_code"] = m.group(1)
                    instrument["name"] = m.group(3)
                # Market price
                if m := re_marketprice.match(clause):
                    instrument["price_currency"] = m.group(1)
                    instrument["market_price"] = dec6.convert(
                        float(f"{m.group(2)}.{m.group(3)}")
                    )
                elif m := re_marketprice01.match(clause):
                    instrument["price_currency"] = decl.PERCENT
                    instrument["market_price"] = dec6.convert(
                        float(f"{m.group(1)}.{m.group(2)}")
                    )
                # Price date
                if m := re_pricedate02.match(clause):
                    instrument["price_date"] = m.group(1)
                elif m := re_pricedate01.match(clause):
                    instrument["price_date"] = m.group(1)
                # Pieces / quantity
                if m := re_pieces.match(clause) or re_pieces01.match(clause):
                    instrument["pieces"] = dec2.convert(
                        float(f"{m.group(1)}.{m.group(2)}")
                    )
                # Total amount
                if m := re_total_amount.match(clause):
                    instrument["amount_currency"] = m.group(1)
                    instrument["total_amount"] = dec2.convert(
                        float(f"{m.group(2)}.{m.group(3)}")
                    )
                # Acquisition price
                if m := re_acquisitionprice.match(clause):
                    instrument["acquisition_price"] = dec6.convert(
                        float(f"{m.group(1)}.{m.group(2)}")
                    )
                # Exchange rate handling
                if m := re_exchange_rate.match(clause):
                    ccy1, ccy2 = m.group(1), m.group(2)
                    rate = float(f"{m.group(3)}.{m.group(4)}")
                    instrument["exchange_currency_1"] = ccy1
                    instrument["exchange_currency_2"] = ccy2
                    instrument["exchange_rate"] = rate
                    if rate != 0:
                        if instrument.get("amount_currency") == ccy2:
                            instrument["amount_currency"] = ccy1
                            instrument["total_amount"] = dec2.divide(
                                instrument["total_amount"], rate
                            )
                        if instrument.get("price_currency") == ccy2:
                            instrument["price_currency"] = ccy1
                            instrument["market_price"] = dec6.divide(
                                instrument["market_price"], rate
                            )
            instrument["total_amount_portfolio"] = total_amount_portfolio
            results.append(instrument)
        return results


class Dialogs(object):
    """
    Dialogues: Customer - Bank
    """
    bpd_updated = False
    upd_updated = False

    def __init__(self):

        self.repo = Repository()
        self.messages = Messages()
        self.identifier_service = IdentifierService()
        result = application_store.get([declm.DB_logging, declm.DB_show_messages])
        if result:
            self._show_message = result[declm.DB_show_messages]
            self._logging = result[declm.DB_logging]
        if not self._show_message:
            self._show_message = decl.ERROR

    def _start_dialog(self, bank: Any) -> Optional[Any]:
        """
        Orchestrates the dialog initialization workflow.
        """
        if self._is_dialog_active(bank):
            return True
        self._reset_dialog_state(bank)
        response = self._initialize_dialog(bank)
        if not response:
            return None
        return self._finalize_dialog(bank, response)

    def _is_dialog_active(self, bank: Any) -> bool:
        """
            1. Dialog State
        Check if dialog is already active.
        """
        return bank.opened_bank_code == bank.bank_code

    def _reset_dialog_state(self, bank: Any) -> None:
        """Reset dialog-related state."""
        bank.opened_bank_code = None
        bank.dialog_id = decl.DIALOG_ID_UNASSIGNED
        bank.tan_process = 4
        bank.sca = True

    def _initialize_dialog(self, bank: Any) -> Optional[Any]:
        """
            2. Dialog Initialization Loop
        Runs the dialog initialization loop until a valid response is received.
        """
        response = None
        while not response:
            bank.message_number = 1
            if not self._ensure_pin(bank):
                return None  # user canceled
            response = self._send_dialog_init(bank)
            if response:
                if self._process_dialog_response(bank, response):
                    return response
            self._reset_retry_state(bank)
        return None

    def _ensure_pin(self, bank: Any) -> bool:
        """
            3. PIN Handling
        Ensure a PIN exists for the bank.

        Returns:
            bool: False if user canceled input
        """
        if bank.bank_code in decl.PNS:
            return True
        input_pin = InputPIN(bank.bank_code, bank_name=bank.bank_name)
        if input_pin.button_state == decl.WM_DELETE_WINDOW:
            return False
        decl.PNS[bank.bank_code] = input_pin.pin
        return True

    def _send_dialog_init(self, bank: Any) -> Optional[Any]:
        """
            4. Sending + Processing
        Send dialog initialization message
        """
        response, _ = self._send_msg(
            bank,
            self.messages.msg_dialog_init(bank),
            dialog_init=True
        )
        return response

    def _process_dialog_response(self, bank: Any, response: Any) -> bool:
        """
        Process response and check if dialog can proceed.

        Returns:
            bool: True if dialog_id was found
        """
        self._update_bank_data(bank, response)
        self._handle_hiupd_segments(bank, response)
        seg = response.find_segment_first(HNHBK3)
        if seg:
            bank.dialog_id = seg.dialog_id
            return True
        return False

    def _update_bank_data(self, bank: Any, response: Any) -> None:

        BPDService(self.repo).update_bank(bank, response, update_bpd=False)
        UPDService(self.repo).process_response(bank, response)

    def _handle_hiupd_segments(self, bank: Any, response: Any) -> None:

        for seg in response.find_segments(HIUPD6):
            if bank.iban == seg.iban and seg.extension:
                formatted = json.dumps(seg.extension, indent=4)
                msg.MessageBoxInfo(
                    message=msg.get_message(
                        msg.MESSAGE_TEXT,
                        'HIUPD_EXTENSION',
                        bank.bank_name,
                        bank.account_number,
                        bank.account_product_name,
                        bank.iban,
                        formatted
                    ),
                    info_storage=msg.Informations.BANKDATA_INFORMATIONS
                )

    def _reset_retry_state(self, bank: Any) -> None:

        msg.Informations.bankdata_informations = ''
        decl.PNS.pop(bank.bank_code, None)

    def _finalize_dialog(self, bank: Any, response: Any) -> Optional[Any]:
        """
            5. TAN Handling
        Handle TAN step and finalize dialog.
        """
        seg = self._get_tan_segment(response)
        if not seg:
            self._handle_missing_tan(bank)
            return None
        bank.task_reference = seg.task_reference
        response, _ = self._get_tan(bank, response)
        if response:
            bank.opened_bank_code = bank.bank_code
            return response
        return None

    def _get_tan_segment(self, response: Any) -> Optional[Any]:
        """Extract HITAN segment."""
        return (
            response.find_segment_first(HITAN7)
            or response.find_segment_first(HITAN6)
        )

    def _handle_missing_tan(self, bank: Any) -> None:
        """Show error if TAN segment missing."""
        msg.MessageBoxInfo(
            message=msg.get_message(
                msg.MESSAGE_TEXT,
                'HITAN_MISSED',
                bank.bank_name,
                bank.account_number,
                bank.account_product_name
            )
        )

    def _end_dialog(self, bank: Any) -> None:
        """
        Orchestrates the dialog termination.
        """
        self._send_dialog_end(bank)
        self._reset_dialog_after_end(bank)

    def _send_dialog_end(self, bank: Any) -> None:
        """
            1. Sending
        Send dialog end message to the bank."""
        self._send_msg(
            bank,
            self.messages.msg_dialog_end(bank)
        )

    def _reset_dialog_after_end(self, bank: Any) -> None:
        """
            2. State Reset
        Reset dialog-related state after termination."""
        bank.message_number = 1
        bank.opened_bank_code = None

    def _get_tan(self, bank: Any, response: Any) -> Tuple[Optional[Any], List[Any]]:
        """
        Orchestrates TAN handling based on response segments.
        """
        if not self._requires_tan(bank, response):
            return response, []
        return self._process_tan(bank)

    def _requires_tan(self, bank: Any, response: Any) -> bool:
        """
        Check if response indicates TAN is required.
        """
        for seg in response.find_segments(HIRMS2):
            for hirms in seg.responses:
                if hirms.code == decl.CODE_0030:
                    bank.tan_process = 2
                    return True
        return False

    def _process_tan(self, bank: Any) -> Tuple[Optional[Any], List[Any]]:
        """
        Handle TAN input and sending.
        """
        message = self._build_tan_message(bank)
        if not message:
            self._handle_tan_cancel(bank)
            return None, []
        return self._send_tan(bank, message)

    def _build_tan_message(self, bank: Any) -> Optional[Any]:
        """Build TAN message."""
        return self.messages.msg_tan(bank)

    def _send_tan(self, bank: Any, message: Any) -> Tuple[Any, List[Any]]:
        """Send TAN message."""
        return self._send_msg(bank, message)

    def _handle_tan_cancel(self, bank: Any) -> None:
        """Handle user canceling TAN input."""
        msg.MessageBoxInfo(
            message=msg.get_message(
                msg.MESSAGE_TEXT,
                'TAN_CANCEL',
                bank.bank_name,
                bank.account_number
            ),
            information=decl.ERROR
        )

    def _get_segment(self, bank, segment_type):

        for seg in [HIKAZ6, HIKAZ7, HIWPD5, HIWPD6]:
            if (seg.__name__[2:5] == segment_type and
                    seg.__name__[5:6] == str(bank.transaction_versions[segment_type])):
                return seg
        msg.MessageBoxTermination(info=msg.get_message(
            msg.MESSAGE_TEXT, 'SEGMENT_VERSION',
            'HI', segment_type, bank.transaction_versions[segment_type]
            ),
            bank=bank)

    def _store_sync_shelve(self, bank, response):

        seg = response.find_segment_first(HNHBK3)
        if seg is not None:
            bank.dialog_id = seg.dialog_id
        else:
            msg.MessageBoxTermination(info=msg.get_message(msg.MESSAGE_TEXT, 'HNHBK3'), bank=bank)
        seg = response.find_segment_first(HISYN4)
        if seg is not None:
            bank.system_id = seg.system_id
            bank.security_identifier = seg.system_id
            self.repo.shelve_put_key(
                bank.bank_code, (decl.KEY_SYSTEM_ID, seg.system_id))
        else:
            msg.MessageBoxTermination(info=msg.get_message(msg.MESSAGE_TEXT, 'HISYN4'), bank=bank)
        UPDService(self.repo).process_response(bank, response)

    def _receive_msg(self, bank, response, hirms_codes):

        if decl.CODE_0030 in hirms_codes:
            seg = response.find_segment_first(HITAN7)
            if not seg:
                seg = response.find_segment_first(HITAN6)
                if not seg:
                    msg.MessageBoxInfo(
                        title=bank.bank_name,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT, decl.CODE_0030, bank.bank_name, bank.account_number,
                            bank.account_product_name
                            ),
                        information=decl.WARNING
                        )
                    return [], hirms_codes
            if msg.is_main_thread():
                bank.task_reference = seg.task_reference
                bank.challenge_hhduc = seg.challenge_hhduc  # e.g. Consors: QR_Code contains TAN
                response, hirms_codes = self._get_tan(bank, response)
            else:
                msg.MessageBoxInfo(
                    title=bank.bank_name,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, decl.CODE_0030, bank.bank_name, bank.account_number,
                        bank.account_product_name
                        ),
                    information=decl.WARNING
                    )
        return response, hirms_codes

    def _decoupled_process(self, bank, response, hirms_codes):

        if decl.CODE_0030 in hirms_codes and bank.bank_code == '76030080':  # Consors  Show QR_Code
            # store QR_code with tan in bank
            bank.challenge_hhduc = None
            bank.challenge = ''
            for seg in response.find_segments(HITAN6):
                bank.challenge_hhduc = seg.challenge_hhduc
                bank.challenge = seg.challenge
                break
        if decl.CODE_3955 in hirms_codes:
            # Security clearance is provided via another channel
            for seg in response.find_segments(HITAN7):
                bank.task_reference = seg.task_reference
                message_box_ask = msg.MessageBoxAsk(
                    title=bank.bank_name,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT, 'HITAN', seg.challenge)
                )
                if message_box_ask.result:
                    bank.tan_process = 'S'
                    return True
        return False

    def _send_msg(self, bank, message, dialog_init=False):

        def fints_code(bank, segment):
            codes = []
            error = False
            for response in segment.responses:
                codes.append(response.code)
                message = ' ' .join(['Code', str(response.code), str(response.text)])
                if response.code == '3076':      # SCA not required
                    bank.sca = False
                if response.code[0] in ['0', '1']:
                    if self._show_message == decl.INFORMATION:
                        msg.bankdata_informations_append(decl.INFORMATION, message)
                elif response.code[0] == '3':
                    if response.code == '3010':    # no entries found
                        msg.MessageBoxInfo(
                            title=bank.bank_name,
                            message=msg.get_message(
                                msg.MESSAGE_TEXT, 'NO_TURNOVER', bank.bank_name,
                                bank.account_number, bank.account_product_name
                                )
                            )
                    if self._show_message in [decl.INFORMATION, decl.WARNING]:
                        msg.bankdata_informations_append(decl.WARNING, message)
                        bank.warning_message = True
                else:
                    error = True
                    msg.bankdata_informations_append(decl.WARNING, message)
                    if response.reference_element:
                        msg.bankdata_informations_append(decl.WARNING, ' ' .join(
                            ['- Bezugssegment', str(response.reference_element)]))
                    if response.parameters:
                        msg.bankdata_informations_append(decl.ERROR, ' ' .join(
                            ['- Parameters', str(response.parameters)]))
            return error, codes

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
            msg.MessageBoxTermination(
                info=msg.get_message(msg.MESSAGE_TEXT, 'SEND_ERROR', r.status_code), bank=bank)
        try:
            response = FinTSInstituteMessage(
                segments=base64.b64decode(r.content.decode('latin1')))
        except Exception:
            msg.MessageBoxException(message=msg.get_message(msg.MESSAGE_TEXT, 'RESPONSE'))
            ProtocolViewer(text=msg.Informations.bankdata_informations)
            if dialog_init:
                return None,  []
            else:
                msg.MessageBoxTermination(bank=bank)
        bank.response = response
        if self._logging:
            with Password.protect():
                response.print_nested(stream=log_out, prefix="\t")
                logger.debug(('Received ' + 30 * '>' + '\n{}\n' + 40 * '>' + '\n').format
                             (log_out.getvalue()))
        # bank feedback message
        seg = response.find_segment_first(HIRMG2)
        hirmg_error, fints_codes = fints_code(bank, seg)
        hirms_error = None
        for seg in response.find_segments(HIRMS2):
            hirms_error, hirms_codes = fints_code(bank, seg)
            fints_codes = fints_codes + hirms_codes
        if hirmg_error or hirms_error:
            ProtocolViewer(text=msg.Informations.bankdata_informations)
            if dialog_init:
                return None,  fints_codes
            else:
                msg.MessageBoxTermination(bank=bank)
        return response, fints_codes

    def anonymous(self, bank):
        """
        Initialize an anonymous dialog with the bank server.
        """
        # Reset the message counter for a new session
        bank.message_number = 1
        # Mark the dialog as not yet assigned
        bank.dialog_id = decl.DIALOG_ID_UNASSIGNED
        # Send anonymous dialog initialization message
        response, _ = self._send_msg(
            bank,
            self.messages.msg_dialog_anonymous(bank)
        )
        # Update bank parameter data (BPD) from the server response
        BPDService(self.repo).update_bank(
            bank,
            response,
            update_bpd=True
        )

    def sync(self, bank):
        """
        Synchronize dialog and update bank parameter data.
        """
        # Start synchronization dialog
        bank.message_number = 1
        bank.dialog_id = decl.DIALOG_ID_UNASSIGNED
        # Send synchronization request
        response, _ = self._send_msg(
            bank,
            self.messages.msg_dialog_syn(bank)
        )
        # Store synchronization data locally
        self._store_sync_shelve(bank, response)
        # Properly close the dialog
        self._end_dialog(bank)
        # Check whether an update segment already exists
        seg = response.find_segment_first(HIUPD6)
        # If no update segment is available, start a second dialog
        if not seg:
            response = self._start_dialog(bank)
            # Process updates only if dialog startup succeeded
            if response not in decl.START_DIALOG_FAILED:
                UPDService(self.repo).process_response(bank, response)
                # Close the update dialog
                self._end_dialog(bank)

    def holdings(self, bank):
        """
        Retrieve and parse securities holdings data from the bank.
        """
        # Start dialog with the bank server
        if self._start_dialog(bank) in decl.START_DIALOG_FAILED:
            return decl.WM_DELETE_WINDOW
        holdings = []
        # Set TAN process version
        bank.tan_process = 4
        # Request holdings data
        response, hirms_codes = self._send_msg(
            bank,
            self.messages.msg_holdings(bank)
        )
        # Receive and process the response
        response, hirms_codes = self._receive_msg(
            bank,
            response,
            hirms_codes
        )
        # Return empty result if no response was received
        if not response:
            return holdings
        # Get the expected WPD segment type
        hiwpd = self._get_segment(bank, 'WPD')
        # Search for the holdings segment in the response
        seg = response.find_segment_first(hiwpd)
        # Abort if the required segment is missing
        if not seg:
            msg.MessageBoxTermination(
                info=msg.get_message(msg.MESSAGE_TEXT, 'HIWPD', hiwpd.__name__),
                bank=bank
            )
            return holdings
        # Decode holdings data if it is provided as bytes
        if type(seg.holdings) is bytes:
            try:
                holding_str = seg.holdings.decode('utf-8')
            except UnicodeDecodeError:
                holding_str = seg.holdings.decode('latin1')
        else:
            holding_str = seg.holdings
        # Write raw MT535 data to the log if logging is enabled
        if self._logging:
            logger.debug('\n\n>>>>> START MT535 DATA ' + 40 * '>' + '\n')
            log_target(holding_str)
            logger.debug(
                '\n\n>>>>> START MT535 DATA PARSING ' +
                30 * '>' + '\n'
            )
        # Close the dialog
        self._end_dialog(bank)
        # Parse MT535 holdings data into structured objects
        holdings = MT535Service().parse(holding_str)
        return holdings

    def statements(self, bank):

        if self._start_dialog(bank) in decl.START_DIALOG_FAILED:
            return decl.WM_DELETE_WINDOW
        bank.tan_process = 4
        statements = []
        response, hirms_codes = self._send_msg(
            bank,
            self.messages.msg_statements(bank),
        )
        if self._decoupled_process(bank, response, hirms_codes):
            response, hirms_codes = self._send_msg(
                bank,
                self.messages.msg_tan_decoupled(bank),
            )
        response, hirms_codes = self._receive_msg(
            bank,
            response,
            hirms_codes,
        )
        # No statements found or SCA in threading mode
        if not response or decl.CODE_3010 in hirms_codes:
            return statements
        if decl.CODE_0030 in hirms_codes:
            self._end_dialog(bank)
            return statements
        # Additional turnovers are available
        if decl.CODE_3040 in hirms_codes:
            msg.MessageBoxInfo(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    decl.CODE_3040,
                    bank.bank_name,
                    bank.account_number,
                    bank.account_product_name,
                ),
                information=decl.WARNING,
            )
        if bank.statement_mt940:
            statements = self._parse_mt940(response, bank)
        elif bank.statement_camt:
            statements = self._parse_camt052(response, bank)
        self._end_dialog(bank)
        return statements

    def _parse_mt940(self, response, bank):

        hikaz = self._get_segment(bank, "KAZ")
        seg = response.find_segment_first(hikaz)
        if not seg:
            msg.MessageBoxInfo(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    "HIKAZ",
                    "HKKAZ",
                    bank.bank_name,
                    bank.account_number,
                    bank.account_product_name,
                ),
                information=decl.ERROR,
            )
            return []
        statement_data = self._decode_statement(seg.statement_booked)
        if self._logging:
            logger.debug(
                "\n\n>>>>> START MT940 DATA " + ">" * 40 + "\n"
            )
            log_target(statement_data)
            logging.getLogger(__name__).debug(
                "\n\n>>>>> START MT940 DATA PARSING "
                + ">" * 30
                + "\n"
            )
        return MT940Service(
            self.repo,
            self.identifier_service,
        ).parse(statement_data, bank.bank_code)

    def _parse_camt052(self, response, bank):

        seg = response.find_segment_first(HICAZ1)
        if not seg:
            msg.MessageBoxInfo(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    "HIKAZ",
                    "HKCAZ",
                    bank.bank_name,
                    bank.account_number,
                    bank.account_product_name,
                ),
                information=decl.ERROR,
            )
            return []
        statements = seg.statement_booked.camt_statements._data[0]
        if self._logging:
            pretty_xml = minidom.parseString(statements).toprettyxml(
                indent="  "
            )
            logger.debug(
                "\n\n>>>>> START CAMT_052 DATA "
                + ">" * 40
                + "\n"
            )
            log_target(pretty_xml)
            logging.getLogger(__name__).debug(
                "\n\n>>>>> START CAMT_052 DATA PARSING "
                + ">" * 30
                + "\n"
            )
        return CAMT052Service(
            self.repo,
            self.identifier_service,
        ).parse(statements, bank)

    @staticmethod
    def _decode_statement(statement_bytes):

        # Try supported encodings in order
        for encoding in ("utf-8", "latin1"):
            try:
                return statement_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError(
            "Unable to decode statement data",
            statement_bytes,
            0,
            len(statement_bytes),
            "Unsupported encoding",
        )
