"""
Created on 18.11.2019
__updated__ = "2024-05-19"
@author: Wolfgang Kramer
"""

import collections
import functools
import glob
import inspect
import operator
import os
import re
import shelve
import sys
import traceback
import requests

from threading import current_thread, main_thread
from tkinter import Tk, messagebox, TclError
from inspect import stack
from datetime import date, timedelta, datetime
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, DivisionByZero

from banking.declarations import (
    BANK_MARIADB_INI,
    EURO,
    KEY_ACCOUNTS, KEY_ACC_ACCOUNT_NUMBER, KEY_BANK_NAME, KEY_DIRECTORY,
    KEY_ACC_PRODUCT_NAME, KEY_ACC_IBAN,
    MESSAGE_TEXT, MESSAGE_TITLE,
    WIDTH_TEXT
)


def check_main_thread():
    """
    True if main thread is in main loop
    """
    # check if its the main thread, Tkinter can be used otherwise avoid T Tk()
    if current_thread() is main_thread():
        return True
    else:
        return False


def date_before_date(date_before, date_current):
    '''
    returns True if date current is next weekday after date_before
    and not a weekend day
    '''
    # Monday is 0 and Sunday is 6
    if isinstance(date_before, str):
        date_before = Datulate().convert(date_before)
    weekday_before = date.weekday(date_before)
    if isinstance(date_current, str):
        date_current = Datulate().convert(date_current)
    weekday_current = date.weekday(date_current)
    if weekday_before in [4, 5, 6] and weekday_current == 0:
        return True
    elif weekday_before in [0, 1, 2, 3] and weekday_current - weekday_before == 1:
        return True
    else:
        return False


def find_pattern(string, pattern):

    if isinstance(string, str):
        find = re.compile(pattern)
        pos = find.search(string)
        if pos:
            return pos.start()
    return None


def list_positioning(listing, pattern):

    # returns 1st item (and index) of listing or next greater or last one
    if not isinstance(listing, list):
        Termination()
    if not listing:
        return listing, 0
    item = ''
    pattern = pattern.lower()
    for _item in listing:
        _item = str(_item)
        if _item.startswith(pattern) or pattern <= _item[:len(pattern)].lower():
            item = _item
            break
    if item == '' and len(listing) > 0:
        item = listing[len(listing) - 1]
    return item, listing.index(item)


def max_len_item(item_list):

    # returns length of list's longest item
    return len(max(item_list, key=len, default=10))


def only_alphanumeric(string_value):

    # Returns only alphanumeric Characters of String_Value '
    return ''.join(char_ for char_ in string_value if char_.isalnum())


def http_error_code(server):
    """
    1    1xx Informational response
    2    2xx Success
    3    3xx Redirection
    4    4xx Client errors
    5    5xx Server errors

    200 OK
        Standard response for successful HTTP requests.
        The actual response will depend on the request method used.
        In a GET request, the response will contain an entity corresponding to
        the requested resource.
        In a POST request, the response will contain an entity describing or
        containing the result of the action.[8]
    404 Not Found
        The requested resource could not be found but may be available in the future.
        Subsequent requests by the client are permissible.
    405 Method Not Allowed
        A request method is not supported for the requested resource;
        for example, a GET request on a form that requires data to be presented via POST,
        or a PUT request on a read-only resource.

    """
    try:
        request = requests.get(server)
        return request.status_code
    except Exception:
        return 999


