"""
Created on 26.11.2019
__updated__ = "2026-05-31"
@author: Wolfgang Kramer
"""
import sqlalchemy
import json
import re
import threading
import csv

from pathlib import Path
from collections.abc import Sequence
from inspect import stack
from typing import Iterable, Any, List
from mariadb import connect, Error
from itertools import chain
from datetime import date
from collections import namedtuple
from fints.types import ValueList

import banking.declarations_mariadb as declm
import banking.declarations as decl
import banking.message_handler as msg

from banking.utils import date_days,  Termination, dec2, dec3, dec6, dec10
from banking.connect_data import connectionresult

NAMED_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):  # @NoSelf
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class MariaDBInitializer(metaclass=SingletonMeta):
    """
    Basic Class
    This class is responsible for:
    - Creating and initializing the database
    - Creating tables and views
    - Managing connections and cursors
    - Collecting table and column metadata
    """

    def __init__(self):
        """
        Initialize the MariaDB singleton.
        Contains only domain-level initialization.
        """
        self.connection = MariaDBConnection()
        self.connection.connect()
        self.executor = MariaDBExecutor()
        self.table_names: list[str] = []
        self._initialize_database()
        self._init_database_info()

    def _initialize_database(self) -> None:
        """Create database, connect, and initialize tables/views/trigger/procedure."""
        try:
            self._create_database_if_missing()
            self._create_tables_and_views()
            self._create_trigger()
            self._create_procedure()
        except Error as exc:
            DatabaseErrorHandler.handle_error(connectionresult.database, msg.Informations.BANKDATA_INFORMATIONS, exc)

    def _create_database_if_missing(self) -> None:
        """Create the database if it does not yet exist."""
        with connect(
            host=connectionresult.host,
            user=connectionresult.user,
            password=connectionresult.password,
        ) as conn:
            cur = conn.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {connectionresult.database.upper()} "
            )

    def _create_procedure(self):
        """Create procedure if necessary."""
        for procedure in declm.PROCEDURES:
            sql = "DROP PROCEDURE IF EXISTS " + procedure
            connectionresult.cursor.execute(sql)
        for sql in declm.CREATE_PROCEDURE:
            connectionresult.cursor.execute(sql)

    def _create_trigger(self):
        """Create trigger if necessary."""
        for statement in declm.CREATE_TRIGGER:
            connectionresult.cursor.execute(statement)

    def _create_tables_and_views(self) -> None:
        """Create tables and update views if necessary."""
        for statement in declm.CREATE_TABLES:
            connectionresult.cursor.execute(statement)

    def _create_engine(self):
        """Create and return a SQLAlchemy engine."""
        credentials = (
            f'{connectionresult.user}:{connectionresult.password}@{connectionresult.host}/{connectionresult.database}')
        try:
            return sqlalchemy.create_engine(
                f'mariadb+mariadbconnector://{credentials}')
        except sqlalchemy.exc.SQLAlchemyError as exc:
            DatabaseErrorHandler.handle_error(connectionresult.database, msg.Informations.PRICES_INFORMATIONS, exc)
            return None

    def _init_database_info(self) -> None:
        """
        Initialize table and column metadata structures.

        Populates:
        - declm.TABLE_NAMES
        - declm.TABLE_FIELDS
        - declm.TABLE_FIELDS_PROPERTIES
        - DATABASE_FIELDS_PROPERTIES
        """
        self._load_table_names()
        self._load_column_metadata()

    def _load_table_names(self) -> None:
        """Load all table names from the current schema."""
        sql = (
            'SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();'
            )
        self.table_names = list(chain(*self.executor.execute(sql)))
        declm.TABLE_NAMES[:] = self.table_names

    def _load_column_metadata(self) -> None:
        """Load column properties for all tables."""
        columns = [
            'column_name',
            'character_maximum_length',
            'numeric_scale',
            'numeric_precision',
            'data_type',
            'column_comment'
            ]
        Column = namedtuple('Column', columns)
        for table in self.table_names:
            sql = (
                f"SELECT {','.join(columns)} FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = '{table}' ORDER BY ordinal_position;"
                )
            result = self.executor.execute(sql)
            field_properties = {}
            for row in result:
                column = Column(*row)
                field_properties[column.column_name] = self._build_field_property(column)
            declm.TABLE_FIELDS[table] = list(field_properties.keys())
            declm.TABLE_FIELDS_PROPERTIES[table] = field_properties
            declm.DATABASE_FIELDS_PROPERTIES.update(field_properties)

    def _build_field_property(self, column):
        """Create a FieldsProperty instance for a column."""
        if column.data_type == 'decimal':
            typ = decl.TYP_DECIMAL
        elif column.data_type == 'date':
            typ = decl.TYP_DATE
        else:
            typ = decl.TYP_ALPHANUMERIC
        length = (
            column.character_maximum_length
            or column.numeric_precision
            or 30
            )
        scale = column.numeric_scale or 0
        return declm.FieldsProperty(length, scale, typ, column.column_comment, column.data_type)

    def _handle_sql_error(self, error: Error) -> None:
        """Format and display SQL errors with stack context."""
        message = msg.get_message(
            msg.MESSAGE_TEXT,
            'MARIADB_ERROR',
            error.errno,
            error.errmsg
            )
        filename, line, method = stack()[1][1:4]
        message = '\n\n'.join(
            [
                message,
                msg.get_message(
                    msg.MESSAGE_TEXT,
                    'STACK',
                    method,
                    line,
                    filename
                    )
                ]
            )
        msg.MessageBoxInfo(message=message)

    def destroy_connection(self):
        """
        close connection >database<
        """
        if connectionresult.conn.is_connected():
            connectionresult.conn.close()
            connectionresult.cursor.close()


