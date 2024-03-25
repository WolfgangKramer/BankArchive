"""
Created on 13.09.2019
__updated__ = "2024-03-25"
@author: Wolfgang Kramer
"""
import logging
import os

from banking.declarations import KEY_LOGGING, KEY_DIRECTORY, BANK_MARIADB_INI, TRUE, MESSAGE_TEXT
from banking.executing import FinTS_MariaDB_Banking
from banking.formbuilts import WM_DELETE_WINDOW
from banking.utils import exception_error, shelve_get_key,  shelve_exist


# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)'
if shelve_exist(BANK_MARIADB_INI) and shelve_get_key(BANK_MARIADB_INI, KEY_LOGGING) == TRUE:
    logging_filename = shelve_get_key(
        BANK_MARIADB_INI, KEY_DIRECTORY) + "logging.txt"
    try:
        os.remove(logging_filename)
    except Exception:
        exception_error(
            message=MESSAGE_TEXT['LOGGING_FILE'])
    logging.basicConfig(filename=logging_filename, level=logging.DEBUG)
    print('Logging activate: ' + logging_filename)
while True:
    executing = FinTS_MariaDB_Banking()
    if executing.button_state == WM_DELETE_WINDOW:
        break
