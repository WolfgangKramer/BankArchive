# 

## Overview

A banking application.

It dynamically builds the complete application menu structure depending on:

* available bank data
* application configuration
* configured accounts
* enabled database and analysis features

It encapsulates all GUI menus and directly connects them with the corresponding workflow classes.

\---

## Purpose

The application menu bar contains:

* ledger functions
* display and reporting functions
* download operations
* database analysis
* configuration and bank management

\---

# Constructor

```python
from banking.bank\_menu\_ui import BankMenu

from banking.declarations import WM\_DELETE\_WINDOW

from banking.connect import ConnectController

from banking.connect\_data import connectionresult



def main():

&#x20;   controller = ConnectController()

&#x20;   controller.run()



&#x20;   if not connectionresult.connected:

&#x20;       return



&#x20;   while True:

&#x20;       executing = BankMenu()



&#x20;       if executing.button\_state == WM\_DELETE\_WINDOW:

&#x20;           break



if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   main()```

## Parameters

|Parameter|Description|
|-|-|
|`title`|Window title|
|`repo`|Repository access for database and configuration|
|`service`|Service layer|
|`footer`|Tkinter `StringVar` for status messages|
|`progress`|ProgressBar instance|
|`window`|Main Tkinter window (`Tk`)|

\---

# Workflow Objects

During initialization, several workflow classes are created:

```python
self.w\_ledg
self.w\_show
self.w\_dwnld
self.w\_db
self.w\_cust
```

## Responsibilities

|Workflow|Purpose|
|-|-|
|`LedgerWorkFlow`|Accounting and ledger operations|
|`ShowWorkFlow`|Display and reporting|
|`DownloadWorkFlow`|Bank data downloads|
|`DatabaseWorkFlow`|Database analysis|
|`CustomizingWorkFlow`|Configuration and administration|

\---

## Main Menus

The application may generate the following top-level menus:

|Menu|Description|
|-|-|
|`Ledger`|Accounting and ledger operations|
|`Show`|Account and portfolio display|
|`Download`|Bank and market data downloads|
|`Database`|Data analysis and reporting|
|`Customize`|Configuration and administration|

\---

# Ledger Menu

Created by:

```python
\_create\_menu\_ledger()
```

## Functions

### Validation

* Check Upload
* Check Bank Statement

### Search

* Ledger search
* Search via statement

### Analysis

* Balances
* Assets
* Journal
* Accounts
* Account categories

### Additional Functions

* Show chart of accounts
* Reset daily ledger balance
* Show statements without ledger entries

\---

# Show Menu

Created by:

```python
\_create\_menu\_show()
```

## Functions

### Websites

Dynamic submenu for:

* banking websites
* external finance websites

### Alpha Vantage

Optional features:

* show market data
* symbol search

### Bank Display Functions

* account balances
* account statements
* holdings
* transactions

\---

# Dynamic Bank Menus

Created by:

```python
\_create\_menu\_banks()
```

The menu structure is dynamically generated from:

```python
bank\_owner\_account
```

## Structure

```text
Bank
 └── Owner
      └── Account
```

If no owner structure exists:

```text
Bank
 └── Account
```

\---

# Download Menu

Created by:

```python
\_create\_menu\_download()
```

## Functions

* Download all banks
* Import prices
* Download individual banks
* Download holdings

\---

# Database Menu

Created by:

```python
\_create\_menu\_database()
```

## Analysis Functions

### Portfolio Analysis

* Performance analysis
* ISIN comparison
* Percentage comparison
* Transaction details

### Price Analysis

* Technical indicators
* Price analysis

### Tables

* Transaction tables
* Holding tables
* ISIN tables

### Updates

* Update holding market prices
* Update portfolio total values

\---

# Customize Menu

Created by:

```python
\_create\_menu\_customizing()
```

## Functions

### Application

* Edit INI configuration file
* Reset screen positions

### Import

* Bank identifier CSV
* Server CSV
* Ticker data

### Bank Administration

* Create new bank
* Delete bank
* Change login data
* Synchronize bank data
* Change FinTS transaction version
* Change security functions

### Display

* Show all bank data
* Show individual bank data

\---

# Error Handling

## Safe Callback Execution

```python
\_safe\_callback()
```

This method wraps menu functions in a safe callback handler:

* prevents Tkinter tracebacks
* handles controlled application exits
* protects the GUI from crashes

\---

# Window Closing

```python
wm\_deletion\_window()
```

## Responsibilities

When the application closes:

* the main window is destroyed
* database connections are closed
* temporary PDF files are deleted
* the application exits cleanly

\---

# Dynamic Menu Logic

The menu structure depends on:

|Condition|Effect|
|-|-|
|available banks|bank menus are created|
|enabled ledger|ledger menu becomes visible|
|Alpha Vantage configured|market data functions enabled|
|available holding accounts|analysis functions enabled|
|completed configuration|database and download menus enabled|

\---

# Architectural Features

## Dynamic Generation

The menus are fully data-driven.

## Separation of Concerns

GUI and business logic are separated:

* `Menue` → GUI layer
* `Workflow` classes → business logic

## Extensibility

New menu functions can easily be added through:

* additional workflow methods
* new `\_create\_menu\_\*` methods

\---

# Example Menu Structure

```text
Ledger
Show
 ├── WebSites
 ├── Alpha Vantage
 └── Banks
      └── Owners
           └── Accounts

Download
Database
Customize
```

# Conclusion

The `Menue` provides a flexible and dynamic menu system for the banking application.

Thanks to the strict separation between GUI and workflow logic, the architecture remains:

* maintainable
* extensible
* modular
* data-driven

It serves as the central entry point for all user interactions within the application.