def exception_error(title=MESSAGE_TITLE, message=''):
    """
    stack()[1][1]     gets the current module
    stack()[1][2]     gets the current line
    stack()[1][3]     gets the current method
    sys.exc_info()
                    If no exception is being handled anywhere on the stack, a tuple
                    containing three None values is returned.
                    Otherwise, the values returned are (type, value, traceback).
                    Their meaning is:

                    type     gets the type of the exception being handled
                             (a subclass of BaseException);

                    value     gets the exception instance (an instance of the exception type);

                    traceback gets a traceback object which encapsulates the call stack at the point
                              the exception originally occurred.
    """

    _type, _value, _traceback = sys.exc_info()
    _traceback = traceback.extract_tb(_traceback)
    try:
        _message = (message + '\n\n' + MESSAGE_TEXT['UNEXCEPTED_ERROR'].format(
            stack()[1][1], stack()[1][2], stack()[1][3], _type, _value.args[0],  _traceback))
    except Exception:
        print("_type, _value, _traceback = sys.exc_info()",
              _type, _value, _traceback)
    # check if its not the main thread, avoid Tk() or ..
    if current_thread() is main_thread():
        Info(title=title, message=_message)
    else:
        print(_message)


def type_error(message=MESSAGE_TEXT['STACK']):

    filename = inspect.stack()[1][1]
    line = inspect.stack()[1][2]
    method = inspect.stack()[1][3]
    Termination(info='TypeError' + '\n' +
                message.format(method, line, filename))


def value_error(message=MESSAGE_TEXT['STACK']):

    filename = inspect.stack()[1][1]
    line = inspect.stack()[1][2]
    method = inspect.stack()[1][3]
    Termination(info='ValueError' + '\n' +
                message.format(method, line, filename))


def copy_list(list_):

    # return a copy of list; same as shallow copy
    list_copy = list_[:]
    return list_copy


def list_item_dict2tupl(dict_list):

    # returns a list of tuples
    if isinstance(dict_list, list):
        tuple_list = []
        for item in dict_list:
            if isinstance(item, dict):
                tuple_list.append(tuple(item.values()))
            else:
                type_error()
        return tuple_list
    else:
        type_error()


def list_of_tuples2list_of_dicts(list_of_tuples):

    # returns a list of tuples (tuple contains 2,3,..  elemnets) to a list of
    # dicts (1,2 .. values as tuple)
    if isinstance(list_of_tuples, list):
        list_of_dicts = []
        for _tuple in list_of_tuples:
            if isinstance(_tuple, tuple):
                dict[_tuple[0]] = _tuple[0:]
            else:
                type_error()
        return list_of_dicts
    else:
        type_error()


def dict_get_first_key(dictionary, value):

    # Returns first KEY key of a given VALUE of a DICTIONARY
    for key in dictionary.keys():
        if dictionary[key] == value:
            return key
    return None


def dict_get_all_keys(dictionary, value):

    # Returns all KEYS of a given VALUE value in DICTIONARY dictionary as a
    # list
    matches = []
    for key in dictionary.keys():
        if dictionary[key] == value:
            matches.append(key)
    return matches


def dict_sum_all_key(dictionary):

    # return the sum of values of dictionary
    # with same keys in list of dictionary
    return dict(functools.reduce(operator.add,
                                 map(collections.Counter, dictionary)))


def delete_shelve_files(shelve_name):

    shelve_name = shelve_name
    shelve_file = (os.path.join(os.getcwd(), shelve_name))
    try:
        shelve_file = (os.path.join(os.getcwd(), shelve_name))
        os.remove(shelve_file + '.dat')
    except Exception:
        pass
    try:
        shelve_file = (os.path.join(os.getcwd(), shelve_name))
        os.remove(shelve_file + '.dir')
    except Exception:
        pass
    try:
        shelve_file = (os.path.join(os.getcwd(), shelve_name))
        os.remove(shelve_file + '.bak')
    except Exception:
        pass


def shelve_filename(shelve_name):
    return shelve_name
    if shelve_name != BANK_MARIADB_INI:
        shelve_name = shelve_get_key(
            BANK_MARIADB_INI, KEY_DIRECTORY) + shelve_name
    return shelve_name


def shelve_exist(shelve_name):
    """ PARAMETER:     shelve_name
        RETURN:        True if shelve_file exists
    """
    shelve_name = shelve_filename(shelve_name)
    if os.path.exists(shelve_name + '.dat') and os.path.exists(shelve_name + '.dir'):
        return True
    else:
        return False


