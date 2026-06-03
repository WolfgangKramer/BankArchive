'''
Created on 05.05.2026

@author: Wolfg
'''
import banking.declarations as decl


class ShelveFormatter:
    def __init__(self, shelve_data, shelve_keys, account_fields=None):
        self.shelve_data = shelve_data
        self.shelve_keys = shelve_keys
        self.account_fields = account_fields  # 👈 NEU
        self.lines = []

    def format(self) -> str:

        for key in self.shelve_keys:
            value = self.shelve_data.get(key)

            if not value:
                self._add_line(key, "None")
                continue

            if key == decl.KEY_ACCOUNTS:
                self._format_accounts(key, value)
            else:
                self._format_generic(key, value)

        return "\n".join(self.lines)

    # ------------------------
    # Core helpers
    # ------------------------

    def _add_line(self, key, value, indent=0):
        prefix = " " * indent
        self.lines.append(f"{prefix}{key:20} {value}")

    def _format_accounts(self, key, accounts):
        self.lines.append(f"{key:20}")
    
        for account in accounts:
            self.lines.append(f"{'':5} {'_' * 80}")
    
            for field, value in account.items():
    
                # 👇 FILTER LOGIK
                if self.account_fields and field not in self.account_fields:
                    continue
    
                if isinstance(value, list):
                    self._format_list(field, value, indent=5)
                else:
                    self._add_line(field, value, indent=5)

    def _format_generic(self, key, value):
        if isinstance(value, list):
            self._format_list(key, value)

        elif isinstance(value, dict):
            self._format_dict(key, value)

        else:
            self._add_line(key, value)

    def _format_list(self, key, values, indent=0):
        description = key
        for item in values:
            self._add_line(description, item, indent)
            description = " " * len(key)

    def _format_dict(self, key, dictionary, indent=0):
        description = key

        for k, v in dictionary.items():
            self._add_line(description, k, indent)
            description = " " * len(key)
            self._add_line(description, v, indent)
