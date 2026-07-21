'''
Created on 02.03.2026
@author: Wolfg
'''

import yfinance as yf
import csv

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, time, date
from abc import ABC, abstractmethod

import banking.declarations as decl
import banking.message_handler as msg
import banking.declarations_mariadb as declm
from banking.repository import Repository
from banking.utils import (
    date_days, dec6, date_yyyymmdd,
    application_store, dec2, check_mixin_method_uniqueness,
    signed_balance
    )
from banking.trading_calendar import xetra_cls
from banking.mariadb import DatabaseErrorHandler


class BuildHoldings:
    """
    Creates holding records from transaction data.

    This class processes transaction rows for a given IBAN and ISIN,
    calculates the daily holding state, enriches it with market prices,
    and stores the resulting holding records in the database.
    """
    def build_holdings(
            self,
            title,
            state,
            iban,
            isin_code,
            trading_days: list[date] | None = None
    ) -> bool:
        """
        Creates holding records for the specified trading days.

        If no trading day list is supplied, all Xetra trading days from the
        first transaction until yesterday are processed.

        Args:
            title (str): Window title for information dialogs.
            state (str): Insert or Replace.
            iban (str): Account IBAN.
            isin_code (str): Security ISIN.
            trading_days (list[date] | None):
                Trading days for which holding rows shall be created.

        Returns:
            bool:
                True if the holdings were successfully created,
                otherwise False.
        """
        last_state = None
        rows = self.repo.get_transactions_delta_of_iban_isin_code(
            iban,
            isin_code
        )
        if not rows:
            return
        # Build the complete trading calendar only if no list was supplied.
        if trading_days is None:
            trading_days = xetra_cls.trading_days(
                start=rows[0][declm.DB_price_date],
                end=date_days.subtract(date.today(), 1),
                as_str=False
            )
        if not trading_days:
            return
        isin_type = self.repo.select_isin_scalar(declm.DB_type, isin_code=isin_code)
        if isin_type != declm.IsinType.BOND.value:
            # ISIN is not a bond
            # Load all market prices with one database query.
            prices = self.repo.get_close_prices(
                isin_code,
                trading_days
            )
        # Calculate the portfolio state after every transaction.
        daily_state = self._get_daily_state(rows)
        first_transaction_date = min(daily_state)

        self.repo.start_transaction()
        try:
            for price_date in trading_days:
                if price_date in daily_state:
                    # A transaction exists on this trading day.
                    # Store the portfolio state calculated after the transaction.
                    field_dict = self._holding_dict(
                        iban,
                        isin_code,
                        price_date,
                        daily_state[price_date],
                        decl.ORIGIN_INSERTED
                        )
                    market_price = self._add_market_price(
                        field_dict,
                        prices,
                        price_date
                        )
                    if market_price:
                        text = msg.get_message(
                            msg.MESSAGE_TEXT,
                            "TEXT_TRANSACTION"
                        )
                        information = decl.INFORMATION
                        self._insert_holding(field_dict, title, information, isin_code, price_date, text)
                else:
                    # No transaction on this trading day.
                    if last_state is None:
                        # Before the first transaction no holding exists.
                        if price_date < first_transaction_date:
                            continue
                        # First holding after the initial transaction.
                        last_state = daily_state[first_transaction_date]
                    result = self.repo.duplicate_holding_row(
                        iban,
                        isin_code,
                        price_date
                    )
                    if result:
                        text = msg.get_message(
                            msg.MESSAGE_TEXT,
                            "TEXT_PREVIOUS_HOLDING"
                        )
                        information = decl.INFORMATION
                        self._message_box_info(title, information, isin_code, price_date, text)
                    else:
                        field_dict = self._holding_dict(
                            iban,
                            isin_code,
                            price_date,
                            last_state,
                            decl.ORIGIN_INSERTED
                            )
                        market_price = self._add_market_price(
                            field_dict,
                            prices,
                            price_date
                            )
                        if market_price:
                            text = msg.get_message(
                                msg.MESSAGE_TEXT,
                                "TEXT_FIRST_HOLDING_PRICE"
                            )
                            text = f"{text} {last_state[declm.DB_price_date]}"
                            information = decl.WARNING
                            self._insert_holding(field_dict, title, information, isin_code, price_date, text)
                        else:
                            field_dict[declm.DB_market_price] = (
                                last_state[declm.DB_acquisition_price]
                            )
                            field_dict[declm.DB_total_amount] = (
                                last_state[declm.DB_acquisition_amount]
                            )
                            text = msg.get_message(
                                msg.MESSAGE_TEXT,
                                "TEXT_FIRST_HOLDING_TRANSACTION"
                            )
                            text = f"{text} {last_state[declm.DB_price_date]}"
                            information = decl.WARNING
                            self._insert_holding(field_dict, title, information, isin_code, price_date, text)
            self.repo.commit()
        except Exception as e:
            self.repo.rollback_transaction()
            msg.MessageBoxInfo(
                title=title,
                info_storage=msg.Informations.HOLDING_INFORMATIONS,
                information=decl.ERROR,
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    "HOLDING_TRANSACTION_ERROR",
                    f"""
                        {self.repo.get_name_of_isin_code(isin_code)} {price_date}: {str(e)}
                     """
                )
            )

    def _insert_holding(self, field_dict, title, information, isin_code, price_date, text):

        result = self.repo.insert_holding(field_dict)
        if result:
            self._message_box_info(title, information, isin_code, price_date, text)

    def _message_box_info(self, title, information, isin_code, price_date, text):

        msg.MessageBoxInfo(
            title=title,
            information=information,
            info_storage=msg.Informations.HOLDING_INFORMATIONS,
            message=msg.get_message(
                msg.MESSAGE_TEXT,
                "HOLDING_TRANSACTION_CREATED",
                self.repo.get_name_of_isin_code(isin_code),
                price_date,
                text
            )
        )

    def _holding_dict(
        self,
        iban,
        isin_code,
        price_date,
        state,
        origin
    ):
        return {
            declm.DB_iban: iban,
            declm.DB_ISIN: isin_code,
            declm.DB_price_date: price_date,
            declm.DB_pieces: state[declm.DB_pieces],
            declm.DB_acquisition_amount:
                state[declm.DB_acquisition_amount],
            declm.DB_acquisition_price:
                state[declm.DB_acquisition_price],
            declm.DB_origin: origin,
        }

    def _add_market_price(
        self,
        field_dict,
        prices,
        price_date
    ):
        market_price = prices.get(price_date)
        if market_price is None:
            return False
        field_dict[declm.DB_market_price] = market_price
        field_dict[declm.DB_total_amount] = dec2.multiply(
            market_price,
            field_dict[declm.DB_pieces]
        )
        return True

    def _get_daily_state(self, rows):
        """
        Calculates the portfolio state after each transaction.

        Buy and sell transactions are processed chronologically to
        determine the current position size, acquisition amount,
        and average acquisition price for each transaction date.

        Args:
            rows (list): Transaction records sorted by price date.

        Returns:
            dict[date, dict]: Mapping of each transaction date to the
                corresponding portfolio state. Each state contains:

                - ``declm.DB_pieces``
                - ``declm.DB_acquisition_amount``
                - ``declm.DB_acquisition_price``
        """
        current_pieces = 0
        acquisition_amount = 0
        acquisition_price = 0
        daily_state = {}
        for row in rows:
            pieces = row[declm.DB_pieces]
            if pieces > 0:
                purchase_amount = row[declm.DB_posted_amount]
                current_pieces += pieces
                acquisition_amount += purchase_amount
                acquisition_price = dec6.divide(acquisition_amount, current_pieces)
            elif pieces < 0:
                sold_pieces = -pieces
                sold_cost = dec2.multiply(acquisition_price, sold_pieces)
                current_pieces -= sold_pieces
                acquisition_amount -= sold_cost
                if current_pieces > 0:
                    acquisition_price = dec6.divide(acquisition_amount, current_pieces)
                else:
                    current_pieces = 0
                    acquisition_amount = 0
                    acquisition_price = 0
            daily_state[row[declm.DB_price_date]] = {
                declm.DB_pieces: current_pieces,
                declm.DB_acquisition_amount: acquisition_amount,
                declm.DB_acquisition_price: acquisition_price
            }
        return daily_state