def shelve_get_key(shelve_name, key, none=True, flag='r'):
    """
        PARAMETER:     KEY of type LIST
        RETURN:        DICTIONARY {key:value,...}
                        (key not found, value = NONE or if none=False empty dict)
        PARAMETER:     KEY of type STRING
        RETURN:        Value of Key; key not found, value = NONE

    """

    shelve_name = shelve_filename(shelve_name)
    if os.path.exists(shelve_name + '.dat') and os.path.exists(shelve_name + '.dir'):
        with shelve.open(shelve_name, flag=flag, protocol=None, writeback=False) as shelve_file:
            if isinstance(key, list):
                key_exist = []
                key_missing = []
                for _item in key:
                    if _item in shelve_file:
                        key_exist.append(_item)
                    else:
                        key_missing.append(_item)
                _dict = {}
                for _item in key_exist:
                    try:
                        _dict[_item] = shelve_file[_item]
                    except Exception:
                        _dict[_item] = ''
                if none:
                    for _item in key_missing:
                        _dict[_item] = None
                return _dict
            if isinstance(key, str):
                if key in shelve_file:
                    return shelve_file[key]
                else:
                    return None
            type_error()
    else:
        # shelve-files incomplete or missing
        delete_shelve_files(shelve_name)
        Termination(info=MESSAGE_TEXT['OS_ERROR'].format(shelve_name))


def shelve_put_key(shelve_name, data, flag='w'):
    """ PARAMETER:   data: LIST of tuples (key, value)   or
                     data: TUPLE (key, value)

            The optional flag argument can be:
            Value    Meaning
            r    Open existing database for reading only (default)
            w    Open existing database for reading and writing
            c    Open database for reading and writing, creating it if it not exist
            n    Always create a new, empty database, open for reading and writing
    """

    shelve_name = shelve_filename(shelve_name)
    with shelve.open(shelve_name, flag=flag, protocol=None, writeback=True) as shelve_file:
        if isinstance(data, list):
            for tupl in data:
                key, value = tupl
                shelve_file[key] = value
            shelve_file.close()
            return
        if isinstance(data, tuple):
            key, value = data
            shelve_file[key] = value
            shelve_file.close()
            return
        value_error()


def listbank_codes():

    shelvefiles = glob.glob('*.dir')
    bank_codes = []
    for bank_code in shelvefiles:
        bank_code = bank_code.strip('.dir')
        if len(bank_code) == 8:
            try:
                int(bank_code)
                bank_codes.append(bank_code)
            except ValueError:
                pass
    return bank_codes


def dict_all_ibans():
    """
    Returns a list of all banks with ibans
    """
    dict_all_ibans = {}
    bank_names = dictbank_names()
    for bank_code in bank_names.keys():
        accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
        for account in accounts:
            dict_all_ibans[account[KEY_ACC_IBAN]
                           ] = account[KEY_ACC_PRODUCT_NAME]
    return dict_all_ibans


def dictbank_names():
    """
    Returns customized BankNames, alternative BankCodes
    """
    bank_names = {}
    for bank_code in listbank_codes():
        bank_name = shelve_get_key(bank_code, KEY_BANK_NAME)
        if bank_name:
            bank_names[bank_code] = bank_name
        else:
            bank_names[bank_code] = bank_code
    return bank_names


def dictaccount(bank_code, account_number):
    """
    Returns Account Information from Shelve-File/HIUPD
    """
    accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
    acc = next(
        (acc for acc in accounts if acc[KEY_ACC_ACCOUNT_NUMBER] == account_number.lstrip('0')), None)
    return acc


