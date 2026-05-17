"""
Created on 18.11.2019
__updated__ = "2026-05-17"
@author: Wolfgang Kramer
"""
from __future__ import annotations

import functools
import importlib
import inspect
import operator
import re
import sys
import requests

from typing import Dict, List 
from collections import Counter
from tkinter import Tk, messagebox, TclError
from datetime import date, timedelta, datetime
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, DivisionByZero

import banking.declarations as decl
import banking.message_handler as msg

from banking.connect_data import connectionresult

def is_title(title, sub_menu_name):
    """
    removes databse_name of title
    """
    result = title.removeprefix(connectionresult.database + ' ')
    return result.startswith(' '.join([get_menu_text("Ledger"), get_menu_text(sub_menu_name)]))


def check_function_exists(package: str, module: str, func: str) -> bool:
    """
    Check if a function exists inside a given package.module

    Args:
        package (str): package name (e.g., 'ta')
        module (str): module name inside the package (e.g., 'trend')
        func (str): function name to check (e.g., 'sma_indicator')

    Returns:
        bool: True if function exists, False otherwise
    """
    try:
        # Import the module dynamically
        mod = importlib.import_module(f"{package}.{module}")
    except ImportError:
        print(f"Module {package}.{module} not found.")
        return False

    # Check if function exists in the module
    return hasattr(mod, func) and inspect.isfunction(getattr(mod, func))


def check_class_exists(package: str, module: str, class_name: str) -> bool:
    """
    Check if a class exists inside a given package.module

    Args:
        package (str): package name (e.g., 'ta')
        module (str): module name inside the package (e.g., 'trend')
        class_name (str): class name to check (e.g., 'SMAIndicator')

    Returns:
        bool: True if class exists, False otherwise
    """
    try:
        # Import the module dynamically
        mod = importlib.import_module(f"{package}.{module}")
    except ImportError:
        print(f"Module {package}.{module} not found.")
        return False

    # Check if class exists in the module
    return hasattr(mod, class_name) and inspect.isclass(getattr(mod, class_name))


def get_popup_menu_text(key):
    """
    Retrieves menu_text from dictionary POPUP_MENU_TEXT
    Errors are handled and key is returned as text:
    - Key not found
    """
    return decl.POPUP_MENU_TEXT.get(key, key)


def get_menu_text(key):
    """
    Retrieves menu_text from dictionary MENU_TEXT
    Errors are handled and key is returned as text:
    - Key not found
    """
    return decl.MENU_TEXT.get(key, key)


def get_signature(obj):
    """
    Returns signature string of function/method
    """
    sig = inspect.signature(obj)
    parts = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue

        # Annotation (type hint)
        annotation = ""
        if param.annotation != inspect._empty:
            annotation = (
                f": {param.annotation.__name__}"
                if hasattr(param.annotation, "__name__")
                else f": {param.annotation}"
            )

        # Default value
        default = ""
        if param.default != inspect._empty:
            default = f" = {repr(param.default)}"

        # Handle *args / **kwargs
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            parts.append(f"*{name}{annotation}")
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            parts.append(f"**{name}{annotation}")
        else:
            parts.append(f"{name}{annotation}{default}")

    return "(" + ", ".join(parts) + ")"


def get_args(obj, wanted):
    """
    Return: list of wanted postional args of function/method
            list of other positional args of function/method
    """
    args = get_signature(obj).split(",")
    if args == ['()']:
        return [], []
    args = [item.translate(str.maketrans('', '', ",)(")) for item in args]
    args = [item.replace(" ", "") for item in args]
    args = [item for item in args if '=' not in item]
    args = [item.split(":")[0] for item in args]
    others = [item for item in args if item not in wanted]

    return args, others


def date_before_date(date_before, date_current):
    """
    returns True if date current is next weekday after date_before
    and not a weekend day
    """
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


def list_move(listing, move, insert, after=True):
    """
    Moves >move< after/before >insert< in list >listing<
    """
    if isinstance(listing, list) and move in listing and insert in listing:
        _index_move = listing.index(move)
        _move = listing[_index_move]
        listing.pop(_index_move)
        _index_insert = listing.index(insert)
        if after:
            _index_insert = _index_insert + 1
        listing.insert(_index_insert, _move)
    return listing


def list_delete_duplicates(listing):
    """
    Using Counter() + keys() to remove duplicated from list >listing<
    Keeps order of list
    """
    if isinstance(listing, list):
        result = Counter(listing)
        listing = [*result]
    return listing