class CostBasisStrategy(ABC):

    @abstractmethod
    def buy(self, pieces: Decimal, amount: Decimal):
        pass

    @abstractmethod
    def sell(self, pieces: Decimal, price: Decimal):
        """Returns: (tx_pieces, proceeds, profit_loss)"""
        pass

    @abstractmethod
    def current_pieces(self) -> Decimal:
        pass


class LotCostBasis(CostBasisStrategy):

    def __init__(self, lifo: bool = False):
        self.lifo = lifo
        self.lots: list[dict] = []

    def buy(self, pieces: Decimal, amount: Decimal):
        price = abs(amount) / pieces
        self.lots.append({
            "pieces": pieces,
            "price": price
        })
        return pieces

    def sell(self, pieces: Decimal, price: Decimal):
        remaining = pieces
        cost_sum = Decimal("0")

        while remaining > 0 and self.lots:
            lot = self.lots[-1] if self.lifo else self.lots[0]
            take = min(lot["pieces"], remaining)

            cost_sum += take * lot["price"]
            lot["pieces"] -= take
            remaining -= take

            if lot["pieces"] == 0:
                self.lots.pop(-1 if self.lifo else 0)

        if remaining > 0:
            raise ValueError("Not enough pieces to sell")

        proceeds = pieces * price
        profit_loss = proceeds - cost_sum

        return -pieces, proceeds, profit_loss

    def current_pieces(self) -> Decimal:
        return sum(lot_item["pieces"] for lot_item in self.lots)


class AverageCostBasis(CostBasisStrategy):

    def __init__(self):
        self.pieces = Decimal("0")
        self.avg_price = Decimal("0")

    def buy(self, pieces: Decimal, amount: Decimal):
        total_cost = self.pieces * self.avg_price + abs(amount)
        self.pieces += pieces
        self.avg_price = total_cost / self.pieces
        return pieces

    def sell(self, pieces: Decimal, price: Decimal):
        cost = pieces * self.avg_price
        proceeds = pieces * price

        self.pieces -= pieces
        if self.pieces == 0:
            self.avg_price = Decimal("0")

        profit_loss = proceeds - cost
        return -pieces, proceeds, profit_loss

    def current_pieces(self) -> Decimal:
        return self.pieces


