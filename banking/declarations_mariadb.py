#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 09.12.2019
__updated__ = "2026-04-22"
@author: Wolfgang Kramer
"""
from collections import namedtuple

TINYINT = 'tinyint'  # data_type only used as check button fields
# allowed integer data_types in database
INTEGER = ['bigint', 'smallint', 'int']
DATABASE_TYP_DECIMAL = 'decimal'

"""
Database info. Initialized by MariaDB instance in method
"""
# List of table names
TABLE_NAMES = []
# Column names of table
# dict key: table_name, dict value: list of table_fieldnames
TABLE_FIELDS = {}
# Initialize dict TABLE_FIELD_PROPERTIES: dict of tables;
#                                        value is dict of fields;
#                                                 value is FieldsProperty of fields
FieldsProperty = namedtuple(
    'FieldsProperty', 'length, places, typ, comment, data_type')
# dict key --> table, value -- > dict key--> field_name value --> properties  for each table
TABLE_FIELDS_PROPERTIES = {}
# dict key--> field_name value --> properties of database
DATABASE_FIELDS_PROPERTIES = {
    'field_name': 'length, places, typ, comment, data_type'}

"""
-------------------------------- MariaDB Tables ----------------------------------
"""
PRODUCTIVE_DATABASE_NAME = 'test_banken'
APPLICATION = 'application'
APPLICATION_VIEW = 'application_view'
BANKIDENTIFIER = 'bankidentifier'
CORPORATE_ACTIONS = 'corporate_actions'
GEOMETRY = 'geometry'
HOLDING = 'holding'
HOLDING_VIEW = 'holding_view'
HOLDING_SYMBOL = 'holding_symbol'
SELECTION = 'selection'
SERVER = 'server'
STATEMENT = 'statement'
TICKERS = 'tickers'
TRANSACTION = 'transaction'
TRANSACTION_VIEW = 'transaction_view'
ISIN = 'isin'
PRICES = 'prices'
PRICES_ISIN_VIEW = 'prices_isin_view'
LEDGER = 'ledger'
LEDGER_DELETE = 'ledger_delete'
LEDGER_COA = 'ledger_coa'
LEDGER_DAILY_BALANCE = 'ledger_daily_balance'
LEDGER_VIEW = 'ledger_view'
LEDGER_STATEMENT = 'ledger_statement'
LEDGER_UNCHECKED_VIEW = 'ledger_unchecked_view'
SHELVES = 'shelves'

"""
-------------------------------- Create MariaDB Tables --------------------------------------------------------
"""
# CREATE_...   copied from HEIDI SQL Create-Tab and IF NOT EXISTS added
# additionally with VIEWs: ALTER ALGORITHM changed to CREATE ALGORITHM and IF NOT EXISTS added

CREATE_APPLICATION = "CREATE TABLE IF NOT EXISTS `application` (\
    `row_id` TINYTEXT NOT NULL DEFAULT '1' COMMENT 'row_id: application values, fields 1-9\r\nrow_id: alpha_vantage values fields 10-11' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `product_id` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Registration ID of FinTS software products' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `alpha_vantage` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Free key for the Alpha Vantage Stock API © with lifetime access' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `directory` VARCHAR(200) NULL DEFAULT NULL COMMENT 'Export Directory of Excel Files (Pandas Tables)' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `show_messages` VARCHAR(20) NULL DEFAULT NULL COMMENT 'Controls the output of FINTS message codes in the log.\nINFORMATION: Outputs codes 0xxx or 1xxx.\nWARNING: Outputs codes 3xxx.\nERROR: Outputs other codes.' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `logging` TINYINT(4) NOT NULL DEFAULT '0' COMMENT 'True: FINTS logging activated',\
    `threading` TINYINT(4) NOT NULL DEFAULT '1' COMMENT 'True: Download (FINTS, Prices) threading activated',\
    `ledger` TINYINT(4) NOT NULL DEFAULT '1' COMMENT 'True: Transfer of bank data to ledger activated',\
    `alpha_vantage_price_period` VARCHAR(50) NULL DEFAULT NULL COMMENT 'API returns raw (as-traded) time series of the global equity specified' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `alpha_vantage_function` LONGTEXT NULL DEFAULT NULL COMMENT 'generated alpha_vantage function names' COLLATE 'utf8mb4_bin',\
    `alpha_vantage_parameter` LONGTEXT NULL DEFAULT NULL COMMENT 'generated alpha_vantage parameter sets' COLLATE 'utf8mb4_bin',\
    PRIMARY KEY (`row_id`(100)) USING BTREE,\
    CONSTRAINT `alpha_vantage_function` CHECK (json_valid(`alpha_vantage_function`)),\
    CONSTRAINT `alpha_vantage_parameter` CHECK (json_valid(`alpha_vantage_parameter`))\
)\
COMMENT='data of application form'\
COLLATE='utf8mb4_uca1400_ai_ci'\
ENGINE=InnoDB\
;"

CREATE_APPLICATION_VIEW = "CREATE OR REPLACE ALGORITHM  = UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `application_view` AS SELECT product_id, alpha_vantage, directory, show_messages, logging, threading, ledger, alpha_vantage_price_period FROM application WHERE row_id=1;"

CREATE_BANKIDENTIFIER = "CREATE TABLE IF NOT EXISTS `bankidentifier` (\
    `code` CHAR(8) NOT NULL COMMENT 'Bank_Code (BLZ)' COLLATE 'latin1_swedish_ci',\
    `payment_provider` CHAR(1) NOT NULL COMMENT 'Merkmal, ob bankleitzahlführender Zahlungsdienstleister >1< oder nicht >2<. Maßgeblich sind nur Datensätze mit dem Merkmal >1<' COLLATE 'latin1_swedish_ci',\
    `payment_provider_name` VARCHAR(70) NOT NULL COLLATE 'latin1_swedish_ci',\
    `postal_code` CHAR(5) NOT NULL COLLATE 'latin1_swedish_ci',\
    `location` VARCHAR(70) NOT NULL DEFAULT '' COMMENT 'Bank Location' COLLATE 'latin1_swedish_ci',\
    `name` VARCHAR(70) NOT NULL DEFAULT '' COMMENT 'Bank Name' COLLATE 'latin1_swedish_ci',\
    `pan` CHAR(5) NOT NULL COMMENT ' Primary Account Number' COLLATE 'latin1_swedish_ci',\
    `bic` VARCHAR(11) NOT NULL DEFAULT '' COMMENT 'Bank Identifier Code (BIC) (S.W.I.F.T.)' COLLATE 'latin1_swedish_ci',\
    `check_digit_calculation` CHAR(2) NOT NULL COMMENT 'Kennzeichen für Prüfzifferberechnungsmethode ' COLLATE 'latin1_swedish_ci',\
    `record_number` CHAR(6) NOT NULL COLLATE 'latin1_swedish_ci',\
    `change_indicator` CHAR(1) NOT NULL COMMENT 'Merkmal, ob bankleitzahlführender Zahlungsdienstleister >1< oder nicht >2<). Maßgeblich sind nur Datensätze mit dem Merkmal >1<' COLLATE 'latin1_swedish_ci',\
    `code_deletion` CHAR(50) NOT NULL COMMENT 'Hinweis auf eine beabsichtigte Bankleitzahllöschung Das Feld enthält das Merkmal >0< (keine Angabe) oder >1< (Bankleitzahl im Feld 1 ist zur' COLLATE 'latin1_swedish_ci',\
    `follow_code` CHAR(8) NOT NULL COMMENT 'Hinweis auf Nachfolge-Bankleitzahl' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`code`, `payment_provider`) USING BTREE,\
    INDEX `BIC` (`bic`) USING BTREE\
)\
COMMENT='Contains German Banks\r\n\r\nSource: https://www.bundesbank.de/resource/blob/602848/50cba8afda2b0b1442016101cfd7e084/mL/merkblatt-bankleitzahlendatei-data.pdf\r\n\r\nDownload CSV: https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_CORPORATE_ACTIONS = "CREATE TABLE IF NOT EXISTS `corporate_actions` (\
    `isin_code` CHAR(12) NOT NULL DEFAULT '0' COMMENT 'Isin_Code' COLLATE 'latin1_swedish_ci',\
    `action_date` DATE NOT NULL COMMENT 'Action_date',\
    `action_type` ENUM('DIVIDEND','SPLIT') NOT NULL COMMENT 'Action type: Dividend / Split' COLLATE 'latin1_swedish_ci',\
    `value` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT 'Action value',\
    PRIMARY KEY (`isin_code`, `action_date`, `action_type`) USING BTREE\
)\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"


CREATE_GEOMETRY = "CREATE TABLE IF NOT EXISTS `geometry` (\
    `caller` VARCHAR(200) NOT NULL COMMENT 'name of called tkinter form' COLLATE 'latin1_swedish_ci',\
    `geometry` VARCHAR(50) NULL DEFAULT NULL COMMENT '>width<x>height<+>x-position<+>y-position<' COLLATE 'latin1_swedish_ci',\
    `column_width` SMALLINT(5) UNSIGNED NULL DEFAULT NULL COMMENT 'column width  in form or pandastable',\
    PRIMARY KEY (`caller`) USING BTREE\
)\
COMMENT='Contains geometry information and column widths for each called tkinter form or pandastable\r\n\r\ngeometry() method sets:\r\n\r\nWindow size- width × height\r\nWindow position- X and Y distance from the top-left corner of the screen\r\n'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_HOLDING = "CREATE TABLE IF NOT EXISTS `holding` (\
    `iban` CHAR(22) NOT NULL COMMENT ':97A:: DepotKonto' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL DEFAULT '2000-01-01' COMMENT ':98A:: M Datum (und Uhrzeit), auf dem/der die Aufstellung basiert',\
    `isin_code` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN-Kennung' COLLATE 'latin1_swedish_ci',\
    `price_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':90B:: ISO 4217-Währungscode' COLLATE 'latin1_swedish_ci',\
    `market_price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':90A:: Marktpreis (Prozentsatz)  :90B:: Markpreis (Börsenkurs)',\
    `acquisition_price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':70E:: Einstandspreis',\
    `pieces` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT ':93B:: Stückzahl oder Nennbetrag',\
    `amount_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':19A:: ISO 4217-Währungscode Depotwert' COLLATE 'latin1_swedish_ci',\
    `total_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':19A:: Depotwert',\
    `total_amount_portfolio` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Deportwert Gesamt',\
    `acquisition_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Einstandswert',\
    `exchange_rate` DECIMAL(14,6) NULL DEFAULT '0.000000' COMMENT ':92B:: Kurs/Satz',\
    `exchange_currency_1` CHAR(3) NULL DEFAULT NULL COMMENT ':92B:: Erste Währung' COLLATE 'latin1_swedish_ci',\
    `exchange_currency_2` CHAR(3) NULL DEFAULT NULL COMMENT ':92B:: Zweite Wöhrung' COLLATE 'latin1_swedish_ci',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'Datensatz Herkunft:  _BANKDATA_  Download Bank' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`iban`, `price_date`, `isin_code`) USING BTREE,\
    INDEX `ISIN_KEY` (`isin_code`) USING BTREE,\
    INDEX `IBAN_ISIN_CODE_PRICE_DATE` (`iban`, `isin_code`, `price_date`) USING BTREE\
)\
COMMENT='Financial Transaction Services (FinTS) ? Messages (Multibankfaehige Geschaeftsvorfaelle), Version 4.1 final version, 25.07.2016, Die Deutsche Kreditwirtschaft\r\n\r\nC.4 MT 535 \r\nVersion: SRG 1998 \r\n?Statement of Holdings?; basiert auf S.W.I.F.T. Standards Release Guide 1998 \r\n\r\nFinancial Transaction Services (FinTS) \r\nDokument: Messages - Finanzdatenformate \r\nVersion: \r\n4.1 FV \r\nKapitel: \r\nB \r\nKapitel: S.W.I.F.T.-Formate \r\nAbschnitt: MT 535  \r\nStand: \r\n20.01.2014 \r\nSeite: \r\n165'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_HOLDING_VIEW = "CREATE OR REPLACE ALGORITHM = UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `holding_view` AS \
SELECT t1.iban, t1.price_date, t1.isin_code, t2.name, t2.symbol, t1.price_currency, t1.market_price, t1.acquisition_price, t1.pieces, t1.amount_currency, \
t1.total_amount, t1.total_amount_portfolio, t1.acquisition_amount, t1.exchange_rate, t1.exchange_currency_1, t1.exchange_currency_2, t1.origin  \
FROM holding AS t1 INNER JOIN isin AS t2 USING(isin_code) ;"

CREATE_ISIN = "CREATE TABLE  IF NOT EXISTS   `isin` (\
    `name` VARCHAR(35) NOT NULL DEFAULT 'NA' COMMENT ':35B:: Wertpapierbezeichnung' COLLATE 'latin1_swedish_ci',\
    `isin_code` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN-Kennung' COLLATE 'latin1_swedish_ci',\
    `type` VARCHAR(50) NOT NULL DEFAULT 'SHARE' COMMENT 'SHARE, BOND, SUBSCRIPTION RIGHT' COLLATE 'latin1_swedish_ci',\
    `validity` DATE NOT NULL DEFAULT '9999-01-01' COMMENT 'Isin valid to this date',\
    `wkn` CHAR(6) NOT NULL DEFAULT 'NA' COMMENT 'Die Wertpapierkennnummer (WKN, vereinzelt auch WPKN oder WPK abgekürzt) ist eine in Deutschland verwendete sechsstellige Ziffern- und Buchstabenkombination zur Identifizierung von Wertpapieren (Finanzinstrumenten). Setzt man drei Nullen vor die WKN, so erhält man die neunstellige deutsche National Securities Identifying Number (NSIN) des jeweiligen Wertpapiers.' COLLATE 'latin1_swedish_ci',\
    `origin_symbol` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'Origin of symbol: Yahoo or AlphaVantage' COLLATE 'latin1_swedish_ci',\
    `symbol` VARCHAR(14) NOT NULL DEFAULT 'NA' COMMENT 'Ticker symbol' COLLATE 'latin1_swedish_ci',\
    `currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT 'Currency Code prices' COLLATE 'latin1_swedish_ci',\
    `exchange` VARCHAR(50) NOT NULL DEFAULT 'XETRA' COMMENT 'Stock Exchange' COLLATE 'latin1_swedish_ci',\
    `price_currency_valid` TINYINT(4) NOT NULL DEFAULT '1' COMMENT 'True: Euro allowed',\
    `last_check` DATE NOT NULL DEFAULT curdate() COMMENT 'Ticker symbol last check',\
    `industry` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'Branch of Industry' COLLATE 'latin1_swedish_ci',\
    `comment` TEXT NULL DEFAULT NULL COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`name`) USING BTREE,\
    UNIQUE INDEX `ISIN` (`isin_code`) USING BTREE,\
    INDEX `symbol` (`symbol`) USING BTREE\
)\
COMMENT='ISIN informations'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_LEDGER = "CREATE TABLE IF NOT EXISTS `ledger` (\
    `id_no` INT(10) UNSIGNED NOT NULL COMMENT 'Position 1-4: Ledger year, Position 5-10: Ledger document number',\
    `entry_date` DATE NULL DEFAULT NULL COMMENT 'Entry date',\
    `date` DATE NULL DEFAULT NULL COMMENT 'Value date',\
    `purpose_wo_identifier` VARCHAR(390) NULL DEFAULT NULL COMMENT 'Purpose of use text without identifiers' COLLATE 'latin1_swedish_ci',\
    `amount` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT 'Amount',\
    `currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT 'Currency' COLLATE 'latin1_swedish_ci',\
    `category` VARCHAR(65) NOT NULL DEFAULT 'NA' COMMENT 'Category' COLLATE 'latin1_swedish_ci',\
    `credit_account` CHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Credit financial account number ' COLLATE 'latin1_swedish_ci',\
    `debit_account` CHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Debit finacial account number' COLLATE 'latin1_swedish_ci',\
    `applicant_name` VARCHAR(65) NULL DEFAULT NULL COMMENT 'Name of the sender / recipient' COLLATE 'latin1_swedish_ci',\
    `vat_amount` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT 'Amount of value added tax',\
    `vat_rate` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT 'Rate of value added tax',\
    `upload_check` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activate if debit-credit account is correct in bank postings ledger records ',\
    `bank_statement_checked` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activate if ledger  id_no is noted on bank statement',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'data source is download bank data  or  _LEDGER_ , then data source is a ledger database' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`id_no`) USING BTREE,\
    INDEX `ENTRY_DATE` (`entry_date`) USING BTREE\
)\
 COMMENT='Preparation of bank data for the income tax return by means of categorisation for rows referring to table STATEMENT (creditor or debitor). \r\nField Origin : STATEMENT or  ACCESS for a deprecated source (Microsoft ACCES Database)\r\nContains also additional rows entered manually if  iban =NA\r\n'\
 COLLATE='latin1_swedish_ci'\
 ENGINE=InnoDB\
 ROW_FORMAT=DYNAMIC\
;"

CREATE_LEDGER_COA = "CREATE TABLE IF NOT EXISTS  `ledger_coa` (\
    `account` CHAR(4) NOT NULL COMMENT 'Account Number(4 digits)' COLLATE 'latin1_swedish_ci',\
    `name` VARCHAR(50) NOT NULL COMMENT 'Account Name' COLLATE 'latin1_swedish_ci',\
    `iban` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'IBAN if  Financial Account represents a Bank Account' COLLATE 'latin1_swedish_ci',\
    `eur_accounting` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated:  EUR Account',\
    `tax_on_input` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Amount subject to input tax',\
    `value_added_tax` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Amount subject to value_added_tax',\
    `earnings` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Earning Account',\
    `spendings` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Spending Account',\
    `transfer_account` CHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Activate: Account number for Transfer; duplicates Accounting Entry to Transfer Account' COLLATE 'latin1_swedish_ci',\
    `transfer_rate` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Amount of the duplicate in the Tansfer Account',\
    `contra_account` VARCHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Recommendation of this Contra Account Number' COLLATE 'latin1_swedish_ci',\
    `asset_accounting` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Account represents Assets',\
    `opening_balance_account` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Opening Balance Account',\
    `portfolio` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated: Account represents Portfolio Assets',\
    `obsolete` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated:  Account Number not used, may be used in the Past',\
    `download` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activated:  Download Financial Postings/Holdings from this bank account',\
    PRIMARY KEY (`account`) USING BTREE\
)\
 COMMENT='The chart of accounts (COA) is a comprehensive listing, categorized by account type, of every account used in an accounting system.\r\nUnlike a trial balance that only includes active or balanced accounts at the end of a period,\r\nthe COA encompasses all accounts in the system, providing a simple list of account numbers and names'\
 COLLATE='latin1_swedish_ci'\
 ENGINE=InnoDB\
;"

CREATE_LEDGER_DAILY_BALANCE = "CREATE TABLE IF NOT EXISTS  `ledger_daily_balance` (\
    `account` CHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Account Number(4 digits)' COLLATE 'latin1_swedish_ci',\
    `entry_date` DATE NOT NULL COMMENT 'Entry date',\
    `balance` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Amount',\
    PRIMARY KEY (`account`, `entry_date`) USING BTREE,\
    INDEX `ENTRY_DATE` (`entry_date`) USING BTREE\
)\
 COMMENT='The table stores the daily balance for the account.'\
 COLLATE='latin1_swedish_ci'\
 ENGINE=InnoDB\
 ROW_FORMAT=DYNAMIC\
;"

CREATE_LEDGER_DELETE = "CREATE TABLE IF NOT EXISTS `ledger_delete` (\
    `id_no` INT(10) UNSIGNED NOT NULL DEFAULT '0' COMMENT 'Position 1-4: Ledger year, Position 5-10: Ledger document number',\
    `entry_date` DATE NULL DEFAULT NULL COMMENT 'Entry date',\
    `date` DATE NULL DEFAULT NULL COMMENT 'Value date',\
    `purpose_wo_identifier` VARCHAR(390) NULL DEFAULT NULL COMMENT 'Purpose of use text without identifiers' COLLATE 'latin1_swedish_ci',\
    `amount` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT 'Amount',\
    `currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT 'Currency' COLLATE 'latin1_swedish_ci',\
    `category` VARCHAR(65) NOT NULL DEFAULT 'NA' COMMENT 'Category' COLLATE 'latin1_swedish_ci',\
    `credit_account` CHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Credit financial account number ' COLLATE 'latin1_swedish_ci',\
    `debit_account` CHAR(4) NOT NULL DEFAULT 'NA' COMMENT 'Debit finacial account number' COLLATE 'latin1_swedish_ci',\
    `applicant_name` VARCHAR(65) NULL DEFAULT NULL COMMENT 'Name of the sender / recipient' COLLATE 'latin1_swedish_ci',\
    `vat_amount` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT 'Amount of value added tax',\
    `vat_rate` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT 'Rate of value added tax',\
    `upload_check` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activate if debit-credit account is correct',\
    `bank_statement_checked` TINYINT(1) NOT NULL DEFAULT '0' COMMENT 'Activate if ledger  id_no is noted on bank statement',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'data source is download bank data  or  _LEDGER_ , then data source is a ledger database' COLLATE 'latin1_swedish_ci'\
)\
 COMMENT='Logging Table:  contains each deleted row of table LEDGER\r\n'\
 COLLATE='latin1_swedish_ci'\
 ENGINE=InnoDB\
 ROW_FORMAT=DYNAMIC\
;"


CREATE_LEDGER_STATEMENT = "CREATE TABLE IF NOT EXISTS  `ledger_statement` (\
    `iban` CHAR(22) NOT NULL COMMENT 'key of table statement ' COLLATE 'latin1_swedish_ci',\
    `entry_date` DATE NOT NULL COMMENT 'key of table statement ',\
    `counter` SMALLINT(5) UNSIGNED NOT NULL COMMENT 'key of table statement ',\
    `status` CHAR(2) NOT NULL COMMENT 'CREDIT C or DEBIT D (some banks return RC or RD)  ' COLLATE 'latin1_swedish_ci',\
    `id_no` INT(10) UNSIGNED NOT NULL COMMENT 'key of table ledger',\
    PRIMARY KEY (`iban`, `entry_date`, `counter`) USING BTREE,\
    INDEX `Ledger` (`id_no`) USING BTREE,\
    CONSTRAINT `ledger` FOREIGN KEY (`id_no`) REFERENCES `ledger` (`id_no`) ON UPDATE NO ACTION ON DELETE CASCADE,\
    CONSTRAINT `statement` FOREIGN KEY (`iban`, `entry_date`, `counter`) REFERENCES `statement` (`iban`, `entry_date`, `counter`) ON UPDATE NO ACTION ON DELETE CASCADE\
)\
 COMMENT='Table links debit and/or credit accounts (if bank_account, means exist in table statement) of ledger table  with the statement table key (iban, entry_date, counter)\r\nStatus C refers to the credit account in ledger\r\nStatus D refers to the debit account in ledger\r\n'\
 COLLATE='latin1_swedish_ci'\
 ENGINE=InnoDB\
 ROW_FORMAT=DYNAMIC\
;"


CREATE_LEDGER_VIEW = "CREATE OR REPLACE ALGORITHM = UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `ledger_view` AS \
SELECT t1.id_no, t1.entry_date, t1.date, t1.purpose_wo_identifier,  t1.amount, t1.currency, t1.category, \
t1.credit_account, credit_name, t1.debit_account, t2.name AS debit_name, \
t1.applicant_name, t1.vat_amount, t1.vat_rate, t1.upload_check, t1.bank_statement_checked, t1.origin \
FROM (SELECT t2.name as credit_name, t1.*  FROM ledger as t1 \
LEFT JOIN (ledger_coa as t2)    ON (t1.credit_account=t2.account) ) as t1 \
LEFT JOIN (ledger_coa as t2)    ON (t1.debit_account=t2.account)  ;"


CREATE_PRICES = "CREATE TABLE IF NOT EXISTS `prices` (\
    `isin_code` CHAR(12) NOT NULL COMMENT 'Isin_Code' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL DEFAULT '2000-01-01' COMMENT 'Date of Prices',\
    `open` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT 'Opening Price',\
    `high` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT 'Highest Price',\
    `low` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT 'Lowest Price',\
    `close` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT 'Closing Price',\
    `volume` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT 'Trading Volume in Units',\
    `adjclose` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT 'Adjusted Price',\
    `origin_prices` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'Origin of Price Symbol data e.g. YAHOO!, AlphaAdVantage' COLLATE 'latin1_swedish_ci',\
    `symbol_prices` VARCHAR(14) NOT NULL DEFAULT 'NA' COMMENT 'Symbol of Prices' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`isin_code`, `price_date`) USING BTREE,\
    CONSTRAINT `fk_isin_code` FOREIGN KEY (`isin_code`) REFERENCES `isin` (`isin_code`) ON UPDATE RESTRICT ON DELETE CASCADE\
)\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_PRICES_ISIN_VIEW = "CREATE OR REPLACE ALGORITHM  = UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `prices_isin_view` AS SELECT * FROM prices INNER JOIN isin USING (isin_code);"

CREATE_SELECTION = "CREATE TABLE IF NOT EXISTS `selection` (\
    `name` VARCHAR(200) NOT NULL COMMENT 'selection name e.g. title of form' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `data` LONGTEXT NULL DEFAULT NULL COMMENT 'contains recently used selection values in JSON format' COLLATE 'utf8mb4_uca1400_ai_ci',\
    PRIMARY KEY (`name`) USING BTREE\
)\
COMMENT='Contains contains recently used selection valuesof a selection form'\
COLLATE='utf8mb4_uca1400_ai_ci'\
ENGINE=InnoDB\
;"


CREATE_SERVER = "CREATE TABLE IF NOT EXISTS `server` (\
    `code` CHAR(8) NOT NULL COMMENT 'Bankleitzahl' COLLATE 'latin1_swedish_ci',\
    `server` VARCHAR(100) NULL DEFAULT NULL COMMENT 'PIN/TAN-Access URL' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`code`) USING BTREE\
)\
COMMENT='German Bank PIN/TAN-Access URL'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_STATEMENT = "CREATE TABLE IF NOT EXISTS `statement` (\
    `iban` CHAR(22) NOT NULL COMMENT 'IBAN' COLLATE 'latin1_swedish_ci',\
    `entry_date` DATE NOT NULL COMMENT ':61: Buchungsdatum MMTT',\
    `counter` SMALLINT(5) UNSIGNED NOT NULL,\
    `date` DATE NOT NULL COMMENT ':61: UMSATZ Valuta Datum',\
    `guessed_entry_date` DATE NULL DEFAULT NULL COMMENT ':61: Buchungsdatum MMTT',\
    `status` CHAR(2) NOT NULL COMMENT ':61:Soll/Habenkennung C,D,RC,RD' COLLATE 'latin1_swedish_ci',\
    `currency_type` CHAR(1) NULL DEFAULT NULL COMMENT ':61:Waehrungsart' COLLATE 'latin1_swedish_ci',\
    `currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':60F:Waehrung' COLLATE 'latin1_swedish_ci',\
    `amount` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT ':61:Betrag' COLLATE 'latin1_swedish_ci',\
    `id` CHAR(4) NOT NULL DEFAULT 'NMSC' COMMENT ':61:Buchungsschluessel' COLLATE 'latin1_swedish_ci',\
    `customer_reference` VARCHAR(65) NOT NULL DEFAULT 'NONREF' COMMENT ':61:Kundenreferenz (oder Feld :86:20-29 KREF oder CREF (Bezeichner Subfeld) Kundenreferenz Customer Reference' COLLATE 'latin1_swedish_ci',\
    `bank_reference` VARCHAR(35) NULL DEFAULT NULL COMMENT ':61:Bankreferenz (oder Feld :86:20-29 BREF (Bezeichner Subfeld) Bankreferenz, Instruction ID' COLLATE 'latin1_swedish_ci',\
    `extra_details` VARCHAR(34) NULL DEFAULT NULL COMMENT ':61:Waehrungsart und Umsatzbetrag in Ursprungswaehrung' COLLATE 'latin1_swedish_ci',\
    `transaction_code` INT(3) UNSIGNED NOT NULL DEFAULT '0' COMMENT ':86:Geschaeftsvorfall-Code',\
    `posting_text` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 00 Buchungstext' COLLATE 'latin1_swedish_ci',\
    `prima_nota` VARCHAR(10) NULL DEFAULT NULL COMMENT ':86: 10 Primanoten-Nr.' COLLATE 'latin1_swedish_ci',\
    `purpose` VARCHAR(390) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck' COLLATE 'latin1_swedish_ci',\
    `purpose_wo_identifier` VARCHAR(390) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ohne Identifier' COLLATE 'latin1_swedish_ci',\
    `applicant_bic` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 30 BLZ Auftraggeber oder BIC (oder Feld :86:20-29 BIC(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `applicant_iban` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 31 KontoNr des Ueberweisenden/Zahlungsempfaengers (oder Feld :86:20-29 IBAN(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `applicant_name` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 32-33 Name des Ueberweisenden / Zahlungsempfaengers (oder Feld :86:20-29 ANAM(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `return_debit_notes` INT(3) NULL DEFAULT '0' COMMENT ':86: 34 SEPA-Rueckgabe Codes',\
    `end_to_end_reference` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck EREF (Bezeichner Subfeld) SEPA End to End-Referenz' COLLATE 'latin1_swedish_ci',\
    `mandate_id` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck MREF(Bezeichner Subfeld) SEPA Mandatsreferenz' COLLATE 'latin1_swedish_ci',\
    `payment_reference` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck PREF(Bezeichner Subfeld) Retourenreferenz' COLLATE 'latin1_swedish_ci',\
    `creditor_id` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck CRED(Bezeichner Subfeld) SEPA Creditor Identifier' COLLATE 'latin1_swedish_ci',\
    `debitor_id` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck DEBT(Bezeichner Subfeld) Originator Identifier' COLLATE 'latin1_swedish_ci',\
    `ordering_party` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ORDP(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `beneficiary` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck BENM(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `ultimate_creditor` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ULTC(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `ultimate_debitor` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ULTD(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `remittance_information` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck REMI(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `purpose_code` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck PURP(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `return_reason` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck RTRN(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `return_reference` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck RREF(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `counterparty_account` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ACCW(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `intermediary_bank` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck IBK(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `exchange_rate` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck EXCH(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `original_amount` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck OCMT oder OAMT (Bezeichner Subfeld) Ursprünglicher Umsatzbetrag' COLLATE 'latin1_swedish_ci',\
    `compensation_amount` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck COAM(Bezeichner Subfeld) Zinskompensationsbetrag' COLLATE 'latin1_swedish_ci',\
    `charges` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck CHGS(Bezeichner Subfeld)' COLLATE 'latin1_swedish_ci',\
    `different_client` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ABWA(Bezeichner Subfeld) Abweichender SEPA Auftraggeber' COLLATE 'latin1_swedish_ci',\
    `different_receiver` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck ABWE(Bezeichner Subfeld) Abweichender SEPA Empfänger' COLLATE 'latin1_swedish_ci',\
    `sepa_purpose` VARCHAR(65) NULL DEFAULT NULL COMMENT ':86: 20-29 Verwendungszweck SVWZ(Bezeichner Subfeld) Abweichender SEPA Verwendungszweck' COLLATE 'latin1_swedish_ci',\
    `additional_purpose` VARCHAR(108) NULL DEFAULT NULL COMMENT ':86: 60-63 Verwendungszweck Fortführung aus :86:20-29' COLLATE 'latin1_swedish_ci',\
    `opening_status` CHAR(1) NOT NULL COMMENT ':60F:Anfangssaldo Soll/Haben-Kennung C,D ' COLLATE 'latin1_swedish_ci',\
    `opening_entry_date` DATE NOT NULL COMMENT ':60F:Buchungsdatum ',\
    `opening_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':60F:Waehrung' COLLATE 'latin1_swedish_ci',\
    `opening_balance` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT '60F: Betrag (in first statement of entry_date!)',\
    `closing_status` CHAR(1) NOT NULL COMMENT ':62F:Schlusssaldo Soll/Haben-Kennung C,D ' COLLATE 'latin1_swedish_ci',\
    `closing_entry_date` DATE NOT NULL COMMENT ':62F:Buchungsdatum ',\
    `closing_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':62F:Waehrung' COLLATE 'latin1_swedish_ci',\
    `closing_balance` DECIMAL(14,2) UNSIGNED NOT NULL DEFAULT '0.00' COMMENT ':62F:Betrag (in last statement of entry_date!)',\
    `reference` VARCHAR(16) NULL DEFAULT NULL COMMENT ':21: BEZUGSREFERENZNUMMER oder NONREF' COLLATE 'latin1_swedish_ci',\
    `order_reference` VARCHAR(16) NULL DEFAULT NULL COMMENT ':20: AUFTRAGSREFERENZNUMMER' COLLATE 'latin1_swedish_ci',\
    `statement_no_page` INT(5) NOT NULL DEFAULT '0' COMMENT ':28C: Blattnummer ',\
    `statement_no` INT(5) UNSIGNED NOT NULL DEFAULT '0' COMMENT ':28C: Auszugsnummer ',\
    `camt` CHAR(3) NULL DEFAULT NULL COMMENT 'data source format: 052: Bank to Customer Account Report (camt.052)' COLLATE 'latin1_swedish_ci',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'data source: _BANKDATA_: download from bank /  _LEDGER_ : generated from ledger database' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`iban`, `entry_date`, `counter`) USING BTREE\
)\
    COMMENT='Financial Transaction Services (FinTS) ? Messages (Multibankfaehige Geschaeftsvorfaelle), Version 4.1 final version, 25.07.2016, Die Deutsche Kreditwirtschaft\r\n\r\nC.8 MT 940 \r\n\r\nC.8.3 Version: SRG 2001/ Anpassung an das SEPA-Datenformat \r\n?Transaction Report?; basiert auf S.W.I.F.T. Standards Release Guide 2001 (keine \r\nÄnderungen im SRG 2002)\r\n\r\nFinancial Transaction Services (FinTS) \r\nDokument: Messages - Finanzdatenformate \r\nVersion: \r\n4.1 FV \r\nKapitel: \r\nB \r\nKapitel: S.W.I.F.T.-Formate \r\nAbschnitt: MT 940  \r\nStand: \r\n20.01.2014 \r\nSeite: \r\n213'\
    COLLATE='latin1_swedish_ci'\
    ENGINE=InnoDB\
;"

CREATE_TICKERS = "CREATE TABLE IF NOT EXISTS `tickers` (\
    `symbol` VARCHAR(14) NOT NULL COMMENT 'Ticker' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `company_name` VARCHAR(255) NOT NULL COMMENT 'Company Name' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `exchange` VARCHAR(50) NOT NULL DEFAULT 'NA' COMMENT 'Name of Stock Exchange' COLLATE 'utf8mb4_uca1400_ai_ci',\
    `isin_code` CHAR(12) NOT NULL DEFAULT 'NA' COMMENT 'Isin Code' COLLATE 'utf8mb4_uca1400_ai_ci',\
    PRIMARY KEY (`symbol`) USING BTREE,\
    INDEX `isin_code` (`isin_code`) USING BTREE\
)\
COMMENT='Stocks Traded on German Exchanges'\
COLLATE='utf8mb4_uca1400_ai_ci'\
ENGINE=InnoDB\
;"


CREATE_TRANSACTION = "CREATE TABLE IF NOT EXISTS `transaction` (\
    `iban` CHAR(22) NOT NULL COMMENT ':97A:: DepotKonto' COLLATE 'latin1_swedish_ci',\
    `isin_code` CHAR(12) NOT NULL DEFAULT '0' COMMENT ':35B:: ISIN Kennung' COLLATE 'latin1_swedish_ci',\
    `price_date` DATE NOT NULL COMMENT ':98C::PREP// Erstellungsdatum',\
    `counter` SMALLINT(5) NOT NULL DEFAULT '0',\
    `transaction_type` CHAR(4) NOT NULL DEFAULT 'RECE' COMMENT ':22H:: Indikator für Eingang/Lieferung DELI=Lieferung(Belastung) RECE=Eingang(Gutschrift)' COLLATE 'latin1_swedish_ci',\
    `price_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':90A:: ISO 4217-Waehrungscode oder  :90B:: PCT  Preis als Prozentsatz' COLLATE 'latin1_swedish_ci',\
    `price` DECIMAL(14,6) NOT NULL DEFAULT '0.000000' COMMENT ':90A::  Preis als Prozentsatz oder  :90B:: Abrechnungskurs',\
    `pieces` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':36B:: Gebuchte Stueckzahl',\
    `amount_currency` CHAR(3) NOT NULL DEFAULT 'EUR' COMMENT ':19A:: Gebuchter Betrag,  ISO 4217-Waehrungscode' COLLATE 'latin1_swedish_ci',\
    `posted_amount` DECIMAL(14,2) NOT NULL DEFAULT '0.00' COMMENT ':19A:: Gebuchter Betrag, Kurswert',\
    `origin` VARCHAR(50) NULL DEFAULT '_BANKDATA_' COMMENT 'Datensatz Herkunft:  _BANKDATA_  Download Bank' COLLATE 'latin1_swedish_ci',\
    `comments` VARCHAR(200) NULL DEFAULT NULL COMMENT 'Comments' COLLATE 'latin1_swedish_ci',\
    PRIMARY KEY (`iban`, `isin_code`, `price_date`, `counter`) USING BTREE\
)\
COMMENT='Statement of Transactions based on S.W.I.F.T Standard Release Guide 1998\r\nMT 536 fields '\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_TRANSACTION_VIEW = "CREATE OR REPLACE ALGORITHM = UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `transaction_view` AS SELECT t1.iban, t1.isin_code, t2.name, t1.price_date, t1.counter, t1.transaction_type, t1.price_currency, t1.price, t1.pieces, t1.amount_currency, t1.posted_amount, t1.origin, t1.comments  FROM transaction AS t1 INNER JOIN isin AS t2 USING(isin_code);"

CREATE_SHELVES = "CREATE TABLE IF NOT EXISTS `shelves` (\
    `code` CHAR(8) NOT NULL COMMENT 'Bank_Code (BLZ)' COLLATE 'latin1_swedish_ci',\
    `bankdata` LONGTEXT NULL DEFAULT NULL COMMENT 'bank data stored in JSON format' COLLATE 'utf8mb4_bin',\
    PRIMARY KEY (`code`) USING BTREE\
)\
COMMENT='Contains one row per bank archived with the app.\r\nRow contains the bank basic data from tables bankidentifier and server.\r\nRow contains BPD data and UPD data  from FINTS for this bank.\r\nData is stored in JSON format\r\n'\
COLLATE='latin1_swedish_ci'\
ENGINE=InnoDB\
;"

CREATE_TRIGGER_trg_ledger_after_update = """CREATE OR REPLACE TRIGGER trg_ledger_after_update
AFTER UPDATE ON ledger
FOR EACH ROW
BEGIN
    IF (OLD.amount <> NEW.amount
        OR OLD.credit_account <> NEW.credit_account
        OR OLD.debit_account <> NEW.debit_account) THEN

        DELETE FROM ledger_daily_balance
        WHERE entry_date >= OLD.entry_date
          AND (account = OLD.credit_account
               OR account = OLD.debit_account);
    END IF;