class MariaDBConnection:

    def __init__(self):

        connectionresult.database = connectionresult.database.lower()
        connectionresult.conn = None
        connectionresult.cursor = None
        connectionresult.engine = None

    def connect(self):
        """
        Connects user to database.
        Creates an empty database if it does not exist.
        """
        with connect(
            host=connectionresult.host,
            user=connectionresult.user,
            password=connectionresult.password
        ) as admin_conn:
            admin_cur = admin_conn.cursor()
            admin_cur.execute(
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = ?",
                (connectionresult.database,)
            )
            exists = admin_cur.fetchone() is not None
            if not exists:
                admin_cur.execute(
                    f"CREATE DATABASE {connectionresult.database} "
                )
        self._connect_to_database()

    def _connect_to_database(self):

        self._create_engine()
        connectionresult.conn = connect(
            host=connectionresult.host,
            user=connectionresult.user,
            password=connectionresult.password,
            database=connectionresult.database,
            local_infile=True
        )
        connectionresult.conn.autocommit = True
        connectionresult.cursor = connectionresult.conn.cursor()
        connectionresult.cursor.execute("SELECT DATABASE()")

    def _create_engine(self):

        credentials = ''.join(
            [connectionresult.user, ":", connectionresult.password, "@", connectionresult.host, "/", connectionresult.database])
        connectionresult.engine = sqlalchemy.create_engine("mariadb+mariadbconnector://" + credentials)

    def close(self):
        if connectionresult.conn and connectionresult.conn.is_connected():
            connectionresult.cursor.close()
            connectionresult.conn.close()