class DownloadServices:

    def all_accounts(self, bank):
        """
        Insert downloaded  Bank Data in Database
        """
        if not bank.accounts:
            msg.bankdata_informations_append(
                decl.INFORMATION,
                msg.get_message(
                    msg.MESSAGE_TEXT,
                    'SYNC',
                    bank.bank_name) + '\n\n'
                )
            return
        for account in bank.accounts:
            bank.account_number = account[decl.KEY_ACC_ACCOUNT_NUMBER]
            bank.account_product_name = account[decl.KEY_ACC_PRODUCT_NAME]
            bank.iban = account[decl.KEY_ACC_IBAN]
            bank.owner_name = account[decl.KEY_ACC_OWNER_NAME]
            bank.statement_mt940 = False
            bank.statement_camt = False
            if 'HKKAZ' in account[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                bank.statement_mt940 = True
            elif 'HKCAZ' in account[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                if bank.supported_camt_messages:
                    bank.statement_camt = True
                else:
                    msg.bankdata_informations_append(
                        decl.WARNING,
                        msg.MessageBoxInfo(
                            msg.MESSAGE_TEXT,
                            'SUPPORTED_CAMT_MESSAGES',
                            bank.bank_name
                            )
                        )
            if self.repo.download_not_activated(bank.iban):
                information = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DOWNLOAD_ACCOUNT_NOT_ACTIVATED',
                    bank.bank_name,
                    bank.owner_name,
                    bank.account_number,
                    bank.account_product_name,
                    bank.iban
                    )
                msg.bankdata_informations_append(decl.WARNING, information)
            else:
                information = msg.get_message(
                    msg.MESSAGE_TEXT,
                    'DOWNLOAD_ACCOUNT',
                    bank.bank_name,
                    bank.owner_name,
                    bank.account_number,
                    bank.account_product_name,
                    bank.iban
                    )
                if bank.scraper:
                    if 'HKKAZ' in account[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                        msg.bankdata_informations_append(decl.INFORMATION, information)
                        if self._statements(bank) is None:
                            msg.bankdata_informations_append(
                                decl.WARNING,
                                msg.get_message(
                                    msg.MESSAGE_TEXT,
                                    'DOWNLOAD_NOT_DONE',
                                    bank.bank_name
                                    )
                                )
                            return
                else:
                    if 'HKWPD' in account[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                        msg.bankdata_informations_append(decl.INFORMATION, information)
                        if self._holdings(bank) in decl.START_DIALOG_FAILED:
                            msg.bankdata_informations_append(
                                decl.WARNING,
                                msg.get_message(
                                    msg.MESSAGE_TEXT,
                                    'DOWNLOAD_NOT_DONE',
                                    bank.bank_name
                                    )
                                )
                            return
                    if bank.statement_mt940 or bank.statement_camt:
                        msg.bankdata_informations_append(decl.INFORMATION, information)
                        if self._statements(bank) in decl.START_DIALOG_FAILED:
                            msg.bankdata_informations_append(
                                decl.WARNING,
                                msg.get_message(
                                    msg.MESSAGE_TEXT,
                                    'DOWNLOAD_NOT_DONE',
                                    bank.bank_name
                                    )
                                )
                            return
        msg.bankdata_informations_append(
            decl.INFORMATION,
            msg.get_message(
                msg.MESSAGE_TEXT,
                'DOWNLOAD_DONE',
                bank.bank_name) + '\n\n'
            )

    def all_holdings(self, bank):
        """
        Insert downloaded  Holding Bank Data in Database
        """
        msg.bankdata_informations_append(
            decl.INFORMATION,
            msg.get_message(
                msg.MESSAGE_TEXT,
                'DOWNLOAD_BANK',
                bank.bank_name
                )
            )
        for account in bank.accounts:
            bank.account_number = account[decl.KEY_ACC_ACCOUNT_NUMBER]
            bank.iban = account[decl.KEY_ACC_IBAN]
            if 'HKWPD' in account[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                msg.bankdata_informations_append(
                    decl.INFORMATION,
                    msg.get_message(
                        msg.MESSAGE_TEXT,
                        'DOWNLOAD_ACCOUNT',
                        bank.bank_name,
                        '',
                        bank.account_number,
                        bank.account_product_name,
                        bank.iban
                        )
                    )
                if self._holdings(bank) in decl.START_DIALOG_FAILED:
                    msg.bankdata_informations_append(
                        decl.WARNING,
                        msg.get_message(
                            msg.MESSAGE_TEXT,
                            'DOWNLOAD_NOT_DONE',
                            bank.bank_name
                            )
                        )
                    return

    def _holdings(self, bank) -> List[Dict[str, Any]]:
        """
        Persist daily holdings of a bank account into the HOLDING table.
        The method:
        1. Downloads current holdings from the bank.
        2. Normalizes the price date (adjusts weekends to the previous business day).
        3. Replaces existing holdings for the same IBAN and price date.
        4. Ensures referenced ISIN master data exists.
        5. Updates acquisition amounts per holding.
        6. Commits all changes as a single database transaction.
        Parameters
        ----------
        bank : Bank
            Bank object providing:
            - IBAN
            - bank_name
            - access to the holdings download dialog
        Returns
        -------
        List[Dict[str, Any]]
            List of holding records persisted in the database.
            Returns an empty list if:
            - no holdings are available, or
            - the transaction is rolled back due to user cancellation.
        """
        # Start database transaction
        self.repo.start_transaction()
        try:
            # Download holdings from bank
            holdings: List[Dict[str, Any]] = bank.dialogs.holdings(bank)
            if holdings in decl.START_DIALOG_FAILED:
                self.repo.rollback_transaction()
                return holdings
            # Determine and normalize price date (weekend adjustment)
            price_date_holding = max(h[declm.DB_price_date] for h in holdings)
            weekday = date_yyyymmdd.convert(price_date_holding).weekday()
            if weekday == 5:          # Saturday
                price_date_holding = date_yyyymmdd.subtract(price_date_holding, 1)
            elif weekday == 6:        # Sunday
                price_date_holding = date_yyyymmdd.subtract(price_date_holding, 2)
            # Remove existing holdings for the same IBAN and price date
            self.repo.delete_holding(bank.iban, price_date_holding)
            # Insert or replace holdings
            for holding in holdings:
                isin = holding[declm.DB_ISIN]
                name = holding[declm.DB_name]
                # Ensure ISIN master record exists
                if not self.repo.exist_isin_name(name):
                    self.repo.replace_isin_name_of_isin_code(isin, name)
                # Prepare holding record
                holding_data = holding.copy()
                holding_data.pop(declm.DB_name)
                holding_data[declm.DB_price_date] = price_date_holding
                holding_data[declm.DB_iban] = bank.iban
                # Persist holding
                self.repo.replace_holding(holding_data)
                # Update acquisition amount
                self._set_acquisition_amount(bank, isin, name)
            # Commit transaction
            self.repo.commit()
            return holdings
        except Exception as e:
            print(str(e))
            self.repo.rollback_transaction()
            msg.MessageBoxInfo(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    "DOWNLOAD_REPEAT",
                    bank.bank_name
                )
            )
            return []

    def _statements(self, bank) -> list[dict]:
        """
        Store bank statements for a bank account in the STATEMENT table.
        Parameters
        ----------
        bank : Bank
            Bank object containing account info and download dialogs.
        Returns
        -------
        list[dict]
            List of statements inserted into the database.
        """
        max_entry_date = self.repo.max_entry_date_of_statement(bank.iban)
        bank.from_date = max_entry_date if max_entry_date else decl.START_DATE_STATEMENTS
        bank.to_date = str(date.today())
        statements = bank.download_statements() if bank.scraper else bank.dialogs.statements(bank)
        if statements in decl.START_DIALOG_FAILED or statements == []:
            return statements
        entry_date = None
        for statement in statements:
            if statement[declm.DB_entry_date] != entry_date:
                entry_date = statement[declm.DB_entry_date]
                counter = 0
            statement[declm.DB_iban] = bank.iban
            statement[declm.DB_counter] = counter
            # Skip if already exists
            if self.repo.exists_statement_row(statement[declm.DB_iban], statement[declm.DB_entry_date], counter):
                pass
            elif declm.DB_bank_reference in statement and self.repo.exist_iban_with_bank_reference(statement[declm.DB_iban], statement[declm.DB_bank_reference]):
                pass
            else:
                if not statement.get(declm.DB_purpose_wo_identifier):
                    statement[declm.DB_purpose_wo_identifier] = statement[declm.DB_purpose]
                self.repo.insert_statement(statement)
            counter += 1
        self.repo.commit()
        if application_store.get(declm.DB_ledger):
            self.transfer_statement_to_ledger(bank)
        return statements

    def transfer_statement_to_ledger(self, bank):
        """
        Upload ledger rows from table statement
        """
        ledger_max_entry_date = self.repo.max_entry_date_of_ledger_statement(bank.iban)
        if ledger_max_entry_date is None:
            ledger_max_entry_date = decl.START_DATE_LEDGER
        statements = self.repo.get_statements_with_amount(bank.iban, (ledger_max_entry_date, date.today()))
        if statements:
            # get ledger account_number assigned to iban of bank account
            account = self.repo.get_account_of_iban(bank.iban)
            if not account:  # cancel download of this bank account
                msg.MessageBoxInfo(
                    message=msg.MessageBoxInfo(
                        msg.MESSAGE_TEXT,
                        'ACCOUNT_IBAN_MISSED',
                        bank.bank_name,
                        bank.account_product_name,
                        bank.account_number
                        )
                    )
                return
            # initialize credit/debit
            opening_balance = statements[0][declm.DB_opening_balance]
            if statements[0][declm.DB_opening_status] == decl.DEBIT:
                opening_balance = -opening_balance
            # check and store statement records in ledger table
            for statement_dict in statements:
                iban = statement_dict[declm.DB_iban]
                entry_date = statement_dict[declm.DB_entry_date]
                counter = statement_dict[declm.DB_counter]
                status = statement_dict[declm.DB_status]
                if self.repo.exist_ledger_statement_with_status(iban, entry_date,  counter, status):
                    pass  # statement already assigned in ledger
                else:
                    # create ledger
                    id_no = self.repo.get_new_id_no_of_year(entry_date)
                    ledger_dict = {declm.DB_id_no: id_no}
                    statement_to_ledger_fields = [
                        declm.DB_entry_date,
                        declm.DB_date,
                        declm.DB_purpose_wo_identifier,
                        declm.DB_amount,
                        declm.DB_currency,
                        declm.DB_applicant_name
                    ]
                    for ledger_field_name in statement_to_ledger_fields:
                        ledger_value = statement_dict[ledger_field_name]
                        if ledger_value:
                            ledger_dict[ledger_field_name] = ledger_value
                    if statement_dict[declm.DB_status] == decl.CREDIT:
                        ledger_dict[declm.DB_credit_account] = account
                        ledger_dict[declm.DB_debit_account] = self._recommend_account(
                            account, statement_dict)
                    else:
                        ledger_dict[declm.DB_debit_account] = account
                        ledger_dict[declm.DB_credit_account] = self._recommend_account(
                            account, statement_dict)
                    self.repo.insert_ledger(ledger_dict)
                    # connect to ledger_statemnt
                    ledger_statement_dict = {}
                    ledger_statement_dict[declm.DB_iban] = statement_dict[declm.DB_iban]
                    ledger_statement_dict[declm.DB_entry_date] = statement_dict[declm.DB_entry_date]
                    ledger_statement_dict[declm.DB_counter] = statement_dict[declm.DB_counter]
                    ledger_statement_dict[declm.DB_status] = statement_dict[declm.DB_status]
                    ledger_statement_dict[declm.DB_id_no] = id_no
                    self.repo.insert_ledger_statement(ledger_statement_dict)
            # check balances of LEDGER and STATEMENT table
            # compare balances
            credit = self.repo.get_sum_of_credits(account, ledger_max_entry_date)
            debit = self.repo.get_sum_of_debits(account, ledger_max_entry_date)
            ledger_balance = opening_balance + credit - debit
            closing_balance = statement_dict[declm.DB_closing_balance]
            if statement_dict[declm.DB_closing_status] == decl.DEBIT:
                closing_balance = -closing_balance
            if closing_balance != ledger_balance:
                msg.MessageBoxInfo(
                    message=msg.get_message(
                        msg.MESSAGE_TEXT,
                        'BALANCE_DIFFERENCE',
                        bank.account_product_name,
                        bank.account_number,
                        closing_balance,
                        self.repo.get_name_of_account(account),
                        account,
                        ledger_balance,
                        str(dec2.subtract(closing_balance, ledger_balance))
                    ),
                    information=decl.WARNING
                )

    def _recommend_account(self, account, statement_dict):
        """
        recommendation contra account, otherwise return 'NA'
        hierarchy of contra_account selection
        """
        # 1. table LEDGER_COA
        contra_account = self.repo.get_contra_account_of_account(account)
        if contra_account != decl.NOT_ASSIGNED:
            return contra_account
        # 2. find contra_account used last 370 days, statement fields checked in this order
        check_field_list = [declm.DB_creditor_id, declm.DB_debitor_id, declm.DB_mandate_id,
                            declm.DB_applicant_iban, declm.DB_applicant_name, declm.DB_purpose_wo_identifier]
        period = (date_days.subtract(statement_dict[declm.DB_entry_date], 370), date_days.subtract(statement_dict[declm.DB_entry_date], 1))
        for field_name in check_field_list:
            if statement_dict[field_name]:
                if field_name == declm.DB_creditor_id:
                    recommended_account = self.repo.get_account_of_creditor_id(statement_dict[declm.DB_iban], period, statement_dict[declm.DB_creditor_id])
                elif field_name == declm.DB_debitor_id:
                    recommended_account = self.repo.get_account_of_debitor_id(statement_dict[declm.DB_iban], period, statement_dict[declm.DB_debitor_id])
                elif field_name == declm.DB_mandate_id:
                    recommended_account = self.repo.get_account_of_mandate_id(
                        statement_dict[declm.DB_iban], period=period, mandate_id=statement_dict[declm.DB_mandate_id])
                elif field_name == declm.DB_applicant_iban:
                    recommended_account = self.repo.get_account_of_applicant_iban(statement_dict[declm.DB_iban], period, statement_dict[declm.DB_applicant_iban])
                elif field_name == declm.DB_applicant_name:
                    recommended_account = self.repo.get_account_of_applicant_name(statement_dict[declm.DB_iban], period, statement_dict[declm.DB_applicant_name])
                elif field_name == declm.DB_purpose_wo_identifier:
                    recommended_account = self.repo.get_account_of_purpose_wo_identifier(statement_dict[declm.DB_iban], period, statement_dict[declm.DB_purpose_wo_identifier])
                if recommended_account not in [decl.NOT_ASSIGNED, account]:
                    return recommended_account
        # 3. dictionary  used posting_text_dict of last 365 days
        if statement_dict[declm.DB_posting_text]:
            # contra_account matched posting_text
            recommended_account = self.repo.get_contra_account_of_posting_text(statement_dict)
            if recommended_account not in [decl.NOT_ASSIGNED, account]:
                return recommended_account
        return decl.NOT_ASSIGNED

    def _set_acquisition_amount(self, bank: object, isin: str, name_: str):
        """
        Update the acquisition amount of a holding based on previous entries.
        Parameters
        ----------
        bank : Bank
            Bank object.
        isin : str
            ISIN of the holding.
        name_ : str
            Name of the security.
        """
        rows = self.repo.get_holding_aquisition_data(bank.iban, isin)
        if not rows:
            return
        data = [HoldingAcquisition(*row) for row in reversed(rows)]
        pieces_diff = data[0].pieces - data[-1].pieces
        if len(data) > 1 and pieces_diff == 0 and data[0].acquisition_price == data[-1].acquisition_price:
            acquisition_amount = data[0].acquisition_amount
        elif data[-1].price_currency == decl.PERCENT:
            msg.MessageBoxInfo(
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'ACQUISITION_AMOUNT',
                    bank.bank_name,
                    bank.iban,
                    name_,
                    isin
                    ),
                information=decl.WARNING
                )
            acquisition_amount = data[0].acquisition_amount
        else:
            acquisition_amount = dec2.multiply(data[-1].pieces, data[-1].acquisition_price)
        data[-1].acquisition_amount = acquisition_amount
        self._update_holding_acquisition(bank.iban, isin, data[-1])

    def _update_holding_acquisition(self, iban, isin_code, HoldingAcquisition):

        if HoldingAcquisition.origin == decl.ORIGIN:
            self.repo.update_holding_aquisition_bankdata(
                HoldingAcquisition.acquisition_amount,
                iban,
                isin_code,
                HoldingAcquisition.price_date
                )
        else:
            self.repo.update_holding_aquisition_with_price(
                HoldingAcquisition.acquisition_price,
                HoldingAcquisition.acquisition_amount,
                iban,
                isin_code,
                HoldingAcquisition.price_date)


@dataclass
class HoldingAcquisition:
    price_date: date
    price_currency: str = field(default=decl.EURO)
    market_price: Decimal = field(default=0)
    acquisition_price: Decimal = field(default=0)
    pieces: Decimal = field(default=0)
    amount_currency: str = field(default=decl.EURO)
    total_amount: Decimal = field(default=0)
    acquisition_amount: Decimal = field(default=0)
    origin: str = field(default=0)


class UpdateHoldingAcquisition:

    def update_holding_acquisition(self, iban, price_date, isin_code):

        holding = self.repo.select_holding_view_row(iban, price_date, isin_code)
        remaining = dec6.convert(holding[declm.DB_pieces])
        acquisition_amount = dec2.convert(0)
        transactions = self.repo.get_transactions_update_acquisition(iban, price_date, isin_code)
        for t_pieces, t_amount in transactions:
            if remaining <= 0:
                break
            if t_pieces <= remaining:
                acquisition_amount += t_amount
                remaining -= t_pieces
            else:
                ratio = remaining / t_pieces
                acquisition_amount += t_amount * ratio
                remaining = 0
                break
        acquisition_price = dec6.convert(0)
        if holding[declm.DB_pieces] > 0:
            acquisition_price = acquisition_amount / holding[declm.DB_pieces]
        field_dict = {declm.DB_acquisition_price: acquisition_price, declm.DB_acquisition_amount: acquisition_amount}
        self.repo.update_holding(iban, price_date, isin_code, field_dict)


class ImportServices:

    def import_transaction_csv(
            self,
            csv_file,
            table_name=declm.TRANSACTION,
            field_mapping={},
            additional_fields={},
            value_transformers={},
            csv_date_format="%d.%m.%Y",
            delimiter=";",
            decimal_separator=',',
            encoding="latin1",
            has_header=True,
            start_line=1,
            commit=True
    ):
        """
        Loads selected CSV fields into a MariaDB table.
        value_transformers can access all current row values.
        Transformer signature:
            lambda value, row_data: ...

        Parameters
        ----------

            csv_file : str              Path to CSV file
            table_name : str            Target table name
            field_mapping : dict        Mapping between CSV fields and DB fields.
            additional_fields : dict    Additional static fields added to every INSERT.
            value_transformers : dict   Optional transformation functions per DB field.
            csv_date_format :           STANDARD "%d.%m.%Y"
            has_header : bool           True: CSV contains header row  False: CSV has no header
            start_line: int             goto startline

        Example:
        --------
                mapping = {
                    "ISIN": "isin_code",
                    "Price": "price",
                    "Quantity": "pieces"
                }

                    Examples:
                    ---------
                    CSV with header:
                        {
                            "Article": "isin_code",
                            "Price": "price"
                        }

                    CSV without header:
                        {
                            0: "isisn_code",
                            3: "price"
                        }

                additional_fields = {
                    "status": None,
                    "total_value": None
                }

                transformers = {
                    # Convert isin_code to uppercase
                    "isin_code": lambda value, row:
                        value.upper(),
                    # Always store positive price
                    "price": lambda value, row:
                        abs(value),
                    # Status depends on price
                    "status": lambda value, row:
                        "EXPENSIVE"
                        if row["price"] > 10
                        else "NORMAL",
                    # total_value depends on price and stock
                    "total_value": lambda value, row:
                        row["price"] * row["pieces"]
                }

        """
        def parse_decimal(value: str, decimal_separator=",", places=2):
            """
            Converts values like:
                1.234,56
                -1.234,56
                1234,56
            into Decimal.
            """
            if value is None:
                return None
            if isinstance(value, str):
                value = value.strip()
                if value == "":
                    return None
                if decimal_separator == ",":  # If a comma is present → German format
                    value = value.replace(".", "")
                    value = value.replace(",", ".")
            if places == 2:
                return dec2.convert(value)
            else:
                return dec6.convert(value)

        message_1st_line = False
        field_properties = declm.TABLE_FIELDS_PROPERTIES[table_name]
        inserted_transactions = []
        with open(csv_file, "r", encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for _ in range(start_line - 1):
                next(reader)
            headers = None
            if has_header:
                headers = next(reader)
            # Final DB field list
            db_fields = (
                list(field_mapping.values()) +
                list(additional_fields.keys())
            )
            price_date = None
            counter = 0
            for _, row in enumerate(reader, start=1):
                # Build original_row with mapped DB field names
                original_row = {}
                for csv_field, db_field in field_mapping.items():
                    if isinstance(csv_field, int):
                        if csv_field < len(row):
                            original_row[db_field] = row[csv_field]
                        else:
                            original_row[db_field] = None
                    else:
                        idx = headers.index(csv_field)
                        if idx < len(row):
                            original_row[db_field] = row[idx]
                        else:
                            original_row[db_field] = None
                values = []
                # Process mapped CSV fields
                for csv_field, db_field in field_mapping.items():
                    value = original_row[db_field]
                    if value is not None:
                        if field_properties[db_field].typ == decl.TYP_DECIMAL:
                            value = parse_decimal(
                                value,
                                decimal_separator=decimal_separator,
                                places=field_properties[db_field].places)
                            original_row[db_field] = value
                        elif field_properties[db_field].typ == decl.TYP_DATE:
                            value = date_days.mariadb_date(value, csv_date_format=csv_date_format)
                            original_row[db_field] = value
                        else:
                            value = value.strip()
                            if value == "":
                                value = None
                    # Apply transformer
                    if db_field in value_transformers:
                        value = value_transformers[db_field](
                            value,
                            original_row
                        )
                    values.append(value)
                # Add additional fields
                for db_field, value in additional_fields.items():
                    if db_field in value_transformers:
                        value = value_transformers[db_field](
                            value,
                            original_row
                        )
                    elif db_field == declm.DB_counter:
                        if price_date == original_row[declm.DB_price_date]:
                            counter += 1
                        else:
                            price_date = original_row[declm.DB_price_date]
                            counter = 0
                        value = counter
                    values.append(value)
                field_dict = dict(zip(db_fields, values))
                result = self.repo.exist_transaction_identical(field_dict)
                if not result:
                    try:
                        self.repo.insert_transaction_ignore_duplicate(field_dict)
                        inserted_transactions.append(field_dict)
                    except Exception:
                        if DatabaseErrorHandler.EXCEPTION.errno == 1062:
                            # ignore duplicate error
                            pass
                        else:
                            raise
                if DatabaseErrorHandler.EXCEPTION:
                    if not message_1st_line:
                        msg.MessageBoxInfo(
                            title=msg.MESSAGE_TITLE,
                            info_storage=msg.Informations.TRANSACTION_INFORMATIONS,
                            message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_ALREADY', csv_file)
                            )
                        message_1st_line = True
                    msg.MessageBoxInfo(
                        title=msg.MESSAGE_TITLE,
                        info_storage=msg.Informations.TRANSACTION_INFORMATIONS,
                        message=field_dict
                        )
            if commit:
                self.repo.commit
            return inserted_transactions

    def import_transaction_consors(self, iban: str, filename: str) -> None:
        mapping = {
            "Ausführungsdatum": declm.DB_price_date,
            "ISIN": declm.DB_ISIN,
            "Stück/Nominal": declm.DB_pieces,
            "Ausführungskurs": declm.DB_price,
            "Ausführungskurs Währung": declm.DB_price_currency,
            "Ordernummer": declm.DB_transaction_no,
            "Orderart": declm.DB_comments
        }
        additional_fields = {
            declm.DB_iban: iban,
            declm.DB_counter: 0,
            declm.DB_transaction_type: decl.TRANSACTION_RECEIPT,
            declm.DB_posted_amount: 0
        }
        transformers = {
            declm.DB_transaction_type: lambda value, row:
                decl.TRANSACTION_RECEIPT
                if row[declm.DB_comments] == "Kauf"
                else decl.TRANSACTION_DELIVERY,
            declm.DB_posted_amount: lambda value, row:
                dec2.multiply(row[declm.DB_pieces], row[declm.DB_price])
                if row[declm.DB_price_currency] != '%'
                else
                dec2.divide(
                    dec2.multiply(row[declm.DB_pieces], row[declm.DB_price]),
                    100
                    ),
            declm.DB_price_currency: lambda value, row:
                decl.PERCENT if value == '%' else decl.EURO
        }
        return self.import_transaction_csv(
            csv_file=filename,
            start_line=8,
            encoding='utf-8',
            decimal_separator='.',
            table_name=declm.TRANSACTION,
            field_mapping=mapping,
            additional_fields=additional_fields,
            value_transformers=transformers
            )

    def import_transaction_flatex(self, iban: str, filename: str) -> None:
        mapping = {
            "Buchungstag": declm.DB_price_date,
            "ISIN": declm.DB_ISIN,
            "Nominal (Stk.)": declm.DB_pieces,
            "Betrag": declm.DB_posted_amount,
            "Kurs": declm.DB_price,
            "Devisenkurs": declm.DB_exchange_rate,
            "TA.-Nr.": declm.DB_transaction_no,
            "Buchungsinformation": declm.DB_comments
        }
        additional_fields = {
            declm.DB_iban: iban,
            declm.DB_counter: 0,
            declm.DB_transaction_type: decl.TRANSACTION_RECEIPT,
        }
        transformers = {
            declm.DB_transaction_type: lambda value, row:
                decl.TRANSACTION_RECEIPT
                if row[declm.DB_posted_amount] > 0
                else decl.TRANSACTION_DELIVERY,
            declm.DB_price: lambda value, row: abs(value),
            declm.DB_posted_amount: lambda value, row: abs(value),
            declm.DB_pieces: lambda value, row: abs(value),
        }
        self.import_transaction_csv(
            csv_file=filename,
            field_mapping=mapping,
            additional_fields=additional_fields,
            value_transformers=transformers
        )

    def import_prices_and_corporate_actions(
            self,
            title: str,
            isin_name_list: list[str],
            period_start: str = decl.START_DATE_PRICES,
            state: str = decl.BUTTON_APPEND
            ):

        warning = False
        period_start = date_days.convert_to_str(period_start)
        isin_code_name_dict = {}
        for name in isin_name_list:
            isin_type = self.repo.select_isin_scalar(declm.DB_type, name=name)
            if isin_type != declm.IsinType.BOND.value:
                # There are no prices for bonds on Yahoo.
                isin_code_name_dict[self.repo.get_isin_of_name(name)] = name
        for isin_code in isin_code_name_dict.keys():
            start_date = period_start
            if state == decl.BUTTON_APPEND:
                last_date = self.repo.prices_max_date_of_isin(isin_code)
                if last_date:
                    start_date = date_days.add(last_date, 1)
            elif state == decl.BUTTON_REPLACE:
                self.repo.delete_prices(isin_code)
                self.repo.delete_corporate_actions_data(isin_code)
            if datetime.now().time() >= time(19, 0):
                end_date = date_days.today()
            else:
                end_date = date_days.subtract(date_days.today(), 1)
            if start_date >= end_date:
                msg.MessageBoxInfo(
                    title=title,
                    info_storage=msg.Informations.PRICES_INFORMATIONS,
                    message=msg.get_message(msg.MESSAGE_TEXT, 'PRICES_ALREADY', name)
                    )
                continue
            msg.MessageBoxInfo(
                title=title,
                info_storage=msg.Informations.PRICES_INFORMATIONS,
                message=msg.get_message(
                    msg.MESSAGE_TEXT,
                    'PRICES_DOWNLOAD',
                    isin_code_name_dict[isin_code],
                    start_date,
                    end_date
                    )
                )
            # Download Prices + Corporate Actions
            try:
                isin_code_data_dict = self.repo.get_isin_symbol_data(isin_code)
                if not isin_code_data_dict:
                    warning = True
                    msg.MessageBoxInfo(
                        title=title,
                        info_storage=msg.Informations.PRICES_INFORMATIONS,
                        information=decl.WARNING,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'ISIN_SYMBOL_MISSED',
                            isin_code_name_dict[isin_code],
                            )
                        )
                    return False
                ticker_obj = yf.Ticker(isin_code_data_dict[declm.DB_symbol])
                # Prices
                with msg.capture_yfinance_logs() as logs:
                    df_prices = ticker_obj.history(
                        start=start_date,
                        end=end_date,
                        auto_adjust=False,
                        actions=False
                    )
                # Logs auswerten
                for log in logs:
                    if "ERROR" in log or "WARNING" in log:
                        warning = True
                        msg.MessageBoxInfo(
                            title=title,
                            info_storage=msg.Informations.PRICES_INFORMATIONS,
                            information=decl.WARNING,
                            message=msg.get_message(
                                msg.MESSAGE_TEXT,
                                'PRICES_ERROR',
                                isin_code_name_dict[isin_code],
                                isin_code_data_dict[declm.DB_symbol],
                                log
                            )
                        )
                # Dividends & Splits
                df_dividends = ticker_obj.dividends
                df_splits = ticker_obj.splits
                # 3. Transform Prices
                if not df_prices.empty:
                    df_prices.reset_index(inplace=True)
                    df_prices.rename(columns={
                        "Date": declm.DB_price_date,
                        "Open": declm.DB_open,
                        "High": declm.DB_high,
                        "Low": declm.DB_low,
                        "Close": declm.DB_close,
                        "Adj Close": declm.DB_adjclose,
                        "Volume": declm.DB_volume
                    }, inplace=True)
                    df_prices[declm.DB_ISIN] = isin_code
                    df_prices[declm.DB_origin] = decl.YAHOO
                    df_prices[declm.DB_symbol_prices] = isin_code_data_dict[declm.DB_symbol]
                    df_prices = df_prices[
                        [declm.DB_ISIN, declm.DB_price_date, declm.DB_open, declm.DB_high, declm.DB_low,
                         declm.DB_close, declm.DB_adjclose, declm.DB_volume,
                         declm.DB_origin, declm.DB_symbol_prices]
                    ]

                    rows_to_delete = df_prices[df_prices[declm.DB_close] == 0]
                    if not rows_to_delete.empty:
                        warning = True
                        msg.MessageBoxInfo(
                            title=title,
                            info_storage=msg.Informations.PRICES_INFORMATIONS,
                            information=decl.WARNING,
                            message=msg.get_message(
                                msg.MESSAGE_TEXT,
                                'PRICES_CLOSE_ZERO',
                                isin_code_name_dict[isin_code],
                                f"{rows_to_delete[declm.DB_price_date].tolist()}"
                                )
                            )
                        df_prices = df_prices[df_prices[declm.DB_close] != 0]
                    self.repo.import_prices_batch(df_prices)
                    msg.MessageBoxInfo(
                        title=title,
                        info_storage=msg.Informations.PRICES_INFORMATIONS,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'PRICES_LOADED',
                            isin_code_name_dict[isin_code],
                            str(len(df_prices)))
                        )
                else:
                    warning = True
                    msg.MessageBoxInfo(
                        title=title,
                        info_storage=msg.Informations.PRICES_INFORMATIONS,
                        information=decl.WARNING,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'PRICES_NO_DOWNLOAD',
                            isin_code_name_dict[isin_code],
                            isin_code_data_dict[declm.DB_symbol],
                            decl.YAHOO)
                    )
                # 4. Transform Corporate Actions
                actions_list = []
                if not df_dividends.empty:
                    for date_, value in df_dividends.items():
                        actions_list.append({
                            declm.DB_ISIN: isin_code,
                            "action_date": date_days.mariadb_date(date_),
                            "action_type": "DIVIDEND",
                            "action_value": dec6.convert(value)
                        })
                if not df_splits.empty:
                    for date_, value in df_splits.items():
                        actions_list.append({
                            declm.DB_ISIN: isin_code,
                            "action_date": date_days.mariadb_date(date_),
                            "action_type": "SPLIT",
                            "action_value": dec6.convert(value)
                        })
                # 5. Insert into corporate_actions
                self.repo.replace_corporate_actions_data(actions_list)
                if actions_list:
                    msg.MessageBoxInfo(
                        title=title,
                        info_storage=msg.Informations.PRICES_INFORMATIONS,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'PRICES_CORPORATE',
                            isin_code_name_dict[isin_code],
                            str(len(actions_list)))
                        )
            except Exception as e:
                warning = True
                msg.MessageBoxInfo(
                    title=title,
                    info_storage=msg.Informations.PRICES_INFORMATIONS,
                    information=decl.WARNING,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT,
                        'PRICES_ERROR',
                        isin_code_name_dict[isin_code],
                        isin_code,
                        e if isinstance(e, str) else str(e))
                    )
            return warning
        return True  # if an attempt was made to import only bond prices