END"""

CREATE_TRIGGER_trg_ledger_after_delete = """CREATE OR REPLACE TRIGGER trg_ledger_after_delete
AFTER DELETE ON ledger
FOR EACH ROW
BEGIN
    DELETE FROM ledger_daily_balance
    WHERE entry_date >= OLD.entry_date
      AND (account = OLD.credit_account
           OR account = OLD.debit_account);
END"""

CREATE_TRIGGER_trg_ledger_after_insert = """CREATE OR REPLACE TRIGGER trg_ledger_after_insert
AFTER INSERT ON ledger
FOR EACH ROW
BEGIN
    DELETE FROM ledger_daily_balance
    WHERE entry_date > NEW.entry_date
      AND (account = NEW.credit_account
           OR account = NEW.debit_account);
END"""

CREATE_PROC_SEARCH_LEDGER_VIA_STATEMENT = """
CREATE PROCEDURE search_ledger_via_statement(IN p_filters JSON) # currently not used 20250412
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE col_name VARCHAR(64);

    DECLARE sql_text LONGTEXT DEFAULT '
        SELECT DISTINCT l.*
        FROM ledger l
        JOIN ledger_statement ls 
            ON l.id_no = ls.id_no
        JOIN statement s 
            ON s.iban = ls.iban
           AND s.entry_date = ls.entry_date
           AND s.counter = ls.counter
        WHERE 1=1
    ';

    DECLARE cur CURSOR FOR
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'statement';

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO col_name;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- JSON-Wert für die Spalte holen
        SET @json_path = CONCAT('$.', col_name);
        SET @value = JSON_UNQUOTE(JSON_EXTRACT(p_filters, @json_path));

        IF @value IS NOT NULL AND @value <> '' THEN
            SET sql_text = CONCAT(
                sql_text,
                ' AND CAST(s.`', col_name, '` AS CHAR) LIKE ''%',
                REPLACE(@value, '''', ''''''),
                '%'''
            );
        END IF;

    END LOOP;

    CLOSE cur;

    SET @final_sql = sql_text;

    PREPARE stmt FROM @final_sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;

END
"""
#  MariaDB stored procedure ------------------------------------------------------------------------------------------
SEARCH_LEDGER_VIA_STATEMENT = 'search_ledger_via_statement'
PROCEDURES = [
    SEARCH_LEDGER_VIA_STATEMENT
    ]

CREATE_PROCEDURE = [
    CREATE_PROC_SEARCH_LEDGER_VIA_STATEMENT
    ]
#  MariaDB trigger ------------------------------------------------------------------------------------------
CREATE_TRIGGER = [
    CREATE_TRIGGER_trg_ledger_after_update,
    CREATE_TRIGGER_trg_ledger_after_delete,
    CREATE_TRIGGER_trg_ledger_after_insert
    ]
#  MariaDB table ------------------------------------------------------------------------------------------
CREATE_TABLES = [CREATE_APPLICATION,
                 CREATE_APPLICATION_VIEW,
                 CREATE_BANKIDENTIFIER,
                 CREATE_CORPORATE_ACTIONS,
                 CREATE_GEOMETRY,
                 CREATE_ISIN,
                 CREATE_HOLDING,
                 CREATE_HOLDING_VIEW,
                 CREATE_PRICES,
                 CREATE_PRICES_ISIN_VIEW,
                 CREATE_SELECTION,
                 CREATE_SERVER,
                 CREATE_STATEMENT,
                 CREATE_TICKERS,
                 CREATE_TRANSACTION,
                 CREATE_TRANSACTION_VIEW,

                 CREATE_LEDGER,
                 CREATE_LEDGER_COA,
                 CREATE_LEDGER_DAILY_BALANCE,
                 CREATE_LEDGER_DELETE,
                 CREATE_LEDGER_STATEMENT,
                 CREATE_LEDGER_VIEW,

                 CREATE_SHELVES,
                 ]
"""
-------------------------------- MariaDB Table Fields --------------------------------------------------------
"""
DB_acquisition_amount = 'acquisition_amount'
DB_acquisition_price = 'acquisition_price'
DB_additional_purpose = 'additional_purpose'
DB_alpha_vantage = 'alpha_vantage'
DB_alpha_vantage_price_period = 'alpha_vantage_price_period'
DB_alpha_vantage_function = 'alpha_vantage_function'
DB_alpha_vantage_parameter = 'alpha_vantage_parameter'
DB_bankdata = 'bankdata'
DB_open = 'open'
DB_low = 'low'
DB_high = 'high'
DB_close = 'close'
DB_dividends = 'dividends'
DB_adjclose = 'adjclose'
DB_amount = 'amount'
DB_amount_currency = 'amount_currency'
DB_applicant_bic = 'applicant_bic'
DB_applicant_iban = 'applicant_iban'
DB_applicant_name = 'applicant_name'
DB_bank_reference = 'bank_reference'
DB_beneficiary = 'beneficiary'
DB_bic = 'bic'
DB_caller = 'caller'
DB_camt = 'camt'
DB_category_name = 'category_name'
DB_change_indicator = 'change_indicator'
DB_charges = 'charges'
DB_check_digit_calculation = 'check_digit_calculation'
DB_closing_balance = 'closing_balance'
DB_closing_currency = 'closing_currency'
DB_closing_entry_date = 'closing_entry_date'
DB_closing_status = 'closing_status'
DB_code = 'code'
DB_code_deletion = 'code_deletion'
DB_column_width = 'column_width'
DB_company_name = 'company_name'
DB_comments = 'comments'
DB_compensation_amount = 'compensation_amount'
DB_counter = 'counter'
DB_counterparty_account = 'counterparty_account'
DB_country = 'country'
DB_creditor_id = 'creditor_id'
DB_currency = 'currency'
DB_currency_type = 'currency_type'
DB_customer_reference = 'customer_reference'
DB_data = 'data'
DB_date = 'date'
DB_debitor_id = 'debitor_id'
DB_different_client = 'different_client'
DB_different_receiver = 'different_receiver'
DB_directory = 'directory'
DB_end_to_end_reference = 'end_to_end_reference'
DB_entry_date = 'entry_date'
DB_exchange = 'exchange'
DB_exchange_currency_1 = 'exchange_currency_1'
DB_exchange_currency_2 = 'exchange_currency_2'
DB_exchange_rate = 'exchange_rate'
DB_extra_details = 'extra_details'
DB_datasource = 'datasource'
DB_follow_code = 'follow_code'
DB_geometry = 'geometry'
DB_guessed_entry_date = 'guessed_entry_date'
DB_high_price = 'high_price'
DB_iban = 'iban'
DB_id = 'id'
DB_industry = 'industry'
DB_intermediary_bank = 'intermediary_bank'
DB_ISIN = 'isin_code'
DB_last_check = 'last_check'
DB_last_price = 'last_price'
DB_ledger = 'ledger'
DB_logging = 'logging'
DB_low_price = 'low_price'
DB_location = 'location'
DB_mandate_id = 'mandate_id'
DB_market_price = 'market_price'
DB_name = 'name'
DB_opening_balance = 'opening_balance'
DB_opening_currency = 'opening_currency'
DB_opening_entry_date = 'opening_entry_date'
DB_opening_status = 'opening_status'
DB_order_reference = 'order_reference'
DB_ordering_party = 'ordering_party'
DB_origin = 'origin'
DB_origin_symbol = 'origin_symbol'
DB_original_amount = 'original_amount'
DB_pan = 'pan'
DB_payment_provider = 'payment_provider'
DB_payment_provider_name = 'payment_provider_name'
DB_payment_reference = 'payment_reference'
DB_pieces = 'pieces'
DB_pieces_cum = 'pieces_cum'
DB_postal_code = 'postal_code'
DB_posted_amount = 'posted_amount'
DB_posting_text = 'posting_text'
DB_product_id = 'product_id'
DB_price = 'price'
DB_price_currency = 'price_currency'
DB_price_currency_valid = 'price_currency_valid'
DB_price_date = 'price_date'
DB_prima_nota = 'prima_nota'
DB_purpose = 'purpose'
DB_purpose_code = 'purpose_code'
DB_purpose_wo_identifier = 'purpose_wo_identifier'
DB_ratio_price = 'ratio_price'
DB_record_number = 'record_number'
DB_reference = 'reference'
DB_remittance_information = 'remittance_information'
DB_return_debit_notes = 'return_debit_notes'
DB_return_reason = 'return_reason'
DB_return_reference = 'return_reference'
DB_row_id = 'row_id'
DB_sepa_purpose = 'sepa_purpose'
DB_server = 'server'
DB_show_messages = 'show_messages'
DB_bank_statement_no = 'statement_no'
DB_bank_statement_no_page = 'statement_no_page'
DB_status = 'status'
DB_splits = 'splits'
DB_symbol = 'symbol'
DB_symbol_prices = 'symbol_prices'
DB_threading = 'threading'
DB_total_amount = 'total_amount'
DB_total_amount_portfolio = 'total_amount_portfolio'
DB_transaction_code = 'transaction_code'
DB_transaction_type = 'transaction_type'
DB_type = 'type'
DB_ultimate_creditor = 'ultimate_creditor'
DB_ultimate_debitor = 'ultimate_debitor'
DB_validity = 'validity'
DB_volume = 'volume'
DB_wkn = 'wkn'
DB_TYPES = ['SHARE', 'BOND', 'INDEX', 'SUBSCRIPTION RIGHT']

"""
-------------------------------- Ledger MariaDB Table Fields --------------------------------------------------------
"""

DB_id_no = 'id_no'
DB_entry_date = 'entry_date'
DB_date = 'date'
DB_amount = 'amount'
DB_currency = 'currency'
DB_category = 'category'
DB_credit_account = 'credit_account'
DB_debit_account = 'debit_account'
DB_vat_amount = 'vat_amount'
DB_vat_rate = 'vat_rate'
DB_upload_check = 'upload_check'
DB_bank_statement_checked = 'bank_statement_checked'
DB_origin = 'origin'

DB_account = 'account'
DB_name = 'name'
DB_iban = 'iban'
DB_eur_accounting = 'eur_accounting'
DB_tax_on_input = 'tax_on_input'
DB_value_added_tax = 'value_added_tax'
DB_earnings = 'earnings'
DB_spendings = 'spendings'
DB_transfer_account = 'transfer_account'
DB_transfer_rate = 'transfer_rate'
DB_contra_account = 'contra_account'
DB_asset_accounting = 'asset_accounting'
DB_portfolio = 'portfolio'
DB_obsolete = 'obsolete'

DB_creditor_id = 'creditor_id'
DB_credit_name = 'credit_name'
DB_debit_name = 'debit_name'
DB_credit_balance = 'credit_balance'
DB_debit_balance = 'debit_balance'
DB_c_iban = 'c_iban'
DB_c_entry_date = 'c_entry_date'
DB_c_counter = 'c_counter'
DB_d_iban = 'd_iban'
DB_d_entry_date = 'd_entry_date'
DB_d_counter = 'd_counter'

DB_balance = 'balance'
