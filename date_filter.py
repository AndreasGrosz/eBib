#!/usr/bin/env python3
"""
date_filter.py - Datums-Referenz-Filter für eb-gui.py
Ergänzung zur bestehenden eBib GUI um Datumsfilterung nach Spalte 0
KORRIGIERT: Verwendet grid() statt pack() für Konsistenz mit Haupt-GUI
"""

import tkinter as tk
from tkinter import ttk
import re
from datetime import datetime, date
from typing import Optional, Tuple, List


class DateReferenceParser:
    """
    Klasse für das Parsing von Datums-Referenzen mit 2-stelliger Jahr-Logik
    Regel: YY < 30 = 20YY, YY >= 30 = 19YY
    """
    
    @staticmethod
    def convert_two_digit_year(year: int) -> int:
        """Konvertiert 2-stellige Jahre zu 4-stelligen Jahren"""
        if year < 30:
            return 2000 + year
        else:
            return 1900 + year
    
    @staticmethod
    def parse_date_reference(date_input: str) -> Optional[datetime]:
        """
        Parst Datums-Eingabe im Format dd.mm.yy mit flexiblen Trennzeichen
        
        Args:
            date_input: Datums-String (z.B. "15.03.25" oder "15.03.85")
            
        Returns:
            datetime-Objekt oder None bei ungültiger Eingabe
        """
        if not date_input or not isinstance(date_input, str):
            return None
            
        date_str = date_input.strip()
        if not date_str:
            return None
        
        # Verschiedene Formate unterstützen
        patterns = [
            r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2})$',      # dd.mm.yy
            r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$',      # dd.mm.yyyy
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                day, month, year = match.groups()
                day, month, year = int(day), int(month), int(year)
                
                # 2-stellige Jahr-Konvertierung
                if year < 100:
                    year = DateReferenceParser.convert_two_digit_year(year)
                
                try:
                    return datetime(year, month, day)
                except ValueError:
                    # Ungültiges Datum (z.B. 31.02.25)
                    return None
        
        return None
    
    @staticmethod
    def format_date_for_display(date_obj: datetime) -> str:
        """Formatiert Datum für Anzeige als dd.mm.yy"""
        if date_obj is None:
            return ""
        year_short = date_obj.year % 100
        return f"{date_obj.day:02d}.{date_obj.month:02d}.{year_short:02d}"
    
    @staticmethod
    def format_date_iso(date_obj: datetime) -> str:
        """Formatiert Datum für CSV-Vergleich als yyyy-mm-dd"""
        if date_obj is None:
            return ""
        return date_obj.strftime("%Y-%m-%d")