class ShowServices:

    def get_balances(self, bank_accounts: List[Dict]):

        period = xetra_cls.last_trading_period()
        # recalculate balance, delete
        balance_accounts = []
        ledger_accounts = []
        for acc in bank_accounts:
            balance_account = {declm.DB_iban: acc[decl.KEY_ACC_IBAN]}
            balance_account[decl.KEY_ACC_OWNER_NAME] = acc[decl.KEY_ACC_OWNER_NAME]
            balance_account[declm.DB_name] = acc[decl.KEY_ACC_PRODUCT_NAME]
            balance_account_data = self.repo.get_balance_account_of_iban(acc[decl.KEY_ACC_IBAN])
            balance_account[declm.DB_account] = balance_account_data.get(declm.DB_account, decl.NOT_ASSIGNED)
            balance_account[declm.DB_portfolio] = balance_account_data.get(declm.DB_portfolio, False)
            balance_account[declm.DB_asset_accounting] = True
            balance_accounts.append(balance_account)
            if balance_account[declm.DB_account] != decl.NOT_ASSIGNED:
                ledger_accounts.append(balance_account[declm.DB_account])
        if ledger_accounts:
            self.repo.delete_ledger_daily_balance_in_period(ledger_accounts, period)
        # calculate balances
        from_date, to_date = period
        balances_from_date = self.ledger_balance_account(from_date, balance_accounts, return_to_date=False)
        if not balances_from_date:
            return None
        balances_to_date = self.ledger_balance_account(to_date, balance_accounts, return_to_date=False)
        # Mapping from account -> BALANCE from balances_from_date
        from_map = {d["account"]: d["BALANCE"] for d in balances_from_date}
        for row in balances_to_date:
            account = row["account"]
            if account not in from_map:
                row[declm.DB_opening_balance] = row[decl.FN_BALANCE]
            else:
                row[declm.DB_opening_balance] = from_map[account]
        for row in balances_to_date:
            opening = row.get(declm.DB_opening_balance)
            current = row.get(decl.FN_BALANCE)
            if opening is None or opening == 0:
                row[decl.FN_DAILY_PERCENT] = None  # oder 0 / "N/A"
            else:
                change = (current - opening) / opening * Decimal(100)
                row[decl.FN_DAILY_PERCENT] = change
        return balances_to_date


