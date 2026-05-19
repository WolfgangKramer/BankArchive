'''
Created on 02.03.2026
@author: Wolfg
'''

import yfinance as yf

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from datetime import date
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
        return sum(l["pieces"] for l in self.lots)


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

        # ------------------------------------------------------------------
        # Start database transaction
        # ------------------------------------------------------------------
        self.repo.start_transaction()
        try:
            # ------------------------------------------------------------------
            # Download holdings from bank
            # ------------------------------------------------------------------
            holdings: List[Dict[str, Any]] = bank.dialogs.holdings(bank)
            if holdings in decl.START_DIALOG_FAILED:
                self.repo.rollback_transaction()
                return holdings
            # ------------------------------------------------------------------
            # Determine and normalize price date (weekend adjustment)
            # ------------------------------------------------------------------
            price_date_holding = max(h[declm.DB_price_date] for h in holdings)
    
            weekday = date_yyyymmdd.convert(price_date_holding).weekday()
            if weekday == 5:          # Saturday
                price_date_holding = date_yyyymmdd.subtract(price_date_holding, 1)
            elif weekday == 6:        # Sunday
                price_date_holding = date_yyyymmdd.subtract(price_date_holding, 2)
            # -----------------------------------------------------------------
            # Remove existing holdings for the same IBAN and price date
            # ------------------------------------------------------------------
            self.repo.delete_holding(bank.iban, price_date_holding)
            # ------------------------------------------------------------------
            # Insert or replace holdings
            # ------------------------------------------------------------------
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
            # ------------------------------------------------------------------
            # Commit transaction
            # ------------------------------------------------------------------
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
            if not account: # cancel download of this bank account
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

    def import_prices_and_corporate_actions(
            self,
            title: str,
            isin_name_list: list[str],
            period_start: str = decl.START_DATE_PRICES,
            state: str = decl.BUTTON_APPEND
            ):
        period_start = date_days.convert_to_str(period_start)
        isin_code_name_dict = {}
        for name in isin_name_list:
            isin_code_name_dict[self.repo.get_isin_of_name(name)] = name

        for isin_code in isin_code_name_dict.keys():

            start_date = period_start
            if state == decl.BUTTON_APPEND:
                last_date = self.repo.prices_max_date_of_isin(isin_code)
                if last_date:
                    start_date = date_days.add(last_date, 1)

            end_date = date_days.today()

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

            # -----------------------------
            # Download Prices + Corporate Actions
            # -----------------------------
            try:
                isin_code_data_dict = self.repo.get_isin_symbol_data(isin_code)
                if not isin_code_data_dict:
                    msg.MessageBoxInfo(
                        title=title,
                        info_storage=msg.Informations.PRICES_INFORMATIONS,                    
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'ISIN_SYMBOL_MISSED',
                            isin_code_name_dict[isin_code],
                            )
                        )
                    return
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
                        msg.MessageBoxInfo(
                            title=title,
                            info_storage=msg.Informations.PRICES_INFORMATIONS,
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

                # -----------------------------
                # 3. Transform Prices
                # -----------------------------
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
                    msg.MessageBoxInfo(
                        title=title,
                        info_storage=msg.Informations.PRICES_INFORMATIONS,
                        message=msg.get_message(
                            msg.MESSAGE_TEXT,
                            'PRICES_NO_DOWNLOAD',
                            isin_code_name_dict[isin_code],
                            isin_code_data_dict[declm.DB_symbol],
                            decl.YAHOO)
                    )
                # -----------------------------
                # 4. Transform Corporate Actions
                # -----------------------------
                actions_list = []

                if not df_dividends.empty:
                    for date, value in df_dividends.items():
                        actions_list.append({
                            declm.DB_ISIN: isin_code,
                            "action_date": date.date(),
                            "action_type": "DIVIDEND",
                            "value": dec6.convert(value)
                        })

                if not df_splits.empty:
                    for date, value in df_splits.items():
                        actions_list.append({
                            declm.DB_ISIN: isin_code,
                            "action_date": date.date(),
                            "action_type": "SPLIT",
                            "value": dec6.convert(value)
                        })

                # -----------------------------
                # 5. Insert into corporate_actions
                # -----------------------------
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
        # Mapping von account -> BALANCE aus balances_from_date
        from_map = {d["account"]: d["BALANCE"] for d in balances_from_date}
        for row in balances_to_date:
            account = row["account"]
            if account not in from_map:
                row[declm.DB_opening_balance] = row[decl.FN_BALANCE]
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
                if self.repo.is_asset_accounting(account) and to_date<date_days.today():
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
            # ------------------------------------------------------------------
            # Only relevant for non-bank accounts
            # 1. Determine latest opening balance booking
            # ------------------------------------------------------------------
            opening_rows = self.repo.get_opening_rows(account, opening_balance_account, to_date)
            # ------------------------------------------------------------------
            # Case A: Opening balance exists
            # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # Case B: No opening balance → STATEMENT fallback
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # Case C: Pure ledger movements within period
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------
        # Resolve opening balance account
        # ------------------------------------------------------------
        opening_account = self.repo.opening_balance_account()
        if not opening_account:
            msg.MessageBoxInfo(
                message=msg.get_message(msg.MESSAGE_TEXT, "OPENING_ACCOUNT_MISSED")
            )
            return {}

        # ------------------------------------------------------------
        # Resolve internal ledger account for IBAN
        # ------------------------------------------------------------
        account = self.repo.get_account_of_iban(iban)
        if not account:
            return {}

        # ------------------------------------------------------------
        # SQL: unified debit / credit view
        # ------------------------------------------------------------
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


class Services(
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