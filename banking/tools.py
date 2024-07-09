"""
Created on 01.02.2021
__updated__ = "2024-05-12"
@author: Wolfg
"""

import re
import pyodbc

from collections import namedtuple
from datetime import date, timedelta

from banking.declarations import (
    DEBIT,
    HOLDING,
    ISIN,
    BANK_MARIADB_INI,
    MESSAGE_TEXT,
    KEY_MS_ACCESS,
    STATEMENT,
)
from banking.formbuilts import (
    MessageBoxInfo, MessageBoxTermination
)
from banking.utils import (
    Calculate,
)
from banking.utils import shelve_get_key


dec2 = Calculate(places=2)
dec6 = Calculate(places=6)


def _ms_access_connect():
    ms_access_file = shelve_get_key(BANK_MARIADB_INI, KEY_MS_ACCESS)
    if ms_access_file is None or ms_access_file == '' or not re.search(".accdb", ms_access_file):

        return None
    try:
        ms_access_string = (
            r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' +
            ms_access_file + ';')
        ms_access = pyodbc.connect(ms_access_string)
        return ms_access.cursor()
    except pyodbc.Error as err:
        print('ms_access_file', ms_access_file)
        print('ms_access_string', ms_access_string)
        MessageBoxTermination(info=err.args[0] + '\n' + err.args[1])


def _ms_access_execute(ms_access_cursor, strSQL, vars_):
    try:
        if vars_ is None:
            return ms_access_cursor.execute(strSQL)
        else:
            return ms_access_cursor.execute(strSQL, vars_)
    except pyodbc.Error as err:
        MessageBoxTermination(
            info=err.args[0] + '\n' + err.args[1] + '\n' + strSQL)



def transfer_holding_to_access(mariadb, iban):
    """
    Transfer records of MariaDB table holding into MS Access DB
    """
    ms_access_cursor = _ms_access_connect()
    if ms_access_cursor is None:
        return
   
    # ............. transfer ....................
    
    ms_access_cursor.commit()


def transfer_statement_to_access(mariadb, bank):
    """
    Transfer records of MariaDB table statement into MS Access DB
    """
    ms_access_cursor = _ms_access_connect()
    if ms_access_cursor is None:
        return

# ............. transfer ....................
    
    
    ms_access_cursor.commit()