class LedgerServices:

    def ledger_balance_account(
        self,
        to_date: str,
        asset_accounts: List[Dict[str, any]],
        *,
        return_to_date: bool = True,
        from_date: str | None = None,
    ) -> Optional[List[Dict[str, any]]]:
        """
        Calculate balances for a list of asset accounts.

        Priority:
            1. Portfolio balance (returns 0 if no entries)
            2. Statement balance (with Ledger fallback)
            3. Ledger balance (for accounts without IBAN or as fallback)

        Parameters:
            to_date (yyyy-mm-dd): The date for which balances are calculated.
            asset_accounts (List[Dict[str, any]]): List of account dictionaries. Each dict
                must contain at least the following keys:
                    - declm.DB_account: account identifier
                    - declm.DB_name: account name
                    - declm.DB_iban: IBAN (can be decl.NOT_ASSIGNED)
                    - declm.DB_portfolio: True if it's a portfolio account, else False
            return_to_date  if True return to_date
            from_date (yyyy-mm-dd): The date from which balances are calculated.

        Returns:
            Optional[List[Dict[str, any]]]: A list of dictionaries, each containing:
                - declm.DB_account: account identifier
                - declm.DB_name: account name
                - decl.FN_BALANCE: calculated balance (float)
            Returns None if a critical error occurs (e.g., missing opening balance or ledger).
        """
        data: List[Dict[str, any]] = []
        to_date = date_days.convert_to_str(to_date)
        if from_date is None:
            from_date = date_days.yyyy_01_01(to_date)
        else:
            from_date = date_days.convert_to_str(from_date)
        period = (from_date, to_date)
        # Get the latest price date for all holdings
        max_price_date_all_iban = self.repo.max_price_date_of_all_ibans((to_date))
        # Get the opening balance account
        opening_balance_account = self.repo.opening_balance_account()
        if not opening_balance_account:
            msg.MessageBoxInfo(
                message=msg.get_message(msg.MESSAGE_TEXT, 'OPENING_ACCOUNT_MISSED')
            )
            return None

        # Helper function: Ledger fallback for missing statement balances
        def ledger_fallback(
                account_dict: Dict[str, any],
                period: tuple
                ) -> Optional[float]:
            """
            Retrieve ledger balance for a given account.

            Parameters:
                account_dict (Dict[str, any]): Account dictionary containing at least declm.DB_name
                period (tuple): Balance period

            Returns:
                Optional[float]: Signed ledger balance, or None if not found.
            """
            balance = self.select_ledger_balance(
                account_dict,
                opening_balance_account,
                period
            )
            if balance is None:
                if account_dict[declm.DB_asset_accounting]:
                    msg.MessageBoxInfo(
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'OPENING_LEDGER_MISSED',
                            (None, to_date),
                            account_dict[declm.DB_name]
                        ),
                        info_storage=msg.Informations.BANKDATA_INFORMATIONS,
                    )
                return 0
                # signed_balance(value, status)
            else:
                return balance
        # Iterate over all asset accounts
        for asset_account_dict in asset_accounts:
            account = asset_account_dict.get(declm.DB_account, decl.NOT_ASSIGNED)
            name = asset_account_dict.get(declm.DB_name, decl.NOT_ASSIGNED)
            owner_name = asset_account_dict.get(decl.KEY_ACC_OWNER_NAME, decl.NOT_ASSIGNED)
            iban = asset_account_dict.get(declm.DB_iban, decl.NOT_ASSIGNED)
            portfolio = asset_account_dict.get(declm.DB_portfolio, 0)
            balance: Optional[float] = None

            balance = self.repo.get_daily_balance(
                account=account,
                entry_date=to_date
            )
            if balance is not None and not portfolio:  # use calculated balance
                balance_entry_date = to_date
                pass

            # 1️⃣ Portfolio account: return 0 if no entries, no fallback
            elif portfolio:
                if max_price_date_all_iban:
                    balance = self.repo.get_balance_of_holding(
                        iban=iban,
                        price_date=max_price_date_all_iban,
                    )
                    balance_entry_date = max_price_date_all_iban
            # 2️⃣ IBAN account: try statement balance, fallback to ledger
            elif iban != decl.NOT_ASSIGNED:
                result = self.repo.get_last_statement_of_iban_period(
                    iban=iban,
                    period=(decl.START_DATE_STATEMENTS, to_date),
                )

                if result:
                    balance = signed_balance(
                        result[declm.DB_closing_balance],
                        result[declm.DB_closing_status]
                    )
                    balance_entry_date = result[declm.DB_closing_entry_date]
                else:
                    balance = ledger_fallback(asset_account_dict, period)
                    balance_entry_date = to_date
            # 3️⃣ Account without IBAN: Ledger only
            else:
                balance = ledger_fallback(asset_account_dict, period)
                balance_entry_date = to_date
            # Append calculated balance
            if balance:
                if self.repo.is_asset_accounting(account) and to_date < date_days.today():
                    self.repo.replace_ledger_daily_balance(account, to_date, balance)
                if return_to_date:
                    date = date_days.convert_to_str(to_date)
                else:
                    date = date_days.convert_to_str(balance_entry_date)
                if owner_name == decl.NOT_ASSIGNED:
                    data.append({
                        declm.DB_account: account,
                        declm.DB_name: name,
                        declm.DB_entry_date: date,
                        decl.FN_BALANCE: balance,
                    })
                else:
                    data.append({
                        decl.KEY_ACC_OWNER_NAME: owner_name,
                        declm.DB_account: account,
                        declm.DB_name: name,
                        declm.DB_entry_date: date,
                        decl.FN_BALANCE: balance,
                    })

        return data

    def select_ledger_balance(
        self,
        account_dict: Dict[str, any],
        opening_balance_account: str,
        period: Tuple[str, str],
    ) -> Optional[Decimal]:
        """
        Determine the balance of a ledger account for a given period.
        Priority order:
        0. Use table LEDGER_DAILY_BALANCE
        1. Use the latest opening balance booking involving the opening balance account
           before or at period end.
        2. If no opening balance booking exists:
           - Use the latest STATEMENT entry (closing balance + movements).
        3. If neither exists:
           - Calculate balance purely from ledger movements within the period.
        Parameters
        ----------
        account_dict : Dict[str, any]
            Ledger account metadata dictionary.
        opening_balance_account : str
            Ledger account used for opening balance postings.
        period : Tuple[str, str]
            Period (from_date, to_date), format YYYY-MM-DD.
        Returns
        -------
        Optional[Decimal]
            Calculated ledger balance, or None if no data exists.
        """
        from_date, to_date = period
        account = account_dict[declm.DB_account]
        balance = self.repo.get_daily_balance(account=account, entry_date=to_date)
        if balance:
            return balance
        # Resolve IBAN (if available)
        iban = self.repo.get_iban_of_account(account=account)
        if account_dict[declm.DB_asset_accounting]:
            # Only relevant for non-bank accounts
            # 1. Determine latest opening balance booking
            opening_rows = self.repo.get_opening_rows(account, opening_balance_account, to_date)
            # Case A: Opening balance exists
            if opening_rows:
                opening_date, opening_balance = opening_rows[0]
                _, _, movements = self.repo.select_ledger_totals(
                    account=account,
                    from_date=opening_date,
                    to_date=to_date,
                    exclude_account=opening_balance_account,
                )
                if account_dict[declm.DB_asset_accounting]:
                    # An opening booking must only exist for asset accounts
                    return opening_balance + movements
                else:
                    return movements
        # Case B: No opening balance → STATEMENT fallback
        if iban and self.repo.exists_statements_of_iban(iban):
            statement_row = self.repo.get_last_statement_of_iban(iban)
            if statement_row:
                closing_balance, closing_status, statement_date = statement_row
                # Normalize statement balance sign
                base_balance = (
                    -closing_balance
                    if closing_status == decl.CREDIT
                    else closing_balance
                )
                _, _, movements = self.repo.select_ledger_totals(
                    account=account,
                    from_date=statement_date,
                    to_date=to_date,
                )
                return base_balance + movements
        # Case C: Pure ledger movements within period
        _, _, balance = self.repo.select_ledger_totals(
            account=account,
            from_date=from_date,
            to_date=to_date,
        )
        return balance

    def select_ledger_total_amount(
        self,
        iban: str,
    ) -> dict[str, Any]:
        """
        Return the most recent ledger entry (date, status, amount)
        for the given IBAN, excluding opening balance postings.
        """
        # Resolve opening balance account
        opening_account = self.repo.opening_balance_account()
        if not opening_account:
            msg.MessageBoxInfo(
                message=msg.get_message(msg.MESSAGE_TEXT, "OPENING_ACCOUNT_MISSED")
            )
            return {}
        # Resolve internal ledger account for IBAN
        account = self.repo.get_account_of_iban(iban)
        if not account:
            return {}
        # SQL: unified debit / credit view
        result = self.repo.get_ledger_rows(account, opening_account)
        return result


