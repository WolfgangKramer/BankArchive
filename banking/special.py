"""
Created on 01.02.2021
__updated__ = "2024-07-09"
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


def KontoSeek(ms_access_cursor, row, HabenKonto, SollKonto):
    strSQL = "SELECT KtoGegen FROM KtoNr WHERE KtoNr=?;"
    if HabenKonto == "9999":
        _ms_access_execute(ms_access_cursor, strSQL, SollKonto)
    else:
        _ms_access_execute(ms_access_cursor, strSQL, HabenKonto)
    for item in ms_access_cursor.fetchall():
        KtoGegen, = item
        if KtoGegen is None:
            break
        return KtoGegen
    strSQL = "SELECT KtoNr FROM KtoText WHERE BelegText=?;"
    _ms_access_execute(ms_access_cursor, strSQL, (row.posting_text,))
    for item in ms_access_cursor.fetchall():
        KtoNr, = item
        return KtoNr
    if HabenKonto == "9999":
        sqlSelect = "SELECT Haben AS KontoNr FROM Belege WHERE Soll=?"
        konto = (SollKonto,)
    else:
        sqlSelect = "SELECT Soll AS KontoNr FROM Belege WHERE Haben=?"
        konto = (HabenKonto,)
    if row.applicant_iban is not None:
        sqlWhere = " AND IBAN = ?;"
        vars_ = konto + (row.applicant_iban,)
        strSQL = sqlSelect + sqlWhere
        _ms_access_execute(ms_access_cursor, strSQL, vars_)
        for row in ms_access_cursor.fetchall():
            KontoNr, = row
            return KontoNr
    if row.creditor_id is not None:
        sqlWhere = " AND CRED = ?;"
        vars_ = konto + (row.creditor_id,)
        strSQL = sqlSelect + sqlWhere
        _ms_access_execute(ms_access_cursor, strSQL, vars_)
        for row in ms_access_cursor.fetchall():
            KontoNr, = row
            return KontoNr
    if row.applicant_name is not None:
        sqlWhere = " AND Empfaenger = ?;"
        vars_ = konto + (row.applicant_name,)
        strSQL = sqlSelect + sqlWhere
        _ms_access_execute(ms_access_cursor, strSQL, vars_)
        for row in ms_access_cursor.fetchall():
            KontoNr, = row
            return KontoNr
    if row.purpose is not None:
        sqlWhere = " AND text = ?"
        vars_ = konto + (row.purpose,)
        strSQL = sqlSelect + sqlWhere
        _ms_access_execute(ms_access_cursor, strSQL, vars_)
        for row in ms_access_cursor.fetchall():
            KontoNr, = row
            return KontoNr
    return '9999'


def transfer_holding_to_access(mariadb, iban):
    """
    Transfer records of MariaDB table holding into MS Access DB
    """
    ms_access_cursor = _ms_access_connect()
    if ms_access_cursor is None:
        return
    field_list = ','.join(mariadb.table_fields[HOLDING])
    Holding = namedtuple('Holding', mariadb.table_fields[HOLDING])
    sql_statement = ("SELECT " + field_list + ' FROM ' + HOLDING +
                     " WHERE iban=? AND price_date IN "
                     " (SELECT MAX(price_date) FROM " + HOLDING + " WHERE iban=?)")
    result = mariadb.execute(sql_statement, vars_=(iban, iban))
    bank_code = iban[4:12]
    for row in result:
        row = Holding._make(row)
        sql_statement = "SELECT name FROM " + ISIN + " WHERE isin=?"
        name = mariadb.execute(sql_statement, vars_=(row.ISIN,))
        if name:
            name, = name[0]
        else:
            name = row.ISIN
        strSQL = "Delete * from DEPOT" + bank_code + " WHERE ISIN=? AND DateOfPrice=?"
        _ms_access_execute(ms_access_cursor, strSQL,
                           (row.ISIN, row.price_date))
        strSQL = ("INSERT INTO DEPOT" + bank_code + " (ISIN, IdentificationOfSecurities, " +
                  "PricePerUnitAmount, SecuritiesQuantity, ValueAmount, DateOfPrice, " +
                  "TotalAmount)  VALUES(?,?,?,?,?,?,?)")
        _ms_access_execute(ms_access_cursor, strSQL,
                           (row.ISIN, name, row.market_price, row.pieces, row.total_amount,
                            row.price_date, row.total_amount_portfolio))
    ms_access_cursor.commit()


def transfer_statement_to_access(mariadb, bank):
    """
    Transfer records of MariaDB table statement into MS Access DB
    """
    ms_access_cursor = _ms_access_connect()
    if ms_access_cursor is None:
        return
    iban = bank.iban
    account = iban[12:]
    bank_code = iban[4:12]
    strSQL = "SELECT KtoNr, Obsolet FROM KtoNr WHERE KtoBlz=? AND KtoKtoNr=?;"
    _ms_access_execute(ms_access_cursor, strSQL, (bank_code, account))
    for pyodbc_row in ms_access_cursor.fetchall():
        FromKtoNr, Obsolet = pyodbc_row
        if Obsolet:
            return
        break
    else:
        MessageBoxTermination(info='ACCESS Table KtoNr with BLZ ' + bank_code +
                              ' Acount ' + account)
    strSQL = ("SELECT max(Datum) FROM Belege WHERE FromKtoNr=?")
    result = _ms_access_execute(ms_access_cursor, strSQL, (FromKtoNr,))
    for pyodbc_row in result:
        item, = pyodbc_row
        if item is None:
            entry_date = date(date.today().year, 1, 1)
        else:
            entry_date = date(item.year, item.month, item.day)
    field_list = ','.join(mariadb.table_fields[STATEMENT])
    Statement = namedtuple('Statement', mariadb.table_fields[STATEMENT])
    sql_statement = ("SELECT " + field_list + ' FROM ' + STATEMENT +
                     " where iban=? AND entry_date>=? ORDER BY entry_date, counter")
    result = mariadb.execute(sql_statement, vars_=(iban, entry_date))
    if not result:
        MessageBoxInfo(message=MESSAGE_TEXT['DATA_NO'].format(
            bank.bank_name, bank.iban), bank=bank)
        return
    for row in result:
        row = Statement._make(row)
        if row.entry_date.year > entry_date.year:
            break
        closing_balance = row.closing_balance
        if row.closing_status == DEBIT:
            closing_balance = dec2.multiply(closing_balance, -1)
        if row.status == DEBIT:
            Soll = FromKtoNr
            Haben = KontoSeek(ms_access_cursor, row, '9999', Soll)
        else:
            Haben = FromKtoNr
            Soll = KontoSeek(ms_access_cursor, row, Haben, '9999')
        from_date = row.entry_date - timedelta(days=4)
        to_date = row.entry_date + timedelta(days=4)
        strSQL = "SELECT * FROM Belege_Deleted WHERE Datum >= ? AND Datum <= ? \
                  AND  Wertstellungsdatum = ? AND Betrag = ? AND FromKtoNr IS NOT NULL and FromKtoNr = ?;"
        _ms_access_execute(ms_access_cursor, strSQL,
                           (from_date, to_date, row.date, row.amount, FromKtoNr))
        no_duplicate = True
        for pyodbc_row in ms_access_cursor.fetchall():
            no_duplicate = False
        if (no_duplicate and dec2.convert(row.amount) > 0):
            strSQL = ("SELECT * FROM Belege " +
                      " WHERE Wertstellungsdatum = ? AND  (Soll=? or Haben=?) and Saldo=?;")
            _ms_access_execute(ms_access_cursor, strSQL, (row.date, FromKtoNr, FromKtoNr,
                                                          closing_balance))
            for pyodbc_row in ms_access_cursor.fetchall():
                no_duplicate = False
            if no_duplicate:
                # Buchung mit MussFeldDaten speichern
                strSQL = ("INSERT INTO Belege(Auszugsdatum, Datum, Betrag, USTDM, [UST%], Soll, " +
                          "Haben, ToCheck, FromKtoNr, BankText, BIC, EREF, KREF, MREF, " +
                          "CRED, DEBT, SVWZ, ABWA, [Text], Wertstellungsdatum, " +
                          "Geschaeftsvorfall, Waehrung, Empfaenger, IBAN, Saldo, " +
                          "Waehrung_Saldo) " +
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                          )
                vars_ = (date(date.today().year, date.today().month, date.today().day),
                         row.entry_date, row.amount, 0, 0, Soll, Haben, 1, FromKtoNr,
                         row.purpose, row.applicant_bic,
                         row.end_to_end_reference,
                         row.customer_reference, row.mandate_id, row.creditor_id,
                         row.debtor_id, row.sepa_purpose, row.different_client,
                         row.purpose_wo_identifier, row.date, row.posting_text,
                         row.currency, row.applicant_name,
                         row.applicant_iban, closing_balance, row.closing_currency
                         )
                _ms_access_execute(ms_access_cursor, strSQL, vars_)
    ms_access_cursor.commit()
    strSQL = "SELECT KtoNr FROM KtoNr WHERE KtoBlz=? AND KtoKtoNr=?;"
    _ms_access_execute(ms_access_cursor, strSQL, (bank_code, account))
    for pyodbc_row in ms_access_cursor.fetchall():
        FromKtoNr, = pyodbc_row
        break
    else:
        MessageBoxTermination(info='ACCESS Table KtoNr with BLZ ' + bank_code +
                              ' Acount ' + account, bank=bank)
        return False  # thread checking
    strSQL = "SELECT SUM(Betrag) FROM Belege WHERE Haben = ?;"
    result = _ms_access_execute(ms_access_cursor, strSQL, FromKtoNr)
    Haben = 0
    for pyodbc_row in result:
        Haben, = pyodbc_row
        if Haben is None:
            Haben = 0
    strSQL = "SELECT SUM(Betrag) as Saldo FROM Belege WHERE Soll = ?;"
    result = _ms_access_execute(ms_access_cursor, strSQL, FromKtoNr)
    Soll = 0
    for pyodbc_row in result:
        Soll, = pyodbc_row
        if Soll is None:
            Soll = 0
    access_balance = dec2.subtract(Haben, Soll)
    if closing_balance != access_balance:
        sMsg = "Konto " + FromKtoNr + " Saldendifferenz zur Bank"
        sMsg = sMsg + "\n" + "BuchSaldo: " + str(access_balance)
        sMsg = sMsg + "\n" + "BankSaldo: " + str(closing_balance)
        sMsg = sMsg + "\n" + "Differenz: " + \
            str(dec2.subtract(closing_balance, access_balance))
        MessageBoxInfo(message=sMsg, bank=bank)