def create_iban(bank_code=None, account_number=None):

    # Eine deutsche IBAN wird wie folgt aus Kontonummer und Bankleitzahl berechnet:
    #
    #        Bilde aus Bankleitzahl, Kontonummer und Laenderkennung eine Zahl.
    #        Am Anfang der Zahl steht die Bankleitzahl.
    #        Die Kontonummer wird, falls sie weniger als zehn Stellen hat, mit fuehrenden Nullen
    #        auf zehn Stellen erweitert.
    #        Falls eine der zahlreichen Sonderregeln fuer die gegebene Bankverbindung gilt, koennte
    #        es auch noetig sein, die Kontonummer auf eine andere Art auf 10 Stellen zu erweitern
    #        oder die Bankleitzahl zu modifizieren.
    #        Die zehnstellige Kontonummer wird an die Bankleitzahl angehaengt.
    #        Schließlich werden noch die Ziffern 131400 angehaengt.
    #        Diese Ziffern stehen fuer "DE00";
    #        Buchstaben werden in zweistellige Ziffern umgewandelt, wobei A den Wert 10 erhaelt,
    #        B den Wert 11 usw.
    #        Beispiel:
    #         Fuer die Kontonummer 123456789 und die Bankleitzahl 50010517 ergibt sich die Zahl
    #         0105170123456789131400.
    #         Der Rest der Division dieser 24stelligen Zahl durch 97 wird von 98 abgezogen.
    #         Sollte das eine einstellige Zahl ergeben, wird sie um eine fuehrende Null erweitert.
    #         Das Resultat sind zwei Pruefziffern.
    verification_number = (
        str(98 - int(bank_code + str(account_number.zfill(10)) + '131400') % 97).zfill(2)
    )
    iban = 'DE' + verification_number + \
        bank_code + str(account_number.zfill(10))
    return iban


def check_iban(iban=None):
    """
    Checks only DE IBAN
    """
    if iban[0:2] == 'DE':
        verification_number = (
            str(98 - int(iban[4:12] +
                         str(iban[12:].zfill(10)) + '131400') % 97).zfill(2)
        )
        if verification_number != iban[2:4]:
            return False
    return True


def printer(print_columns=['col1', 'col2', 'col4'], print_line_length=WIDTH_TEXT,
            def_columns={'col1': (12, 0, 'char'), 'col2': (12, 2, 'decimal'),
                         'col3': (12, 0, 'char'), 'col4': (12, 0, 'date')},
            data_list=[{'col1': 'col1 text', 'col2': 21.45,
                        'col3': 'col3 text', 'col4': '2020-02-01'}]):
    header = ''
    for column in print_columns:
        def_length, def_dec_places, def_type = def_columns[column]
        if def_type == 'varchar':
            def_length = len(column)
            def_columns[column] = (def_length, def_dec_places, def_type)
            for data_line in data_list:
                try:
                    data_line_column = data_line[column]
                    if data_line_column is not None:
                        data_line_column = data_line_column.strip()
                except KeyError:
                    data_line_column = None
                if data_line_column is not None:
                    def_length_new = len(str(data_line_column))
                    if def_length_new > def_length:
                        def_columns[column] = (
                            def_length_new, def_dec_places, def_type)
                        def_length = def_length_new
    for column in print_columns:
        def_length, def_dec_places, def_type = def_columns[column]
        formatcolumn = '{:^' + str(def_length) + '}'
        header = header + \
            formatcolumn.format(column.upper())[0:def_length] + '|'
    print_list = ''
    for data_line in data_list:
        print_line = ''
        for column in print_columns:
            def_length, def_dec_places, def_type = def_columns[column]
            try:
                value = data_line[column]
            except KeyError:
                value = ''
            if value is None:
                value = ' '
            if def_type in ['int', 'smallint']:
                formatline = '{:>' + str(def_length) + '}'
            elif def_type == 'decimal':
                formatline = '{: ' + str(def_length) + \
                    '.' + str(def_dec_places) + 'f}'
            elif def_type == 'date':
                formatline = '{:^' + str(def_length) + '}'
            else:
                formatline = '{:' + str(def_length) + '}'
            if value is None:
                print_line = print_line + formatline.format(' ') + '|'
            else:
                if def_type == 'date':
                    try:
                        print_line = (print_line + formatline.
                                      format(value.strftime('%Y-%m-%d')) + '|')
                    except AttributeError:
                        print_line = print_line + \
                            formatline.format(value) + '|'
                else:
                    if isinstance(value, str):
                        print_line = print_line + \
                            formatline.format(value[0:def_length]) + '|'
                    else:
                        print_line = print_line + \
                            formatline.format(value) + '|'
        print_list = print_list + print_line + '\n'
    return header, print_list


