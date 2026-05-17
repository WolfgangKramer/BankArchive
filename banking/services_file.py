'''
Created on 17.05.2026

@author: Wolfg
'''
import zipfile
import tempfile
import os

from pandas import read_excel
from pathlib import Path
from fpdf import FPDF


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


class PDFService:
    """
    Framework: 
        with headings (H1–H3),
        body text,
        logs (INFO/WARN/ERROR),
        tables and clean styling
        
    Example:
    
                    pdf = PDFService("report.pdf")
                    pdf.add_page()
                    
                    # Titel
                    pdf.add_heading("System Report", level=1)
                    pdf.add_heading("Zusammenfassung", level=2)
                    
                    # Text
                    pdf.add_text("Das ist ein Beispieltext.\nMit Zeilenumbruch.")
                    
                    # Logs
                    pdf.add_log("System gestartet", "INFO")
                    pdf.add_log("Speicher fast voll", "WARN")
                    pdf.add_log("Fehler beim Laden!", "ERROR")
                    
                    # Tabelle
                    headers = ["Name", "Status", "Wert"]
                    rows = [
                        ["CPU", "OK", "45%"],
                        ["RAM", "WARN", "85%"],
                        ["Disk", "ERROR", "95%"]
                    ]
                    
                    pdf.add_heading("Systemwerte", level=2)
                    pdf.add_table(headers, rows)
                    
                    # Seitenumbruch testen
                    pdf.add_text("Neue Seite\fHier geht es weiter")
                    
                    pdf.save()
                    pdf.show()    
        
    """
    PDF_FILE_NAME = "report.pdf"

    def __init__(self, filename=PDF_FILE_NAME):
        self.pdf = FPDF()
        self.filename = filename
        self.pdf.set_auto_page_break(auto=True, margin=15)

        # 🔹 Stylesystem
        self.styles = {
            "H1": {"size": 12, "color": (0, 0, 0), "style": "B"},
            "H2": {"size": 10, "color": (0, 0, 0), "style": "B"},
            "H3": {"size": 8, "color": (50, 50, 50), "style": "B"},
            "BODY": {"size": 8, "color": (0, 0, 0), "style": ""},
            "INFO": {"size": 8, "color": (0, 102, 204), "style": ""},
            "WARN": {"size": 8, "color": (255, 140, 0), "style": "B"},
            "ERROR": {"size": 8, "color": (200, 0, 0), "style": "B"},
        }

    def _apply_style(self, style_name):
        style = self.styles.get(style_name, self.styles["BODY"])
        self.pdf.set_font("Arial", style=style["style"], size=style["size"])
        self.pdf.set_text_color(*style["color"])

    def add_page(self):
        self.pdf.add_page()

    def add_text(self, text, style="BODY", line_height=8):
        self._apply_style(style)

        pages = text.split("\f")
        for i, page in enumerate(pages):
            if i > 0:
                self.add_page()
            self.pdf.multi_cell(0, line_height, page)

    def add_heading(self, text, level=1):
        style = f"H{level}"
        self._apply_style(style)
        self.pdf.ln(5)
        self.pdf.cell(0, 10, text, ln=True)
        self.pdf.ln(2)

    def add_log(self, text, level="INFO"):
        prefix = f"[{level}] "
        self.add_text(prefix + text, style=level)

    def add_table(self, headers, rows, col_widths=None):
        self._apply_style("BODY")

        if not col_widths:
            col_widths = [190 / len(headers)] * len(headers)

        # Header
        self._apply_style("H3")
        for i, header in enumerate(headers):
            self.pdf.cell(col_widths[i], 10, str(header), border=1)
        self.pdf.ln()

        # Rows
        self._apply_style("BODY")
        for row in rows:
            for i, col in enumerate(row):
                self.pdf.cell(col_widths[i], 8, str(col), border=1)
            self.pdf.ln()

    def save(self):
        self.pdf.output(self.filename)

    def show(self):
        os.startfile(self.filename)


