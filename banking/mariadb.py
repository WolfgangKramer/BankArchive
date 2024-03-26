'''
Created on 26.11.2019
__updated__ = "2024-03-26"
@author: Wolfgang Kramer
'''

import itertools
import re
import mariadb
import sqlalchemy

from datetime import date, timedelta, datetime
from inspect import stack
from json import dumps, loads

from banking.declarations import (
    CREDIT,
    DATABASES,
    DB_name, DB_counter, DB_price_date, DB_ISIN, DB_transaction_type,
    DB_price_currency, DB_price, DB_pieces, DB_posted_amount,
    DB_amount_currency, DB_symbol,
    TRUE, FALSE,
    HoldingAcquisition,
    Informations,
    ERROR,
    INFORMATION,
    BANKIDENTIFIER,
    CREATE_TABLES,
    HOLDING, HOLDING_VIEW, HOLDING_T,
    ISIN, PRICES,
    KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_PRODUCT_NAME,
    MESSAGE_TEXT,
    ORIGIN,
    PERCENT,
    SCRAPER_BANKDATA, SERVER, STATEMENT,
    TRANSACTION, TRANSACTION_VIEW, TRANSACTION_RECEIPT, TRANSACTION_DELIVERY,
    WARNING,
)
from banking.formbuilts import (
    FIELDS_HOLDING,
    FIELDS_STATEMENT,
    FIELDS_TRANSACTION, FIELDS_BANKIDENTIFIER,
    FIELDS_SERVER, FIELDS_ISIN, FIELDS_PRICES,
    MessageBoxError, MessageBoxInfo, WM_DELETE_WINDOW
)
from banking.forms import Acquisition
from banking.tools import transfer_holding_to_access, transfer_statement_to_access
from banking.utils import Calculate, check_main_thread


dec2 = Calculate(places=2)
dec6 = Calculate(places=6)
# statement begins with SELECT or is a Selection via CTE and begins with WITH
select_statement = re.compile(r'^SELECT|^WITH')
rowcount_statement = re.compile(r'^UPDATE|^DELETE|^INSERT|^REPLACE')

'''
Cursor attributes
.description
This read-only attribute is a sequence of 7-item sequences.

Each of these sequences contains information describing one result column:

name
type_code
display_size
internal_size
precision
scale
null_ok
'''

# used type_codes
TYPE_CODE_VARCHAR = 253
TYPE_CODE_CHAR = 254,
TYPE_CODE_DECIMAL = 246
TYPE_CODE_DATE = 10
TYPE_CODE_INT = 3
TYPE_CODE_SMALLINT = 2


def _sqlalchemy_exception(title, storage, info):
    '''
    SQLAlchemy Error Handling
    '''

    MessageBoxInfo(title=title, information_storage=storage, information=ERROR,
                   message=MESSAGE_TEXT['SQLALCHEMY_ERROR'].format('MESSAGE', info.args[0]))
    MessageBoxInfo(title=title, information_storage=storage, information=ERROR,
                   message=MESSAGE_TEXT['SQLALCHEMY_ERROR'].format('STATEMENT', info.statement))
    MessageBoxInfo(title=title, information_storage=storage, information=ERROR,
                   message=MESSAGE_TEXT['SQLALCHEMY_ERROR'].format('PARAMS', info.params))


