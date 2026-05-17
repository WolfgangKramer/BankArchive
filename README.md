# README – BankArchive

## Overview

This application is applicable only to banks in Germany that support the FINTS protocol.

The `ConnectController` class establishes the connection to the MariaDB database.

The `BankMenu` class implements the central Tkinter menu system of the banking application.
It dynamically builds the complete application menu structure depending on:

- available bank data
- application configuration
- configured accounts
- enabled database and analysis features

The class encapsulates all GUI menus and directly connects them with the corresponding workflow classes.

---

# Prerequisites

```
Microsoft WIN 11
Microsoft Edge
Python 3.13
MariaDB 11.8
```

## Purpose

The application creates the complete menu bar and manages:

- ledger functions
- display and reporting functions
- download operations
- database analysis
- configuration and bank management

---

# Application Startup

The application is started through the following bootstrap code:

```python
from banking.bank_menu_ui import BankMenu
from banking.declarations import WM_DELETE_WINDOW
from banking.connect import ConnectController
from banking.connect_data import connectionresult


def main():
    controller = ConnectController()
    controller.run()

    if not connectionresult.connected:
        return

    while True:
        executing = BankMenu()

        if executing.button_state == WM_DELETE_WINDOW:
            break


if __name__ == "__main__":
    main()
```

## Startup Sequence

| Step | Description |
|---|---|
| `ConnectController()` | Initializes the connection controller |
| `controller.run()` | Starts the database and banking connection process |
| `connectionresult.connected` | Verifies that the connection was successful |
| `BankMenu()` | Starts the Tkinter banking application |
| `WM_DELETE_WINDOW` | Detects proper application shutdown |

## Purpose

The startup procedure ensures that:

- all required connections are established before the GUI starts
- the application exits safely if no connection is available
- the Tkinter main application loop can restart safely if required

---

# Workflow Objects

During initialization, several workflow classes are created:

```python
self.w_ledg
self.w_show
self.w_dwnld
self.w_db
self.w_cust
```

## Responsibilities

| Workflow | Purpose |
|---|---|
| `LedgerWorkFlow` | Accounting and ledger operations |
| `ShowWorkFlow` | Display and reporting |
| `DownloadWorkFlow` | Bank data downloads |
| `DatabaseWorkFlow` | Database analysis |
| `CustomizingWorkFlow` | Configuration and administration |

---

# Menu Creation

The method:

```python
create_menu()
```

creates the complete menu structure.

## Main Menus

The application may generate the following top-level menus:

| Menu | Description |
|---|---|
| `Ledger` | Accounting and ledger operations |
| `Show` | Account and portfolio display |
| `Download` | Bank and market data downloads |
| `Database` | Data analysis and reporting |
| `Customize` | Configuration and administration |

---

# Ledger Menu

Created by:

```python
_create_menu_ledger()
```

## Functions

### Validation

- Check Upload
- Check Bank Statement

### Search

- Ledger search
- Search via statement

### Analysis

- Balances
- Assets
- Journal
- Accounts
- Account categories

### Additional Functions

- Show chart of accounts
- Reset daily ledger balance
- Show statements without ledger entries

---

# Show Menu

Created by:

```python
_create_menu_show()
```

## Functions

### Websites

Dynamic submenu for:

- banking websites
- external finance websites

### Alpha Vantage

Optional features:

- show market data
- symbol search

### Bank Display Functions

- account balances
- account statements
- holdings
- transactions

---

# Dynamic Bank Menus

Created by:

```python
_create_menu_banks()
```

The menu structure is dynamically generated from:

```python
bank_owner_account
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

---

# Download Menu

Created by:

```python
_create_menu_download()
```

## Functions

- Download all banks
- Import prices
- Download individual banks
- Download holdings

---

# Database Menu

Created by:

```python
_create_menu_database()
```

## Analysis Functions

### Portfolio Analysis

- Performance analysis
- ISIN comparison
- Percentage comparison
- Transaction details

### Price Analysis

- Technical indicators
- Price analysis

### Tables

- Transaction tables
- Holding tables
- ISIN tables

### Updates

- Update holding market prices
- Update portfolio total values

---

# Customize Menu

Created by:

```python
_create_menu_customizing()
```

## Functions

### Application

- Edit INI configuration file
- Reset screen positions

### Import

- Bank identifier CSV
- Server CSV
- Ticker data

### Bank Administration

- Create new bank
- Delete bank
- Change login data
- Synchronize bank data
- Change FinTS transaction version
- Change security functions

### Display

- Show all bank data
- Show individual bank data

---

# Error Handling

## Safe Callback Execution

```python
_safe_callback()
```

This method wraps menu functions in a safe callback handler:

- prevents Tkinter tracebacks
- handles controlled application exits
- protects the GUI from crashes

---

# Window Closing

```python
wm_deletion_window()
```

## Responsibilities

When the application closes:

- the main window is destroyed
- database connections are closed
- temporary PDF files are deleted
- the application exits cleanly
- the log file is not being deleted !!!

---

# Dynamic Menu Logic

The menu structure depends on:

| Condition | Effect |
|---|---|
| available banks | bank menus are created |
| enabled ledger | ledger menu becomes visible |
| Alpha Vantage configured | market data functions enabled |
| available holding accounts | analysis functions enabled |
| completed configuration | database and download menus enabled |

---

# Architectural Features

## Dynamic Generation

The menus are fully data-driven.

## Separation of Concerns

GUI, business logic, bank dialogue, services, repository, MariaDB database are separated:

- GUI: `bank_menu_ui.py`
- Business Logic: `bank_menu_workflows.py`
- Bank dialogue: `dialog.py`
- Services: `services.py`
- Repository: `repository.py`
- MariaDB database: `mariadb.py`