class TransactionOverviewService:

    def get_transaction_overview(
        self,
        isin_code: str,
        period: tuple,
        iban: str | None = None,
        cost_method: str = "FIFO"
    ) -> list[list]:
        title = 'TransactionOverviewService'
        strategy = self._create_strategy(cost_method)
        from_date, to_date = period

        result = []
        name = self.repo.get_name_of_isin_code(isin_code)

        # 1️⃣ Opening
        historical = self.repo.get_transactions_before(
            isin_code, iban, from_date
        )

        for t_type, pieces, amount, price in historical:
            self._apply(strategy, t_type, pieces, amount, price)

        current_pieces = strategy.current_pieces()

        if current_pieces > 0:
            market_price = self._get_price(iban, from_date, isin_code, name)
            if not market_price:
                msg.MessageBoxInfo(
                    title=title,
                    info_storage=msg.Informations.PRICES_INFORMATIONS,
                    information=decl.WARNING,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT,
                        'PRICES_ERROR',
                        name,
                        isin_code,
                        declm.DB_market_price)
                    )
                return result

        # 2️⃣ Period transactions
        transactions = self.repo.get_transactions(
            isin_code, iban, period
        )

        for price_date, counter, t_type, price, pieces, posted_amount in transactions:

            tx_pieces, proceeds, profit_loss = self._apply(
                strategy, t_type, pieces, posted_amount, price
            )

            current_pieces = strategy.current_pieces()

            result.append([
                price_date,
                counter,
                t_type,
                price,
                tx_pieces,
                current_pieces,
                proceeds,
                profit_loss,
                iban
            ])

        # 3️⃣ Virtual Close
        if strategy.current_pieces() > 0:

            end_price = self._get_price(iban, to_date, isin_code, name)
            if not end_price:
                msg.MessageBoxInfo(
                    title=title,
                    info_storage=msg.Informations.PRICES_INFORMATIONS,
                    information=decl.WARNING,
                    message=msg.get_message(
                        msg.MESSAGE_TEXT,
                        'PRICES_ERROR',
                        name,
                        isin_code,
                        declm.DB_market_price)
                    )
                return result
            tx_pieces, proceeds, profit_loss = strategy.sell(
                strategy.current_pieces(),
                end_price
            )

            result.append([
                to_date,
                9999,
                "CLOSE",
                end_price,
                tx_pieces,
                strategy.current_pieces(),
                proceeds,
                profit_loss,
                iban
            ])

        return result

    def _get_price(self, iban, price_date, isin_code, name):

        market_price = self.repo.get_holding_market_price(iban, price_date, isin_code)
        if not market_price:
            market_price = self.repo.get_close_price(isin_code, price_date)
            if not market_price:
                # import price data
                self.import_prices_and_corporate_actions(msg.MESSAGE_TITLE, [name], state=decl.BUTTON_APPEND)
            market_price = self.repo.get_close_price(isin_code, price_date)

    def _create_strategy(self, cost_method: str):

        if cost_method == "FIFO":
            return LotCostBasis(lifo=False)

        if cost_method == "LIFO":
            return LotCostBasis(lifo=True)

        if cost_method == "AVERAGE":
            return AverageCostBasis()

        raise ValueError("Unknown cost method")

    def _apply(self, strategy, t_type, pieces, amount, price):

        pieces = Decimal(pieces)

        if t_type != decl.TRANSACTION_DELIVERY:
            tx_pieces = strategy.buy(pieces, Decimal(amount))
            return tx_pieces, abs(Decimal(amount)), Decimal("0")

        return strategy.sell(pieces, Decimal(price))


class TradingCalendarService:

    def compare_dates(self, dates):

        trading_days = xetra_cls.trading_days(
            dates[0],
            dates[-1],
            as_str=True
        )
        invalid = [date_days.convert(d) for d in dates if d not in trading_days]
        missing = [date_days.convert(d) for d in trading_days if d not in dates]
        return invalid, missing


class Services(
        TradingCalendarService,
        BuildHoldings,
        DownloadServices,
        LedgerServices,
        HoldingAcquisition,
        UpdateHoldingAcquisition,
        ShowServices,
        TransactionOverviewService,
        ImportServices,
        ):

    def __init__(self, repo: Repository):
        self.repo = repo


conflicts = check_mixin_method_uniqueness(Repository)

if conflicts:
    print("Conflicts found")
    for method, classes in conflicts.items():
        raise ValueError(f"Method {method} in class {classes} already exists in another class")
