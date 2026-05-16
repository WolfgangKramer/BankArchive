'''
Created on 27.02.2026

@author: Wolfg
'''
import os
import tempfile
import json


from pathlib import Path
from decimal import Decimal
from itertools import chain
from typing import Dict, Optional, Iterable, List, Tuple, Any, Union
from datetime import date
from collections import defaultdict

import banking.declarations as decl
import banking.declarations_mariadb as declm

from banking.mariadb import MariaDB
from banking.utils import date_days
from banking.declarations import FN_PROFIT


class SingletonNoLockMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):  # @NoSelf
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]    


class BaseRepository(metaclass=SingletonNoLockMeta):

    def __init__(self):
        self.db = MariaDB()


class ApplicationRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def replace_application(self, field_dict):

        self.db.execute_replace(declm.APPLICATION, field_dict)

    def get_application(self):

        result = self.db.select_table(declm.APPLICATION, '*', result_dict=True, row_id=1)
        if result:
            return {k: v for d in result for k, v in d.items()}
        else:
            return {}

    def alpha_vantage_get(self, field_name: str) -> dict:
        """
        Retrieve Alpha Vantage values for a specific field.

        Parameters
        ----------
        field_name : str
            Column name in APPLICATION table (DB_alpha_vantage_parameter
            or DB_alpha_vantage_function).

        Returns
        -------
        dict
            Dictionary containing the Alpha Vantage values. Empty dict if not found.
        """
        alpha_vantage = self.db.select_scalar(declm.APPLICATION, field_name, row_id=2)
        if alpha_vantage:
            return json.loads(alpha_vantage)
        return {}

    def alpha_vantage_put(self, field_name: str, data: dict) -> None:
        """
        Store Alpha Vantage values for a specific field in JSON format.

        Parameters
        ----------
        field_name : str
            Column name in APPLICATION table (DB_alpha_vantage_parameter
            or DB_alpha_vantage_function).
        data : dict
            Dictionary of values to store for the field.
        """
        json_data = json.dumps(data)
        if self.db.select_exists(declm.APPLICATION, row_id=2):
            self.db.execute_update(declm.APPLICATION, {field_name: json_data}, row_id=2)
        else:
            self.db.execute_insert(declm.APPLICATION, {declm.DB_row_id: 2, field_name: json_data})

    def get_alpha_vantage_functions(self):

        return self.alpha_vantage_get(declm.DB_alpha_vantage_function)

    def put_alpha_vantage_functions(self, function_list: List):

        self.alpha_vantage_put(declm.DB_alpha_vantage_function, function_list)

    def get_alpha_vantage_parameters(self):

        return self.alpha_vantage_get(declm.DB_alpha_vantage_parameter)

    def put_alpha_vantage_parameters(self, parameter_dict):

        self.alpha_vantage_put(declm.DB_alpha_vantage_parameter, parameter_dict)


class BankIdentifierRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_bankidentifier_name_bic_of_bankcode(self, bank_code: str) -> Dict:

        result = self.db.select_table(
                declm.BANKIDENTIFIER,
                [declm.DB_name, declm.DB_bic], result_dict=True, code=bank_code)
        if result:
            return result[0]
        else:
            return {}

    def count_bankidentifier(self) -> int:

        return self.db.select_scalar(declm.BANKIDENTIFIER, 'COUNT(*)')

    def get_bankidentifier_data(self) -> list[dict]:

        result = self.db.select_table(
            declm.BANKIDENTIFIER, field_list=declm.TABLE_FIELDS[declm.BANKIDENTIFIER],  result_dict=True)
        return result

    def import_bankidentifier(self, filename: str) -> None:
        """
        Import bank identifier data into the BANKIDENTIFIER table.
    
        Notes
        -----
        Source:
        Bundesbank - Bankleitzahlen
        https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592
        """
    
        columns = """
            `code`,
            `payment_provider`,
            `payment_provider_name`,
            `postal_code`,
            `location`,
            `name`,
            `pan`,
            `bic`,
            `check_digit_calculation`,
            `record_number`,
            `change_indicator`,
            `code_deletion`,
            `follow_code`
        """
    
        try:
            # Remove existing records
            self.db.executor.execute(
                f"DELETE FROM {declm.BANKIDENTIFIER}"
            )
    
            # Import CSV file
            self.db.execute_load_data(
                filename=filename,
                table=declm.BANKIDENTIFIER,
                columns=columns,
            )
    
            # Remove unwanted payment providers
            cleanup_sql = f"""
                DELETE FROM {declm.BANKIDENTIFIER}
                WHERE payment_provider = '2'
            """
    
            self.db.executor.execute(cleanup_sql)
    
            return None
    
        except Exception as exc:
    
            return exc


class CustomizingRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def save_bankdata(self, bank_code, data):
        return self.db.shelve_put_key(bank_code, data)

    def bank_names(self):
        return self.db.dictbank_names()

    def select_application_data(self):
        return self.db.select_table(
            declm.APPLICATION,
            [declm.DB_directory, declm.DB_logging],
            result_dict=True,
            row_id=1
            )


class GeometryRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def replace_geometry_only(self, caller: str, geometry: str):

        self.db.execute_replace(
            declm.GEOMETRY,
            {declm.DB_caller: caller, declm.DB_geometry: geometry}
            )

    def replace_geometry(self, caller: str, geometry: str, column_width: int):

        self.db.execute_replace(
            declm.GEOMETRY,
            {declm.DB_caller: caller, declm.DB_geometry: geometry, declm. DB_column_width: column_width}
            )

    def select_geometry_of_caller(self, caller: str) -> str:

        geometry = self.db.select_scalar(declm.GEOMETRY, declm.DB_geometry, caller=caller)
        return geometry

    def select_geometry_width_of_caller(self, caller: str) -> int:

        column_width = self.db.select_scalar(declm.GEOMETRY, declm.DB_column_width, caller=caller)
        return column_width

    def update_geometry_width_of_caller(self, column_width: int, caller: str):

        self.db.execute_update(declm.GEOMETRY, {declm.DB_column_width: column_width}, caller=caller)

    def update_geometry_of_caller(self, geometry: str, caller: str):

        self.db.execute_update(declm.GEOMETRY, {declm.DB_geometry: geometry}, caller=caller)

    def reset_geometry(self):

        self.db.execute_delete(declm.GEOMETRY)

    def delete_geometry(self, title):

        self.db.execute_delete(declm.GEOMETRY, caller=title)


class HoldingRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_holding_market_price(self, iban, price_date, isin_code):

        return self.db.select_scalar(declm.HOLDING, declm.DB_market_price, iban=iban, price_date=price_date, isin_code=isin_code)

    def forward_holding_acqusition_data(
            self,
            iban: str,
            price_date: str
            ):
        """
        The goal of this update is to:

            Carry forward acquisition values when a position remains unchanged (pieces)
            Reset values to zero when no historical reference exists
            Avoid overwriting data when the position size (pieces) has changed
        """
        sql_statement = f"""
                UPDATE {declm.HOLDING} h_curr

        LEFT JOIN {declm.HOLDING} h_prev
          ON h_prev.{declm.DB_iban} = h_curr.{declm.DB_iban}
         AND h_prev.{declm.DB_ISIN} = h_curr.{declm.DB_ISIN}
         AND h_prev.{declm.DB_price_date} = (
             SELECT MAX(h2.{declm.DB_price_date})
             FROM {declm.HOLDING} h2
             WHERE h2.{declm.DB_iban} = h_curr.{declm.DB_iban}
               AND h2.{declm.DB_ISIN} = h_curr.{declm.DB_ISIN}
               AND h2.{declm.DB_price_date} < ?
         )

        SET
            h_curr.acquisition_price =
                CASE
                    WHEN h_prev.{declm.DB_price_date} IS NULL THEN 0
                    WHEN h_curr.{declm.DB_pieces} = h_prev.{declm.DB_pieces} THEN h_prev.{declm.DB_acquisition_price}
                    ELSE h_curr.{declm.DB_acquisition_price}
                END,

            h_curr.acquisition_amount =
                CASE
                    WHEN h_prev.{declm.DB_price_date} IS NULL THEN 0
                    WHEN h_curr.{declm.DB_pieces} = h_prev.{declm.DB_pieces} THEN h_prev.{declm.DB_acquisition_amount}
                    ELSE h_curr.{declm.DB_acquisition_amount}
                END

        WHERE h_curr.{declm.DB_price_date} = ? and h_curr.{declm.DB_iban} = ?;
        """
        self.db.execute(sql_statement, vars_=(price_date, price_date, iban))

    def _select_holding_all_total(self, *, result_dict: bool = False, **kwargs):
        return self.db.select_rows(
            table=declm.HOLDING,
            fields=[
                declm.DB_price_date,
                f"SUM({declm.DB_total_amount}) AS {declm.DB_total_amount}",
                f"SUM({declm.DB_acquisition_amount}) AS {declm.DB_acquisition_amount}",
            ],
            group_by=declm.DB_price_date,
            order=declm.DB_price_date,
            sort="ASC",
            result_dict=result_dict,
            **kwargs
            )

    def _select_holding_isins_interval(
        self,
        iban: str | None,
        comparison_field: str,
        isin_codes: Iterable[str],
        **kwargs
    ) -> Tuple[Any, Any, list]:
        """
        Select holding data for multiple ISINs within their maximum common
        available time interval.

        The method determines the overlapping date range in which *all*
        given ISINs have data available and then selects the corresponding
        holding data for that interval.

        Parameters
        ----------
        iban : str | None
            IBAN to restrict the holding data to a specific account.
            If None, all IBANs are considered.
        comparison_field : str
            Database field used for comparison or calculation.
            If FN_PROFIT_LOSS is provided, the value is calculated as
            (total_amount - acquisition_amount).
        isin_codes : Iterable[str]
            List or iterable of ISIN codes to be evaluated.
        **kwargs
            Additional filters passed to `_where_clause()`
            (e.g. portfolio, currency, period).

        Returns
        -------
        tuple
            (
                from_date,
                to_date,
                selected_holding_data
            )

            from_date : date
                Start date of the common interval.
            to_date : date
                End date of the common interval.
            selected_holding_data : list
                Holding data rows for the calculated interval.
        """
        # ------------------------------------------------------------
        # Determine min/max price_date per ISIN (QueryBuilder-basiert)
        # ------------------------------------------------------------
        periods: list[tuple] = []

        for isin in isin_codes:
            min_date = self.db.select_scalar(
                declm.HOLDING,
                f"MIN({declm.DB_price_date})",
                isin_code=isin,
                **kwargs
            )
            max_date = self.db.select_scalar(
                declm.HOLDING,
                f"MAX({declm.DB_price_date})",
                isin_code=isin,
                **kwargs
            )

            if min_date and max_date:
                periods.append((min_date, max_date))

        if not periods:
            return None, None, []
        # ------------------------------------------------------------
        # Calculate common overlapping interval
        # ------------------------------------------------------------
        from_dates, to_dates = zip(*periods)

        from_date = max(from_dates)
        to_date = min(to_dates)

        if from_date > to_date:
            return None, None, []
        # ------------------------------------------------------------
        # Define selected fields
        # ------------------------------------------------------------
        if comparison_field == decl.FN_PROFIT_LOSS:
            field_list = [
                declm.DB_name,
                declm.DB_price_date,
                f"{declm.DB_total_amount} - {declm.DB_acquisition_amount} AS {decl.FN_PROFIT_LOSS}",
            ]
        else:
            field_list = [
                declm.DB_name,
                declm.DB_price_date,
                comparison_field,
            ]
        # ------------------------------------------------------------
        # Fetch holding data for common interval
        # ------------------------------------------------------------
        query_kwargs = {
            declm.DB_ISIN: list(isin_codes),
            "period": (from_date, to_date),
        }

        if iban:
            query_kwargs[declm.DB_iban] = iban

        selected_holding_data = self._select_holding_data(
            field_list=field_list,
            **query_kwargs
        )

        return from_date, to_date, selected_holding_data

    def _select_holding_data(
        self,
        field_list: Union[str, Iterable[str]] = (
            declm.DB_ISIN, declm.DB_name, declm.DB_total_amount, declm.DB_acquisition_amount,
            declm.DB_pieces, declm.DB_market_price, declm.DB_price_currency, declm.DB_amount_currency
        ),
        *,
        result_dict: bool = True,
        **kwargs
    ) -> List[dict] | List[tuple]:
        """
        Select holding data from HOLDING_VIEW with optional filters.

        The method builds the WHERE clause using `_where_clause()` and
        returns holding rows either as dictionaries or tuples.

        Parameters
        ----------
        field_list : str | Iterable[str], optional
            Fields to select. Can be a comma-separated string or
            an iterable of column names.
        result_dict : bool, optional
            If True, rows are returned as dictionaries.
            If False, rows are returned as tuples.
        **kwargs
            Additional filters passed to `_where_clause()`
            (e.g. iban, isin_code, period).

        Returns
        -------
        list[dict] | list[tuple]
            Selected holding rows.
            Returns an empty list if no fields are specified.
        """
        if not field_list:
            return []

        return self.db.select_table(
            declm.HOLDING_VIEW,
            field_list,
            result_dict=result_dict,
            **kwargs
        )

    def get_holding_existing_isin_codes(self):

        max_price_date_all_iban = self.max_price_date_of_all_ibans((date_days.today()))
        result = self.db.select_table_distinct(
            declm.HOLDING, declm.DB_ISIN, price_date=max_price_date_all_iban)
        return [x[0] for x in result]
    
    def get_holding_price_dates_of_iban(self, iban):

        data = self.db.select_table_distinct(
            declm.HOLDING, declm.DB_price_date, iban=iban, order=declm.DB_price_date)
        return data

    def exist_holding_position(self, iban: str, price_date: str, isin_code: str) -> bool:

        return self.db.select_exists(declm.HOLDING, iban=iban, isin_code=isin_code, price_date=price_date)

    def exist_holding_of_iban_price_date(self, iban, price_date):

        return self.db.select_exists(declm.HOLDING, iban=iban, price_date=price_date)

    def update_holding_aquisition_bankdata(
            self,
            acquisition_amount: Decimal,
            iban: str,
            isin_code: str,
            price_date: str
            ):

        sql_statement = ("UPDATE " + declm.HOLDING +
                         " SET acquisition_amount=? WHERE iban=? AND isin_code=? AND price_date=?")
        self.db.execute(sql_statement, vars_=(acquisition_amount, iban, isin_code, price_date))

    def update_holding_aquisition_with_price(
            self,
            acquisition_price: Decimal,
            acquisition_amount: Decimal,
            iban: str,
            isin_code: str,
            price_date: str
            ):

        sql_statement = ("UPDATE " + declm.HOLDING + " SET acquisition_price=?, "
                         " acquisition_amount=? WHERE iban=? AND isin_code=?  AND price_date=?")
        self.db.execute(sql_statement, vars_=(acquisition_price, acquisition_amount, iban, isin_code, price_date))

    def get_holding_aquisition_data(self, iban, isin_code):

        sql = f"""
            SELECT price_date, price_currency, market_price, acquisition_price,
                   pieces, amount_currency, total_amount, acquisition_amount, origin
            FROM {declm.HOLDING}
            WHERE iban=? AND isin_code=?
            ORDER BY price_date DESC
            LIMIT 2
        """
        rows = self.db.executor.execute(sql, (iban, isin_code))
        return rows

    def update_holding_all_isin_codes(self, field_dict: Dict, iban: str, price_date: str):

        self.db.execute_update(
            declm.HOLDING, field_dict, iban=iban, price_date=price_date)

    def replace_holding(self, holding_data: Dict):

        self.db.execute_replace(declm.HOLDING, holding_data)

    def delete_holding(self, iban: str, price_date: str):

        self.db.execute_delete(
            declm.HOLDING,
            iban=iban,
            price_date=price_date
        )

    def delete_holding_position(self, iban, price_date, isin_code):

        self.db.execute_delete(declm.HOLDING, iban=iban, isin_code=isin_code, price_date=price_date)

    def max_price_date_of_all_ibans(self, to_date: str) -> str:

        result = self.db.select_last_row(
            declm.HOLDING,
            declm.DB_price_date,
            order=declm.DB_price_date,
            clause=f"{declm.DB_price_date} <= ?",
            clause_vars=(to_date,)
            )
        if result:
            return result[0]
        return result

    def get_holding_to_update_acquisition_amount(self, iban, isin_code, price_date):

        result = self._select_holding_data(iban=iban, price_date=price_date)
        return result

    def get_holding_of_iban_date(self, iban, price_date):

        result = self._select_holding_data(iban=iban, price_date=price_date)
        return result

    def get_max_previous_date_of_holding(self, iban, price_date):

        # HOLDING previous entry
        clause = ' ' + declm.DB_price_date + ' < ' + \
            '"' + price_date.strftime("%Y-%m-%d") + '"'
        result = self.db.select_scalar(declm.HOLDING, f"MAX({declm.DB_price_date})", iban=iban, clause=clause)
        return result

    def get_balance_of_holding_dict(self, iban: str, price_date: str) -> list[dict]:

        fields = [declm.DB_total_amount_portfolio, declm.DB_amount_currency]
        result = self.db.select_table(declm.HOLDING, fields, result_dict=True, iban=iban, price_date=price_date)
        return result

    def get_balance_of_holding(self, iban: str, price_date: str) -> Decimal:

        result = self.db.select_scalar(
            declm.HOLDING,
            declm.DB_total_amount_portfolio,
            iban=iban,
            price_date=price_date,
            default=0
        )
        return result

    def get_max_price_date_of_all_holding(self):

        result = self.db.select_scalar(declm.HOLDING, f"MAX({declm.DB_price_date})")
        return result

    def get_max_price_date_of_holding(self, iban):

        result = self.db.select_scalar(declm.HOLDING, f"MAX({declm.DB_price_date})", iban=iban)
        return result

    def select_holding_total(
            self,
            *,
            period: tuple):
        return self._select_holding_all_total(period=period)

    def select_holding_total_of_iban(
            self,
            *,
            iban: str,
            period: tuple):
        return self._select_holding_all_total(iban=iban, period=period)

    def get_isin_dict_of_iban(
        self,
        *,
        iban: str,
        period: tuple,
    ) -> Dict:
        return self.db.select_dict(
            declm.HOLDING_VIEW, declm.DB_ISIN, declm.DB_name, iban=iban, period=period, order=declm.DB_name)

    def get_isin_dict(
        self,
        *,
        period: tuple,
    ) -> Dict:
        return self.db.select_dict(
            declm.HOLDING_VIEW, declm.DB_ISIN, declm.DB_name, period=period, order=declm.DB_name)

    def select_holding_data_of_iban(
        self,
        *,
        field_list: Union[str, Iterable[str]],
        iban: str,
        selected_isins: Union[str, Iterable[str]],
        period: tuple
    ) -> List[dict] | List[tuple]:
        return self._select_holding_data(
            field_list=field_list, iban=iban, isin_code=selected_isins, period=period)

    def select_holding_data(
        self,
        *,
        field_list: Union[str, Iterable[str]],
        selected_isins: Union[str, Iterable[str]],
        period: tuple
    ) -> List[dict] | List[tuple]:
        return self._select_holding_data(
            field_list=field_list, isin_code=selected_isins, period=period)

    def select_holding_isins_interval(
        self,
        iban: str,
        comparison_field: str,
        selected_isins: Iterable[str],
        *,
        period: tuple
    ) -> Tuple[Any, Any, list]:
        return self._select_holding_isins_interval(
            iban, comparison_field, selected_isins, period=period)

    def select_holding_view_row(
            self,
            iban: str,
            price_date: str,
            isin_code: str
            ) -> Dict:
        result = self.db.select_table(
                declm.HOLDING_VIEW,
                '*',
                result_dict=True,
                date_name=declm.DB_price_date,
                iban=iban,
                price_date=price_date,
                isin_code=isin_code
                )
        if result:
            return result[0]
        return {}

    def select_holding_view_table_of_iban(
            self,
            *,
            field_list: Union[str, Iterable[str]],
            iban: str,
            period: tuple
            ) -> List[dict]:
        return self.db.select_table(
                declm.HOLDING_VIEW, field_list=field_list, result_dict=True, date_name=declm.DB_price_date,
                iban=iban, period=period)

    def holding_max_date(
        self,
        *,
        to_date: str  # "must be in format YYYY-MM-DDm"
    ):
        return self.db.select_scalar(
                    declm.HOLDING,
                    f"MAX({declm.DB_price_date})",
                    clause=f"{declm.DB_price_date} < ?",
                    clause_vars=(to_date,)
                    )

    def select_holding_table_of_iban(
            self,
            *,
            field_list: Union[str, Iterable[str]],
            iban: str,
            period: tuple
            ) -> List[dict]:
        return self.db.select_table(
                declm.HOLDING, field_list=field_list, result_dict=True, date_name=declm.DB_price_date,
                iban=iban, period=period)

    def insert_holding(self, field_dict: Dict):
        self.db.execute_insert(declm.HOLDING, field_dict)

    def update_total_holding_amount(self, **kwargs) -> None:
        """
        Update the portfolio total amount per price date in batch using MariaDBTables.

        Aggregates total_amount per IBAN and price_date and updates the
        HOLDING table with the calculated totals in a single query.

        Parameters
        ----------
        **kwargs
            Filters passed to `_where_clause()` to restrict the aggregation
            (e.g. iban, period, portfolio).

        Returns
        -------
        None
        """
        # ------------------------------------------------------------
        # Aggregate total_amount per IBAN and price_date
        # ------------------------------------------------------------
        rows = self.db.select_grouped(
            table=declm.HOLDING,
            fields=[
                declm.DB_iban,
                declm.DB_price_date,
                f"SUM({declm.DB_total_amount}) AS total_amount_portfolio"
            ],
            group_by=[declm.DB_iban, declm.DB_price_date],
            **kwargs
        )

        if not rows:
            return  # nothing to update
        # ------------------------------------------------------------
        # Batch update each row using execute_update and _where_clause
        # ------------------------------------------------------------
        for iban, price_date, total_amount_portfolio in rows:
            self.db.execute_update(
                table=declm.HOLDING,
                field_dict={"total_amount_portfolio": total_amount_portfolio},
                iban=iban,
                **{declm.DB_price_date: price_date}
            )

    def update_holding(
            self,
            iban: str,
            price_date: str,
            isin_code: str,
            field_dict: dict,
            ):
        return self.db.execute_update(
            declm.HOLDING, field_dict,
            iban=iban,
            isin_code=isin_code,
            price_date=price_date
            )


class IsinRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_isin_industries(self) -> List:

        result = self.db.select_table_distinct(declm.ISIN, declm.DB_industry)
        return sorted([item[0] for item in result])

    def insert_isin(self, field_dict: Dict):

        self.db.execute_insert(declm.ISIN, field_dict)

    def delete_isin(self, isin_code: str):

        self.db.execute_delete(declm.ISIN, isin_code=isin_code)

    def replace_isin(self, field_dict: Dict):

        self.db.execute_replace(declm.ISIN, field_dict)

    def replace_isin_name_of_isin_code(self, isin_code, name):

        self.db.execute_replace(
            declm.ISIN,
            {
                declm.DB_ISIN: isin_code,
                declm.DB_name: name,
            }
        )

    def exist_isin_isin_code(self, isin_code: str) -> bool:

        return self.db.select_exists(declm.ISIN, isin_code=isin_code)

    def exist_isin_name(self, name: str) -> bool:

        return self.db.select_exists(declm.ISIN, name=name)

    def select_isin_scalar(
        self,
        field: str,
        **kwargs
    ):
        return self.db.select_scalar(declm.ISIN, f"{field}", **kwargs)

    def get_alpha_vantage_tickers(self) -> Dict:

        YAHOO_TO_ALPHA_SUFFIX = {
            ".DE": ".DEX",  # Xetra
            ".F": ".FRK",   # Frankfurt
            ".SG": ".STU",  # Stuttgart
            ".MU": ".MUN",  # München
            ".BE": ".BER",  # Berlin
            ".DU": ".DUS",  # Düsseldorf
            ".HM": ".HAM",  # Hamburg
            ".HA": ".HAN",  # Hannover
        }

        def yahoo_to_alpha_symbol(yahoo_symbol: str) -> str:
            for y_suffix, a_suffix in YAHOO_TO_ALPHA_SUFFIX.items():
                if yahoo_symbol.endswith(y_suffix):
                    return yahoo_symbol.replace(y_suffix, a_suffix)
            return decl.NOT_ASSIGNED

        yahoo_symbols = self.db.select_dict(
            declm.ISIN, declm.DB_name, declm.DB_symbol, origin_symbol=decl.YAHOO, order=declm.DB_name)
        alpha_vantage_symbols = {
            key: yahoo_to_alpha_symbol(value)
            for key, value in yahoo_symbols.items()
            }
        return alpha_vantage_symbols

    def get_name_origin_symbol(self, selected_isins: str | list[str]) -> Dict:

        result = self.db.select_dict(
            declm.ISIN,
            declm.DB_name,
            declm.DB_origin_symbol,
            isin_code=selected_isins
            )
        return result

    def get_names_isin_dict(self):
        return self.db.select_dict(declm.ISIN, declm.DB_name, declm.DB_ISIN, order=declm.DB_name)

    def select_isin_table(
            self,
            field_list: Union[str, Iterable[str]] | None = None,
            **kwargs
            ) -> List[dict]:
        if field_list is None:
            field_list = '*'
        return self.db.select_table(declm.ISIN, field_list=field_list, result_dict=True, order=declm.DB_name, **kwargs)

    def isin_names(self) -> list:

        tuples_list = self.db.select_table(
            declm.ISIN,
            declm.DB_name,
            order=declm.DB_name
            )
        result = [x[0] for x in tuples_list]
        return result

    def isin_names_with_ticker(self, origin_symbol=decl.YAHOO) -> list:

        tuples_list = self.db.select_table(
            declm.ISIN,
            declm.DB_name,
            clause=f"{declm.DB_symbol} != ?",
            clause_vars=('NA',),
            order=declm.DB_name,
            origin_symbol=origin_symbol
            )
        result = [x[0] for x in tuples_list]
        return result

    def isin_with_ticker(self) -> Dict:

        result = self.db.select_dict(
            declm.ISIN,
            declm.DB_name,
            declm.DB_ISIN,
            clause=f"{declm.DB_symbol} != ?",
            clause_vars=('NA',),
            order=declm.DB_name
            )
        return result

    def symbol_of_isin_not_assigned(self, isin: str) -> bool:

        return self.db.select_exists(declm.ISIN, iisin_code=isin, symbol=decl.NOT_ASSIGNED)

    def get_isin_of_name(self, name: str) -> str:

        result = self.db.select_scalar(declm.ISIN, declm.DB_ISIN, name=name)
        return result

    def get_name_of_isin_code(self, isin_code: str):

        result = self.db.select_scalar(declm.ISIN, declm.DB_name, isin_code=isin_code)
        return result

    def get_names_of_isin_codes(self, isin_code: str | list[str]) -> list[tuple]:

        result = self.db.select_scalar(declm.ISIN, declm.DB_name, isin_code=isin_code)
        return result

    def get_isin_symbol_data(self, isin_code
                             ) -> Dict:

        result = self.select_isin_table(
            field_list=[declm.DB_symbol, declm.DB_exchange, declm.DB_currency,
                        declm.DB_origin_symbol, declm.DB_last_check],
            isin_code=isin_code,
            clause=f"""{declm.DB_symbol} != '{decl.NOT_ASSIGNED}'"""        
            )
        if result:
            return result[0]
        return {}


class LedgerCoaRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def exist_ledger_coa_with_iban(self, iban):

        return self.db.select_exists(declm.LEDGER_COA, iban=iban)

    def exist_ledger_coa_with_account(self, account):

        return self.db.select_exists(declm.LEDGER_COA, account=account)

    def insert_ledger_coa(self, field_dict):

        self.db.execute_insert(declm.LEDGER_COA, field_dict)

    def replace_ledger_coa(self, field_dict):

        self.db.execute_replace(declm.LEDGER_COA, field_dict)

    def delete_ledger_coa(self, account):

        self.db.execute_delete(declm.LEDGER_COA, account=account)

    def count_ledger_coa(self, **kwargs) -> int:

        return self.db.select_scalar(declm.LEDGER_COA, 'COUNT(*)', **kwargs)

    def get_account_of_iban(self, iban: str) -> str:

        result = self.db.select_scalar(declm.LEDGER_COA, declm.DB_account, iban=iban)
        return result

    def get_ledger_coa_names_with_iban(self) -> Dict:

        clause = f"{declm.DB_iban} != '{decl.NOT_ASSIGNED}'"
        return self.db.select_dict(declm.LEDGER_COA, declm.DB_iban, declm.DB_name, clause=clause)

    def get_name_of_account(self, account: str) -> str:

        result = self.db.select_scalar(declm.LEDGER_COA, declm.DB_name, account=account)
        return result

    def get_account_of_name(self, name: str) -> str:

        result = self.db.select_scalar(declm.LEDGER_COA, declm.DB_account, name=name)
        return result

    def get_contra_account_of_account(self, account: str) -> str:

        result = self.db.select_scalar(declm.LEDGER_COA, declm.DB_contra_account, account=account)
        return result

    def get_iban_of_account(self, account) -> str:

        result = self.db.select_scalar(declm.LEDGER_COA, declm.DB_iban, account=account)
        if result == decl.NOT_ASSIGNED:
            return None
        return result

    def get_ledger_coa(self) -> List[Dict]:

        result = self.db.select_table(
            declm.LEDGER_COA,
            declm.TABLE_FIELDS[declm.LEDGER_COA],
            result_dict=True
            )
        return result

    def get_ledger_coa_of_account(self, account):

        result = self.db.select_table(
            declm.LEDGER_COA,
            '*',
            result_dict=True,
            account=account
             )
        if result:
            return result[0]
        return {}

    def get_all_accounts(self) -> List[Tuple]:

        return self.db.select_table(
            declm.LEDGER_COA,
            [declm.DB_account, declm.DB_name],
            order=declm.DB_account
            )

    def opening_balance_account(self) -> str:

        result = self.db.select_scalar(
            declm.LEDGER_COA,
            declm.DB_account,
            opening_balance_account=True
        )
        return result

    def get_balance_accounts(self) -> List[Dict]:

        field_list = [declm.DB_account, declm.DB_name, declm.DB_iban, declm.DB_portfolio,
                      declm.DB_asset_accounting]
        result = self.db.select_table(
            declm.LEDGER_COA,
            field_list,
            order=declm.DB_account,
            result_dict=True
            )
        return result

    def get_balance_account_of_iban(self, iban: str) -> Dict:

        field_list = [declm.DB_account, declm.DB_portfolio, declm.DB_asset_accounting]
        result = self.db.select_table(
            declm.LEDGER_COA,
            field_list,
            result_dict=True,
            iban=iban
            )
        if result:
            return result[0]
        return {}

    def get_balance_assets(self) -> List[Dict]:

        field_list = [declm.DB_account, declm.DB_name, declm.DB_iban, declm.DB_portfolio,
                      declm.DB_asset_accounting]
        result = self.db.select_table(
            declm.LEDGER_COA,
            field_list,
            order=declm.DB_account,
            result_dict=True,
            asset_accounting=True
            )
        return result

    def is_asset_accounting(self, account: str) -> bool:

        result = self.db.select_scalar(
            declm.LEDGER_COA,
            declm.DB_asset_accounting,
            account=account
            )
        return result

    def download_not_activated(self, iban: str) -> bool:

        result = self.db.select_exists(
           declm.LEDGER_COA,
           iban=iban,
           download=False
           )
        return result


class LedgerDailyBalanceRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_ledger_daily_balance_account_name(self) -> Dict:

        result = self.db.select_table_distinct(declm.LEDGER_DAILY_BALANCE, declm.DB_account)
        accounts = tuple(account for (account,) in result)
        if accounts:
            return self.db.select_dict(declm.LEDGER_COA, declm.DB_account, declm.DB_name, **{declm.DB_account: accounts})
        else:
            return {}

    def delete_ledger_daily_balance(self, accounts_to_delete):

        self.db.execute_delete(
            declm.LEDGER_DAILY_BALANCE,
            **{declm.DB_account: accounts_to_delete}
            )

    def delete_ledger_daily_balance_in_period(self, accounts_to_delete, period):

        self.db.execute_delete(
            declm.LEDGER_DAILY_BALANCE,
            **{declm.DB_account: accounts_to_delete},
            period=period,
            date_name=declm.DB_entry_date,
            )


    def replace_ledger_daily_balance(self, account: str, entry_date: str, balance: Decimal):

        self.db.execute_replace(
            declm.LEDGER_DAILY_BALANCE,
            {declm.DB_account: account, declm.DB_entry_date: entry_date, declm.DB_balance: balance}
            )

    def get_daily_balance(self, account: str, entry_date: str) -> Decimal:

        result = self.db.select_scalar(
            declm.LEDGER_DAILY_BALANCE,
            declm.DB_balance,
            account=account,
            entry_date=entry_date
            )
        return result


class LedgerDeleteRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def insert_ledger_delete(self, field_dict):

        self.db.execute_insert(declm.LEDGER_DELETE, field_dict)


class LedgerStatementRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_statement_of_ledger(self, id_no: str, status: str) -> Dict:

        result = self.db.select_table(
            declm.LEDGER_STATEMENT, '*', result_dict=True, id_no=id_no, status=status)
        if result:
            ledger_statement = result[0]
            result = self.db.select_table(
                declm.STATEMENT,
                '*',
                result_dict=True,
                iban=ledger_statement[declm.DB_iban],
                entry_date=ledger_statement[declm.DB_entry_date],
                counter=ledger_statement[declm.DB_counter]
                )
            if result:
                return result[0]
        return {}

    def get_ledger_statement_data(self, id_no: int, status: str) -> Dict:

        result = self.db.select_table(
            declm.LEDGER_STATEMENT,
            '*',
            result_dict=True,
            id_no=id_no,
            status=status
            )
        if result:
            return result[0]
        return {}

    def delete_ledger_statement_with_idno_status(self, id_no, status):

        self.db.execute_delete(
            declm.LEDGER_STATEMENT,
            id_no=id_no,
            status=status
            )

    def delete_ledger_statement_id_no(self, id_no):

        self.db.execute_delete(
            declm.LEDGER_STATEMENT,
            id_no=id_no,
            )

    def insert_ledger_statement(self, ledger_statement: Dict):

        self.db.execute_insert(declm.LEDGER_STATEMENT, ledger_statement)

    def exist_ledger_statement(self, iban: str, entry_date: str, counter: int) -> bool:

        return self.db.select_exists(
            declm.LEDGER_STATEMENT,
            iban=iban,
            entry_date=entry_date,
            counter=counter
            )

    def exist_ledger_statement_with_status(self, iban: str, entry_date: str, counter: int, status: str) -> bool:

        return self.db.select_exists(
            declm.LEDGER_STATEMENT,
            iban=iban,
            entry_date=entry_date,
            counter=counter,
            status=status
            )

    def exist_ledger_statement_with_id_no_and_status(self, id_no, status) -> bool:

        return self.db.select_exists(declm.LEDGER_STATEMENT, id_no=id_no, status=status)

    def max_entry_date_of_ledger_statement(self, iban):

        result = self.db.select_scalar(
            declm.LEDGER_STATEMENT,
            f"MAX({declm.DB_entry_date})",
            iban=iban
            )
        return result


class LedgerRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def ledger_is_not_empty(self):    

        return self.db.select_exists(declm.LEDGER)

    def get_ledgers_via_statement(self, search_dict: Dict) -> list[Dict]:    
        """
        get ledger rows via (partial) values of statement columns
        """
        sql = f"""
            SELECT DISTINCT l.*
            FROM ledger l
            JOIN ledger_statement ls 
                ON l.id_no = ls.id_no AND  ls.entry_date LIKE "%{search_dict[declm.DB_entry_date]}%"
            JOIN statement s 
                ON s.iban = ls.iban
               AND s.iban LIKE "%{search_dict[declm.DB_iban]}%"  
               AND s.entry_date = ls.entry_date
               AND s.counter = ls.counter
            WHERE 1=1        
        """
        conditions = []
        vars_ = []
    
        for field, value in search_dict.items():
            if field not in [declm.DB_iban, declm.DB_entry_date]:
                if value not in ['0', '']:
                    # CAST(`entry_date` AS CHAR)
                    conditions.append(f"s.{field} LIKE %s")
                    vars_.append(f"%{value}%")  # Teilstring-Suche
    
        if conditions:
            sql = sql + " AND " + " AND ".join(conditions)       
        result =  self.db.executor.execute(sql, vars_, result_dict=True)
        return result

    def get_ledgers_of_search(self, search_dict):    
        """
        get ledger rows via (partial) values of ledger columns
        """
    
        conditions = []
        vars_ = []
    
        for field, value in search_dict.items():
            if value not in ['0', '']:
                conditions.append(f"{field} LIKE %s")
                vars_.append(f"%{value}%")  # Teilstring-Suche
    
        if conditions:
            where_clause = " AND ".join(conditions)
            sql = f"SELECT * FROM ledger_view WHERE {where_clause}"
    
            result = self.db.executor.execute(sql, vars_, result_dict=True)
            return result
        return []

    def get_contra_account_of_posting_text(self, statement):
        """
        Select  contra account from the corresponding ledger row of a previous statement with the same posting_text.
        """
        sql = f"""
            SELECT
                CASE
                    WHEN status="{statement[declm.DB_status]}" THEN l.debit_account
                    ELSE l.credit_account
                END AS account
            FROM ledger_statement ls
            JOIN ledger l
                ON l.id_no = ls.id_no
            JOIN (
                SELECT s_old.iban, s_old.entry_date, s_old.counter
                FROM statement s_old
                WHERE s_old.posting_text = "{statement[declm.DB_posting_text]}"
                AND s_old.entry_date < "{statement[declm.DB_entry_date]}"
                and s_old.iban = "{statement[declm.DB_iban]}"
                ORDER BY s_old.entry_date DESC
                LIMIT 1
            ) s_match
            ON ls.iban = s_match.iban
            AND ls.entry_date = s_match.entry_date
            AND ls.counter = s_match.counter;
        """
        result = self.db.executor.execute(sql)
        if result:
            return result[0][0]
        return decl.NOT_ASSIGNED

    def select_ledger_statement_missed(
        self,
        period: tuple
    ) -> tuple[list[int], list[int]]:
        """
        Return ledger entry IDs that have no corresponding statement entries
        within the given period.

        The result is separated into credit and debit ledger IDs.
        """

        # ------------------------------------------------------------
        # WHERE clause for date filtering
        # ------------------------------------------------------------
        where_sql, vars_ = self.db._where_clause(
            date_name=declm.DB_entry_date,
            period=period
        )

        # ------------------------------------------------------------
        # Base SQL template
        # ------------------------------------------------------------
        sql_template = f"""
            WITH eligible_ledger AS (
                SELECT
                    l.id_no,
                    {{account_field}} AS account
                FROM ledger l
                JOIN ledger_coa c
                  ON {{account_field}} = c.account
                 AND c.download = 1
                 AND c.portfolio = 0
                {where_sql}
            )
            SELECT el.id_no
            FROM eligible_ledger el
            WHERE NOT EXISTS (
                SELECT 1
                FROM ledger_statement s
                WHERE s.id_no = el.id_no
                  AND s.status = ?
            )
        """

        # ------------------------------------------------------------
        # Debit side
        # ------------------------------------------------------------
        debit_ids = [
            row[0]
            for row in self.db.select_cte(
                sql=sql_template.format(account_field="l.debit_account"),
                vars_=vars_ + (decl.DEBIT,),
                fields=("id_no",),
            )
        ]

        # ------------------------------------------------------------
        # Credit side
        # ------------------------------------------------------------
        credit_ids = [
            row[0]
            for row in self.db.select_cte(
                sql=sql_template.format(account_field="l.credit_account"),
                vars_=vars_ + (decl.CREDIT,),
                fields=("id_no",),
            )
        ]

        return credit_ids, debit_ids

    def get_new_id_no_of_year(self, entry_date):

        entry_date = date_days.convert_to_date(entry_date)
        from_id_no = entry_date.year * 1000000
        to_id_no = (entry_date.year + 1) * 1000000
        clause = ' '.join([declm.DB_id_no, ">", str(from_id_no), 'AND', declm.DB_id_no, "<", str(to_id_no)])
        max_id_no = self.db.select_scalar(
            declm.LEDGER,
            f"MAX({declm.DB_id_no})",
            clause=clause
            )
        if max_id_no:
            id_no = max_id_no + 1
        else:
            id_no = from_id_no + 1
        return id_no

    def get_account_of_creditor_id(self, iban, period, creditor_id):

        return self.select_sepa_fields_in_statement(
            iban,
            period=period,
            creditor_id=creditor_id
            )

    def get_account_of_debitor_id(self, iban, period, debitor_id):

        return self.select_sepa_fields_in_statement(
            iban,
            period=period,
            debitor_id=debitor_id
            )

    def get_account_of_mandate_id(self, iban, period, mandate_id):

        return self.select_sepa_fields_in_statement(
            iban,
            period=period,
            mandate_id=mandate_id
            )

    def get_account_of_applicant_iban(self, iban, period, applicant_iban):

        return self.select_sepa_fields_in_statement(
            iban,
            period=period,
            applicant_iban=applicant_iban
            )

    def get_account_of_applicant_name(self, iban, period, applicant_name):

        return self.select_sepa_fields_in_statement(
            iban,
            period=period,
            applicant_name=applicant_name
            )

    def get_account_of_purpose_wo_identifier(self, iban, period, purpose_wo_identifier):

        return self.select_sepa_fields_in_statement(
            iban,
            period=period,
            clause=f"{declm.DB_purpose_wo_identifier} LIKE ?",
            clause_vars=(f"{purpose_wo_identifier[:20]}%",)
            )

    def select_sepa_fields_in_statement(
        self,
        iban: str,
        clause: str | None = None,
        clause_vars: tuple = (),
        **kwargs
    ) -> str:
        """
        Resolve the corresponding ledger account for a SEPA statement entry.

        Credit statement → debit ledger account
        Debit statement  → credit ledger account

        Parameters
        ----------
        iban : str
            IBAN of the statement account.
        **kwargs
            Filters forwarded to `_where_clause()` (exactly one SEPA field).

        Returns
        -------
        str
            Ledger account number or decl.NOT_ASSIGNED.
        """

        rows = self.db.select_rows(
            table=declm.STATEMENT,
            fields=[declm.DB_iban, declm.DB_entry_date, declm.DB_counter, declm.DB_status],
            order=declm.DB_entry_date,
            date_name=declm.DB_entry_date,
            sort='DESC',
            limit=1,
            result_dict=True,
            iban=iban,
            clause=clause,
            clause_vars=clause_vars,
            **kwargs
        )    

        if not rows:
            return decl.NOT_ASSIGNED

        row = rows[0]

        id_no = self.db.select_scalar(
            declm.LEDGER_STATEMENT,
            declm.DB_id_no,
            iban=row[declm.DB_iban],
            entry_date=row[declm.DB_entry_date],
            counter=row[declm.DB_counter],
            status=row[declm.DB_status]
        )

        if not id_no:
            return decl.NOT_ASSIGNED

        ledger_field = (
            declm.DB_debit_account if row[declm.DB_status] == decl.CREDIT
            else declm.DB_credit_account
        )

        account = self.db.select_scalar(
            declm.LEDGER,
            ledger_field,
            id_no=id_no,
            default=decl.NOT_ASSIGNED
        )

        return account

    def get_sum_of_credits(self, account: str, entry_date: str) -> Decimal:

        period = (entry_date, date(date.today().year, 12, 31))
        result = self.db.select_scalar(
            declm.LEDGER,
            f"SUM({declm.DB_amount})",
            default=0,
            date_name=declm.DB_entry_date,
            period=period,
            credit_account=account)
        return result

    def get_sum_of_debits(self, account: str, entry_date: str) -> Decimal:

        period = (entry_date, date(date.today().year, 12, 31))
        result = self.db.select_scalar(
            declm.LEDGER,
            f"SUM({declm.DB_amount})",
            default=0,
            date_name=declm.DB_entry_date,
            period=period,
            debit_account=account)
        return result

    def update_ledger(self, field_dict, id_no):

        self.db.execute_update(declm.LEDGER, field_dict, id_no=id_no)

    def update_ledger_upload_check(self, id_no):

        clause_upload_check = ' '.join([declm.DB_id_no, "<=", id_no, "AND NOT", declm.DB_upload_check])
        self.db.execute_update(declm.LEDGER, {declm.DB_upload_check: 1}, clause=clause_upload_check)

    def insert_ledger(self, ledger: Dict):

        self.db.execute_insert(declm.LEDGER,  ledger)

    def delete_ledger(self, id_no):

        self.db.execute_delete(declm.LEDGER,  id_no=id_no)

    def select_ledger_totals(
        self,
        *,
        account: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        exclude_account: Optional[str] = None,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Calculate debit sum, credit sum and balance for a ledger account.

        The balance is calculated as:
            credit_sum - debit_sum

        Parameters
        ----------
        account : str
            Ledger account number to calculate totals for.
        from_date : Optional[str]
            Start date (inclusive), format YYYY-MM-DD.
            If None, no lower date bound is applied.
        to_date : Optional[str]
            End date (inclusive), format YYYY-MM-DD.
            If None, no upper date bound is applied.
        exclude_account : Optional[str]
            Ledger account to exclude from the calculation.
            Used to ignore opening balance postings.

        Returns
        -------
        Tuple[Decimal, Decimal, Decimal]
            A tuple containing:
            - debit_sum  : Total debit amount for the account
            - credit_sum : Total credit amount for the account
            - balance    : Net balance (credit - debit)
        """

        # Base condition: account appears on either debit or credit side
        conditions = [
            f"({declm.DB_debit_account} = :account OR {declm.DB_credit_account} = :account)"
        ]

        vars_ = {"account": account}

        # Apply optional date range filters
        if from_date:
            conditions.append(f"{declm.DB_entry_date} >= :from_date")
            vars_["from_date"] = from_date

        if to_date:
            conditions.append(f"{declm.DB_entry_date} <= :to_date")
            vars_["to_date"] = to_date

        # Exclude postings involving a specific account (e.g. opening balance account)
        if exclude_account:
            conditions.append(
                f"NOT ({declm.DB_debit_account} = :exclude OR {declm.DB_credit_account} = :exclude)"
            )
            vars_["exclude"] = exclude_account

        where_sql = " AND ".join(conditions)

        rows = self.db.select_cte(
            sql=f"""
                SELECT
                    SUM(
                        CASE
                            WHEN {declm.DB_debit_account} = :account
                            THEN {declm.DB_amount}
                            ELSE 0
                        END
                    ) AS debit_sum,
                    SUM(
                        CASE
                            WHEN {declm.DB_credit_account} = :account
                            THEN {declm.DB_amount}
                            ELSE 0
                        END
                    ) AS credit_sum,
                    SUM(
                        CASE
                            WHEN {declm.DB_debit_account}  = :account THEN -{declm.DB_amount}
                            WHEN {declm.DB_credit_account} = :account THEN  {declm.DB_amount}
                            ELSE 0
                        END
                    ) AS balance
                FROM {declm.LEDGER}
                WHERE {where_sql}
            """,
            vars_=vars_,
            fields=("debit_sum", "credit_sum", "balance"),
        )

        # Normalize NULL aggregates to Decimal(0)
        if not rows:
            return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

        debit_sum, credit_sum, balance = rows[0]
        return (
            debit_sum or Decimal("0.00"),
            credit_sum or Decimal("0.00"),
            balance or Decimal("0.00"),
        )

    def get_opening_rows(self, account: str, opening_balance_account: str, to_date: str):

        # Determine latest opening balance booking
        opening_rows = self.db.select_cte(
            sql=f"""
                SELECT
                    l.{declm.DB_entry_date} AS opening_date,
                    SUM(
                        CASE
                            WHEN l.{declm.DB_debit_account}  = :account THEN -l.{declm.DB_amount}
                            WHEN l.{declm.DB_credit_account} = :account THEN  l.{declm.DB_amount}
                            ELSE 0
                        END
                    ) AS opening_balance
                FROM {declm.LEDGER} l
                WHERE (
                        l.{declm.DB_debit_account}  = :opening_account
                     OR l.{declm.DB_credit_account} = :opening_account
                )
                  AND (
                        l.{declm.DB_debit_account}  = :account
                     OR l.{declm.DB_credit_account} = :account
                )
                  AND l.{declm.DB_entry_date} <= :to_date
                GROUP BY l.{declm.DB_entry_date}
                ORDER BY l.{declm.DB_entry_date} DESC
                LIMIT 1
            """,
            vars_={
                "account": account,
                "opening_account": opening_balance_account,
                "to_date": to_date,
            },
            fields=("opening_date", "opening_balance"),
        )
        return opening_rows

    def get_ledger_rows(self, account, opening_account):

        sql = """
            SELECT
                l.entry_date,
                CASE
                    WHEN l.credit_account = ? THEN ?
                    ELSE ?
                END AS status,
                l.amount
            FROM ledger l
            WHERE (
                    l.credit_account = ?
                AND l.debit_account != ?
            )
               OR (
                    l.debit_account = ?
                AND l.credit_account != ?
            )
            ORDER BY l.entry_date DESC
            LIMIT 1
        """

        rows = self.db.select_cte(
            sql=sql,
            vars_=(
                account, decl.CREDIT, decl.DEBIT,
                account, opening_account,
                account, opening_account,
                ),
            fields=(declm.DB_entry_date, declm.DB_status, declm.DB_amount),
            )
        if not rows:
            return {}

        entry_date, status, amount = rows[0]

        return {
            declm.DB_entry_date: entry_date,
            declm.DB_status: status,
            declm.DB_amount: amount,
        }

    def get_ledger_of_statement(
            self, iban: str, entry_date: str, counter: int) -> Dict:

        ledger_id_no = self.db.select_scalar(
            declm.LEDGER_STATEMENT,
            declm.DB_id_no,
            iban=iban,
            entry_date=entry_date,
            counter=counter
            )
        if ledger_id_no:
            ledger_row = self.db.select_table(
                declm.LEDGER,
                ['*'],
                result_dict=True,
                id_no=ledger_id_no)
            if ledger_row:
                return ledger_row[0]
        return {}


class LedgerViewRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_ledger_view(self, id_no):

        result = self.db.select_table(
                    declm.LEDGER_VIEW, '*', result_dict=True, id_no=id_no)
        if result:
            return result[0]
        return {}

    def get_ledger_view_in_period(self, period):

        result = self.db.select_table(
            declm.LEDGER_VIEW,
            declm.TABLE_FIELDS[declm.LEDGER_VIEW],
            date_name=declm.DB_entry_date,
            result_dict=True,
            period=period,
        )
        return result

    def get_ledger_bank_statement(self, field_list, account, period):

        result = self.db.select_table(
            declm.LEDGER_VIEW,
            field_list,
            clause=f"({declm.DB_credit_account} = ? OR {declm.DB_debit_account} = ?)",
            clause_vars=(account, account),
            date_name=declm.DB_entry_date,
            result_dict=True,
            period=period,
            bank_statement_checked=False
        )
        return result

    def get_ledger_account(self, field_list, account, period):

        result = self.db.select_table(
            declm.LEDGER_VIEW,
            field_list,
            clause=f"({declm.DB_credit_account} = ? OR {declm.DB_debit_account} = ?)",
            clause_vars=(account, account),
            date_name=declm.DB_entry_date,
            result_dict=True,
            period=period,
        )
        return result

    def get_ledger_upload_check(self, period):

        result = self.db.select_table(
            declm.LEDGER_VIEW,
            declm.TABLE_FIELDS[declm.LEDGER_VIEW],
            result_dict=True,
            date_name=declm.DB_entry_date,
            period=period,
            upload_check=False,
            origin=decl.ORIGIN
            )
        return result


class MariaDBRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_field_values_of_table_in_period(
            self,
            table: str,
            field_name: str,
            date_name: str,
            period: Tuple
            ) -> list[Tuple]:

        select_field_values = self.db.select_table_distinct(
            table, field_name, date_name=date_name, period=period)
        return select_field_values

    def get_field_values_of_table(
            self,
            table: str,
            field_name: str,
            ) -> list[Tuple]:

        select_field_values = self.db.select_table_distinct(table, field_name)
        return select_field_values

    def rollback_transaction(self):

        self.db.executor.execute("ROLLBACK;")

    def start_transaction(self):

        self.db.executor.execute("START TRANSACTION;")

    def destroy_connection(self):

        self.db.destroy_connection()

    def get_database_name(self):

        result = self.db.execute("SELECT DATABASE()")
        return result[0][0]

    def commit(self):

        self.db.executor.execute('COMMIT;')

    def iban_exists(self, table: str, bank_code: str,) -> bool:
        """
        Check whether at least one IBAN containing the given bank code exists.

        Parameters
        ----------
        table : str
            Table or view name.
        bank_code : str
            Bank code fragment to search for within the IBAN.
        **kwargs
            Additional WHERE filters passed to `_where_clause()`.

        Returns
        -------
        bool
            True if at least one matching IBAN exists, otherwise False.
        """
        return self.db.select_exists(
            table=table,
            clause=f"{declm.DB_iban} LIKE ?",
            clause_vars=(f"%{bank_code}%",)
            )


class PricesRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def count_prices(self) -> int:

        return self.db.select_scalar(declm.PRICES, 'COUNT(*)')

    def get_isin_names(self) -> List[Dict]:

        isin_names = self.db.select_table_distinct(
            declm.PRICES_ISIN_VIEW, [declm.DB_ISIN, declm.DB_name], result_dict=True, order=declm.DB_name)
        return isin_names

    def get_close_price(
        self,
        isin_code: str,
        price_date: str  # "must be in format YYYY-MM-DDm"
    ):
        return self.db.select_scalar(declm.PRICES_ISIN_VIEW, declm.DB_close, isin_code=isin_code, price_date=price_date)

    def get_selected_price_data(
            self, selected_fields: list[str], selected_isins: list[str], period: tuple
    ) -> list[dict]:

        result = self.db.select_table(
            declm.PRICES_ISIN_VIEW,
            [declm.DB_name, declm.DB_price_date] + selected_fields,
            order=declm.DB_name,
            result_dict=True,
            isin_code=selected_isins,
            period=period)
        return result

    def get_prices_of_period(
            self, isin_code: str, period: tuple
    ) -> list[dict]:

        result = self.db.select_table(
            declm.PRICES,
            [declm.DB_price_date, declm.DB_open, declm.DB_high, declm.DB_low, declm.DB_close, declm.DB_volume],
            result_dict=True,
            order=declm.DB_price_date,
            isin_code=isin_code,
            period=period
            )
        return result

    def prices_max_date_of_isin(self, isin_code: str) -> str:

        result = self.db.select_scalar(
            declm.PRICES,
            f"MAX({declm.DB_price_date})",
            isin_code=isin_code
            )
        return result

    def replace_corporate_actions_data(self, actions_list: list[dict]):

        for actions in actions_list:
            self.db.execute_replace(declm.CORPORATE_ACTIONS, actions)

    def import_prices_batch(self, dataframe) -> None:
        """
        Import a pandas DataFrame into the prices table.
        """
    
        if dataframe.empty:
            return None
    
        dataframe = dataframe.reset_index()
    
        tmp = tempfile.mktemp(suffix=".csv")
    
        dataframe.to_csv(
            tmp,
            index=False,
        )
    
        tmp = tmp.replace("\\", "/")
    
        fields = [
            "@dummy",
            declm.DB_ISIN,
            declm.DB_price_date,
            declm.DB_open,
            declm.DB_high,
            declm.DB_low,
            declm.DB_close,
            declm.DB_adjclose,
            declm.DB_volume,
            declm.DB_origin,
            declm.DB_symbol_prices,
        ]
    
        try:
            self.db.import_local_infile(
                tmp,
                fields,
            )
    
            return None
    
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


class SelectionRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    """
    Helper class for storing and retrieving last used selection values
    of selection forms in the SELECTION table.
    """

    def selection_get(self, selection_name: str) -> Dict | list:
        """
        Retrieve the last used selection data for a given selection form.

        Parameters
        ----------
        selection_name : str
            Name of the selection form.

        Returns
        -------
        dict | list
            Dictionary of last used selection values, or list of last
            selected check button names. Returns empty dict if not found.
        """
        selection = self.db.select_scalar(declm.SELECTION, declm.DB_data, name=selection_name)
        if selection:
            return json.loads(selection)
        return {}

    def selection_put(self, selection_name: str, selection_dict: dict | list) -> None:
        """
        Store the last used selection data for a selection form in JSON format.

        Parameters
        ----------
        selection_name : str
            Name of the selection form.
        selection_dict : dict | list
            Dictionary of selection values or list of check button names to store.
        """
        selection_data = json.dumps(selection_dict)
        self.db.execute_replace(
            declm.SELECTION,
            {declm.DB_name: selection_name, declm.DB_data: selection_data}
        )


class ShelvesRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def shelve_delete(self, bank_code):

        self.db.execute_delete(declm.SHELVES, code=bank_code)

    def shelve_del_key(
        self,
        shelve_name: str,
        key: str | list[str],
    ) -> None:
        return self.db.shelve_del_key(shelve_name, key)

    def shelve_get_key(
        self,
        shelve_name: str,
        key: str | list[str],
        none: bool = True
    ) -> Dict | Any:
        result = self.db.shelve_get_key(shelve_name, key)
        return result

    def shelve_put_key(
            self,
            shelve_name: str,
            data: tuple | list[tuple]
            ) -> None:
        return self.db.shelve_put_key(shelve_name, data)

    def shelve_put_bank_data(self, bank_code: str, field_dict: dict):

        data = [(decl.KEY_BANK_CODE, bank_code),
                (decl.KEY_BANK_NAME, field_dict[decl.KEY_BANK_NAME]),
                (decl.KEY_USER_ID,  field_dict[decl.KEY_USER_ID]),
                (decl.KEY_PIN,  field_dict[decl.KEY_PIN]),
                (decl.KEY_BIC,  field_dict[decl.KEY_BIC]),
                (decl.KEY_SERVER,  field_dict[decl.KEY_SERVER]),
                (decl.KEY_IDENTIFIER_DELIMITER, field_dict[decl.KEY_IDENTIFIER_DELIMITER]),
                (decl.KEY_DOWNLOAD_ACTIVATED, field_dict[decl.KEY_DOWNLOAD_ACTIVATED]),
                (decl.KEY_LOGIN_ONLINE_BANKING, field_dict[decl.KEY_LOGIN_ONLINE_BANKING]),]
        self.shelve_put_key(bank_code, data)

    def shelve_get_keys(self, bank_code):

        return self.shelve_get_key(bank_code, decl.SHELVE_KEYS, none=False)

    def shelve_get_server(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_SERVER)

    def shelve_get_bank(self, bank_code):

        shelve_keys = [decl.KEY_USER_ID, decl.KEY_PIN, decl.KEY_BIC, decl.KEY_BPD, decl.KEY_SERVER,
                       decl.KEY_SECURITY_FUNCTION]
        return self.shelve_get_key(bank_code, shelve_keys, none=False)

    def shelve_get_login_data(self, bank_code):

        shelve_keys = [decl.KEY_BANK_NAME, decl.KEY_USER_ID, decl.KEY_PIN, decl.KEY_BIC, decl.KEY_SERVER,
                       decl.KEY_IDENTIFIER_DELIMITER, decl.KEY_DOWNLOAD_ACTIVATED, decl.KEY_LOGIN_ONLINE_BANKING,]
        return self.shelve_get_key(bank_code, shelve_keys)

    def shelve_get_pin_length(self, bank_code):

        return self.shelve_get_key(bank_code, [decl.KEY_MAX_PIN_LENGTH, decl.KEY_MIN_PIN_LENGTH])

    def shelve_get_loging_online_banking(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_LOGIN_ONLINE_BANKING)

    def shelve_get_tan_max_length(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_MAX_TAN_LENGTH)

    def shelve_get_shelve_keys(self, bank_code):

        return self.shelve_get_key(bank_code, decl.SHELVE_KEYS)

    def shelve_get_upd(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_UPD)

    def shelve_get_version_transaction(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_VERSION_TRANSACTION)

    def shelve_get_download_activated(self, bank_code):

        result = self.shelve_get_key(bank_code, decl.KEY_DOWNLOAD_ACTIVATED)
        return result

    def shelve_get_twostep(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_TWOSTEP)

    def shelve_get_accounts(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_ACCOUNTS)

    def shelve_get_identifier_delimiter(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_IDENTIFIER_DELIMITER)

    def shelve_get_security_function(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_SECURITY_FUNCTION)

    def shelve_get_bank_name(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_BANK_NAME)

    def shelve_get_version_transaction_allowed(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_VERSION_TRANSACTION_ALLOWED)

    def shelve_get_tan_required(self, bank_code):

        return self.shelve_get_key(bank_code, decl.KEY_TAN_REQUIRED)

    def listbank_codes(self) -> list[str]:
        """
        List all bank codes from the SHELVES table.

        Returns
        -------
        list[str]
            List of bank codes.
        """
        result = self.db.select_table(declm.SHELVES, declm.DB_code)
        return list(chain.from_iterable(result))

    def dictbank_names(self) -> Dict[str, str]:
        """
        Map bank codes to customized bank names (fall back to code if name missing).

        Returns
        -------
        dict[str, str]
            Dictionary {bank_code: bank_name}.
        """
        return {
            code: self.shelve_get_key(code, decl.KEY_BANK_NAME) or code
            for code in self.listbank_codes()
        }

    def get_bank_owner_accounts(self) -> Dict:
        bank_owner_account = {}
    
        for bank_code in self.dictbank_names():
            accounts = self.shelve_get_accounts(bank_code)
            if not accounts:
                continue
    
            product_names = [acc[decl.KEY_ACC_PRODUCT_NAME] for acc in accounts]
            if len(product_names) == len(set(product_names)):
                continue
    
            owners = defaultdict(list)
            for acc in accounts:
                owner = acc.get(decl.KEY_ACC_OWNER_NAME) or bank_code
                acc[decl.KEY_ACC_OWNER_NAME] = owner
                owners[owner].append(acc)
    
            bank_owner_account[bank_code] = dict(owners)
    
        return bank_owner_account


class StatementRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_statements_of_amount(self, iban: str, period: Tuple, status: str, amount: Decimal) -> List[Dict]:

        result = self.db.select_table(
            declm.STATEMENT,
            '*',
            result_dict=True,
            date_name=declm.DB_entry_date,
            period=period,
            iban=iban,
            status=status,
            amount=amount
        )
        return result

    def get_statements_with_amount(self, iban: str, period: Tuple) -> List[Dict]:

        result = self.db.select_table(
            declm.STATEMENT,
            '*',
            result_dict=True,
            date_name=declm.DB_entry_date,
            period=period,
            iban=iban,
            clause=' '.join([declm.DB_amount, '!=', str(0)])
        )
        return result

    def insert_statement(self, statement: Dict):

        self.db.execute_insert(declm.STATEMENT, statement)

    def get_last_statement_of_iban_period(self, iban: str, period: str) -> Dict:

        result = self.db.select_last_row(
            declm.STATEMENT,
            [declm.DB_closing_balance, declm.DB_closing_status, declm.DB_closing_entry_date],
            order=[declm.DB_entry_date, declm.DB_counter],
            date_name=declm.DB_entry_date,
            result_dict=True,
            iban=iban,
            period=period,
        )
        return result

    def get_last_statement_of_iban(self, iban):

        statement_row = self.db.select_last_row(
            table=declm.STATEMENT,
            fields=(declm.DB_closing_balance, declm.DB_closing_status, declm.DB_closing_entry_date),
            order=[declm.DB_entry_date, declm.DB_counter],
            iban=iban,
        )
        return statement_row

    def exists_statements_of_iban(self, iban):

        return self.db.select_exists(declm.STATEMENT, iban=iban)

    def exists_statement_row(self, iban, entry_date, counter):

        return self.db.select_exists(declm.STATEMENT, iban=iban, entry_date=entry_date, counter=counter)

    def exist_iban_with_bank_reference(self, iban, bank_reference):

        return self.db.select_exists(declm.STATEMENT, iban=iban, bank_reference=bank_reference)

    def get_statements(self, fields: str | list[str] | tuple[str, ...], iban: str, period: tuple) -> list[dict]:

        result = self.db.select_table(
                declm.STATEMENT,
                fields,
                result_dict=True,
                date_name=declm.DB_date,
                iban=iban,
                period=period)
        return result

    def get_statement(self, iban: str, entry_date: str, counter: int) -> Dict:

        result = self.db.select_table(
            declm.STATEMENT,
            '*',
            result_dict=True,
            iban=iban,
            entry_date=entry_date,
            counter=counter
            )
        if result:
            return result[0]
        return {}

    def max_entry_date_of_statement(self, iban: str) -> str:

        result = self.db.select_scalar(declm.STATEMENT, f"MAX({declm.DB_entry_date})", iban=iban)
        return result

    def get_balance_of_statement(self, iban, entry_date):

        fields = [declm.DB_counter,
                  declm.DB_closing_status, declm.DB_closing_balance, declm.DB_closing_currency, declm.DB_closing_entry_date,
                  declm.DB_opening_status, declm.DB_opening_balance, declm.DB_opening_currency, declm.DB_opening_entry_date]
        result = self.db.select_table(
            declm.STATEMENT, fields, result_dict=True, date_name=declm.DB_date, iban=iban, entry_date=entry_date, order=declm.DB_counter)
        return result

    def get_statement_copy_to_ledger(self, iban: str, entry_date: str, counter: int) -> Dict:

        statement_row = self.db.select_table(
            declm.STATEMENT,
            [declm.DB_date, declm.DB_amount, declm.DB_status, declm.DB_currency,
             declm.DB_purpose_wo_identifier, declm.DB_applicant_name],
            result_dict=True,
            iban=iban,
            entry_date=entry_date,
            counter=counter)
        if statement_row:
            return statement_row[0]
        return {}

    def get_statement_without_ledger(self,field_list, period) -> List[Dict]:     
        
        if declm.DB_amount in field_list and declm.DB_status not in field_list:
            field_list.append(declm.DB_status)
        if declm.DB_opening_balance in field_list and declm.DB_opening_status not in field_list:
            field_list.append(declm.DB_opening_status)
        if declm.DB_closing_balance in field_list and declm.DB_closing_status not in field_list:
            field_list.append(declm.DB_closing_status)
        field_list = ["s." + item for item in field_list]
        field_list = self.db._normalize_fields(field_list)
        from_date, to_date = period
        sql  = f"""
                SELECT {field_list}
                FROM statement s
                LEFT JOIN ledger_statement ls
                  ON s.{declm.DB_iban} = ls.{declm.DB_iban}
                 AND s.{declm.DB_entry_date} = ls.{declm.DB_entry_date}
                 AND s.{declm.DB_counter} = ls.{declm.DB_counter}
                WHERE ls.iban IS NULL 
                 AND s.{declm.DB_entry_date} >= ?
                 AND s.{declm.DB_entry_date} <= ?
                 AND s.{declm.DB_amount} != 0
            """
        vars_ =   (from_date, to_date)  
        result = self.db.executor.execute(sql, vars_, result_dict=True, compress=True)
        return result

class ServerRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_server_of_bankcode(self, bank_code):

        result = self.db.select_table(declm.SERVER, declm.DB_server, result_dict=True, code=bank_code)
        if result:
            return result[0]
        else:
            return {}

    def count_server(self) -> int:

        return self.db.select_scalar(declm.SERVER, 'COUNT(*)')

    def get_server_codes(self) -> list[str]:

        result = self.db.select_table_distinct(declm.SERVER, declm.DB_code)
        if result:
            return [item[0] for item in result]
        else:
            return []

    def get_server_data(self) -> list[dict]:

        result = self.db.select_table(
            declm.SERVER, field_list=declm.TABLE_FIELDS[declm.SERVER],  result_dict=True)
        return result

    def import_server(self, filename: str) -> None:
        """
        Import server data into the SERVER table.
    
        Notes
        -----
        The CSV contains 28 columns.
        Only the columns 'code' and 'server'
        are imported.
        """
    
        # Create placeholders for unused CSV columns
        csv_columns = [f'@VAR{x}' for x in range(28)]
    
        # Import only required columns
        csv_columns[1] = 'code'
        csv_columns[24] = 'server'
    
        columns = ", ".join(csv_columns)
    
        try:
            # Remove existing records
            self.db.executor.execute(
                f"DELETE FROM {declm.SERVER}"
            )
    
            # Import CSV file
            self.db.execute_load_data(
                filename=filename,
                table=declm.SERVER,
                columns=columns,
            )
    
            # Remove invalid placeholder servers
            cleanup_sql = f"""
                DELETE FROM {declm.SERVER}
                WHERE server = '\\r'
            """
    
            self.db.executor.execute(cleanup_sql)
    
            # Insert additional known servers
            insert_sql = f"""
                INSERT INTO {declm.SERVER}
                SET code = ?, server = ?
            """
    
            for code, (server, *_) in decl.SCRAPER_BANKDATA.items():
                self.db.executor.execute(
                    insert_sql,
                    (code, server),
                )
    
            return None
    
        except Exception as exc:
    
            return exc

class TickersRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_ticker_exchange(self, symbol: str) -> str:

        result = self.db.select_table(declm.TICKERS, declm.DB_exchange, symbol=symbol)
        if result:
            return result[0][0]
        return decl.NOT_ASSIGNED

    def get_yahoo_symbols(self, name) -> list:

        def select_ticker_rows(clause):
            return self.db.select_rows(
                table=declm.TICKERS,
                fields=[declm.DB_symbol, declm.DB_company_name],
                clause=clause
                )

        name_start, name_end = name.split()[0], name.split()[-1]
        if name_start != name_end:
            clause = f"""{declm.DB_company_name} LIKE '{name_start}%' AND {declm.DB_company_name} LIKE '%{name_end}'"""
        else:
            clause = f"""{declm.DB_company_name} LIKE '{name_start}%'"""
        result = select_ticker_rows(clause)

        if not result:
            clause = f"""{declm.DB_company_name} LIKE '{name_start}%'"""
            result = select_ticker_rows(clause)

        return [symbol + "    " + company_name for symbol, company_name in result]

    def get_tickers_data(self) -> list[dict]:

        result = self.db.select_table(
            declm.TICKERS, field_list=declm.TABLE_FIELDS[declm.TICKERS],  result_dict=True)
        return result

    def import_tickers(self, filename):

        sql = f"""
        LOAD DATA LOCAL INFILE '{filename}'
        INTO TABLE tickers
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\r\n'
        (symbol, company_name, exchange)
        SET {declm.DB_ISIN} = 'NA'
        """

        self.db.executor.execute(sql)

    def delete_ticker_with_spaces(self):

        self.db.execute_delete(declm.TICKERS, symbol='')

class TransactionRepository(BaseRepository):

    def __init__(self):
        super().__init__()

    def get_transactions_name_isin_of_iban(self, iban):

        return self.db.select_dict(
            declm.TRANSACTION_VIEW,
            declm.DB_name, declm.DB_ISIN,
            iban=iban,
            order=declm.DB_name
            )

    def exist_transaction(self, iban, isin_code, price_date, counter):

        self.db.select_exists(declm.TRANSACTION, iban=iban, isin_code=isin_code, price_date=price_date, counter=counter)

    def insert_transaction(self, field_dict):

        self.db.execute_insert(declm.TRANSACTION, field_dict)

    def replace_transaction(self, field_dict):

        self.db.execute_replace(declm.TRANSACTION, field_dict)

    def delete_transaction(self, iban, isin_code, price_date, counter):

        self.db.execute_delete(declm.TRANSACTION, iban=iban, isin_code=isin_code, price_date=price_date, counter=counter)

    def get_transaction_name_isin(self) -> Dict:

        return self.db.select_dict(declm.TRANSACTION_VIEW, declm.DB_name, declm.DB_ISIN, order=declm.DB_name)

    def get_iban_of_transactions(self, period):
        return self.db.select_table_distinct(declm.TRANSACTION, declm.DB_iban, period=period)

    def _transaction_base_cte(self, where_sql: str) -> str:
        return f"""
            WITH tx AS (
                SELECT
                    {declm.DB_ISIN},
                    {declm.DB_name},
                    {declm.DB_amount_currency},
                    CASE
                        WHEN {declm.DB_transaction_type} = '{decl.TRANSACTION_DELIVERY}' THEN  pieces
                        WHEN {declm.DB_transaction_type} = '{decl.TRANSACTION_RECEIPT}'  THEN -pieces
                    END AS pieces,
                    CASE
                        WHEN {declm.DB_transaction_type} = '{decl.TRANSACTION_DELIVERY}' THEN  posted_amount
                        WHEN {declm.DB_transaction_type} = '{decl.TRANSACTION_RECEIPT}'  THEN -posted_amount
                    END AS posted_amount
                FROM {declm.TRANSACTION_VIEW}
                {where_sql}
                AND {declm.DB_transaction_type} IN ('{decl.TRANSACTION_DELIVERY}', '{decl.TRANSACTION_RECEIPT}')
            )
        """

    def _transaction_profit_closed_sql(self, where_sql: str) -> str:
        return f"""
            {self._transaction_base_cte(where_sql)}
            SELECT
                {declm.DB_ISIN},
                {declm.DB_name},
                SUM({declm.DB_posted_amount}) AS profit,
                {declm.DB_amount_currency},
                SUM({declm.DB_pieces}) AS pieces
            FROM tx
            GROUP BY {declm.DB_ISIN}, {declm.DB_name}, {declm.DB_amount_currency}
            HAVING SUM({declm.DB_pieces}) = 0
        """

    def transaction_profit_closed(
        self,
        iban: str,
        period: tuple
    ) -> List[Tuple[str, str, Decimal, str, Decimal]]:

        where_sql, vars_ = self.db._where_clause(iban=iban, period=period)
        sql = self._transaction_profit_closed_sql(where_sql)

        return self.db.select_cte(
            sql=sql,
            vars_=vars_,
            fields=[declm.DB_ISIN, declm.DB_name, FN_PROFIT, declm.DB_amount_currency, declm.DB_pieces]
        )

    def transaction_profit_all(
        self,
        iban: str,
        period: tuple
    ) -> List[Tuple[str, str, Decimal, str, Decimal]]:

        where_sql, vars_ = self.db._where_clause(iban=iban, period=period)

        max_price_date = self.db.select_scalar(
            declm.HOLDING, f"MAX({declm.DB_price_date})", iban=iban, period=period
        )
        if max_price_date is None:
            return []

        closed_sql = self._transaction_profit_closed_sql(where_sql)

        holding_sql = f"""
            SELECT
                {declm.DB_ISIN},
                {declm.DB_name},
                ({declm.DB_total_amount} - {declm.DB_acquisition_amount}) AS profit,
                {declm.DB_amount_currency},
                {declm.DB_pieces}
            FROM {declm.HOLDING_VIEW}
            WHERE {declm.DB_price_date} = ?
        """

        sql = f"""
            {closed_sql}
            UNION ALL
            {holding_sql}
        """

        vars_ = vars_ + (str(max_price_date),)

        return self.db.select_cte(
            sql=sql,
            vars_=vars_,
            fields=[declm.DB_ISIN, declm.DB_name, FN_PROFIT, declm.DB_amount_currency, declm.DB_pieces]
        )

    def get_transaction_view_data_of_iban_period(self, fields, iban, period):

        result = self.db.select_table(
                declm.TRANSACTION_VIEW, fields, result_dict=True,
                date_name=declm.DB_price_date, iban=iban, period=period, order=declm.DB_price_date)
        return result

    def get_transaction_data_of_iban(self, iban) -> list[dict]:

        result = self.db.select_table(
            declm.TRANSACTION, field_list=declm.TABLE_FIELDS[declm.TRANSACTION],  result_dict=True, iban=iban)
        return result

    def import_transaction(
        self,
        iban: str,
        filename: str,
    ) -> None:
        """
        Import transaction data into the TRANSACTION table.
        """
    
        columns = f"""
            {declm.DB_price_date},
            {declm.DB_ISIN},
            {declm.DB_counter},
            {declm.DB_pieces},
            {declm.DB_price}
        """
    
        set_clause = f"""
            {declm.DB_iban} = '{iban}',
            {declm.DB_transaction_type} =
                '{decl.TRANSACTION_RECEIPT}',
            {declm.DB_price_currency} = 'EUR',
            {declm.DB_amount_currency} = 'EUR',
            {declm.DB_posted_amount} =
                {declm.DB_price} * {declm.DB_pieces},
            {declm.DB_origin} =
                '{Path(filename).name[-50:]}'
        """
    
        try:
            # Import CSV file
            self.db.execute_load_data(
                filename=filename,
                table=declm.TRANSACTION,
                columns=columns,
                set_clause=set_clause,
                line_terminator="\\n",
            )
    
            # Convert negative transactions
            # into delivery transactions
            normalize_sql = f"""
                UPDATE {declm.TRANSACTION}
                SET
                    {declm.DB_transaction_type} = ?,
                    {declm.DB_counter} =
                        ABS({declm.DB_counter}),
                    {declm.DB_pieces} =
                        ABS({declm.DB_pieces}),
                    {declm.DB_posted_amount} =
                        ABS({declm.DB_posted_amount})
                WHERE {declm.DB_pieces} < 0
            """
    
            self.db.executor.execute(
                normalize_sql,
                (decl.TRANSACTION_DELIVERY,),
            )
    
            return None
    
        except Exception as exc:
    
            return exc

    def get_transaction(self, iban, isin_code, price_date, counter):

        result = self.db.select_table(
            declm.TRANSACTION_VIEW, '*', result_dict=True,
            iban=iban, price_date=price_date, isin_code=isin_code, counter=counter
            )
        if result:
            return result[0]
        else:
            return {}

    def get_transactions_update_acquisition(self, iban, price_date, isin_code):
        """
        Retrieve transaction records for a given ISIN and IBAN, filtered up to a specified date.

        This query selects the number of pieces and posted amount from the TRANSACTION table,
        restricted to transactions of type RECEIPT. Only records with a price_date less than
        or equal to the provided `price_date` are included.

        Results are ordered in descending order by price_date and counter, ensuring the most
        recent transactions appear first.

        Parameters:
            isin_code (str): The ISIN identifying the financial instrument.
            iban (str): The IBAN identifying the account.
            price_date (date/datetime): Upper bound for transaction price_date filtering.

        Returns:
            list[tuple]: A list of rows containing (pieces, posted_amount).
        """
        return self.db.select_rows(
            table=declm.TRANSACTION,
            fields=[declm.DB_pieces, declm.DB_posted_amount],
            order=[declm.DB_price_date, declm.DB_counter],
            sort='DESC',
            transaction_type=decl.TRANSACTION_RECEIPT,
            isin_code=isin_code,
            iban=iban,
            clause='price_date <= ?',
            clause_vars=(price_date,)
        )

    def get_transactions(self, isin_code, iban, period):
        return self.db.select_rows(
            table=declm.TRANSACTION,
            fields=(
                "price_date",
                "counter",
                "transaction_type",
                "price",
                "pieces",
                "posted_amount"
            ),
            order=[("price_date", "ASC"), ("counter", "ASC")],
            isin_code=isin_code,
            iban=iban,
            period=period
        )

    def get_transactions_before(self, isin_code, iban, until_date):
        return self.db.select_rows(
            table=declm.TRANSACTION,
            fields=("transaction_type", "pieces", "posted_amount", "price"),
            isin_code=isin_code,
            iban=iban,
            clause="price_date < ?",
            clause_vars=(until_date,),
            order=[("price_date", "ASC"), ("counter", "ASC")]
        )

    def check_pieces_consistency_for_iban(self, iban, start_date, end_date):
        """
        For a specific IBAN within a given period, checks
        whether the accumulated pieces from TRANSACTION table
        match the HOLDING table pieces.

        Returns only discrepancies.
        """

        sql = """
            SELECT
                h.iban,
                h.name,
                h.isin_code,
                h.price_date,
                h.pieces AS holding_pieces,

                COALESCE((
                    SELECT SUM(
                        CASE
                            WHEN t.transaction_type = 'DELI'
                                THEN -t.pieces
                            ELSE t.pieces
                        END
                    )
                    FROM transaction t
                    WHERE t.iban = h.iban
                      AND t.isin_code = h.isin_code
                      AND t.price_date <= h.price_date
                ), 0) AS transaction_cum_pieces,

                COALESCE((
                    SELECT SUM(
                        CASE
                            WHEN t.transaction_type = 'DELI'
                                THEN -t.pieces
                            ELSE t.pieces
                        END
                    )
                    FROM transaction t
                    WHERE t.iban = h.iban
                      AND t.isin_code = h.isin_code
                      AND t.price_date <= h.price_date
                ), 0) - h.pieces AS difference

            FROM holding_view h
            WHERE h.iban = %s
              AND h.price_date BETWEEN %s AND %s
            HAVING difference != 0
            ORDER BY h.isin_code, h.price_date
        """
        return self.db.execute(sql, (iban, start_date, end_date), result_dict=True)

    def get_transactions_of_iban_isin_code(self, iban, isin_code, period):

        return self.db.select_table(
                declm.TRANSACTION_VIEW,
                declm.TABLE_FIELDS[declm.TRANSACTION_VIEW],
                result_dict=True,
                iban=iban,
                isin_code=isin_code,
                period=period
                )


def forward_methods(repo_names, debug=False):
    def decorator(cls):

        def __getattr__(self, name):
            for repo_name in repo_names:
                repo = getattr(self, repo_name)

                if hasattr(repo, name):
                    if debug:
                        print(f"[forward] {cls.__name__}.{name} → {repo_name}.{name}")
                    return getattr(repo, name)

            raise AttributeError(f"{cls.__name__} hat keine Methode '{name}'")

        cls.__getattr__ = __getattr__
        return cls

    return decorator


REPOSITORIES = {
    "application": ApplicationRepository,
    "bank_identifier": BankIdentifierRepository,
    "customizing": CustomizingRepository,
    "geometry": GeometryRepository,
    "holding": HoldingRepository,
    "isin": IsinRepository,
    "ledger": LedgerRepository,
    "ledger_daily_balance": LedgerDailyBalanceRepository,
    "ledger_delete": LedgerDeleteRepository,
    "ledger_statement": LedgerStatementRepository,
    "ledger_coa": LedgerCoaRepository,
    "ledger_view": LedgerViewRepository,
    "mariadb": MariaDBRepository,
    "prices": PricesRepository,
    "statement": StatementRepository,
    "server": ServerRepository,
    "selection": SelectionRepository,
    "shelves": ShelvesRepository,
    "transaction": TransactionRepository,
    "tickers": TickersRepository,
}


@forward_methods(REPOSITORIES.keys(), debug=False)
class Repository:

    def __init__(self):
        for name, cls in REPOSITORIES.items():
            setattr(self, name, cls())