class Calculate(object):
    """
    Methods with Decimal fixed point and floating point arithmetic
    PARAMETER:
        precision    The context precision does not affect how many digits are stored.
                     That is determined exclusively by the number of digits in value.
                     For example, Decimal('3.00000') records all five zeros
                     even if the context precision is only three.
                     The purpose of the context argument is determining what to do
                     if value is a malformed string.
        places       None means Decimal floating point arithmetic
                     Integer means places of Decimal fixed point
        rounding    decimal.ROUND_CEILING
                        Round towards Infinity.
                    decimal.ROUND_DOWN
                        Round towards zero.
                    decimal.ROUND_FLOOR
                        Round towards -Infinity.
                    decimal.ROUND_HALF_DOWN
                        Round to nearest with ties going towards zero.
                    decimal.ROUND_HALF_EVEN
                        Round to nearest with ties going to nearest even integer.
                    decimal.ROUND_HALF_UP
                        Round to nearest with ties going away from zero.
                    decimal.ROUND_UP
                        Round away from zero.
                    decimal.ROUND_05UP
                        Round away from zero if last digit after rounding towards zero
                        would have been 0 or 5; otherwise round towards zero.
    Class ATTRIBUTE:
        context     Contexts are environments for arithmetic operations. They govern precision,
                    set rules for rounding, determine which signals are treated as exceptions,
                    and limit the range for exponents.
    """

    context = getcontext()

    def __init__(self, precision=15, places=2, rounding=ROUND_HALF_EVEN):
        self.context.prec = precision
        self.context.rounding = rounding
        self.places = places

    def _places(self, result):
        if self.places is not None:
            places = -1 * self.places
            return self.context.quantize(result, Decimal(10) ** places)
        else:
            return result

    def convert(self, x):
        result = Decimal(x)
        return self._places(result)

    def add(self, x, y):
        result = self.context.add(Decimal(x), Decimal(y))
        return self._places(result)

    def subtract(self, x, y):
        result = self.context.subtract(Decimal(x), Decimal(y))
        return self._places(result)

    def multiply(self, x, y):
        result = self.context.multiply(Decimal(x), Decimal(y))
        return self._places(result)

    def divide(self, x, y):
        try:
            assert y != 0, 'Division by Zero {}/{}'.format(x, y)
            result = self.context.divide(Decimal(x), Decimal(y))
        except DivisionByZero:
            Termination()
        return self._places(result)

    def percent(self, x, y):
        '''
        returns percentage of x basis y
        e.g. x=39 y=46 returns 84.78
             x=46 y=39 returns 117.95
        '''
        assert y != 0, 'Division by Zero {}/{}'.format(x, y)
        result = Decimal(x) / Decimal(y) * 100
        return result.quantize(Decimal('0.01'))

    def string_to_decimal(self, string):

        pattern = "-?(0|([1-9]\d*))(\.\d+)?"
        string = string.replace('.', '')
        string = string.replace(',', '.')
        match = re.search(pattern, string)
        if match:
            return self.convert(match.group())