def list_positioning(listing, pattern):
    """
    Returns 1st item (and index) of listing or next greater or last one
    """
    if not isinstance(listing, list):
        Termination().terminate()
    if not listing:
        return listing, 0
    lowercase_list = list(map(str.lower, listing))
    lowercase_list.sort()
    # get item starting with pattern
    lowercase_result = [item for item in lowercase_list if item.startswith(
        pattern.lower())]
    if not lowercase_result:
        # get next greater item
        lowercase_result = [
            item for item in lowercase_list if item > pattern.lower()]
    if lowercase_result:
        # get item from original listing
        lowercase_result = lowercase_result[0]
        listing_result = [
            item for item in listing if item.lower().startswith(lowercase_result)]
        listing_result = listing_result[0]
        return listing_result, listing.index(listing_result)
    else:
        return listing[-1], len(listing)-1


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


def type_error(message=msg.get_message(msg.MESSAGE_TEXT, 'STACK')):

    filename = inspect.stack()[1][1]
    line = inspect.stack()[1][2]
    method = inspect.stack()[1][3]
    Termination(info='TypeError' + '\n' +
                message.format(method, line, filename)).terminate()


def value_error(message=msg.get_message(msg.MESSAGE_TEXT, 'STACK')):

    filename = inspect.stack()[1][1]
    line = inspect.stack()[1][2]
    method = inspect.stack()[1][3]
    Termination(info='ValueError' + '\n' +
                message.format(method, line, filename)).terminate()


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


def dict_get_nested_value(dictionary: Dict, keys: List[str]):
    """
    get values of a list of keys in nested dictionaries
    """
    cur = dictionary
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


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
    return dict(functools.reduce(operator.add, map(Counter, dictionary)))


def create_iban(bank_code=None, account_number=None):

    # Eine deutsche IBAN wird wie folgt aus Kontonummer und Bankleitzahl berechnet:
    #
    #        Bilde aus Bankleitzahl, Kontonummer und Laendrkennung eine Zahl.
    #        Am Anfang der Zahl steht die Bankleitzahl.
    #        Die Kontonummer wird, falls sie weniger als zehn Stellen hat, mit fuehrendn Nullen
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
    #         Sollte das eine einstellige Zahl ergeben, wird sie um eine fuehrend Null erweitert.
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


def signed_balance(amount: Decimal | float, status: str) -> Decimal:
    """
    Return signed balance depending on credit/debit status.
    """
    return dec2.convert(amount) if status == decl.CREDIT else dec2.convert(-amount)


