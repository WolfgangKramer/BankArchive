"""
Created on 13.09.2019
__updated__ = "2023-10-10"
@author: Wolfgang Kramer
"""


import logging

from banking.declarations import KEY_LOGGING, BANK_MARIADB_INI, TRUE
from banking.executing import FinTS_MariaDB_Banking
from banking.formbuilts import WM_DELETE_WINDOW
from banking.utils import shelve_get_key,  shelve_exist


if shelve_exist(BANK_MARIADB_INI) and shelve_get_key(BANK_MARIADB_INI, KEY_LOGGING) == TRUE:
    logging.basicConfig(level=logging.DEBUG)
while True:
    executing = FinTS_MariaDB_Banking()
    if executing.button_state == WM_DELETE_WINDOW:
        break
