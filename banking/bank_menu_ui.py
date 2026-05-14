"""0
Created on 09.12.2019
__updated__ = "2026-05-13"
Author: Wolfang Kramer
"""
import sys
import logging

from PIL import ImageTk
from pathlib import Path

from tkinter import Tk, Menu, TclError, GROOVE, ttk, Canvas, StringVar, font
from tkinter.ttk import Label

import banking.declarations as decl
import banking.declarations_mariadb as declm
import banking.message_handler as msg
import banking.bank_menu_workflows as wrk

from banking.formbuilts import ProgressBar
from banking.utils import application_store, dict_get_first_key, get_menu_text
from banking.repository import Repository
from banking.services import Services
from banking.connect_data import connectionresult
from banking.services import PDFService


class BankMenu:
    """
    Start of Application
    Execution of Application Customizing
    Execution of MARIADB Retrievals
    Execution of Bank Dialogues

    holdings : ignores download (all_banks) holdings if False
    """

    def __init__(self,  title=msg.MESSAGE_TITLE):

        self.repo = Repository()
        self.srv = Services(self.repo)
        self.window = Tk()
        self.progress = ProgressBar(self.window)        
        self.footer = StringVar() 
        self.men = Menue(title, self.repo, self.srv, self.footer, self.progress, self.window)
        application_store.load_data(self.repo.get_application())
        if application_store.get(declm.DB_logging):
            self.configure_logging(application_store.get(declm.DB_directory))        
        self.bank_names = self.repo.dictbank_names()
        while True:

            self.window.title(title)
            self.window.geometry('600x500+1+1')
            self.window.resizable(0, 1)
            self.canvas = Canvas(self.window, width=600, height=400)
            self.canvas.pack(fill="both", expand=True)
            try:
                self.bg_photo = ImageTk.PhotoImage(file="background.gif")
                self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
            except Exception as e:
                print('BankenLedger', msg.get_message(msg.MESSAGE_TEXT, 'CONNECT_IMAGE_ERROR', e))
            if connectionresult.database.lower() != declm.PRODUCTIVE_DATABASE_NAME:
                fill_colour = 'red'
            else:
                fill_colour = 'lightblue'
            self.canvas.create_text(300, 200, fill=fill_colour, font=(
                'Arial', 20, 'bold'), text=msg.get_message(msg.MESSAGE_TEXT, 'DATABASE', self.repo.get_database_name()))
            self._def_styles()
           
            self.men.create_menu(connectionresult.database, self.window)
            self.window.config(menu=self.men.menu, borderwidth=10, relief=GROOVE)
            self.message_widget = Label(self.window,
                                        textvariable=self.footer, foreground='RED', justify='center')
            # self.footer.set('')
            self.message_widget.pack(side='bottom', fill='both', expand=True)
            self.load_timer = None
            self.window.protocol(decl.WM_DELETE_WINDOW, self.men.wm_deletion_window)
            self.window.mainloop()
        try:
            self.window.destroy()
        except TclError:
            pass

    def configure_logging(self, directory: str):
        logging.basicConfig(
            filename=f"{directory}/logging.txt",
            level=logging.DEBUG
        )

    def _bank_name(self, bank_code):

        bank_name = bank_code
        if bank_code in self.bank_names:
            bank_name = self.bank_names[bank_code]
        return bank_name

    def _def_styles(self):

        style = ttk.Style()
        style.theme_use(style.theme_names()[0])
        style.configure('TLabel', font=('Arial', 8, 'bold'))
        style.configure('OPT.TLabel', font=(
            'Arial', 8, 'bold'), foreground='Grey')
        style.configure('HDR.TLabel', font=(
            'Courier', 12, 'bold'), foreground='Grey')
        style.configure('TButton', font=('Arial', 8, 'bold'), relief=GROOVE,
                        highlightcolor='blue', highlightthickness=5, shiftrelief=3)
        style.configure('TText', font=('Courier', 8))