class DateReferenceFilter:
    """
    GUI-Komponente für Datums-Referenz-Filter
    Integriert sich nahtlos in die bestehende eb-gui.py
    KORRIGIERT: Verwendet grid() für Konsistenz
    """
    
    def __init__(self, parent_frame: tk.Widget, colors: dict, row: int, filter_callback=None):
        """
        Initialisiert den Datums-Filter
        
        Args:
            parent_frame: Übergeordnetes tkinter Widget
            colors: Farbschema-Dictionary aus der Haupt-GUI
            row: Grid-Row Position für die Platzierung
            filter_callback: Callback-Funktion für Filter-Änderungen
        """
        self.parent_frame = parent_frame
        self.colors = colors
        self.row = row
        self.filter_callback = filter_callback
        self.parser = DateReferenceParser()
        
        # Interne Variablen
        self.current_date = None
        self.is_valid = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Erstellt die UI-Komponenten für den Datums-Filter - MIT GRID()"""
        
        # Haupt-Frame für Datums-Filter - KONSISTENT mit bestehender GUI
        self.date_filter_frame = tk.Frame(
            self.parent_frame, 
            bg=self.colors['bg'],
            relief='solid', 
            bd=1
        )
        # VERWENDET GRID() statt pack() für Konsistenz
        self.date_filter_frame.grid(row=self.row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=5)
        
        # Titel
        title_label = tk.Label(
            self.date_filter_frame, 
            text="🗓️ Datum der Referenz",
            bg=self.colors['bg'], 
            fg=self.colors['fg'],
            font=('Arial', 10, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(5, 10), padx=5)
        
        # Eingabe-Label
        date_label = tk.Label(
            self.date_filter_frame, 
            text="Datum dd.mm.yy:",
            bg=self.colors['bg'], 
            fg=self.colors['fg']
        )
        date_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Datums-Eingabefeld
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(
            self.date_filter_frame,
            textvariable=self.date_var,
            width=15,
            font=('Arial', 11)
        )
        self.date_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        
        # Validierungs-Label
        self.validation_label = tk.Label(
            self.date_filter_frame,
            text="",
            bg=self.colors['bg'],
            font=('Arial', 10)
        )
        self.validation_label.grid(row=1, column=2, padx=10, pady=2, sticky=tk.W)
        
        # Clear Button
        self.clear_btn = tk.Button(
            self.date_filter_frame,
            text="❌ Löschen",
            command=self.clear_date_filter,
            bg=self.colors['button_bg'],
            fg=self.colors['fg'],
            relief='raised',
            bd=1,
            font=('Arial', 9),
            cursor='hand2'
        )
        self.clear_btn.grid(row=1, column=3, padx=5, pady=2)
        
        # Grid-Konfiguration für das Datums-Filter-Frame
        self.date_filter_frame.columnconfigure(2, weight=1)
        
        # WICHTIG: Grid-Konfiguration für parent_frame
        self.parent_frame.columnconfigure(1, weight=1)
        # Event-Binding
        self.date_var.trace('w', self.on_date_change)
        self.date_entry.bind('<Return>', lambda e: self.apply_filter_if_valid())
        
    def on_date_change(self, *args):
        """Wird aufgerufen, wenn sich die Datums-Eingabe ändert"""
        date_input = self.date_var.get().strip()
        
        if not date_input:
            self.validation_label.config(text="", fg=self.colors['fg'])
            self.current_date = None
            self.is_valid = False
            if self.filter_callback:
                self.filter_callback(None, None)
            return
        
        # Datum parsen
        parsed_date = self.parser.parse_date_reference(date_input)
        
        if parsed_date:
            # Gültiges Datum
            formatted_date = self.parser.format_date_for_display(parsed_date)
            iso_date = self.parser.format_date_iso(parsed_date)
            
            self.validation_label.config(
                text=f"✓ {formatted_date} → {iso_date}", 
                fg="green"
            )
            
            self.current_date = parsed_date
            self.is_valid = True
            
            # Filter anwenden
            if self.filter_callback:
                self.filter_callback(parsed_date, date_input)
        else:
            # Ungültiges Datum
            self.validation_label.config(
                text="✗ Ungültiges Datum", 
                fg="red"
            )
            self.current_date = None
            self.is_valid = False
    
    def apply_filter_if_valid(self):
        """Wendet Filter an, falls Datum gültig ist (für Enter-Taste)"""
        if self.is_valid and self.filter_callback:
            self.filter_callback(self.current_date, self.date_var.get().strip())
    
    def clear_date_filter(self):
        """Löscht den Datums-Filter"""
        self.date_var.set("")
        self.validation_label.config(text="", fg=self.colors['fg'])
        self.current_date = None
        self.is_valid = False
        if self.filter_callback:
            self.filter_callback(None, None)
    
    def get_current_date(self) -> Optional[datetime]:
        """Gibt das aktuell eingegebene Datum zurück"""
        return self.current_date if self.is_valid else None
    
    def get_current_iso_date(self) -> Optional[str]:
        """Gibt das aktuelle Datum im ISO-Format (yyyy-mm-dd) zurück"""
        if self.current_date:
            return self.parser.format_date_iso(self.current_date)
        return None


def filter_tsv_rows_by_date(rows: List[List[str]], target_date: datetime) -> List[List[str]]:
    """
    Filtert TSV-Zeilen nach Datum in Spalte 0
    
    Args:
        rows: Liste von TSV-Zeilen als String-Listen
        target_date: Ziel-Datum für den Filter
        
    Returns:
        Gefilterte Liste von Zeilen
    """
    if not target_date:
        return rows
    
    target_iso = DateReferenceParser.format_date_iso(target_date)
    filtered_rows = []
    
    for row in rows:
        if len(row) > 0:
            # Spalte 0 ist das Datum
            row_date = row[0].strip()
            
            # Exakter Vergleich mit ISO-Format
            if row_date.startswith(target_iso):
                filtered_rows.append(row)
    
    return filtered_rows


# Test-Funktion für das Modul
def test_date_parser():
    """Testet die Datums-Parser-Funktionalität"""
    parser = DateReferenceParser()
    
    test_cases = [
        "15.03.25",  # → 2025-03-15
        "15.03.85",  # → 1985-03-15
        "01.01.99",  # → 1999-01-01
        "31.12.29",  # → 2029-12-31
        "15/03/25",  # Alternative Trenner
        "15-03-25",  # Alternative Trenner
        "invalid",   # Ungültig
        "32.01.25",  # Ungültiger Tag
        "",          # Leer
    ]
    
    print("=== Test der Datums-Parser-Funktionalität ===")
    for test_input in test_cases:
        result = parser.parse_date_reference(test_input)
        if result:
            iso_format = parser.format_date_iso(result)
            display_format = parser.format_date_for_display(result)
            print(f"'{test_input}' → {iso_format} (Display: {display_format})")
        else:
            print(f"'{test_input}' → UNGÜLTIG")


if __name__ == "__main__":
    # Test ausführen wenn Modul direkt gestartet wird
    test_date_parser()