class MariaDBExecutor:
    """
    Centralized SQL execution layer.
    GUI independent.
    """

    SELECT_RE = re.compile(r'^\s*(SELECT|WITH)\b', re.I)
    MODIFY_RE = re.compile(r'^\s*(INSERT|UPDATE|DELETE|REPLACE)\b', re.I)

    def __init__(self):

        self._cursor = connectionresult.cursor
        self._conn = connectionresult.conn

    def execute(
        self,
        sql: str,
        vars_: tuple | None = None,
        *,
        duplicate: bool = False,
        result_dict: bool = False,
        compress: bool = False
    ):
        """
        Execute SQL statement.

        Parameters:
            sql_statement: SQL string
            vars_: bind parameters
            duplicate: ignore duplicate key error (1062)
            result_dict: return list of dicts instead of tuples
            compress: normalize whitespace in SQL

        Returns:
            SELECT/WITH   -> list[tuple] | list[dict]
            INSERT/UPDATE/DELETE/REPLACE -> affected row count
            otherwise    -> None
        """
        sql = self._prepare_sql(sql, compress)
        try:
            # print(sql, vars_)
            self._execute(sql, vars_)
            if self._is_select(sql):
                return self._fetch(result_dict)
            if self._is_modify(sql):
                return self._row_count()
            return None

        except Exception as exc:
            # Executor does NOT decide how to display errors
            exc.statement = sql
            exc.params = vars_
            raise

    def _prepare_sql(self, sql: str, compress: bool) -> str:

        if not compress:
            return sql
        return re.sub(r'\s+', ' ', sql.replace('\n', ' ')).strip()

    def _callproc(
        self,
        sql: str,
        params: list | None = None,
        *,
        result_dict: bool = False,
    ):
        if params:
            # print(sql, params)
            self._cursor.callproc(sql, params)
        else:
            print(sql)
            self._cursor.callproc(sql)
        return self._fetch(result_dict)

    def _execute(self, sql: str, params):

        if params:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)

    def _is_select(self, sql: str) -> bool:

        return bool(self.SELECT_RE.match(sql))

    def _is_modify(self, sql: str) -> bool:

        return bool(self.MODIFY_RE.match(sql))

    def _fetch(self, result_dict: bool):

        rows = self._cursor.fetchall()
        if not result_dict:
            return rows
        columns = [c[0] for c in self._cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def _row_count(self) -> int:

        self._cursor.execute('SELECT ROW_COUNT()')
        return self._cursor.fetchone()[0]


class DatabaseErrorHandler:
    """
    Handles database-related errors and user-facing error messages.
    Fully compatible with legacy MariaDB.execute() error handling.
    """

    @staticmethod
    def handle_error(

        title: str,
        storage,
        exc: Exception,
        *,
        sql: str | None = None,
        params=None,
        duplicate: bool = False
    ):
        messages: list[str] = []
        # --- Base SQL error message -------------------------------------
        if sql is not None:
            messages.append(
                msg.get_message(
                    msg.MESSAGE_TEXT,
                    'MARIADB_ERROR_SQL',
                    sql,
                    params
                )
            )
        # --- DB error details (errno / errmsg) --------------------------
        errno = getattr(exc, 'errno', None)
        errmsg = getattr(exc, 'errmsg', None)
        if errno is not None and errmsg is not None:
            messages.append(
                msg.get_message(
                    msg.MESSAGE_TEXT,
                    'MARIADB_ERROR',
                    errno,
                    errmsg
                )
            )
        # --- Duplicate key handling ------------------------------------
        if duplicate and errno == 1062:
            msg.MessageBoxInfo(
                title=title,
                info_storage=storage,
                information=decl.ERROR,
                message="\n\n".join(messages)
            )
            return errno
        # --- LOAD statement handling -----------------------------------
        if sql and sql.upper().startswith('LOAD'):
            msg.MessageBoxInfo(
                title=title,
                info_storage=storage,
                information=decl.ERROR,
                message="\n\n".join(messages)
            )
            return False
        # --- Stack trace (legacy behavior) -----------------------------
        try:
            frame = stack()[2]
            filename = frame.filename
            line = frame.lineno
            method = frame.function

            messages.append(
                msg.get_message(
                    msg.MESSAGE_TEXT,
                    'STACK',
                    line,
                    filename,
                    method
                )
            )
        except Exception:
            pass
        # --- Fatal error ------------------------------------------------
        msg.MessageBoxError(
            title=title,
            info_storage=storage,
            message="\n\n".join(messages)
        )
        return False


class MariaDBTables:
    # ------------------------------------------------------------------
    # Core QueryBuilder helpers
    # ------------------------------------------------------------------
    def _order_clause(self, order=None, sort: str = 'ASC') -> str:
        """Build ORDER BY clause"""
        if not order:
            return ''
        sort = sort.upper()
        if isinstance(order, list) and isinstance(order[0], str):
            clause = ', '.join(f"{o} {sort}" for o in order)
        elif isinstance(order, tuple):
            clause = f"{order[0]} {order[1]}"
        elif isinstance(order, list) and isinstance(order[0], tuple):
            clause = ', '.join(f"{o[0]} {o[1]}" for o in order)
        else:
            clause = f"{order} {sort}"
        return f" ORDER BY {clause} "

    def _where_clause(
        self,
        *,
        clause: str | None = None,
        clause_vars: Sequence[Any] = (),
        date_name: str | None = None,
        **kwargs
    ) -> tuple[str, tuple[Any, ...]]:
        """
        Build WHERE clause and bind variables.

        Returns:
            (sql, vars)
        """
        sql_parts: list[str] = []
        vars_: list[Any] = []
        for key, value in kwargs.items():
            if isinstance(value, date):
                value = date_days.convert_to_str(value)
            if key == "period":
                from_date, to_date = map(date_days.convert_to_str, value)
                field = date_name or declm.DB_price_date
                sql_parts.append(f"{field} BETWEEN ? AND ?")
                vars_.extend((from_date, to_date))
            elif isinstance(value, (list, tuple)):
                placeholders = ", ".join("?" for _ in value)
                sql_parts.append(f"{key} IN ({placeholders})")
                vars_.extend(value)
            else:
                sql_parts.append(f"{key} = ?")
                vars_.append(value)
        if clause:
            sql_parts.append(f"({clause})")
            vars_.extend(clause_vars)
        if not sql_parts:
            return "", ()
        return "WHERE " + " AND ".join(sql_parts) + " ", tuple(vars_)

    def _normalize_fields(
        self,
        fields: str | Iterable[str]
    ) -> str:
        """
        Normalize the field list to a SQL-compatible string.
        """
        if isinstance(fields, (list, tuple, set)):
            return ', '.join(fields)
        return fields

    def _normalize_vars(self, vars_):
        """
        Normalize SQL variables to a tuple.

        Accepts:
        - tuple
        - list
        - dict (values only, ordered)
        - None

        Returns
        -------
        tuple
        """
        if vars_ is None:
            return ()
        if isinstance(vars_, tuple):
            return vars_
        if isinstance(vars_, list):
            return tuple(vars_)
        if isinstance(vars_, dict):
            return tuple(vars_.values())
        raise TypeError(f"Unsupported vars type: {type(vars_)}")

    def _normalize_named_sql(self, sql: str, vars_: dict):
        """
        Replace :named parameters with ? placeholders
        and return ordered tuple of bind variables.
        """
        if not vars_:
            return sql, ()
        order = []

        def repl(match):
            key = match.group(1)
            if key not in vars_:
                raise KeyError(f"Missing SQL bind parameter: {key}")
            order.append(key)
            return "?"

        sql = NAMED_PARAM_RE.sub(repl, sql)
        values = tuple(vars_[k] for k in order)
        return sql, values

    def _select(
        self,
        *,
        table: str,
        fields: str | list[str] | tuple[str, ...],
        distinct: bool = False,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | tuple | list[tuple] | None = None,
        sort: str = "ASC",
        group_by: str | list[str] | None = None,
        having: str | None = None,
        having_vars: tuple = (),
        limit: int | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> list:
        """
        Build and execute a unified SQL SELECT statement.

        This internal helper constructs a SELECT query supporting DISTINCT,
        WHERE filtering, GROUP BY, HAVING, ORDER BY, and LIMIT clauses.
        All SQL execution is delegated to the configured database executor.

        Parameters
        ----------
        table : str
            Name of the database table or view.
        fields : str | list[str] | tuple[str, ...]
            Fields to select. May be a comma-separated string or an iterable
            of column names.
        distinct : bool, optional
            If True, generate a SELECT DISTINCT statement.
        clause : str | None, optional
            Additional raw SQL WHERE clause fragment. This fragment may
            contain positional placeholders (`?`) which must be bound via
            `clause_vars`.
        date_name : str | None, optional
            Overrides the default date column used for period-based filters.
        order : str | list[str] | None, optional
            Column or columns used for ORDER BY.
            Tuple or list of tuples used for ORDER BY e.g. [(column, 'ASC'), ...]
        sort : str, optional
            Sort direction for ORDER BY. Must be 'ASC' or 'DESC'.
            Not used if order are tuple o list of tuples
        group_by : str | list[str] | None, optional
            Column or columns used for GROUP BY.
        having : str | None, optional
            SQL HAVING clause applied after GROUP BY. May contain positional
            placeholders (`?`) which must be bound via `having_vars`.
        limit : int | None, optional
            Maximum number of rows to return.
        result_dict : bool, optional
            If True, return rows as dictionaries.
            If False, return rows as tuples.
        clause_vars : tuple, optional
            Positional bind variables for placeholders defined in `clause`.
        having_vars : tuple, optional
            Positional bind variables for placeholders defined in `having`.
        **kwargs
            Column-value filters passed to `_where_clause()`.

        Returns
        -------
        list
            Query result rows. Each row is returned either as a tuple or
            as a dictionary depending on `result_dict`.
        """
        if not fields:
            return []
        fields = self._normalize_fields(fields)
        select_kw = "SELECT DISTINCT" if distinct else "SELECT"
        sql = f"{select_kw} {fields} FROM {table} "
        where_sql, vars_ = self._where_clause(
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            **kwargs
        )
        sql += where_sql
        if group_by:
            group_sql = (
                ", ".join(group_by)
                if isinstance(group_by, (list, tuple))
                else group_by
            )
            sql += f" GROUP BY {group_sql} "
        if having:
            sql += f" HAVING {having} "
            vars_ += having_vars
        if order:
            sql += self._order_clause(order=order, sort=sort)
        if limit is not None:
            sql += f" LIMIT {limit} "
        return self.executor.execute(
            sql,
            vars_=vars_,
            result_dict=result_dict
        )

    def _select_scalar(
        self,
        *,
        table: str,
        expression: str,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        default=None,
        **kwargs
    ):
        """
        Execute a SELECT query that returns a single scalar value.

        This helper is intended for aggregate queries such as COUNT, SUM,
        MIN, MAX, or any SQL expression that yields exactly one value.

        Parameters
        ----------
        table : str
            Name of the database table or view.
        expression : str
            SQL expression to select (e.g. 'COUNT(*)', 'SUM(amount)',
            'MAX(created_at)').
        clause : str | None, optional
            Additional raw SQL WHERE clause fragment.
        date_name : str | None, optional
            Overrides the default date column used for period-based filters.
        default : Any, optional
            Value returned if the query yields no result or NULL.
        **kwargs
            Column-value filters passed to `_where_clause()`.

        Returns
        -------
        Any
            The scalar result value, or `default` if no row was returned.
        """
        rows = self._select(
            table=table,
            fields=expression,
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            limit=1,
            **kwargs
        )
        if not rows:
            return default
        value = rows[0][0]
        return default if value is None else value

    def _select_exists(
        self,
        *,
        table: str,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        **kwargs
    ) -> bool:
        """
        Check whether at least one row exists for the given conditions.

        Parameters
        ----------
        table : str
            Table or view name.
        clause : str | None, optional
            Additional SQL WHERE clause fragment.
        date_name : str | None, optional
            Overrides the default date column for period filters.
        **kwargs
            WHERE filters passed to `_where_clause()`.

        Returns
        -------
        bool
            True if at least one matching row exists, otherwise False.
        """
        rows = self._select(
            table=table,
            fields="1",
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            limit=1,
            **kwargs
        )
        return bool(rows)

    def _select_cte(
        self,
        *,
        sql: str,
        fields: str | Iterable[str],
        vars_: dict | tuple | None = None,
        result_dict: bool = False,
    ) -> list:
        """
        Execute a CTE-based SELECT statement.

        Parameters
        ----------
        sql : str
            Inner SELECT or CTE SQL statement.
            May contain positional ('?') or named (':name') placeholders.
        fields : str | Iterable[str]
            Fields to select from the CTE result.
        vars_ : dict | tuple | None, optional
            Bind parameters for the SQL statement.
            - dict: named parameters
            - tuple/list: positional parameters
        result_dict : bool, optional
            If True, return rows as dictionaries.

        Returns
        -------
        list
            Query result rows as tuples or dictionaries.
        """
        if not fields:
            fields = '*'
        if isinstance(vars_, dict):
            sql, vars_ = self._normalize_named_sql(sql, vars_)
        else:
            vars_ = self._normalize_vars(vars_)
        fields_sql = self._normalize_fields(fields)
        final_sql = f"""
            SELECT {fields_sql}
            FROM (
                {sql}
            ) AS cte
        """
        return self.executor.execute(
            final_sql,
            vars_=vars_,
            result_dict=result_dict,
            compress=True
        )

    def select_table(
        self,
        table: str,
        field_list,
        *,
        order=None,
        clause=None,
        clause_vars: tuple = (),
        sort: str = "ASC",
        result_dict: bool = False,
        date_name: str | None = None,
        **kwargs
    ):
        """Select rows from a table."""
        return self._select(
            table=table,
            fields=field_list,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            sort=sort,
            date_name=date_name,
            result_dict=result_dict,
            **kwargs
        )

    def select_table_distinct(
        self,
        table: str,
        field_list,
        *,
        order=None,
        clause=None,
        clause_vars: tuple = (),
        result_dict: bool = False,
        date_name: str | None = None,
        **kwargs
    ):
        """Select distinct rows from a table."""
        return self._select(
            table=table,
            fields=field_list,
            distinct=True,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            date_name=date_name,
            result_dict=result_dict,
            **kwargs
        )

    def select_first_row(
        self,
        table: str,
        fields: str | list[str] | tuple[str, ...],
        *,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> str | list:
        """Select first row based on ordering."""
        rows = self._select(
            table=table,
            fields=fields,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            date_name=date_name,
            sort="ASC",
            limit=1,
            result_dict=result_dict,
            **kwargs
        )
        if isinstance(fields, str):
            if fields == '*':
                return rows[0] if rows else None  # returns list or dict
            else:
                return rows[0] if rows[0][0] else None  # returns scalar
        else:
            return rows[0] if rows else None

    def select_last_row(
        self,
        table: str,
        fields: str | list[str] | tuple[str, ...],
        *,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> str | list:
        """Select last row based on ordering."""
        rows = self._select(
            table=table,
            fields=fields,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            date_name=date_name,
            sort="DESC",
            limit=1,
            result_dict=result_dict,
            **kwargs
        )
        if not rows:
            return None
        if isinstance(fields, str):
            if fields == '*':
                return rows[0] if rows else None  # returns list or dict
            else:
                return rows[0] if rows[0][0] else None  # returns scalar
        else:
            return rows[0] if rows else None

    def select_grouped(
        self,
        table: str,
        fields,
        *,
        group_by: str,
        having: str | None = None,
        date_name: str | None = None,
        result_dict: bool = False,
        **kwargs
    ):
        """
        Select grouped rows with optional HAVING conditions.
        """
        return self._select(
            table=table,
            fields=fields,
            group_by=group_by,
            having=having,
            date_name=date_name,
            result_dict=result_dict,
            **kwargs
        )

    def select_dict(
        self,
        table: str,
        key_name: str,
        value_name: str,
        *,
        order: str | None = None,
        clause: str | None = None,
        clause_vars: tuple = (),
        **kwargs
    ) -> dict:
        """
        Return a dictionary mapping keys to values from a table.

        Parameters
        ----------
        table : str
            Table or view name.
        key_name : str
            Column used as dictionary key.
        value_name : str
            Column used as dictionary value.
        order : str | list[str], optional
            ORDER BY column(s).
        **kwargs
            WHERE filters passed to `_where_clause()`.

        Returns
        -------
        dict
            Dictionary mapping key_name -> value_name.
            Returns an empty dict if no rows match.
        """
        rows = self._select(
            table=table,
            fields=[key_name, value_name],
            order=order,
            clause=clause,
            clause_vars=clause_vars,
            **kwargs
        )
        return dict(rows) if rows else {}

    def select_rows(
        self,
        *,
        table: str,
        fields,
        distinct: bool = False,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | None = None,
        sort: str = "ASC",
        group_by: str | list[str] | None = None,
        having: str | None = None,
        limit: int | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> list:
        """
        Select rows from a table.

        This is the primary public entry point for row-based SELECT queries.
        """
        return self._select(
            table=table,
            fields=fields,
            distinct=distinct,
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            order=order,
            sort=sort,
            group_by=group_by,
            having=having,
            limit=limit,
            result_dict=result_dict,
            **kwargs
        )

    def select_scalar(
        self,
        table: str,
        expression: str,
        *,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        default=None,
        **kwargs
    ):
        """
        Execute a SELECT query returning a single scalar value.
        """
        return self._select_scalar(
            table=table,
            expression=expression,
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            default=default,
            **kwargs
        )

    def select_exists(
        self,
        table: str,
        *,
        clause: str | None = None,
        date_name: str | None = None,
        **kwargs
    ) -> bool:
        """
        Return True if at least one matching row exists.
        """
        return self._select_exists(
            table=table,
            clause=clause,
            date_name=date_name,
            **kwargs
        )

    def select_cte(
        self,
        *,
        sql: str,
        fields: str | Iterable[str],
        vars_: dict | tuple | None = None,
        result_dict: bool = False,
    ) -> list:
        """
        Execute a SELECT statement based on a Common Table Expression (CTE).

        This method wraps an arbitrary SELECT or CTE SQL statement and applies
        a unified result projection and execution strategy. It supports both
        positional and named SQL parameters and returns the result either as
        tuples or dictionaries.

        Parameters
        ----------
        sql : str
            Inner SELECT or CTE SQL statement.
            May contain positional ('?') or named (':name') placeholders.
        fields : str | Iterable[str]
            Fields to select from the CTE result.
            Must not be empty.
        vars_ : dict | tuple | None, optional
            Bind parameters for the SQL statement.
            - dict: named parameters
            - tuple/list: positional parameters
            - None: no bind parameters
        result_dict : bool, optional
            If True, rows are returned as dictionaries.
            If False, rows are returned as tuples.

        Returns
        -------
        list
            Query result rows.
            Returns an empty list if `fields` is empty.
        """

        # ------------------------------------------------------------
        # Guard clause – consistent with other select_* methods
        # ------------------------------------------------------------
        if not fields:
            return []
        return self._select_cte(
            sql=sql,
            fields=fields,
            vars_=vars_,
            result_dict=result_dict,
        )

    # ------------------------------------------------------------------
    # INSERT / UPDATE / DELETE / REPLACE
    # ------------------------------------------------------------------

    def execute(self, *args, **kwargs):

        def _normalize_execute_args(args, kwargs):
            """
            Normalize positional and keyword arguments of execute()
            into explicit named values.
            """
            sql = args[0] if len(args) > 0 else kwargs.get("sql")
            params = args[1] if len(args) > 1 else kwargs.get("vars_")

            duplicate = kwargs.get("duplicate", False)
            result_dict = kwargs.get("result_dict", False)
            compress = kwargs.get("compress", False)

            return {
                "sql": sql,
                "params": params,
                "duplicate": duplicate,
                "result_dict": result_dict,
                "compress": compress,
            }

        exec_args = _normalize_execute_args(args, kwargs)
        try:
            return self.executor.execute(*args, **kwargs)
        except Exception as exc:
            return DatabaseErrorHandler.handle_error(
                title="Database error",
                storage=self,
                exc=exc,
                sql=exec_args["sql"],
                params=exec_args["params"],
                duplicate=exec_args["duplicate"],
            )

    def execute_insert(self, table: str, field_dict: dict) -> None:
        """Insert a record into a table."""
        columns = ', '.join(field_dict.keys())
        placeholders = ', '.join('?' for _ in field_dict)
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.executor.execute(sql, vars_=tuple(field_dict.values()))

    def execute_update(self, table: str, field_dict: dict, **kwargs) -> None:
        """Update rows in a table."""
        set_clause = ', '.join(f"{k}=?" for k in field_dict)
        sql = f"UPDATE {table} SET {set_clause} "
        where_sql, vars_where = self._where_clause(**kwargs)
        sql += where_sql
        vars_ = tuple(field_dict.values()) + vars_where
        self.executor.execute(sql, vars_=vars_)

    def execute_replace(self, table, field_dict):
        """
        Insert/Change Record in MARIADB table
        """
        set_fields = ' SET '
        vars_ = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            if table == declm.ISIN and key_ == declm.DB_name:
                field_dict[key_] = field_dict[key_].upper()
            vars_ = vars_ + (field_dict[key_],)
        sql_statement = 'REPLACE INTO ' + table + set_fields
        sql_statement = sql_statement[:-2]
        self.executor.execute(sql_statement, vars_=vars_)

    def execute_delete(
        self,
        table: str,
        *,
        clause: str | None = None,
        clause_vars: Sequence[Any] = (),
        **kwargs
    ) -> None:
        """Delete rows from a table."""
        where_sql, vars_ = self._where_clause(
            clause=clause,
            clause_vars=clause_vars,
            **kwargs
        )

        sql = f"DELETE FROM {table} {where_sql}"

        self.executor.execute(sql, vars_)


class MariaDBShelves:
    """
    Shelve JSON Helpers
    """
    def shelve_serialize(self, obj) -> list:
        """
        Convert ValueList objects to JSON-serializable lists.

        Parameters
        ----------
        obj : ValueList
            Object to serialize.

        Returns
        -------
        list
            Serialized list.

        Raises
        ------
        TypeError
            If the object is not a ValueList.
        """
        if isinstance(obj, ValueList):
            return list(obj)
        raise TypeError(f"Expected ValueList, got {type(obj)}")

    def shelve_get_key(
        self,
        shelve_name: str,
        key: str | list[str],
        none: bool = True
    ) -> dict | Any:
        """
        Retrieve a key or list of keys from the shelve JSON data.

        Parameters
        ----------
        shelve_name : str
            Bank/shelve identifier.
        key : str | list[str]
            Key(s) to fetch from the JSON data.
        none : bool, default True
            If True, missing keys return None; otherwise return empty dict.

        Returns
        -------
        dict | any
            Dictionary (for list input) or single value (for string input).
        """
        _bankdata = self.select_scalar(declm.SHELVES, declm.DB_bankdata, code=shelve_name)
        if not _bankdata:
            Termination(
                info=msg.get_message(msg.MESSAGE_TEXT, "SHELVE_NAME_MISSED", shelve_name)
            ).terminate()
        bankdata = json.loads(_bankdata)
        if isinstance(key, list):
            res_dict = dict.fromkeys(key, None) if none else {}
            res_dict.update(bankdata)
            return res_dict
        result = bankdata.get(key, {} if not none else None)
        return result

    def shelve_put_key(self, shelve_name: str, data: tuple | list[tuple]) -> None:
        """
        Insert or update key-value pairs in shelve JSON data.

        Parameters
        ----------
        shelve_name : str
            Bank/shelve identifier.
        data : tuple | list[tuple]
            Key-value pair(s) to update.
        """
        _bankdata = self.select_scalar(declm.SHELVES, declm.DB_bankdata, code=shelve_name)
        bankdata = json.loads(_bankdata) if _bankdata else {}
        if isinstance(data, tuple):
            data = [data]
        bankdata.update(dict(data))
        bankdata_json = json.dumps(bankdata, default=self.shelve_serialize)
        self.execute_replace(declm.SHELVES, {declm.DB_code: shelve_name, declm.DB_bankdata: bankdata_json})

    def shelve_del_key(self, shelve_name: str, key: str) -> None:
        """
        Delete a key from shelve JSON data.

        Parameters
        ----------
        shelve_name : str
            Bank/shelve identifier.
        key : str
            Key to remove.
        """
        _bankdata = self.select_scalar(declm.SHELVES, declm.DB_bankdata, code=shelve_name)
        if _bankdata:
            bankdata = json.loads(_bankdata)
            bankdata.pop(key, None)
            self.execute_replace(declm.SHELVES, {declm.DB_code: shelve_name, declm.DB_bankdata: json.dumps(bankdata)})


class MariaDBImporter:
    """
    Class to import bank identifiers, servers, transactions, and prices, tickers
    into MariaDB tables in a structured, safe way.
    """
    def execute_load_data(
        self,
        *,
        filename: str,
        table: str,
        columns: str,
        set_clause: str | None = None,
        line_terminator: str = "\\r\\n",
        field_terminator: str = ";",
        encoding: str = "latin1",
        ignore_lines: int = 1,
        replace: bool = True,
        local: bool = True,
        commit: bool = False,
    ) -> None:
        """
        Execute a generic MySQL LOAD DATA import.

        Parameters
        ----------
        filename : str
            Path to the CSV file.

        table : str
            Target database table.

        columns : str
            Column definition for the LOAD DATA statement.

        set_clause : str, optional
            Optional SQL SET clause.

        line_terminator : str, optional
            CSV line ending.

        field_terminator : str, optional
            CSV field delimiter.

        encoding : str, optional
            File encoding.

        ignore_lines : int, optional
            Number of header rows to ignore.

        replace : bool, optional
            Use REPLACE INTO TABLE.

        local : bool, optional
            Use LOCAL INFILE.

        commit : bool, optional
            Execute COMMIT after import.
        """
        sql_filename = str(Path(filename)).replace("\\", "\\\\")
        local_sql = "LOCAL" if local else ""
        replace_sql = "REPLACE" if replace else ""
        load_sql = f"""
            LOAD DATA LOW_PRIORITY {local_sql} INFILE '{sql_filename}'
            {replace_sql} INTO TABLE {table}
            CHARACTER SET {encoding}
            FIELDS TERMINATED BY '{field_terminator}'
            OPTIONALLY ENCLOSED BY '"'
            ESCAPED BY '"'
            LINES TERMINATED BY '{line_terminator}'
            IGNORE {ignore_lines} LINES
            (
                {columns}
            )
        """
        if set_clause:
            load_sql += f"\nSET\n{set_clause}"
        load_sql += ";"
        self.executor.execute(load_sql)
        if commit:
            self.executor.execute("COMMIT")

    def parse_decimal(self, value: str, decimal_separator=",", places=2):
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
        elif places == 3:
            return dec3.convert(value)
        elif places == 6:
            return dec6.convert(value)
        elif places == 10:
            return dec10.convert(value)
        raise "Method parse_decimal: Param places not 2, 3, 6 or 10"

    def transaction_exists(self, table: str, db_fields: List[str], values: List[Any]) -> bool:
        """
        Build a SQL EXISTS query for checking whether a row already exists.

        Args:
            table: Name of the database table.
            data: Dictionary containing column names and values.

        Returns:
            Tuple containing:
            - SQL query string
            - List of query parameters
        """
        where_clauses: List[str] = []
        params: List[Any] = []
        for field, value in zip(db_fields, values):
            # Handle NULL values separately
            if value is None:
                where_clauses.append(f"`{field}` IS NULL")
            else:
                where_clauses.append(f"`{field}` = %s")
                params.append(value)
        sql: str = f"""
        SELECT EXISTS(
            SELECT 1
            FROM `{table}`
            WHERE {' AND '.join(where_clauses)}
        ) AS row_exists
        """
        result = self.executor.execute(sql, params)
        return result

    def load_csv_to_table(
            self,
            csv_file,
            table_name,
            field_mapping,
            additional_fields=None,
            value_transformers=None,
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
            start_line: int             Positioonieren auf Startzeile

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

                load_csv_to_table(
                    cursor=cursor,
                    csv_file="holding.csv",
                    table_name="holding",
                    field_mapping=mapping,
                    additional_fields=additional_fields,
                    value_transformers=transformers
                )
        """
        message_1st_line = False
        field_properties = declm.TABLE_FIELDS_PROPERTIES[table_name]
        if additional_fields is None:
            additional_fields = {}
        if value_transformers is None:
            value_transformers = {}
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
            placeholders = ", ".join(["?"] * len(db_fields))
            sql = f"""
                INSERT INTO {table_name}
                ({", ".join(db_fields)})
                VALUES ({placeholders})
            """
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
                            value = self.parse_decimal(
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
                result_row = dict(zip(db_fields, values))
                result = self.select_exists(table_name, date_name=declm.DB_price_date, **result_row)
                if not result:
                    self.executor.execute(sql, values)
                else:
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
                        message=result_row
                        )
            if commit:
                self.executor.execute("COMMIT")


class MariaDB(
        MariaDBInitializer,
        MariaDBTables,
        MariaDBShelves,
        MariaDBImporter,
        ):
    """
    Singleton access layer for MariaDB.

    Combines all MariaDB modules (Ledger, Transactions, Prices, Shelves, Selection,
    Application, Server, Services, Importer, Holdings, Statements, Tables, Initializer)
    into a single unified interface.

    """

    def __init__(self):
        """
        Initialize the MariaDB connection once.

        """
        if getattr(self, "_initialized", False):
            return  # Already initialized
        super().__init__()
        self._initialized = True