class MariaDB(object):
    '''
    Create Connection MARIADB
    Create MARIADB Tables
    Retrieve Records from MARIADB Tables
    Insert and Modify Records of MARIADB Tables

    holding_switch:  'ON         use table HOLDING
                     'OFF'       use table HOLDING_
    '''

    def __init__(self, user, password, database, holding_switch):

        self.user = user
        self.password = password
        self.database = database.lower()
        self.holding_switch = holding_switch
        self.table_names = []  # list of table names
        self.table_fields = {}  # dict key: table_name, dict value: list of table_fieldnames
        self.host = "localhost"
        try:
            conn = mariadb.connect(
                host="localhost", user=self.user, password=self.password)
            cur = conn.cursor()
            sql_statement = "CREATE DATABASE IF NOT EXISTS " + self.database.upper()
            cur.execute(sql_statement)
            sql_statement = "show databases"
            cur.execute(sql_statement)
            for databases in cur:
                if databases[0] not in ['information_schema', 'mysql', 'performance_schema']:
                    DATABASES.append(databases[0])
            conn = mariadb.connect(user=self.user, password=self.password, host=self.host,
                                   database=self.database)
            self.cursor = conn.cursor()
            self.conn = conn
            self.conn.autocommit = True
            for sql_statement in CREATE_TABLES:
                self.cursor.execute(sql_statement)
                if sql_statement.startswith("CREATE ALGORITHM"):
                    sql_statement = sql_statement.replace(
                        "CREATE ALGORITHM", "ALTER ALGORITHM")
                    sql_statement = sql_statement.replace(
                        "IF NOT EXISTS", "")
                    # update view data if view already exists
                    self.cursor.execute(sql_statement)
            self._get_database_names()
        except mariadb.Error as error:
            message = MESSAGE_TEXT['MARIADB_ERROR_SQL'].format(
                sql_statement, '')
            message = '\n\n'.join([
                message, MESSAGE_TEXT['MARIADB_ERROR'].format(error.errno, error.errmsg)])
            filename = stack()[1][1]
            line = stack()[1][2]
            method = stack()[1][3]
            message = '\n\n'.join(
                [message, MESSAGE_TEXT['STACK'].format(method, line, filename)])
            MessageBoxInfo(message=message)

    def _get_database_names(self):
        '''
        Initialize Class Variables
        '''
        sql_statement = "SELECT table_name FROM information_schema.tables WHERE table_schema = database();"
        self.table_names = list(itertools.chain(*self.execute(sql_statement)))
        for table in self.table_names:
            sql_statement = ("SELECT column_name, character_maximum_length, " +
                             " numeric_scale, numeric_precision, data_type " +
                             " FROM information_schema.columns " +
                             " WHERE table_schema = database() " +
                             " AND table_name = '" + table + "';")
            result = self.execute(sql_statement)
            for _tuple in result:
                if _tuple[4] in ['decimal']:
                    compressed_tuple = (_tuple[3], _tuple[2], 'decimal')
                elif _tuple[4] in ['date']:
                    compressed_tuple = (10, 0, 'date')
                else:
                    compressed_tuple = (_tuple[1], 0, _tuple[4])
                if table == BANKIDENTIFIER:
                    FIELDS_BANKIDENTIFIER[_tuple[0]] = compressed_tuple
                if table == HOLDING:
                    FIELDS_HOLDING[_tuple[0]] = compressed_tuple
                if table == ISIN:
                    FIELDS_ISIN[_tuple[0]] = compressed_tuple
                if table == PRICES:
                    FIELDS_PRICES[_tuple[0]] = compressed_tuple
                if table == SERVER:
                    FIELDS_SERVER[_tuple[0]] = compressed_tuple
                if table == STATEMENT:
                    FIELDS_STATEMENT[_tuple[0]] = compressed_tuple
                if table == TRANSACTION:
                    FIELDS_TRANSACTION[_tuple[0]] = compressed_tuple
            self.table_fields[table] = list(map(lambda x: x[0], result))

    def _holdings(self, bank):
        '''
        Storage of holdings on a daily basis of >bank.account_number<
        in MARIADB table HOLDING

        '''

        self.execute('START TRANSACTION;')
        holdings = bank.dialogs.holdings(bank)
        if holdings:
            price_date_holding = None
            for holding in holdings:  # find more frequent price_date
                if not price_date_holding or price_date_holding < holding[DB_price_date]:
                    price_date_holding = holding[DB_price_date]
            if datetime.strptime(price_date_holding, '%Y%m%d').weekday() == 5:  # Saturday
                price_date_holding = datetime.strptime(
                    price_date_holding, '%Y%m%d') - timedelta(1)
            elif datetime.strptime(price_date_holding, '%Y%m%d').weekday() == 6:  # Sunday
                price_date_holding = datetime.strptime(
                    price_date_holding, '%Y%m%d') - timedelta(2)
            for holding in holdings:
                if not self.row_exists(ISIN, name=holding[DB_name]):
                    field_dict = {
                        'ISIN': holding['ISIN'], DB_name: holding[DB_name]}
                    self.execute_replace(ISIN, field_dict)
                name_ = holding[DB_name]
                del holding[DB_name]
                holding[DB_price_date] = price_date_holding
                holding['iban'] = bank.iban
                self.execute_replace(HOLDING, holding)
            # Update acquisition_amount (exists not in MT535 data)
                button_state = self._set_acquisition_amount(
                    bank, holding['ISIN'], name_)
                if button_state == WM_DELETE_WINDOW:
                    self.execute('ROLLBACK')
                    MessageBoxInfo(
                        message=MESSAGE_TEXT['DOWNLOAD_REPEAT'].format(bank.bank_name))
                    return
            self.execute('COMMIT;')
            transfer_holding_to_access(self, bank.iban)
        return holdings

    def _set_acquisition_amount(self, bank, isin, name_):

        button_state = None
        sql_statement = ("SELECT price_date, price_currency, market_price, acquisition_price,"
                         " pieces, amount_currency, total_amount, acquisition_amount, origin"
                         " FROM " + HOLDING +
                         " WHERE iban=? AND isin=?"
                         " ORDER BY price_date DESC"
                         " LIMIT 2")
        vars_ = (bank.iban, isin, )
        result = self.execute(sql_statement, vars_=vars_)
        if not result:
            return
        data = []
        for row in result:
            data.insert(0, HoldingAcquisition(*row))
        pieces = data[0].pieces - data[-1].pieces
        if (len(data) > 1 and pieces == 0 and
                data[0].acquisition_price == data[-1].acquisition_price):
            # no change in position
            acquisition_amount = data[0].acquisition_amount
        else:
            if data[-1].price_currency == PERCENT:
                if check_main_thread():
                    data[-1].acquisition_amount = data[-1].total_amount
                    acquisition_input_amount = Acquisition(
                        header=MESSAGE_TEXT['ACQUISITION_HEADER'].format(
                            bank.iban, name_, data[0].price_date, data[-1].price_date),
                        data=data)
                    button_state = acquisition_input_amount.button_state
                    if button_state == WM_DELETE_WINDOW:
                        return button_state
                    holding_acquisition = HoldingAcquisition(
                        *acquisition_input_amount.array[-1])
                    acquisition_amount = dec2.convert(
                        holding_acquisition.acquisition_amount)
                else:  # ad just acquisition amount of percent price positions manually
                    MessageBoxInfo(message=MESSAGE_TEXT['ACQUISITION_AMOUNT'].format(bank.bank_name, bank.iban, name_, isin),
                                   bank=bank, information=WARNING)
                    acquisition_amount = data[0].acquisition_amount
            else:
                acquisition_amount = dec2.multiply(
                    data[-1].pieces, data[-1].acquisition_price)
        data[-1].acquisition_amount = acquisition_amount
        self.update_holding_acquisition(bank.iban, isin, data[-1])
        return button_state

    def _statements(self, bank):
        '''
        Storage of statements of >bank.account_number< starting from the last stored entry_date
        in table STATEMENT.
        For the first time: all available statements will be stored.
        Use of touchdowns is not implemented
        '''
        sql_statement = (
            "select max(entry_date) from " + STATEMENT + " where iban=?"
        )
        vars_ = (bank.iban,)
        max_entry_date = self.execute(sql_statement, vars_=vars_)
        if max_entry_date[0][0]:
            bank.from_date = max_entry_date[0][0]
        else:
            bank.from_date = date(2020, 1, 1)
        bank.to_date = date.today()
        if bank.scraper:
            bank.to_date = ''.join(str(bank.to_date))
            bank.from_date = ''.join(str(bank.from_date))
            statements = bank.download_statements(bank)
        else:
            statements = bank.dialogs.statements(bank)
        if statements:
            entry_date = None
            for statement in statements:
                if statement['entry_date'] != entry_date:
                    entry_date = statement['entry_date']
                    counter = 0
                statement['iban'] = bank.iban
                statement[DB_counter] = counter
                self.execute_replace(STATEMENT, statement)
                counter += 1
            self.execute('COMMIT;')
            transfer_statement_to_access(self, bank)
        return statements

    def _where_clause(self, **kwargs):
        '''
        Generates WHERE Clause of kwargs items
        kwargs contain >database_fieldname<=>value< AND ....  >database_fieldname< IN >list<  ...
               and optional key >clause< with additional >AND< >OR< condition parts
        result:  where    WHERE >database_fieldname<=? AND .... AND '
                 vars_    (>value<, ..>list<, .....)
        '''
        WHERE = ' WHERE '
        vars_ = ()
        where = WHERE
        clause = None
        for key, value in kwargs.items():
            if key == 'clause':
                clause = value
                where = where + ' ' + clause + '   AND '
            elif key == 'period':
                from_date, to_date = value
                if where != WHERE:
                    vars_ = vars_ + (from_date, to_date)
                else:
                    vars_ = (from_date, to_date)
                where = where + " price_date>=? AND price_date<=? AND "
            else:
                if isinstance(value, list):
                    where = where + ' ' + key + ' IN ('
                    for item in value:
                        where = where + "?,"
                        vars_ = vars_ + (item,)
                    where = where[:-1] + ') AND '
                else:
                    where = where + ' ' + key + '=? AND '
                    vars_ = vars_ + (value,)
        if vars_ or clause:
            return where[0:-5], vars_
        else:
            return ' ', vars_

    def all_accounts(self, bank):
        '''
        Insert downloaded  Bank Data in Database
        '''
        Informations.bankdata_informations = (Informations.bankdata_informations + '\n\n' + INFORMATION +
                                              MESSAGE_TEXT['DOWNLOAD_BANK'].format(bank.bank_name) + '\n\n')
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.account_product_name = account[KEY_ACC_PRODUCT_NAME]
            bank.iban = account[KEY_ACC_IBAN]
            Informations.bankdata_informations = Informations.bankdata_informations + '\n' + INFORMATION + (
                MESSAGE_TEXT['DOWNLOAD_ACCOUNT'].format(bank.bank_name, bank.account_number,
                                                        bank.account_product_name, bank.iban))
            if bank.scraper:
                if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    if self._statements(bank) is None:
                        Informations.bankdata_informations = (Informations.bankdata_informations + '\n' + WARNING +
                                                              MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                        return
            else:
                if 'HKWPD' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    if self._holdings(bank) is None:
                        Informations.bankdata_informations = (Informations.bankdata_informations + '\n' + WARNING +
                                                              MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                        return
                if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    if self._statements(bank) is None:
                        Informations.bankdata_informations = (Informations.bankdata_informations + '\n' + WARNING +
                                                              MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                        return
        Informations.bankdata_informations = (Informations.bankdata_informations + '\n\n' + INFORMATION +
                                              MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name) + '\n\n')
        if bank.scraper:
            try:
                bank.driver.quit()
            except Exception:
                pass

    def all_holdings(self, bank):
        '''
        Insert downloaded  Holding Bank Data in Database
        '''
        Informations.bankdata_informations = (Informations.bankdata_informations + '\n\n' + INFORMATION +
                                              MESSAGE_TEXT['DOWNLOAD_BANK'].format(bank.bank_name) + '\n\n')
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.iban = account[KEY_ACC_IBAN]
            if 'HKWPD' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                Informations.bankdata_informations = Informations.bankdata_informations + '\n' + INFORMATION + (
                    MESSAGE_TEXT['DOWNLOAD_ACCOUNT'].format(bank.bank_name, bank.account_number,
                                                            bank.account_product_name, bank.iban))
                if self._holdings(bank) is None:
                    Informations.bankdata_informations = (Informations.bankdata_informations + '\n' + WARNING +
                                                          MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                    return

    def destroy_connection(self):
        '''
        close connection >database<
        '''
        if self.conn.is_connected():
            self.conn.close()
            self.cursor.close()

    def execute(self, sql_statement, vars_=None, duplicate=False, result_dict=False):
        '''
        Parameter:  duplicate=True --> Ignore Error 1062 (Duplicate Entry)
                    result_dict -----> True: returns a list of dicts

        SQL SELECT:
        Method fetches all (or all remaining) rows of a query  result set
        and returns a list of tuples.
        If no rows are available, it returns an empty list.
        SQL REPLACE, UPDATE, ...
        Method executes SQL statement; no result set will be returned!
        rowcount = True   returns row_count of UPDATE, INSERT; DELETE
        '''
        # print(sql_statement, "\n", vars_, "\n")
        if self.holding_switch == HOLDING_T:
            sql_statement = sql_statement.replace(HOLDING, HOLDING_T)
            sql_statement = sql_statement.replace(HOLDING_T + '_t', HOLDING_T)

        try:
            if vars_:
                self.cursor.execute(sql_statement, vars_)
            else:
                self.cursor.execute(sql_statement)
            if select_statement.match(sql_statement.upper()):
                # returns result if sql_statement begins with SELECT
                result = []
                for item in self.cursor.fetchall():
                    result.append(item)
                if result_dict:
                    # contains fieldname in description tuple
                    fields = list(
                        map(lambda field: field[0], self.cursor.description))
                    # returns list of dictionaries
                    result = list(
                        map(lambda row: dict(zip(fields, row)), result))
                return result
            if rowcount_statement.match(sql_statement.upper()):
                # returns result if sql_statement begins with REPLACE, UPDATE,
                # DELETE, INSERT
                result = self.cursor.execute('SELECT row_count()')
                if result:
                    counted, = result[0]
                else:
                    counted = None
                return counted
            return None
        except mariadb.Error as error:
            if duplicate and error.errno == 1062:
                MessageBoxInfo(message=MESSAGE_TEXT['MARIADB_DUPLICATE'].format(
                    sql_statement, error, vars_))
                return error.errno
            else:
                message = MESSAGE_TEXT['MARIADB_ERROR_SQL'].format(
                    sql_statement, vars_)
                message = '\n\n'.join([
                    message, MESSAGE_TEXT['MARIADB_ERROR'].format(error.errno, error.errmsg)])
                filename = stack()[1][1]
                line = stack()[1][2]
                method = stack()[1][3]
                message = '\n\n'.join(
                    [message, MESSAGE_TEXT['STACK'].format(method, line, filename)])
                MessageBoxError(message=message)
                return False  # thread checking

    def execute_replace(self, table, field_dict):
        '''
        Insert/Change Record in MARIADB table
        '''
        set_fields = ' SET '
        vars_ = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            if table == ISIN and key_ == DB_name:
                field_dict[key_] = field_dict[key_].upper()
            vars_ = vars_ + (field_dict[key_],)
        sql_statement = "REPLACE INTO " + table + set_fields
        sql_statement = sql_statement[:-2]
        self.execute(sql_statement, vars_=vars_)

    def execute_update(self, table, field_dict, **kwargs):
        '''
        Updates columns of existing rows in the MARIADB table with new values
        '''
        where, vars_where = self._where_clause(**kwargs)
        set_fields = ' SET '
        vars_set = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            vars_set = vars_set + (field_dict[key_],)
        sql_statement = "UPDATE " + table + set_fields
        sql_statement = sql_statement[:-2] + where
        self.execute(sql_statement, vars_=vars_set + vars_where)

    def execute_delete(self, table, **kwargs):
        '''
        Deletion of record in MARIADB table
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "DELETE FROM " + table + where
        self.execute(sql_statement, vars_=vars_)

    def import_bankidentifier(self, filename):
        '''
        Import CSV file into table bankidentifier
        Download CSV from https://www.bundesbank.de/de/aufgaben/
        unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/
        download-bankleitzahlen-602592
        '''
        sql_statement = "DELETE FROM " + BANKIDENTIFIER
        self.execute(sql_statement)
        sql_statement = ("LOAD DATA LOW_PRIORITY LOCAL INFILE '" + filename +
                         "' REPLACE INTO TABLE " + BANKIDENTIFIER +
                         " CHARACTER SET latin1 FIELDS TERMINATED BY ';'"
                         " OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'"
                         " LINES TERMINATED BY '\r\n' IGNORE 1 LINES"
                         " (`code`, `payment_provider`, `payment_provider_name`, `postal_code`,"
                         " `location`, `name`, `pan`, `bic`, `check_digit_calculation`, `record_number`, `change_indicator`, `code_deletion`, `follow_code`);"
                         )
        self.execute(sql_statement)
        sql_statement = "DELETE FROM " + BANKIDENTIFIER + " WHERE payment_provider='2'"
        self.execute(sql_statement)
        return

    def import_holding_t(self, title, dataframe):
        '''
        Insert/Replace holdings of transactions
        '''
        # engine = sqlalchemy.create_engine(
        #    "mariadb+mariadbconnector://root:" + self.password + "@127.0.0.1:3306/" + self.database)
        try:
            credentials = ''.join(
                [self.user, ":", self.password, "@", self.host, "/", self.database])
            engine = sqlalchemy.create_engine(
                "mariadb+mariadbconnector://" + credentials)
            dataframe.to_sql(HOLDING_T, con=engine, index=False,
                             if_exists="append")
            self.execute('COMMIT')
        except sqlalchemy.exc.SQLAlchemyError as info:
            _sqlalchemy_exception(
                title, Informations.HOLDING_T_INFORMATIONS, info)
            return False

    def import_server(self, filename):
        '''
        Import CSV file into table server
                CSV_File contains 28 columns
        Registration see https://www.hbci-zka.de/register/prod_register.htm

        Imports only bank_code and server
        '''
        columns = 28
        csv_columns = ['@VAR' + str(x) for x in range(columns)]
        csv_columns[1] = 'code'
        csv_columns[24] = 'server'
        csv_columns = ', '.join([*csv_columns])
        sql_statement = "DELETE FROM " + SERVER
        self.execute(sql_statement)
        sql_statement = ("LOAD DATA LOW_PRIORITY LOCAL INFILE '" + filename +
                         "' REPLACE INTO TABLE " + SERVER +
                         " CHARACTER SET latin1 FIELDS TERMINATED BY ';'"
                         " OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'"
                         " LINES TERMINATED BY '\\r\\n'"
                         " IGNORE 1 LINES (" + csv_columns + ");")
        self.execute(sql_statement)
        sql_statement = "DELETE FROM " + SERVER + " WHERE server='\r'"
        for item in list(SCRAPER_BANKDATA.keys()):
            code = item
            server = SCRAPER_BANKDATA[code][0]
            sql_statement = ("INSERT INTO " + SERVER +
                             " SET code=?, server=?")
            vars_ = (code, server)  # bankdata[0] = >login Link<
            self.execute(sql_statement, vars_=vars_)
        return

    def import_transaction(self, iban, filename):
        '''
        Import CSV file into table transaction
        '''
        sql_statement = ("LOAD DATA LOW_PRIORITY LOCAL INFILE '" + filename +
                         "' REPLACE INTO TABLE " + TRANSACTION +
                         " CHARACTER SET latin1 FIELDS TERMINATED BY ';'"
                         " OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'"
                         " LINES TERMINATED BY '\r\n' IGNORE 1 LINES"
                         " (price_date, ISIN, counter, pieces, price)"
                         " SET iban='" + iban + "', transaction_type='"
                         + TRANSACTION_RECEIPT + "', "
                         " price_currency='EUR', amount_currency='EUR',"
                         " posted_amount=price*pieces, "
                         " origin='" + filename[-50:] + "'"
                         ";"
                         )
        self.execute(sql_statement)
        sql_statement = ("UPDATE " + TRANSACTION +
                         " SET transaction_type = ?, counter=Abs(counter), "
                         "pieces=Abs(pieces), posted_amount=Abs(posted_amount) WHERE pieces < 0")
        vars_ = (TRANSACTION_DELIVERY,)
        self.execute(sql_statement, vars_=vars_)

    def import_prices(self, title, dataframe):
        '''
        Insert/Replace prices
        '''

        # engine = sqlalchemy.create_engine(
        #    "mariadb+mariadbconnector://root:" + self.password + "@127.0.0.1:3306/" + self.database)
        credentials = ''.join(
            [self.user, ":", self.password, "@", self.host, "/", self.database])
        '''
        if_exists{>fail<, >replace<, >append<}, default >fail<
            How to behave if the table already exists.
            fail: Raise a ValueError.
            replace: Drop the table before inserting new values.
            append: Insert new values to the existing table.
        '''
        try:
            engine = sqlalchemy.create_engine(
                "mariadb+mariadbconnector://" + credentials)
            dataframe.to_sql(PRICES, con=engine, if_exists="append",
                             index_label=['symbol', 'price_date'])
            self.execute('COMMIT')
            return True
        except sqlalchemy.exc.SQLAlchemyError as info:
            _sqlalchemy_exception(
                title, Informations.PRICES_INFORMATIONS, info)
            return False

    def select_data_exist(self, table, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT EXISTS(SELECT * FROM " + table + where + ");")
        result = self.execute(sql_statement, vars_=vars_)
        if result == [(0,)]:
            return False    # exist not
        else:
            return True     # exist

    def select_dict(self, table, key_name, value_name, **kwargs):
        '''
        result: dictionary
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT " + key_name + ', ' + \
            value_name + " FROM " + table + where
        sql_statement = sql_statement + " ORDER BY name ASC;"
        result = self.execute(sql_statement, vars_=vars_)
        if result and len(result[0]) == 2:
            return dict(result)
        return {}

    def select_holding_acquisition(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT price_date, price_currency, market_price,"
                         " acquisition_price, pieces, amount_currency, total_amount, "
                         " acquisition_amount, origin FROM " + HOLDING + where)
        sql_statement = sql_statement + " ORDER BY price_date"
        result = self.execute(sql_statement, vars_=vars_)
        return list(map(lambda row: HoldingAcquisition(*row), result))

    def select_isin_adjustments(self):
        '''
        Return:  List of tuples (names, ISIN, adjustments) of table ISIN
        '''
        sql_statement = "SELECT name, symbol, adjustments FROM " + \
            ISIN + "  WHERE adjustments not in (NULL, NONE)"
        result = self.execute(sql_statement)
        names_list = list(map(lambda x: x[0], result))
        names_symbol_dict = dict(list(map(lambda x: (x[0], x[1]), result)))
        names_adjustment_dict = dict(list(map(lambda x: (x[0], x[2]), result)))
        return names_list, names_symbol_dict, names_adjustment_dict

    def select_isin_with_ticker(self, field_list, order=None, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        if isinstance(field_list, list):
            field_list = ','.join(field_list)
        sql_statement = "SELECT " + field_list + \
            " FROM " + ISIN + " WHERE symbol != 'NA'"
        if vars_:
            sql_statement = ' '.join([sql_statement, 'AND', where])
        if order is not None:
            if isinstance(order, list):
                order = ','.join(order)
            sql_statement = sql_statement + " ORDER BY " + order
        return self.execute(sql_statement, vars_=vars_)

    def select_holding_all_total(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT price_date, SUM(total_amount), SUM(acquisition_amount) "
                         " FROM " + HOLDING + where)
        sql_statement = sql_statement + " GROUP BY price_date ORDER BY price_date ASC;"
        return self.execute(sql_statement, vars_=vars_)

    def select_holding_total(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT price_date, total_amount_portfolio, SUM(acquisition_amount)"
                         " FROM " + HOLDING + where +
                         " GROUP BY price_date ORDER BY price_date ASC;")
        return self.execute(sql_statement, vars_=vars_)

    def select_holding_data(self,
                            field_list='ISIN, name, total_amount, acquisition_amount, pieces, market_price, price_currency, amount_currency',
                            result_dict=True,
                            **kwargs):
        '''
        returns a list (of dictionaries)
        '''
        if field_list:
            where, vars_ = self._where_clause(**kwargs)
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT " + field_list + " FROM " + HOLDING_VIEW + where
            result = self.execute(sql_statement, vars_=vars_,
                                  result_dict=result_dict)
            return result
        else:
            return []

    def select_holding_all_isins_acquisition_amount(self, **kwargs):
        '''
        returns a dictionary: key: ISIN, value: current acquisition_amount
        '''
        max_price_date = self.select_max_price_date(HOLDING, **kwargs)
        if max_price_date:
            where, vars_ = self._where_clause(**kwargs)
            sql_statement = "SELECT ISIN, acquisition_amount FROM " + HOLDING + where
            result_list = self.execute(sql_statement, vars_=vars_)
            if result_list and len(result_list) == 2:
                return dict(result_list)
        return None

    def select_holding_last(self, iban, isin, period,
                            field_list='price_date, market_price, pieces, total_amount, acquisition_amount'):
        '''
        returns tuple with last portfolio entries
        '''
        last_download = self.select_max_price_date(
            HOLDING, iban=iban, isin=isin, period=period)
        if last_download is not None:
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = ("SELECT " + field_list + " FROM " + HOLDING_VIEW +
                             " WHERE iban=? AND ISIN=? AND price_date=?")
            vars_ = (iban, isin, str(last_download))
            result = self.execute(sql_statement, vars_=vars_)
            return result[0]
        else:
            return None

    def select_holding_pre_day(self, iban, isin, period,
                               field_list='price_date, market_price, pieces, total_amount, acquisition_amount'):
        '''
        returns tuple with second last portfolio entries
        '''
        from_date, to_date = period
        pre_day = self.select_max_price_date(
            HOLDING, iban=iban, isin=isin, period=period)
        if pre_day is not None:
            if str(pre_day) == str(datetime.today())[0:10]:
                download_today = self.select_max_price_date(
                    HOLDING, iban=iban, period=(to_date,  to_date))
                if download_today is None:      # download not yet executed on  to_date
                    return None
                pre_day = pre_day - timedelta(days=1)
                pre_day = self.select_max_price_date(
                    HOLDING, iban=iban, isin=isin, period=(from_date, pre_day))
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = ("SELECT " + field_list + " FROM " + HOLDING_VIEW +
                             " WHERE iban=? AND ISIN=? AND price_date=?")
            vars_ = (iban, isin, str(pre_day))
            result = self.execute(sql_statement, vars_=vars_)
            return result[0]
        else:
            return None

    def select_holding_fields(self, field_list='price_date', **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT DISTINCT " + field_list + " FROM " + HOLDING + where
        result = []
        for item in self.execute(sql_statement, vars_=vars_):
            field_value, = item
            result.append(field_value)
        return result

    def select_sepa_transfer_creditor_data(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT applicant_iban, applicant_bic, purpose FROM " + STATEMENT +
                         where + " ORDER BY date DESC;")
        result = self.execute(sql_statement, vars_=vars_)

        if result:
            applicant_iban, applicant_bic, purpose = result[0]
            return applicant_iban, applicant_bic, purpose
        else:
            return None, None, None

    def select_sepa_transfer_creditor_names(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT DISTINCT applicant_name FROM " + STATEMENT +
                         where + " ORDER BY applicant_name ASC;")
        result = self.execute(sql_statement, vars_=vars_)
        creditor_names = []
        for item in result:
            creditor_name, = item
            creditor_names.append(creditor_name)
        return creditor_names

    def select_server_code(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT code FROM " + SERVER + where
        result = self.execute(sql_statement, vars_=vars_)
        bank_codes = []
        for item in result:
            bank_code, = item
            bank_codes.append(bank_code)
        return bank_codes

    def select_server(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT server FROM " + SERVER + where
        result = self.execute(sql_statement, vars_=vars_)
        servers = []
        for item in result:
            server, = item
            servers.append(server)
        return servers

    def select_table(self, table, field_list, order=None, result_dict=False, **kwargs):

        if field_list:
            where, vars_ = self._where_clause(**kwargs)
            if table == STATEMENT:
                where = where.replace(DB_price_date, 'date')
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            else:
                field_list = '*'
            sql_statement = "SELECT " + field_list + " FROM " + table + where
            if order is not None:
                if isinstance(order, list):
                    order = ','.join(order)
                sql_statement = sql_statement + " ORDER BY " + order
            return self.execute(sql_statement, vars_=vars_, result_dict=result_dict)
        else:
            return []

    def select_table_distinct(self, table, field_list, order=None, **kwargs):

        if field_list:
            where, vars_ = self._where_clause(**kwargs)
            if table == STATEMENT:
                where = where.replace(DB_price_date, 'date')
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT DISTINCT " + field_list + " FROM " + table + where
            if order is not None:
                if isinstance(order, list):
                    order = ','.join(order)
                sql_statement = sql_statement + " ORDER BY " + order
            return self.execute(sql_statement, vars_=vars_)
        else:
            return []

    def select_table_next(self, table, field_list, key_name, sign, key_value, **kwargs):

        assert sign in [
            '>', '>=', '<', '<='], 'Comparison Operators {} not allowed'.format(sign)
        if field_list:
            where, vars_ = self._where_clause(**kwargs)
            if vars_:
                where = where + ' AND '
            else:
                where = ' WHERE '
            if table == STATEMENT:
                where = where.replace(DB_price_date, 'date')
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT " + field_list + " FROM " + table + \
                where + key_name + sign + "? ORDER BY " + key_name
            if sign in ['>', '>=']:
                sql_statement = sql_statement + " LIMIT 1"
            else:
                sql_statement = sql_statement + " DESC LIMIT 1"
            vars_ = vars_ + (key_value,)
            return self.execute(sql_statement, vars_=vars_)
        else:
            return []

    def select_total_amounts(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        where = where.replace(DB_price_date, 'date')
        from_date, to_date = vars_
        vars_ = (str(datetime.strptime(
            from_date, "%Y-%m-%d").date() + timedelta(days=1)), to_date)
        # search first row if no statements/holding in period., use it for as
        # from_date data
        sql_statement = ("WITH max_date_rows AS (SELECT iban AS max_iban, MAX(entry_date) AS max_date FROM " + STATEMENT + " WHERE entry_date <= '" + from_date + "' GROUP BY iban) "
                         "SELECT iban, date('" + from_date + "'), closing_status AS status, closing_balance AS saldo FROM " + STATEMENT + ", max_date_rows WHERE iban = max_iban AND entry_date = max_date GROUP BY iban;")
        first_row_statement = self.execute(sql_statement)
        sql_statement = ("WITH max_date_rows AS (SELECT iban AS max_iban, MAX(price_date) AS max_date FROM " + HOLDING + " WHERE price_date <= '" + from_date + "' GROUP BY iban) "
                         "SELECT iban, date('" + from_date + "'), '" + CREDIT + "' AS status, total_amount_portfolio AS saldo FROM " + HOLDING + ", max_date_rows WHERE iban = max_iban AND price_date = max_date GROUP BY iban;")
        first_row_holding = self.execute(sql_statement)
        sql_statement = ("WITH total_amounts AS ("
                         "SELECT iban, price_date AS date, '" + CREDIT +
                         "' AS status, total_amount_portfolio AS saldo  FROM "
                         + HOLDING + " GROUP BY iban, price_date "
                         " UNION "
                         "SELECT iban, entry_date AS date, closing_status AS status, closing_balance AS saldo FROM "
                         + STATEMENT + " GROUP BY iban, entry_date) "
                         "SELECT iban, date, status, saldo FROM total_amounts " + where)
        result = self.execute(sql_statement, vars_=vars_)
        return first_row_statement + first_row_holding + result

    def select_max_price_date(self, table, field_name_date=DB_price_date, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT max(" + field_name_date + \
            ") FROM " + table + where
        result = self.execute(sql_statement, vars_=vars_)
        if result:
            return result[0][0]  # returns max_price_date
        else:
            return None

    def select_first_price_date_of_prices(self, symbol_list, **kwargs):
        '''
        Selects first price_date of symbols in symbol_list in table PRICES
        for which row exists for all symbols
        skips symbols with no row
        '''
        where, vars_ = self._where_clause(**kwargs)
        if vars_:
            where = where + ' AND '
        else:
            where = ' WHERE '
        price_dates = []
        for symbol in symbol_list:
            symbol = "'" + symbol + "'"
            sql_statement = ' '.join(
                ["SELECT MIN(", DB_price_date, ") FROM ", PRICES, where, DB_symbol, "=", symbol])
            result = self.execute(sql_statement, vars_)
            if result[0][0]:
                # convert datetime to string
                price_dates.append(str(result[0][0])[:10])
        if price_dates:
            return max(price_dates)
        else:
            return None

    def row_exists(self, table, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT EXISTS(SELECT * FROM " + table + where + ")"
        result = self.execute(sql_statement, vars_=vars_)
        if result:
            return result[0][0]  # returns 1/0

    def select_transactions_data(
            self,
            field_list='price_date, counter, transaction_type, price_currency,\
                          price, pieces, amount_currency, posted_amount, comments',
            **kwargs):
        ''' returns a list of tuples '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT  " + field_list +
                         " FROM " + TRANSACTION + where)
        sql_statement = sql_statement + " ORDER BY price_date ASC, counter ASC;"
        return self.execute(sql_statement, vars_=vars_)

    def transaction_pieces(self, **kwargs):
        '''
        Returns transaction balance of pieces
        '''
        where, vars_ = self._where_clause(**kwargs)

        sql_statement = ("SELECT  t1.ISIN, t1.NAME, t1.pieces FROM"
                         " (SELECT t.ISIN, t.name, SUM(t.pieces) AS pieces FROM"
                         " (SELECT ISIN, name, SUM(pieces) AS pieces FROM transaction_view "
                         + where + " AND transaction_type = '" + TRANSACTION_RECEIPT +
                         "' GROUP BY name"
                         " UNION"
                         " SELECT ISIN, name, -SUM(pieces) AS pieces FROM transaction_view "
                         + where + " AND transaction_type = '" + TRANSACTION_DELIVERY +
                         "' GROUP BY name ) AS t  GROUP BY t.ISIN) AS t1 WHERE t1.pieces != 0")
        return self.execute(sql_statement, vars_ + vars_)

    def _transaction_profit_closed_sql(self, where):

        sql_statement = ("SELECT t.isin AS isin, t. NAME AS name, sum(posted_amount) as profit, amount_currency, sum(pieces) FROM \
                         (\
                         (SELECT  isin, NAME, price_date, counter, transaction_type, price, sum(pieces) AS pieces, \
                          sum(posted_amount) AS posted_amount, amount_currency FROM " + TRANSACTION_VIEW + where +
                         " AND transaction_type='" + TRANSACTION_DELIVERY +
                         "' GROUP BY isin ORDER  by price_date ASC, counter ASC) \
                         UNION \
                         (SELECT  isin, NAME, price_date, counter, transaction_type, price, -sum(pieces) AS pieces, \
                         -sum(posted_amount)AS posted_amount, amount_currency  FROM " + TRANSACTION_VIEW + where +
                         " AND transaction_type='" + TRANSACTION_RECEIPT +
                         "' GROUP BY isin ORDER  by price_date ASC, counter ASC)\
                         ) \
                         AS t GROUP BY t.isin HAVING sum(pieces) = 0")
        return sql_statement

    def transaction_profit_closed(self, **kwargs):
        '''
        Returns profit of closed stocks
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = self._transaction_profit_closed_sql(where)
        return self.execute(sql_statement, vars_ + vars_)

    def _transaction_profit_portfolio_sql(self, where, max_price_date):

        sql_statement = ("SELECT ISIN, name, total_amount AS profit, \
                         amount_currency AS currency, pieces FROM " + HOLDING_VIEW +
                         + where + " AND price_date='" + str(max_price_date) +
                         "' GROUP BY ISIN ")
        return sql_statement

    def transaction_profit_all(self, **kwargs):
        '''
        Returns profit all transactions inclusive portfolio values
        '''
        where, vars_ = self._where_clause(**kwargs)
        max_price_date = self.select_max_price_date(HOLDING, **kwargs)
        if max_price_date is None:
            return None
        else:
            sql_statement = (self._transaction_profit_closed_sql(where) +
                             " UNION  "
                             " SELECT ISIN, name, (total_amount - acquisition_amount) AS profit,"
                             " amount_currency AS currency, pieces FROM holding_view "
                             + where + " AND price_date='" + str(max_price_date) +
                             "' GROUP BY ISIN ")
        return self.execute(sql_statement, vars_ + vars_ + vars_)

    def transaction_portfolio(self, **kwargs):
        '''
        Returns comparison between Portfolio and stored Transactions
        '''
        where, vars_ = self._where_clause(**kwargs)
        max_price_date = self.select_max_price_date(HOLDING, **kwargs)
        if max_price_date is None:
            return None
        else:
            result_transaction = self.transaction_pieces(**kwargs)
            sql_statement = ("SELECT isin, NAME, pieces FROM holding_view" + where +
                             " AND price_date='" + str(max_price_date) + "'")
            result_portfolio = self.execute(sql_statement, vars_)
            result = []
            for item in set(result_transaction).symmetric_difference(set(result_portfolio)):
                if item in result_portfolio:
                    result.append(('PORTFOLIO',) + item)
                else:
                    result.append(('TRANSACTION',) + item)
            return result

    def transaction_change(self, iban, transaction):
        '''
        Modify of transaction in MARIADB table TRANSACTION

        '''
        sql_statement = "REPLACE INTO " + TRANSACTION + " SET iban=?"
        vars_ = (iban,)
        for key in transaction:
            if key in self.table_fields[TRANSACTION] and key != DB_name:
                if transaction[key] is not None:
                    sql_statement = sql_statement + ", " + str(key) + " =?"
                    vars_ = vars_ + (transaction[key],)
        self.execute(sql_statement, vars_)

    def transaction_delete(self, **kwargs):
        '''
        Deletion of transaction in MARIADB table TRANSACTION
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "DELETE FROM " + TRANSACTION + where
        self.execute(sql_statement, vars_=vars_)

    def transaction_new(self, iban, transaction, data_table=[]):
        '''
        Storage of transaction of >bank.account_number<
        in MARIADB table TRANSACTION
        '''
        if (self.row_exists(TRANSACTION, iban=iban, isin=transaction['ISIN'],
                            price_date=transaction[DB_price_date], counter=transaction[DB_counter])):
            filtered_data_table = []
            if isinstance(transaction[DB_price_date], str):
                price_date = datetime.strptime(
                    transaction[DB_price_date], '%Y-%m-%d').date()
            else:
                price_date = transaction[DB_price_date]
            for item in filter(lambda item: item[0] == price_date, data_table):
                if item.counter >= int(transaction[DB_counter]):
                    filtered_data_table.append(item)
            if filtered_data_table:
                for item in reversed(filtered_data_table):
                    counter = item.counter + 1
                    sql_statement = ("UPDATE " + TRANSACTION + " SET counter = ?" +
                                     " WHERE iban=? AND ISIN=? AND price_date=? and counter=? ")
                    vars_ = (counter, iban, transaction['ISIN'], transaction[DB_price_date],
                             transaction[DB_counter])
                    self.execute(sql_statement, vars_=vars_)
        sql_statement = "INSERT INTO " + TRANSACTION + " SET iban=?"
        vars_ = (iban,)
        for key in transaction:
            if key in self.table_fields[TRANSACTION] and key != DB_name:
                if transaction[key] is not None:
                    vars_ = vars_ + (transaction[key],)
                    sql_statement = sql_statement + ", " + str(key) + "=?"
        self.execute(sql_statement, vars_=vars_)

    def transaction_sync(self, iban, isin, name, data):
        '''
        Synchronisation Portfolio and Transactions
        '''

        transaction_fields = {
            DB_ISIN: isin,
            DB_price_date: data[-1].price_date,
            DB_counter: 0,
            DB_name: name,
            DB_transaction_type: TRANSACTION_RECEIPT,
            DB_price_currency: data[-1].price_currency,
            DB_price: data[-1].acquisition_price,
            DB_pieces: data[-1].pieces,
            DB_amount_currency: data[-1].amount_currency,
            DB_posted_amount: data[-1].acquisition_amount
        }
        generated = []
        if len(data) == 1:  # create first transaction
            self.transaction_new(iban, transaction_fields)
            generated.append(transaction_fields)
        else:
            pieces = dec2.subtract(data[-1].pieces, data[0].pieces)
            if pieces > 0:  # receipt (buy), create transaction
                transaction_fields[DB_pieces] = pieces
                transaction_fields[DB_posted_amount] = dec2.subtract(data[-1].acquisition_amount,
                                                                     data[0].acquisition_amount)
                self.transaction_new(iban, transaction_fields)
                generated.append(transaction_fields)
            elif pieces < 0:  # delivery (sell)
                pieces = pieces.copy_negate()
                transaction_fields[DB_transaction_type] = TRANSACTION_DELIVERY
                transaction_fields[DB_price] = data[-1].market_price
                pieces = pieces.copy_abs()
                transaction_fields[DB_pieces] = pieces
                part = dec6.divide(pieces, data[0].pieces)
                transaction_fields[DB_posted_amount] = dec2.multiply(
                    data[-1].total_amount, part)
                self.transaction_new(iban, transaction_fields)
                generated.append(transaction_fields)
        return generated

    def transaction_sell_off(self, iban, isin, name, data):
        '''
        Sell Off Transaction of ISIN
        '''
        max_price_date = self.select_max_price_date(
            TRANSACTION, iban=iban, isin=isin)
        transaction = {
            'ISIN': isin,
            DB_price_date: data[-1].price_date,
            DB_counter: 0,
            DB_name: name,
            DB_transaction_type: TRANSACTION_DELIVERY,
            DB_price_currency: data[-1].price_currency,
            DB_price: data[-1].market_price,
            DB_pieces: data[-1].pieces,
            DB_amount_currency: data[-1].amount_currency,
            DB_posted_amount: dec2.convert(data[-1].total_amount)
        }
        if max_price_date == data[-1].price_date:
            transaction[DB_counter] = 1
        sql_statement = "INSERT INTO " + TRANSACTION + " SET iban=?"
        vars_ = (iban,)
        for key in transaction:
            if key in self.table_fields[TRANSACTION] and key != DB_name:
                if transaction[key] is not None:
                    vars_ = vars_ + (transaction[key],)
                    sql_statement = sql_statement + ", " + str(key) + "=?"
        result = self.execute(sql_statement, vars_=vars_, duplicate=True)
        if result is not None:
            transaction[DB_transaction_type] = result
        return [transaction]

    def update_holding_acquisition(self, iban, isin, HoldingAcquisition, period=None, mode=None):

        if HoldingAcquisition.origin == ORIGIN:
            sql_statement = ("UPDATE " + HOLDING +
                             " SET acquisition_amount=? WHERE iban=? AND ISIN=?")
            vars_ = (HoldingAcquisition.acquisition_amount, iban, isin,
                     HoldingAcquisition.price_date)
        else:
            sql_statement = ("UPDATE " + HOLDING + " SET acquisition_price=?, "
                             " acquisition_amount=? WHERE iban=? AND ISIN=?")
            vars_ = (HoldingAcquisition.acquisition_price, HoldingAcquisition.acquisition_amount,
                     iban, isin, HoldingAcquisition.price_date)
        if mode is None:
            sql_statement = sql_statement + " AND price_date=?"
        else:
            if period is None:
                sql_statement = sql_statement + " AND price_date>=?"
            else:
                _, to_date = period
                vars_ = vars_ + (to_date,)
                sql_statement = sql_statement + " AND price_date>=? AND price_date<=?"
        self.execute(sql_statement, vars_=vars_)

    def update_prices_histclose(self, name, symbol, adjustments):

        adjustments = loads(adjustments)
        for to_date, adjustment in adjustments.items():
            r_factor, used = adjustment
            if used == FALSE:
                # calculate histclose
                sql_statement = "UPDATE " + PRICES + \
                    " SET histclose = close / " + r_factor + " WHERE symbol=? AND price_date<=?"
                vars_ = (symbol, to_date)
                self.execute(sql_statement, vars_=vars_)
                adjustments[to_date] = (r_factor, TRUE)

        sql_statement = "UPDATE " + PRICES + \
            " SET histclose=close WHERE symbol=? AND histclose=0"
        vars_ = (symbol)
        self.execute(sql_statement, vars_=vars_)

        adjustments[to_date] = (r_factor, TRUE)
        sql_statement = "UPDATE " + ISIN + " SET adjustments=?  WHERE name=?"
        vars_ = (dumps(adjustments), name)
        self.execute(sql_statement, vars_=vars_)
