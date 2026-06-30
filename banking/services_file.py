'''
Created on 17.05.2026

@author: Wolfg
'''
import zipfile
import tempfile
import os
import atexit

from pandas import read_excel
from pathlib import Path


class TempFileManager:
    """
    Handles creation, tracking, printing, and cleanup of temporary files.

    The manager keeps an internal registry of all temporary files that
    it creates. Files can be generated from text content and optionally
    sent to the operating system's default print service. All tracked
    temporary files are automatically deleted when the application
    terminates or when `cleanup()` is called explicitly.

    Attributes:
        _files (set[pathlib.Path]): Set containing paths of all tracked
            temporary files.
    """
    def __init__(self):
        self._files = set()
        atexit.register(self.cleanup)

    def register(self, filename):
        self._files.add(filename)

    def unregister(self, filename):
        self._files.discard(filename)

    def create_temp_file(self, content, suffix=".txt"):
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            mode="w",
            encoding="utf-8"
        )

        with temp_file:
            temp_file.write(content)

        path = Path(temp_file.name)
        self._files.add(path)

        return path

    def print(self, content):
        filename = self.create_temp_file(content)

        if os.name == "nt":
            os.startfile(str(filename), "print")
        else:
            result = os.system(f"lp '{filename}'")
            if result != 0:
                raise RuntimeError("Printing failed.")
        return filename

    def cleanup(self):
        for file in self._files.copy():
            try:
                file.unlink(missing_ok=True)
            except Exception:
                pass

        self._files.clear()


class FileService:

    @staticmethod
    def spreadsheet_zip_to_csv(
        zip_file: str,
        target_file: str | None = None,
        *,
        sheet_name: str | int = 0,
        separator: str = ",",
        encoding: str = "utf-8",
        index: bool = False,
    ) -> str:
        """
        Extract a spreadsheet from a ZIP archive
        and convert it to CSV.
        Supported spreadsheet formats
        -----------------------------
        - .xlsx
        - .xls
        - .ods
        Parameters
        ----------
        zip_file : str
            Path to the ZIP archive.
        target_file : str, optional
            Output CSV filename.
            If omitted, the filename is generated automatically.
        sheet_name : str | int, optional
            Worksheet name or index.
            Default is first sheet.
        separator : str, optional
            CSV field separator.
            Default is ','.
        encoding : str, optional
            CSV encoding.
            Default is 'utf-8'.
        index : bool, optional
            Export DataFrame index.
            Default is False.
        Returns
        -------
        str
            Path to the generated CSV file.
        Raises
        ------
        FileNotFoundError
            If no spreadsheet file exists in the ZIP archive.
        """
        supported_extensions = {
            ".xlsx",
            ".xls",
            ".ods",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract ZIP archive
            with zipfile.ZipFile(zip_file, "r") as archive:
                archive.extractall(temp_dir)
            # Search for spreadsheet file
            spreadsheet_file = None
            for path in Path(temp_dir).rglob("*"):
                if path.suffix.lower() in supported_extensions:
                    spreadsheet_file = path
                    break
            if spreadsheet_file is None:
                raise FileNotFoundError(
                    "No spreadsheet file found in ZIP archive."
                )
            # Generate target filename
            if target_file is None:
                target_file = (
                    Path(zip_file).with_suffix(".csv")
                )
            # Read spreadsheet
            dataframe = read_excel(
                spreadsheet_file,
                sheet_name=sheet_name,
            )
            # Export CSV
            dataframe.to_csv(
                target_file,
                sep=separator,
                encoding=encoding,
                index=index,
            )
        return str(target_file)