class Menue:

    def __init__(self,  title, repo, service, footer, progress, window):

        self.window = window
        self.repo = repo
        application_store.load_data(self.repo.get_application())
        self.bank_names = self.repo.dictbank_names()
        self.w_ledg = wrk.LedgerWorkFlow(title, repo, service, footer, progress)
        self.w_show = wrk.ShowWorkFlow(title, repo, service, footer, progress)
        self.w_dwnld = wrk.DownloadWorkFlow(title, repo, service, footer, progress)
        self.w_db = wrk.DatabaseWorkFlow(title, repo, service, footer, progress)
        self.w_cust = wrk.CustomizingWorkFlow(title, repo, service, footer, progress)
        self.wpd_iban = []
        self.kaz_iban = []          


    def wm_deletion_window(self):

        try:
            self.window.destroy()
        except TclError:
            pass
        try:
            self.repo.destroy_connection()
        except AttributeError:
            pass
        Path(PDFService.PDF_FILE_NAME).unlink(missing_ok=True)
        sys.exit()

    def _safe_callback(self, func):
        """
            `workflow_method` is not executed, but passed to the function.

            `_safe_callback` builds a new function (wrapper) from this.

            Tkinter calls the wrapper.

            The wrapper:
            calls `workflow_method`
            catches errors
            prevents the traceback.
        """

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except msg.ExitBankMenu:
                self.wm_deletion_window()
        return wrapper

    def create_menu(self, MariaDBname, window):

        menu_font = font.Font(family='Arial', size=11)
        self.menu = Menu(window)
        window.config(menu=self.menu, borderwidth=10, relief=GROOVE)
        self.bank_owner_account = self.repo.get_bank_owner_accounts()
        if application_store.get(declm.DB_ledger):
            self._create_menu_ledger(self.menu, menu_font)
            # self.menu_builder = MenuBuilder(self).build(menu)
        if self.bank_names != {} and application_store.get(None):  # application customizing is done
            self._create_menu_show(self.menu, self.bank_owner_account, menu_font)
            self._create_menu_download(self.menu, menu_font)
        if application_store.get(None):  # application customizing is done
            self._create_menu_database(
                self.menu, menu_font, self.bank_owner_account)
        self._create_menu_customizing(self.menu, menu_font, MariaDBname)

    def _create_menu_ledger(self, menu, menu_font):
        """
         LEDGER Menu
        """
        ledger_menu = Menu(
            menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(
            label=get_menu_text("Ledger"), menu=ledger_menu)
        if self.repo.count_ledger_coa():  # count rows in LEDGER_COA table
            ledger_menu.add_command(
                label=get_menu_text("Check Upload"), command=self.w_ledg.ledger_upload_check)
            ledger_menu.add_command(
                label=get_menu_text("Check Bank Statement"), command=self.w_ledg.ledger_bank_statement_check)
            ledger_menu.add_separator()
            ledger_menu.add_command(
                label=get_menu_text("Search"), command=self.w_ledg.ledger_search)
            ledger_menu.add_command(
                label=get_menu_text("Search via Statement"), command=self.w_ledg.ledger_search_of_statement)
            ledger_menu.add_separator()
            ledger_menu.add_command(
                label=get_menu_text("Balances"), command=self.w_ledg.ledger_balances)
            ledger_menu.add_command(
                label=get_menu_text("Assets"), command=self.w_ledg.ledger_assets)
            ledger_menu.add_command(
                label=get_menu_text("Journal"), command=self.w_ledg.ledger_journal)
            ledger_menu.add_command(
                label=get_menu_text("Account"), command=self.w_ledg.ledger_account)
            ledger_menu.add_command(
                label=get_menu_text("Account Category"), command=self.w_ledg.ledger_account_category)
            ledger_menu.add_separator()
        if self.repo.ledger_is_not_empty():
            ledger_menu.add_command(
                label=get_menu_text("Reset Ledger_daily_balance"), command=self.w_ledg.ledger_daily_balance)            
        ledger_menu.add_command(
            label=get_menu_text("Chart of Accounts"), command=self.w_ledg.ledger_coa_table)
        ledger_menu.add_separator()       
        if self.repo.ledger_is_not_empty():
            ledger_menu.add_command(
                label=get_menu_text("Statement_wo"), command=self.w_ledg.show_statements_no_ledger)

    def _create_menu_show(self, menu, bank_owner_account, menu_font):
        """
         SHOW Menu
        """
        show_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=get_menu_text("Show"), menu=show_menu)
        site_menu = Menu(show_menu, tearoff=0,
                         font=menu_font, bg='Lightblue')
        show_menu.add_cascade(
            label=get_menu_text("WebSites"), menu=site_menu, underline=0)
        for website in decl.WEBSITES.keys():
            site_menu.add_command(label=website,
                                  command=lambda x=decl.WEBSITES[website]: self.w_show.websites(x))
        show_menu.add_separator()
        if application_store.get(declm.DB_alpha_vantage):
            show_menu.add_command(
                label=get_menu_text("Alpha Vantage"), command=self.w_show.show_alpha_vantage)
            show_menu.add_command(
                label=get_menu_text("Alpha Vantage Symbol Search"), command=self.w_show.show_alpha_vantage_search_symbol)
        show_menu.add_separator()
        show_menu.add_command(
            label=get_menu_text("Balances"), command=self.w_show.show_balances_all_banks)
        show_menu.add_separator()
        self._create_menu_banks(
            get_menu_text("Show"), bank_owner_account, show_menu, menu_font)

    def _create_menu_download(self, menu, menu_font):
        """
        DOWNLOAD Menu
        """
        download_menu = Menu(
            menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=get_menu_text("Download"), menu=download_menu)
        download_menu.add_command(
            label=get_menu_text("All_Banks"), command=self.w_dwnld.all_banks)
        download_menu.add_separator()
        download_menu.add_command(
            label=get_menu_text("Prices"), command=self.w_dwnld.import_prices)
        download_menu.add_separator()
        for bank_name in self.bank_names.values():
            bank_code = dict_get_first_key(self.bank_names, bank_name)
            download_menu.add_cascade(
                label=bank_name,
                command=lambda x=bank_code: self.w_dwnld.all_accounts(x))
            accounts = self.repo.shelve_get_accounts(bank_code)
            if accounts:
                for acc in accounts:
                    if 'HKWPD' in acc[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                        download_menu.add_cascade(
                            label=' '.join(
                                [bank_name, get_menu_text("Holding"), acc[decl.KEY_ACC_PRODUCT_NAME]]),
                            command=lambda x=bank_code: self.w_dwnld.all_holdings(x))
                        break
            download_menu.add_separator()

    def _create_menu_database(self, menu, menu_font, bank_owner_account):
        """
        DATABASE Menu
        """
        database_menu = Menu(
            menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=get_menu_text("Database"), menu=database_menu)
        bank_names = {}
        for bank_name in self.bank_names.values():
            bank_code = dict_get_first_key(self.bank_names, bank_name)
            accounts = self.repo.shelve_get_accounts(bank_code)
            if accounts:
                for acc in accounts:
                    if 'HKWPD' in acc[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                        bank_names[bank_code] = bank_name
        if bank_names != {}:
            all_banks_menu = Menu(
                database_menu, tearoff=0, font=menu_font, bg='Lightblue')
            database_menu.add_cascade(
                label=get_menu_text("All_Banks"), menu=all_banks_menu, underline=0)
            database_menu.add_separator()
            all_banks_menu.add_command(
                label=get_menu_text("Holding Performance"),
                command=(lambda x=decl.FN_ALL_BANKS, y='':
                         self.w_db.data_holding_performance(x, y)))
            all_banks_menu.add_command(
                label=get_menu_text("Holding ISIN Comparision"),
                command=(lambda x=decl.FN_ALL_BANKS: self.w_db.data_holding_isin_comparision(x, '')))
            all_banks_menu.add_command(
                label=get_menu_text("Holding ISIN Comparision") + '%',
                command=(lambda x=decl.FN_ALL_BANKS: self.w_db.data_holding_isin_comparision_percent(x, '')))
            all_banks_menu.add_command(
                label=get_menu_text("Transaction Detail"),
                command=(lambda x=decl.FN_ALL_BANKS,
                         y=None: self.w_db.data_transaction_detail(x, y)))
            self._create_menu_banks(
                get_menu_text("Database"), bank_owner_account, database_menu, menu_font)
        database_menu.add_command(
            label=get_menu_text("ISIN Table"), command=self.w_db.data_isin_table)
        if self.repo.isin_with_ticker():
            database_menu.add_separator()
            database_menu.add_command(
                label=get_menu_text("Technical Indicators"), command=self.w_db.data_technical_indicators)
            database_menu.add_separator()
            database_menu.add_command(
                label=get_menu_text("Prices ISINs"),
                command=(lambda x=None: self.w_db.data_prices(x)))
            database_menu.add_command(
                label=get_menu_text("Prices ISINs") + '%',
                command=(lambda x=decl.PERCENT: self.w_db.data_prices(x)))

    def _create_menu_customizing(self, menu, menu_font, MariaDBname):
        """
        CUSTOMIZE Menu
        """
        customize_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=get_menu_text("Customize"), menu=customize_menu)
        customize_menu.add_command(label=get_menu_text("Application INI File"),
                                   command= self._safe_callback(self.w_cust.appcustomizing))
        if application_store.get(None):  # Customizing is done
            customize_menu.add_separator()
            customize_menu.add_command(label=get_menu_text("Import Bankidentifier CSV-File"),
                                       command=self.w_cust.import_bankidentifier)
            customize_menu.add_command(label=get_menu_text("Import Server CSV-File"),
                                       command=self.w_cust.import_server)
            customize_menu.add_command(label="Import Tickers",
                                       command=self.w_cust.import_tickers)
            customize_menu.add_separator()
            customize_menu.add_command(label=get_menu_text("Reset Screen Positions"),
                                       command=self.w_cust.reset)
            if application_store.get(declm.DB_alpha_vantage):
                customize_menu.add_command(label=get_menu_text("Refresh Alpha Vantage"),
                                           command=self.w_cust.alpha_vantage_refresh)
                customize_menu.add_separator()
            if application_store.get(None):  # application customizing is done
                if self.repo.count_server():
                    customize_menu.add_command(label=get_menu_text("New Bank"),
                                               command=self._safe_callback(self.w_cust.bank_data_new))
                    customize_menu.add_command(label=get_menu_text("Delete Bank"),
                                               command=self._safe_callback(self.w_cust.bank_data_delete))
                else:
                    msg.MessageBoxInfo(message=msg.get_message(msg.MESSAGE_TEXT, 'IMPORT_CSV_MISSED', declm.SERVER.upper()))
            if self.bank_names:
                customize_menu.add_command(label=get_menu_text("Show All Data"),
                                           command=self._safe_callback(self.w_cust.bank_show_all_shelve))
                for bank_name in self.bank_names.values():
                    bank_code = dict_get_first_key(self.bank_names, bank_name)
                    cust_bank_menu = Menu(customize_menu, tearoff=0,
                                          font=menu_font, bg='Lightblue')
                    cust_bank_menu.add_command(label=get_menu_text("Change Login Data"),
                                               command=lambda x=bank_code: self.w_cust.bank_data_change(x))
                    if bank_code not in list(decl.SCRAPER_BANKDATA.keys()):
                        cust_bank_menu.add_command(label=get_menu_text("Refresh BankParameterData"),
                                                   command=lambda
                                                   x=bank_code: self.w_cust.bank_refresh_bpd(x))                        
                        cust_bank_menu.add_command(label=get_menu_text("Change Security Function"),
                                                   command=lambda
                                                   x=bank_code: self.w_cust.bank_security_function(x, False))
                        cust_bank_menu.add_command(label=get_menu_text("Change FinTS Transaction Version"),
                                                   command=lambda
                                                   x=bank_code: self.w_cust.bank_version_transaction(x))
                        cust_bank_menu.add_command(label=get_menu_text("Synchronize"),
                                                   command=lambda x=bank_code: self.w_cust.bank_sync(x))
                    cust_bank_menu.add_command(label=get_menu_text("Show Data"),
                                               command=lambda x=bank_code: self.w_cust.bank_show_shelve(x))
                    customize_menu.add_separator()
                    customize_menu.add_cascade(
                        label=bank_name, menu=cust_bank_menu, underline=0)

    def _create_menu_banks(self, menu_text, bank_owner_account, typ_menu, menu_font):
        """
        Populate the top-level bank menu with owners and their accounts.
        
        :param menu_text: Type of menu ("Show", "Transfer", "Database").
        :param bank_owner_account: Dict mapping bank_code -> owner_name -> accounts.
        :param typ_menu: The Tkinter menu object to populate.
        :param menu_font: Font for menus.
        """
        def add_account_menu(accounts, parent_menu, bank_code, bank_name, owner_name=None):
            """Helper to create the appropriate account submenu based on menu_text."""
            if menu_text == get_menu_text("Show"):
                return self._create_menu_show_accounts(accounts, parent_menu, bank_code, bank_name, owner_name)
            elif menu_text == get_menu_text("Database"):
                return self._create_menu_database_accounts(accounts, parent_menu, bank_name, menu_font)
            return False
    
        for bank_code, bank_name in self.bank_names.items():
            # If bank has owner accounts
            if bank_code in bank_owner_account:
                owner_menu = Menu(typ_menu, tearoff=0, font=menu_font, bg='Lightblue')
    
                # Add balances at bank level if in "Show" menu
                if menu_text == get_menu_text("Show"):
                    owner_menu.add_command(
                        label=get_menu_text("Balances"),
                        command=lambda bc=bank_code, bn=bank_name: self.w_show.show_balances(bc, bn)
                    )
    
                owners_exist = False
                for owner_name, accounts in bank_owner_account[bank_code].items():
                    account_menu = Menu(owner_menu, tearoff=0, font=menu_font, bg='Lightblue')
                    accounts_exist = add_account_menu(accounts, account_menu, bank_code, bank_name, owner_name)
                    
                    if accounts_exist:
                        owners_exist = True
                        owner_menu.add_cascade(label=owner_name, menu=account_menu, underline=0)
    
                if owners_exist:
                    typ_menu.add_cascade(label=bank_name, menu=owner_menu, underline=0)
                    typ_menu.add_separator()
    
            # If bank has no owner accounts, create menu directly for bank
            else:
                account_menu = Menu(typ_menu, tearoff=0, font=menu_font, bg='Lightblue')
                # Fallback to first bank code in bank_names if not in bank_owner_account
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                accounts = self.repo.shelve_get_accounts(bank_code)
                accounts_exist = add_account_menu(accounts, account_menu, bank_code, bank_name)
    
                if accounts_exist:
                    typ_menu.add_cascade(label=bank_name, menu=account_menu, underline=0)
                    typ_menu.add_separator()


    def _create_menu_show_accounts(self, accounts, account_menu, bank_code, bank_name, owner_name=None):
        """
        Populate account menu with balances, statements, holdings, and transactions
        using a concise mapping-driven approach.
        """


        if self.repo.shelve_get_loging_online_banking(bank_code):
            login_website = self.repo.shelve_get_loging_online_banking(bank_code)
            if login_website:
                account_menu.add_command(
                    label=get_menu_text("Login Online Banking"),
                    command=lambda x=login_website: self.w_show.websites(x))


        account_menu.add_command(
            label=get_menu_text("Balances"),
            command=lambda bc=bank_code, bn=bank_name: self.w_show.show_balances(bc, bn, owner_name=owner_name)
        )
    
        if not accounts:
            return True
    
        TRANSACTION_MAP = {
            'HKKAZ': ('Statement', self.w_show.show_statements),
            'HKCAZ': ('Statement', self.w_show.show_statements),
            'HKWPD': [('Holding', self.w_show.show_holdings), ('Transactions', self.w_show.show_transactions)],
        }
    
        for acc in accounts:
            transactions = acc.get(decl.KEY_ACC_ALLOWED_TRANSACTIONS, "")
            for txn_type, actions in TRANSACTION_MAP.items():
                if txn_type not in transactions:
                    continue
                actions = actions if isinstance(actions, list) else [actions]
                for label_prefix, callback in (action if isinstance(action, tuple) else action for action in actions):
                    if label_prefix == 'Statement':
                        self.kaz_iban.append(acc[decl.KEY_ACC_IBAN])
                    label = f"{get_menu_text(label_prefix)} {acc[decl.KEY_ACC_PRODUCT_NAME]} {acc[decl.KEY_ACC_ACCOUNT_NUMBER]}"
                    if label_prefix == 'Transactions':
                        label += f" {declm.TRANSACTION.upper()}"
                    account_menu.add_command(
                        label=label,
                        command=lambda bc=bank_code, a=acc, cb=callback: cb(bc, a)
                    )
    
        return True

    def _create_menu_database_accounts(self, accounts, account_menu, bank_name, menu_font):

        accounts_exist = False
        if accounts:
            for acc in accounts:
                if 'HKWPD' in acc[decl.KEY_ACC_ALLOWED_TRANSACTIONS]:
                    accounts_exist = True
                    account_menu.add_command(
                        label=get_menu_text("Holding Performance"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.data_holding_performance(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Holding ISIN Comparision"),
                        command=(lambda x=bank_name, y=acc[decl.KEY_ACC_IBAN]: self.w_db.data_holding_isin_comparision(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Holding ISIN Comparision") + '%',
                        command=(lambda x=bank_name, y=acc[decl.KEY_ACC_IBAN]: self.w_db.data_holding_isin_comparision_percent(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Transaction Detail"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.data_transaction_detail(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Profit of closed Transactions"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.transactions_profit(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Profit Transactions incl. current Depot Positions"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.transactions_profit_all(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Prices ISINs"),
                        command=(lambda x=None: self.w_db.data_prices(x)))
                    account_menu.add_command(
                        label=get_menu_text("Prices ISINs") + '%',
                        command=(lambda x=decl.PERCENT: self.w_db.data_prices(x)))

                    account_menu.add_separator()
                    account_menu.add_command(
                        label=get_menu_text("Transactions Table"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.data_transaction_table(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Holding Table"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.data_holding_table(x, y)))
                    account_menu.add_separator()
                    account_menu.add_command(
                        label=get_menu_text("Update Holding Market Price by Closing Price"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]:
                                 self.w_db.data_update_holding_and_prices(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Update Portfolio Total Amount"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]:
                                 self.w_db.update_holding_total_amount_portfolio(x, y)))
                    account_menu.add_separator()
                    account_menu.add_command(
                        label=get_menu_text("Import Transactions"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.import_transaction(x, y)))
                    account_menu.add_command(
                        label=get_menu_text("Check Transactions Pieces"),
                        command=(lambda x=bank_name,
                                 y=acc[decl.KEY_ACC_IBAN]: self.w_db.transactions_pieces(x, y)))
        return accounts_exist