def printer(print_columns=['col1', 'col2', 'col4'], print_line_length=decl.WIDTH_TEXT,
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
        if result == Decimal('Infinity'):
            return result
        elif self.places is not None:
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
            Termination().terminate()
        return self._places(result)

    def percent(self, x, y):
        """
        returns percenday_e of x basis y
        e.g. x=39 y=46 returns 84.78
             x=46 y=39 returns 117.95
        """
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


dec2 = Calculate(places=2)
dec3 = Calculate(places=2)
dec6 = Calculate(places=6)
dec10 = Calculate(places=10)


class Datulate(object):
    """
    Methods with date operations
    PARAMETER:
        date_format    YYY-MM-DD (standard
        date_unit      days (standard), weeks
    """

    DAYS = 'DAYS'
    WEEKS = 'WEEKS'
    YEARS = 'YEARS'

    def __init__(self, date_format='%Y-%m-%d', date_unit='DAYS'):
        self.date_format = date_format
        self.date_unit = date_unit

    def convert(self, x):

        if isinstance(x, date):
            return x.strftime(self.date_format)  # returns string
        if isinstance(x, str):
            return datetime.strptime(x, self.date_format).date()  # returns date
        return None

    def convert_to_str(self, x):

        if isinstance(x, date):
            return x.strftime(self.date_format)  # returns string
        else:
            return x  # returns date

    def convert_to_date(self, x):

        if isinstance(x, str):
            return datetime.strptime(x, self.date_format).date()  # returns date
        else:
            return x

    def add(self, x, y, ignore_weekend=True):


        x = self.convert_to_date(x)
        if self.date_unit == Datulate.DAYS:
            x = x + timedelta(days=y)
            if ignore_weekend:
                # day of the week as an integer, where Monday is 0 and Sunday
                # is 6.
                while x.weekday() in [5, 6]:
                    x = x + timedelta(days=y)
            return self.convert_to_str(x)
        if self.date_unit == Datulate.WEEKS:
            return self.convert_to_str(x + timedelta(weeks=y))
        if self.date_unit == Datulate.YEARS:
            return self.convert_to_str(date(x.year + y, x.month, x.day))
        raise

    def subtract(self, x, y, ignore_weekend=True):

        x = self.convert_to_date(x)
        if self.date_unit == Datulate.DAYS:
            x = x - timedelta(days=y)
            if ignore_weekend:
                # day of the week as an integer, where Monday is 0 and Sunday
                # is 6.
                while x.weekday() in [5, 6]:
                    x = x - timedelta(days=y)
            return self.convert_to_str(x)
        if self.date_unit == Datulate.WEEKS:
            return self.convert_to_str(x - timedelta(weeks=y))
        if self.date_unit == Datulate.YEARS:
            return self.convert_to_str(date(x.year - y, x.month, x.day))
        raise

    def isweekend(self, x):
        """
        Checks if the date is a Saturday or a Sunday
        """
        x = self.convert_to_date(x)
        if x.weekday() == 5 or x.weekday() == 6:
            return True
        else:
            return False

    def get_year(self, x):
        """
        Returns year of date
        """
        x = self.convert_to_date(x)
        return int(x.year)
    
    def yyyy_01_01(self, x):
        """
        Returns January 1st of the year x
        """
        x = self.convert_to_date(x)
        year = int(x.year)
        return self.convert_to_str(date(year, 1, 1))

    def day_of_week(self, x):
        """
        returns
        0    Monday
        1    Tuesday
        2    Wednesday
        3    Thursday
        4    Friday
        5    Saturday
        6    Sunday
        """
        x = self.convert_to_date(x)
        return x.weekday()

    def today(self):

        return self.convert_to_str(date.today())


date_days = Datulate()
date_weeks = Datulate(date_unit=Datulate.WEEKS)
date_years = Datulate(date_unit=Datulate.YEARS)

date_yymmdd = Datulate(date_format='%y%m%d')  # input string format yymmdd
date_yyyymmdd = Datulate(date_format='%Y%m%d')  # input string format yyyymmdd


class Info():

    def __init__(self, message=None, title=msg.MESSAGE_TITLE):

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

        message = msg.get_message(msg.MESSAGE_TEXT, 'TERMINATION') + '\n\n'
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
        super().__init__(message=message, title=msg.MESSAGE_TITLE)

    def terminate(self, code=1):
        sys.exit(code)


class Amount():
    """Amount object containing currency and amount
    Args:
        amount (str): Amount using either a , or a . as decimal separator
        currency (str): A 3 letter currency (e.g. EUR)
    >>> Amount('123.45', 'EUR') --> 123.45 EUR
    """

    def __init__(self, amount, currency=decl.EURO, places=2):

        self.amount = str(amount)
        if self.amount == 'nan':
            self.amount = ''
        self.currency = currency
        if places:
            self.places = places
        else:
            self.places = 0
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=self.places).convert(
                    self.amount.replace(',', '.'))
                if self.currency == decl.EURO:
                    self.currency = u"\N{euro sign}"
        else:
            self.currency = ''

    def to_decimal(self):

        if isinstance(self.amount, Decimal):
            return self.amount
        elif isinstance(self.amount, str):
            try:
                amount = self.amount.split()[0]
            except IndexError:
                return self.amount
            return Calculate(places=self.places).convert(amount)
        else:
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


class ApplicationStore:

    _instance = None
    _data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApplicationStore, cls).__new__(cls)
        return cls._instance

    def load_data(self, data):
        self._data = data

    def get(self, keys=None):
        """
        Zugriff auf das geladene Dictionary:
        - None → alles
        - string key → einzelner Eintrag
        - list of keys → Teilmenge als Dictionary
        """
        if keys is None:
            return self._data
        elif isinstance(keys, list):
            return {key: self._data[key] for key in keys if key in self._data}
        else:
            return self._data.get(keys, None)


application_store = ApplicationStore()



from collections import defaultdict

def check_mixin_method_uniqueness(cls):
    """
    Prüft, ob Methodennamen in Mixins eindeutig sind.
    Gibt ein Dict mit Konflikten zurück.
    """
    method_map = defaultdict(list)

    # Alle Basisklassen außer der Klasse selbst
    for base in cls.__mro__[1:]:
        for name, _ in inspect.getmembers(base, predicate=inspect.isfunction):
            method_map[name].append(base.__name__)

    # Konflikte filtern (mehr als 1 Vorkommen)
    conflicts = {
        method: classes
        for method, classes in method_map.items()
        if len(classes) > 1 and method!='__init__'
    }

    return conflicts