class Datulate(object):
    """
    Methods with date operations
    PARAMETER:
        date_format    YYY-MM-DD (standard
        date_unit      days (standard), weeks
    """

    DAYS = 'DAYS'
    WEEKS = 'WEEKS'

    def __init__(self, date_format='%Y-%m-%d', date_unit='DAYS'):
        self.date_format = date_format
        self.date_unit = date_unit

    def convert(self, x):

        if isinstance(x, date):
            return x.strftime(self.date_format)  # returns string
        if isinstance(x, str):
            # returns date
            return datetime.strptime(x, self.date_format).date()
        return None

    def add(self, x, y, ignore_weekend=True):

        if isinstance(x, str):
            x = self.convert(x)
        if self.date_unit == Datulate.DAYS:
            x = x + timedelta(days=y)
            if ignore_weekend:
                # day of the week as an integer, where Monday is 0 and Sunday
                # is 6.
                while x.weekday() in [5, 6]:
                    x = x + timedelta(days=y)
            return x
        if self.date_unit == Datulate.WEEKS:
            return x + timedelta(weeks=y)
        return None

    def subtract(self, x, y, ignore_weekend=True):

        if isinstance(x, str):
            x = self.convert(x)
        if self.date_unit == Datulate.DAYS:
            x = x - timedelta(days=y)
            if ignore_weekend:
                # day of the week as an integer, where Monday is 0 and Sunday
                # is 6.
                while x.weekday() in [5, 6]:
                    x = x - timedelta(days=y)
            return x
        if self.date_unit == Datulate.WEEKS:
            return x - timedelta(weeks=y)
        return None

    def today(self):

        return date.today()


class Info():

    def __init__(self, message=None, title=MESSAGE_TITLE):

        window = Tk()
        window.withdraw()
        window.title(title)
        # window.geometry(BOX_WINDOW_POSITION)
        messagebox.showinfo(title=title, message=message,)
        try:
            window.destroy()
        except TclError:
            pass


class Termination(Info):

    def __init__(self, info=''):

        message = MESSAGE_TEXT['TERMINATION'] + '\n\n'
        if info:
            message = message + info + '\n\n'
        for stack_item in inspect.stack()[2:]:
            filename = stack_item[1]
            line = stack_item[2]
            method = stack_item[3]
            message = (
                message + '\n' + filename + '\n' + 'LINE:   ' +
                str(line) + '   METHOD: ' + method
            )
        super().__init__(message=message, title=MESSAGE_TITLE)
        sys.exit()


class Amount():
    """Amount object containing currency and amount
    Args:
        amount (str): Amount using either a , or a . as decimal separator
        status (str): Either C or D for credit or debit respectively
        currency (str): A 3 letter currency (e.g. EUR)
    >>> Amount('123.45', 'C', 'EUR')
    <123.45 EUR>
    >>> Amount('123.45', 'D', 'EUR')
    <-123.45 EUR>
    """

    def __init__(self, amount, currency=EURO, places=2):

        self.amount = str(amount)
        if self.amount == 'nan':
            self.amount = ''
        self.currency = currency
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.currency == EURO:
                    self.currency = u"\N{euro sign}"
        else:
            self.currency = ''

    def to_decimal(self):

        return self.amount

    def __str__(self):

        return '%s %s' % (self.amount, self.currency)

    def __repr__(self):

        return '<%s>' % self

    def __eq__(self, other):
        """
        see PEP 207
        in my case needed (and following methods) to sort PandasTables
        """
        if isinstance(other, str) or isinstance(self.amount, str):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other):

        if isinstance(other, str) or isinstance(self.amount, str):
            return False
        return self.amount < other.amount and self.currency == other.currency

    def __le__(self, other):

        if isinstance(other, str) or isinstance(self.amount, str):
            return False
        return self.amount <= other.amount and self.currency == other.currency

    def __ne__(self, other):

        if isinstance(other, str) or isinstance(self.amount, str):
            return True
        return self.amount != other.amount or self.currency == other.currency

    def __gt__(self, other):

        if isinstance(other, str) or isinstance(self.amount, str):
            return True
        return self.amount > other.amount and self.currency == other.currency

    def __ge__(self, other):

        if isinstance(other, str) or isinstance(self.amount, str):
            return True
        return self.amount >= other.amount and self.currency == other.currency
