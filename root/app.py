'''
Created on 02.01.2026

@author: Wolfg
'''
# banking/app.py


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
