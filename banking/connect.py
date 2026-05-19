'''
Created on 02.01.2026
__updated__ = "2026-05-18"
@author: Wolfgang Kramer
'''
from tkinter import (
    Tk, Canvas, StringVar, GROOVE, END
)
from tkinter.ttk import Style, Entry, Label, Combobox, Button
from PIL import ImageTk
from mariadb import connect, Error

import banking.declarations as decl
import banking.declarations_mariadb as declm
import banking.message_handler as msg

from banking.connect_data import ConnectionResult, connectionresult

class ConnectController:

    def run(self) -> ConnectionResult:
        view = ConnectView()
        view.show()

class ConnectView:

    def __init__(self, title=msg.MESSAGE_TITLE):

        self.directory = ""
        self.logging = False
        self.load_timer = None

        self.window = Tk()
        self.window.title(title)
        self.window.geometry("600x450+1+1")
        self.window.resizable(0, 0)

        self.canvas = Canvas(self.window, width=600, height=400)
        self.canvas.pack(fill="both", expand=True)

        try:
            self.bg_photo = ImageTk.PhotoImage(file="background.gif")
            self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        except Exception as e:
            print(msg.get_message(msg.MESSAGE_TEXT, "CONNECT_IMAGE_ERROR", e))

        self._build_ui()

        self.footer = StringVar(value="")
        self.message_widget = Label(
            self.window,
            textvariable=self.footer,
            foreground="RED",
            justify="center"
        )
        self.message_widget.pack(side="bottom", fill="x")

        self.window.protocol(decl.WM_DELETE_WINDOW, self._on_close)

    def _build_ui(self):
        self._define_styles()

        self.user_entry = self._add_labeled_entry(
            decl.MARIADB_USER, connectionresult.user, 40
        )
        self.user_entry.focus_set()
        self.user_entry.bind("<KeyRelease>", self._schedule_db_load)

        self.password_entry = self._add_labeled_entry(
            decl.MARIADB_PASSWORD, connectionresult.password, 80, show="*"
        )
        self.password_entry.bind("<KeyRelease>", self._schedule_db_load)

        self.host_entry = self._add_labeled_entry(
            decl.MARIADB_HOST, connectionresult.host, 120
        )

        self.db_label = Label(self.window, text=decl.MARIADB_NAME)
        self.db_combo = Combobox(self.window, state="normal", width=30)
        self.db_combo.bind("<<ComboboxSelected>>", self._database_selected)

        self.canvas.create_window(150, 160, window=self.db_label, anchor="e")
        self.canvas.create_window(160, 160, window=self.db_combo, anchor="w")

        self.connect_button = Button(
            self.window,
            text=decl.BUTTON_OK,
            command=self._connect_to_db
        )
        self.canvas.create_window(300, 240, window=self.connect_button)

    def _define_styles(self):
        style = Style()
        style.theme_use(style.theme_names()[0])
        style.configure("TLabel", font=("Arial", 8, "bold"))
        style.configure("OPT.TLabel", font=("Arial", 8, "bold"), foreground="Grey")
        style.configure("HDR.TLabel", font=("Courier", 12, "bold"), foreground="Grey")
        style.configure(
            "TButton",
            font=("Arial", 8, "bold"),
            relief=GROOVE,
            highlightcolor="blue",
            highlightthickness=5,
            shiftrelief=3,
        )
        style.configure("TText", font=("Courier", 8))

    def _add_labeled_entry(self, label_text, field_value, y, show=None):
        label = Label(self.window, text=label_text)
        entry = Entry(self.window, show=show) if show else Entry(self.window)
        entry.delete(0, END)
        entry.insert(0, field_value)
        entry.bind("<FocusIn>", self._schedule_db_load)

        self.canvas.create_window(150, y, window=label, anchor="e")
        self.canvas.create_window(160, y, window=entry, anchor="w")

        return entry

    def _schedule_db_load(self, event=None):
        if self.load_timer:
            self.window.after_cancel(self.load_timer)
        self.load_timer = self.window.after(500, self._load_databases)

    def _load_databases(self):
        connectionresult.user = self.user_entry.get().strip()
        connectionresult.password = self.password_entry.get().strip()
        connectionresult.host = self.host_entry.get().strip()

        if not connectionresult.user or not connectionresult.password:
            return

        try:
            conn = connect(
                host=connectionresult.host,
                user=connectionresult.user,
                password=connectionresult.password,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")

            databases = [db[0] for db in cursor.fetchall()]
            system_dbs = {
                "information_schema",
                "mysql",
                "performance_schema",
                "sys",
            }
            databases = [db for db in databases if db not in system_dbs]

            self.db_combo["values"] = databases
            if databases:
                self.db_combo.current(0)   
                if declm.PRODUCTIVE_DATABASE_NAME in databases:
                    index = databases.index(declm.PRODUCTIVE_DATABASE_NAME)
                    self.db_combo.current(index)                

        except Error:
            self.db_combo["values"] = []
            self.db_combo.set("")

    def _database_selected(self, event=None):
        connectionresult.database = self.db_combo.get()

    def _connect_to_db(self):
        connectionresult.database = self.db_combo.get()

        self.footer.set(msg.get_message(msg.MESSAGE_TEXT, "CONNECT_MARIADB", connectionresult.database))
        connectionresult.connected = True

        self.window.destroy()

    def _on_close(self):
        connectionresult.connected = False
        self.window.quit()

    def show(self):
        self.window.mainloop()

