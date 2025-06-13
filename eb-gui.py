#!/usr/bin/env python3
"""
eb-gui.py - Grafische Suchoberfläche für die eBib-Datenbank
Mit MD5-Duplikat-Filterung, robuster TSV-Behandlung, Dark Mode und Datums-Referenz-Filter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
from pathlib import Path
import csv
import os
import sys
from datetime import datetime
import re
from collections import defaultdict
import sqlite3
import time

# Import der bestehenden eBib-Funktionalität
try:
    from eb import create_ods_with_hyperlinks, INPUT_FILE, OUTPUT_DIR, TAG_DEFS
except ImportError:
    # Fallback falls eb.py nicht verfügbar
    INPUT_FILE = '/media/synology/files/projekte/kd0089 my eBib & DMS/Compare-n-Share/s_250518-list-of-all-files-in-eBib-HDD-v032.tsv'
    OUTPUT_DIR = Path.home() / 'Downloads'
    # ERWEITERTE TAG_DEFS basierend auf Extension-Analyse
    TAG_DEFS = {
        "#text": {
            # Bestehende
            "pdf", "doc", "docx", "txt", "djvu", "odt", "rtf", "html", "htm", "epub", "mobi", "tex", "md", "chm",
            # Neue aus Analyse
            "shtml", "mht", "url", "memo", "wps", "hlp", "man", "info", "rst",
            # Spreadsheets
            "ods", "xls", "xlsx", "csv", "tsv"
        },
        "#audio": {
            # Bestehende
            "mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus", "mp2", "ra", "au", "mid", "midi",
            # Neue aus Analyse (besonders wichtig: frf mit 5.532 Dateien!)
            "frf", "m3u", "ram", "aiff", "cda"
        },
        "#graphik": {
            # Bestehende
            "jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff", "tif", "webp", "ico", "psd", "raw", "cr2", "nef",
            # Neue aus Analyse
            "pcx", "emz", "thm", "eps", "wmf", "emf", "pct", "pic"
        },
        "#video": {
            # Bestehende
            "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ogv", "rm", "asf", "vob",
            # Neue aus Analyse
            "bup", "ifo", "mpg", "mpeg", "divx", "xvid", "ogm"
        }
    }

# Import des neuen Datums-Filter-Moduls
try:
    from date_filter import DateReferenceFilter, filter_tsv_rows_by_date
    HAS_DATE_FILTER = True
except ImportError:
    # KEIN Fallback - Fehler sofort sichtbar machen
    print("FEHLER: date_filter.py nicht gefunden!")
    print("Bitte stellen Sie sicher, dass date_filter.py im gleichen Verzeichnis liegt.")
    sys.exit(1)

# SQLite-DB für Performance
SQLITE_DB = '/tmp/ebib_search.db'

FIELD_MAP = {
    "datum": 0,
    "name": 3,
    "pfad": 2,
    "ext": 4,
    "md5": 7,  # MD5-Spalte für Duplikat-Erkennung
}

FIELD_ALIASES = {
    "dateiname": "name",
    "docdatum": "datum",
}

class EBibGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("eBib Search GUI - Mit Duplikat-Filter und Datums-Referenz")
        self.root.geometry("1000x700")  # Noch kleiner: 700 statt 800
        self.root.minsize(900, 700)     # Kleineres Minimum

        # Fenster beim Start maximieren - PLATTFORM-SICHER
        try:
            # Versuche verschiedene Maximierungs-Methoden
            self.root.state('zoomed')  # Linux/Windows
        except tk.TclError:
            try:
                self.root.wm_state('zoomed')  # Alternative
            except tk.TclError:
                try:
                    # macOS/andere Systeme
                    self.root.attributes('-zoomed', True)
                except tk.TclError:
                    # Fallback: Manuelle Maximierung
                    self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
                    print("[INFO] Fenster manuell maximiert (zoomed nicht unterstützt)")

        # Dark Mode Styling
        self.setup_dark_theme()

        # Variablen für die Suche
        self.search_running = False
        self.search_thread = None
        self.found_rows = []

        # Neue Variable für Datums-Filter
        self.current_date_filter = None

        # Lokaler Cache für bessere Performance (jetzt SQLite)
        self.sqlite_db = SQLITE_DB
        self.db_ready = False

        self.setup_ui()

        # SQLite-DB beim Start prüfen
        self.init_sqlite_db()

    def setup_dark_theme(self):
        """Konfiguriert sehr dunkles Theme für bessere Lesbarkeit bei grauem Star"""
        # Sehr dunkle Farben mit hohem Kontrast
        self.colors = {
            'bg': '#1a1a1a',           # Sehr dunkler Hintergrund
            'fg': '#e0e0e0',           # Helles Grau statt Weiß
            'select_bg': '#2d2d2d',    # Dunkler Auswahl-Hintergrund
            'entry_bg': '#262626',     # Sehr dunkle Eingabefelder
            'entry_fg': '#f0f0f0',     # Sehr heller Text in Eingaben
            'button_bg': '#333333',    # Dunkle Buttons
            'frame_bg': '#1a1a1a',     # Gleich wie Haupthintergrund - komplett dunkel
            'highlight': '#4a9eff',    # Sanfteres Blau
            'border': '#404040',       # Dunkle Borders
            'disabled': '#666666',     # Disabled Text
        }

        # Root-Fenster styling
        self.root.configure(bg=self.colors['bg'])

        # TTK Style konfigurieren - mit GRÖßEREN Checkboxen
        style = ttk.Style()
        style.theme_use('clam')  # Basis-Theme

        # Checkbutton Styles - GRÖßER
        style.configure('TCheckbutton',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       focuscolor='none',
                       borderwidth=0,
                       font=('Arial', 11))  # Größere Schrift

        style.map('TCheckbutton',
                 background=[('active', self.colors['bg'])],
                 foreground=[('active', self.colors['fg'])],
                 indicatorcolor=[('selected', self.colors['highlight']),
                               ('!selected', self.colors['entry_bg'])])

        # Checkbox-Größe anpassen (System-abhängig)
        style.configure('TCheckbutton',
                       indicatormargins=[3, 3, 3, 3],  # Mehr Platz um Checkbox
                       indicatorsize=16)  # Größere Checkbox

        # Frame Styles - sehr dunkel
        style.configure('TFrame',
                       background=self.colors['bg'],
                       borderwidth=0)

        style.configure('TLabelFrame',
                       background=self.colors['bg'],  # Haupthintergrund auch dunkel
                       foreground=self.colors['fg'],
                       borderwidth=1,
                       relief='solid',
                       bordercolor=self.colors['border'])

        style.configure('TLabelFrame.Label',
                       background=self.colors['bg'],  # Label-Hintergrund auch dunkel
                       foreground=self.colors['fg'],
                       font=('Arial', 10, 'bold'))

        # Label Styles - heller Text auf dunklem Grund
        style.configure('TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'])

        style.configure('Heading.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       font=('Arial', 12, 'bold'))

        # Button Styles - sehr dunkel
        style.configure('TButton',
                       background=self.colors['button_bg'],
                       foreground=self.colors['fg'],
                       borderwidth=1,
                       focuscolor='none',
                       relief='solid')

        style.map('TButton',
                 background=[('active', self.colors['highlight']),
                           ('pressed', self.colors['select_bg'])],
                 foreground=[('active', '#ffffff'),
                           ('pressed', '#ffffff')])

        # Entry Styles - sehr dunkle Eingabefelder
        style.configure('TEntry',
                       fieldbackground=self.colors['entry_bg'],
                       foreground=self.colors['entry_fg'],
                       borderwidth=1,
                       insertcolor=self.colors['entry_fg'],
                       relief='solid',
                       bordercolor=self.colors['border'])

        style.map('TEntry',
                 fieldbackground=[('focus', self.colors['entry_bg'])],
                 bordercolor=[('focus', self.colors['highlight'])])

        # Combobox Styles - sehr dunkel
        style.configure('TCombobox',
                       fieldbackground=self.colors['entry_bg'],
                       foreground=self.colors['entry_fg'],
                       borderwidth=1,
                       arrowcolor=self.colors['fg'],
                       relief='solid',
                       bordercolor=self.colors['border'])

        style.map('TCombobox',
                 fieldbackground=[('readonly', self.colors['entry_bg']),
                                ('focus', self.colors['entry_bg'])],
                 foreground=[('readonly', self.colors['entry_fg'])],
                 bordercolor=[('focus', self.colors['highlight'])],
                 selectbackground=[('readonly', self.colors['highlight'])])

        # Checkbutton Styles - sehr dunkel (überschreibt die obige Definition)
        style.configure('TCheckbutton',
                       background=self.colors['bg'],
                       foreground=self.colors['fg'],
                       focuscolor='none',
                       borderwidth=0,
                       font=('Arial', 12, 'bold'))  # NOCH größere, fette Schrift

        style.map('TCheckbutton',
                 background=[('active', self.colors['bg'])],
                 foreground=[('active', self.colors['fg'])],
                 indicatorcolor=[('selected', self.colors['highlight']),
                               ('!selected', self.colors['entry_bg'])])

        # Notebook Styles - sehr dunkel
        style.configure('TNotebook',
                       background=self.colors['bg'],
                       borderwidth=0,
                       tabmargins=[0, 0, 0, 0])

        style.configure('TNotebook.Tab',
                       background=self.colors['button_bg'],
                       foreground=self.colors['fg'],
                       padding=[20, 8],
                       borderwidth=1,
                       relief='solid')

        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['highlight']),
                           ('active', self.colors['select_bg'])],
                 foreground=[('selected', '#ffffff'),
                           ('active', self.colors['fg'])])

        # Progressbar Style - sanfteres Blau
        style.configure('TProgressbar',
                       background=self.colors['highlight'],
                       troughcolor=self.colors['entry_bg'],
                       borderwidth=0,
                       lightcolor=self.colors['highlight'],
                       darkcolor=self.colors['highlight'])

    def setup_ui(self):
        # Hauptframe mit Padding
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        # Notebook für Tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Tab 1: Einfache Suche
        self.simple_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(self.simple_frame, text="Einfache Suche")
        self.setup_simple_search()

        # Tab 2: Erweiterte Suche
        self.advanced_frame = tk.Frame(notebook, bg=self.colors['bg'])
        notebook.add(self.advanced_frame, text="Erweiterte Suche")
        self.setup_advanced_search()

        # Duplikat-Filter Frame
        filter_frame = tk.Frame(main_frame, bg=self.colors['bg'], relief='solid', bd=1)
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10), padx=5)

        # Titel für Filter-Optionen
        filter_title = tk.Label(filter_frame, text="Filter-Optionen",
                               bg=self.colors['bg'], fg=self.colors['fg'],
                               font=('Arial', 10, 'bold'))
        filter_title.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5, 5), padx=5)

        self.remove_duplicates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="🔄 Duplikate entfernen (per MD5)",
                       variable=self.remove_duplicates_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)

        self.show_stats_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_frame, text="📊 Statistiken anzeigen",
                       variable=self.show_stats_var).grid(row=1, column=1, sticky=tk.W, padx=20, pady=5)

        # Status und Buttons Frame - SICHTBAR machen
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # Such-Button - GROSS und SICHTBAR
        self.search_button = tk.Button(button_frame,
                                      text="🔍 SUCHE STARTEN",
                                      command=self.start_search,
                                      bg=self.colors['highlight'],
                                      fg='white',
                                      font=('Arial', 14, 'bold'),
                                      padx=30,
                                      pady=10,
                                      relief='raised',
                                      borderwidth=3,
                                      cursor='hand2')
        self.search_button.grid(row=0, column=0, padx=(0, 15), pady=5)

        # Fortschrittsbalken
        self.progress = ttk.Progressbar(button_frame, mode='indeterminate', length=250)
        self.progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 15))

        # Ergebnisse öffnen Button
        self.open_button = tk.Button(button_frame,
                                    text="📊 CALC ÖFFNEN",
                                    command=self.open_results,
                                    state='disabled',
                                    bg=self.colors['button_bg'],
                                    fg=self.colors['fg'],
                                    font=('Arial', 12, 'bold'),
                                    padx=20,
                                    pady=8,
                                    relief='raised',
                                    borderwidth=2,
                                    cursor='hand2')
        self.open_button.grid(row=0, column=2, pady=5)

        # Status Label
        self.status_label = tk.Label(main_frame, text="Bereit für Suche",
                                    bg=self.colors['bg'], fg=self.colors['fg'],
                                    font=('Arial', 11))
        self.status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # Ergebnisse Textfeld mit Dark Mode
        self.results_text = scrolledtext.ScrolledText(
            main_frame,
            height=15,  # Zurück auf 15
            width=90,
            bg=self.colors['entry_bg'],
            fg=self.colors['entry_fg'],
            insertbackground=self.colors['fg'],  # Cursor-Farbe
            selectbackground=self.colors['highlight'],
            selectforeground=self.colors['fg'],
            borderwidth=1,
            relief='solid',
            font=('Consolas', 10)
        )
        self.results_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

        # Grid-Konfiguration für Responsive Design
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Textfeld kann sich ausdehnen
        button_frame.columnconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Globale Keyboard-Shortcuts
        self.root.bind('<Control-Return>', lambda e: self.start_search())
        self.root.bind('<F5>', lambda e: self.start_search())

        # Tab-Wechsel mit Page Up/Down
        self.root.bind('<Prior>', lambda e: self.switch_to_tab(0))  # Page Up -> Einfache Suche
        self.root.bind('<Next>', lambda e: self.switch_to_tab(1))   # Page Down -> Erweiterte Suche

        # Escape zum Stoppen
        self.root.bind('<Escape>', lambda e: self.stop_search() if self.search_running else None)

    def init_sqlite_db(self):
        """Prüft SQLite-DB beim Start"""
        if not os.path.exists(self.sqlite_db):
            self.status_label.config(text="❌ SQLite-DB nicht gefunden. Bitte erst ebib_preprocessor.py ausführen!")
            self.db_ready = False
            print(f"[ERROR] SQLite-DB nicht gefunden: {self.sqlite_db}")
            print("Bitte führen Sie zuerst 'python ebib_preprocessor.py' aus!")
            return

        try:
            # Test-Verbindung
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM files")
            record_count = cursor.fetchone()[0]
            conn.close()

            self.db_ready = True
            self.status_label.config(text=f"✅ SQLite-DB bereit - {record_count:,} Records für ultra-schnelle Suche")
            print(f"[INFO] SQLite-DB geladen: {record_count:,} Records")

        except Exception as e:
            self.status_label.config(text=f"❌ SQLite-DB Fehler: {e}")
            self.db_ready = False
            print(f"[ERROR] SQLite-DB Fehler: {e}")

    def search_sqlite(self, query, has_date_filter, has_type_filter):
        """Ultra-schnelle SQLite-Suche"""
        if not self.db_ready:
            return []

        conn = sqlite3.connect(self.sqlite_db)
        cursor = conn.cursor()

        # SQL-Query dynamisch aufbauen
        conditions = []
        params = []

        # Text-Suche (falls vorhanden)
        if query.strip():
            conditions.append("filename_lower LIKE ?")
            params.append(f"%{query.lower()}%")

        # Datums-Filter
        if has_date_filter and self.current_date_filter:
            date_str = self.current_date_filter.strftime("%Y-%m-%d")
            conditions.append("date_of_work LIKE ?")
            params.append(f"{date_str}%")

        # Dateityp-Filter
        if has_type_filter:
            type_conditions = []
            if self.type_vars['text'].get():
                type_conditions.append("file_type = 'text'")
            if self.type_vars['audio'].get():
                type_conditions.append("file_type = 'audio'")
            if self.type_vars['graphik'].get():
                type_conditions.append("file_type = 'graphik'")
            if self.type_vars['video'].get():
                type_conditions.append("file_type = 'video'")
            if self.type_vars['sonstige'].get():
                type_conditions.append("file_type = 'sonstige'")

            if type_conditions:
                conditions.append(f"({' OR '.join(type_conditions)})")

        # SQL zusammensetzen
        base_query = """
            SELECT date_of_work, link, path, filename, extension, size, date, hash
            FROM files
        """

        if conditions:
            sql = base_query + " WHERE " + " AND ".join(conditions)
        else:
            sql = base_query

        # Limit für Performance
        sql += " LIMIT 50000"

        start_time = time.time()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        query_time = (time.time() - start_time) * 1000

        conn.close()

        print(f"[DEBUG] SQLite-Query: {len(results)} Ergebnisse in {query_time:.1f}ms")
        return results

    def switch_to_tab(self, tab_index):
        """Wechselt zwischen den Tabs (0=Einfach, 1=Erweitert)"""
        try:
            # Finde das Notebook Widget
            for widget in self.root.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Notebook):
                        if tab_index < len(child.tabs()):
                            child.select(tab_index)
                        return
        except Exception as e:
            print(f"[DEBUG] Tab-Wechsel fehlgeschlagen: {e}")

    def setup_simple_search(self):
        """Einfache Suche mit einem Textfeld"""
        # Titel
        title_label = tk.Label(self.simple_frame, text="Schnellsuche",
                              bg=self.colors['bg'], fg=self.colors['fg'],
                              font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Suchfeld
        search_label = tk.Label(self.simple_frame, text="Suchbegriff:",
                               bg=self.colors['bg'], fg=self.colors['fg'])
        search_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.simple_search_var = tk.StringVar()
        search_entry = ttk.Entry(self.simple_frame, textvariable=self.simple_search_var, width=50)
        search_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))

        # Enter-Taste für Suche aktivieren
        search_entry.bind('<Return>', lambda e: self.start_search())
        search_entry.bind('<KP_Enter>', lambda e: self.start_search())  # Numpad Enter

        # Fokus auf Suchfeld setzen
        search_entry.focus_set()

        # **NEUE ERGÄNZUNG: Datums-Referenz-Filter**
        if HAS_DATE_FILTER:
            self.date_filter = DateReferenceFilter(
                self.simple_frame,
                self.colors,
                row=2,  # Position nach Suchfeld
                filter_callback=self.on_date_filter_change
            )

        # Datei-Typ Filter
        type_frame = tk.Frame(self.simple_frame, bg=self.colors['bg'], relief='solid', bd=1)
        type_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=5)

        # Titel für Dateityp Filter
        type_title = tk.Label(type_frame, text="Dateityp Filter",
                             bg=self.colors['bg'], fg=self.colors['fg'],
                             font=('Arial', 10, 'bold'))
        type_title.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(5, 10), padx=5)

        self.type_vars = {}
        self.type_vars['text'] = tk.BooleanVar(value=True)  # Text als Standard
        self.type_vars['audio'] = tk.BooleanVar()
        self.type_vars['graphik'] = tk.BooleanVar()
        self.type_vars['video'] = tk.BooleanVar()
        self.type_vars['sonstige'] = tk.BooleanVar()

        ttk.Checkbutton(type_frame, text="📄 Text (PDF, DOC, HTML...)",
                       variable=self.type_vars['text']).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Checkbutton(type_frame, text="🎵 Audio (MP3, WAV, FRF...)",
                       variable=self.type_vars['audio']).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Checkbutton(type_frame, text="🖼️ Graphik (JPG, PNG, PCX...)",
                       variable=self.type_vars['graphik']).grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Checkbutton(type_frame, text="🎬 Video (MP4, AVI, BUP...)",
                       variable=self.type_vars['video']).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Checkbutton(type_frame, text="📋 Sonstige",
                       variable=self.type_vars['sonstige']).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Beispiele
        examples_frame = tk.Frame(self.simple_frame, bg=self.colors['bg'], relief='solid', bd=1)
        examples_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10, padx=5)

        # Titel für Beispiele
        examples_title = tk.Label(examples_frame, text="Beispiele",
                                 bg=self.colors['bg'], fg=self.colors['fg'],
                                 font=('Arial', 10, 'bold'))
        examples_title.grid(row=0, column=0, sticky=tk.W, pady=(5, 10), padx=5)

        examples_text = """• archive → Findet alle Dateien mit "archive" im Namen oder Pfad
• 2023 → Findet alle Dateien von 2023
• manual → Findet alle Handbücher und Anleitungen
• german → Findet alle Dateien in deutschen Ordnern"""

        examples_label = tk.Label(examples_frame, text=examples_text,
                                 bg=self.colors['bg'], fg=self.colors['fg'],
                                 justify=tk.LEFT)
        examples_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5))

        self.simple_frame.columnconfigure(1, weight=1)

    def setup_advanced_search(self):
        """Erweiterte Suche mit mehreren Feldern und Boolean-Logik"""
        # Titel
        title_label = tk.Label(self.advanced_frame, text="Erweiterte Suche",
                              bg=self.colors['bg'], fg=self.colors['fg'],
                              font=('Arial', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # UND-Bedingungen
        and_frame = tk.Frame(self.advanced_frame, bg=self.colors['bg'], relief='solid', bd=1)
        and_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Titel für UND-Bedingungen
        and_title = tk.Label(and_frame, text="UND-Bedingungen (alle müssen erfüllt sein)",
                            bg=self.colors['bg'], fg=self.colors['fg'],
                            font=('Arial', 10, 'bold'))
        and_title.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(5, 10), padx=5)

        self.and_entries = []
        field_options = ["", "name", "pfad", "ext", "datum"]
        ext_values = ["", "pdf", "doc", "docx", "txt", "mp3", "wav", "jpg", "jpeg", "png", "gif", "mp4", "avi", "zip", "rar"]

        for i in range(3):
            field_var = tk.StringVar(value="name" if i == 0 else "")
            value_var = tk.StringVar()
            ext_var = tk.StringVar()

            # Labels mit dunklem Hintergrund
            condition_label = tk.Label(and_frame, text=f"Bedingung {i+1}:",
                                      bg=self.colors['bg'], fg=self.colors['fg'])
            condition_label.grid(row=i+1, column=0, sticky=tk.W, pady=2, padx=5)

            field_combo = ttk.Combobox(and_frame, textvariable=field_var, width=12,
                                     values=field_options, state="readonly")
            field_combo.grid(row=i+1, column=1, padx=5, pady=2)
            field_combo.bind('<<ComboboxSelected>>', lambda e, idx=i: self.on_field_change(idx, 'and'))

            # Dynamisches Widget für Wert/Extension
            value_frame = tk.Frame(and_frame, bg=self.colors['bg'])
            value_frame.grid(row=i+1, column=2, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))

            # Text-Entry (Standard)
            value_entry = ttk.Entry(value_frame, textvariable=value_var, width=30)
            value_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))

            # Extension Combobox (versteckt)
            ext_combo = ttk.Combobox(value_frame, textvariable=ext_var, width=15,
                                   values=ext_values, state="readonly")

            value_frame.columnconfigure(0, weight=1)

            self.and_entries.append({
                'field_var': field_var,
                'value_var': value_var,
                'ext_var': ext_var,
                'value_entry': value_entry,
                'ext_combo': ext_combo,
                'value_frame': value_frame
            })

        # ODER-Bedingungen
        or_frame = tk.Frame(self.advanced_frame, bg=self.colors['bg'], relief='solid', bd=1)
        or_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Titel für ODER-Bedingungen
        or_title = tk.Label(or_frame, text="ODER-Bedingungen (mindestens eine muss erfüllt sein)",
                           bg=self.colors['bg'], fg=self.colors['fg'],
                           font=('Arial', 10, 'bold'))
        or_title.grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(5, 10), padx=5)

        self.or_entries = []
        for i in range(3):
            field_var = tk.StringVar()
            value_var = tk.StringVar()
            ext_var = tk.StringVar()

            # Labels mit dunklem Hintergrund
            alt_label = tk.Label(or_frame, text=f"Alternative {i+1}:",
                                bg=self.colors['bg'], fg=self.colors['fg'])
            alt_label.grid(row=i+1, column=0, sticky=tk.W, pady=2, padx=5)

            field_combo = ttk.Combobox(or_frame, textvariable=field_var, width=12,
                                     values=field_options, state="readonly")
            field_combo.grid(row=i+1, column=1, padx=5, pady=2)
            field_combo.bind('<<ComboboxSelected>>', lambda e, idx=i: self.on_field_change(idx, 'or'))

            # Dynamisches Widget für Wert/Extension
            value_frame = tk.Frame(or_frame, bg=self.colors['bg'])
            value_frame.grid(row=i+1, column=2, columnspan=2, padx=5, pady=2, sticky=(tk.W, tk.E))

            # Text-Entry (Standard)
            value_entry = ttk.Entry(value_frame, textvariable=value_var, width=30)
            value_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))

            # Extension Combobox (versteckt)
            ext_combo = ttk.Combobox(value_frame, textvariable=ext_var, width=15,
                                   values=ext_values, state="readonly")

            value_frame.columnconfigure(0, weight=1)

            self.or_entries.append({
                'field_var': field_var,
                'value_var': value_var,
                'ext_var': ext_var,
                'value_entry': value_entry,
                'ext_combo': ext_combo,
                'value_frame': value_frame
            })

        # Jahres-Filter
        year_frame = tk.Frame(self.advanced_frame, bg=self.colors['bg'], relief='solid', bd=1)
        year_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Titel für Jahres-Filter
        year_title = tk.Label(year_frame, text="Datums-Filter (Jahr)",
                             bg=self.colors['bg'], fg=self.colors['fg'],
                             font=('Arial', 10, 'bold'))
        year_title.grid(row=0, column=0, columnspan=5, sticky=tk.W, pady=(5, 10), padx=5)

        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()

        # Labels auf eine Zeile
        year_from_label = tk.Label(year_frame, text="Von Jahr:",
                                  bg=self.colors['bg'], fg=self.colors['fg'])
        year_from_label.grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)

        year_from_entry = ttk.Entry(year_frame, textvariable=self.year_from_var, width=8)
        year_from_entry.grid(row=1, column=1, padx=5, pady=2)

        year_to_label = tk.Label(year_frame, text="Bis Jahr:",
                                bg=self.colors['bg'], fg=self.colors['fg'])
        year_to_label.grid(row=1, column=2, sticky=tk.W, padx=(20,5), pady=2)

        year_to_entry = ttk.Entry(year_frame, textvariable=self.year_to_var, width=8)
        year_to_entry.grid(row=1, column=3, padx=5, pady=2)

        help_label = tk.Label(year_frame, text="(z.B. 2020 bis 2023, leer = alle)",
                             bg=self.colors['bg'], fg=self.colors['disabled'],
                             font=('Arial', 8))
        help_label.grid(row=1, column=4, sticky=tk.W, padx=(10,0), pady=2)

        if HAS_DATE_FILTER:
            self.date_filter_advanced = DateReferenceFilter(
                self.advanced_frame,
                self.colors,
                row=2,  # Position nach Jahr-Filter (kompakter)
                filter_callback=self.on_date_filter_change
            )

        # Ausschluss-Bedingungen
        not_frame = tk.Frame(self.advanced_frame, bg=self.colors['bg'], relief='solid', bd=1)
        not_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)

        # Titel für Ausschluss
        not_title = tk.Label(not_frame, text="Ausschließen (darf NICHT enthalten sein)",
                            bg=self.colors['bg'], fg=self.colors['fg'],
                            font=('Arial', 10, 'bold'))
        not_title.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5, 10), padx=5)

        self.not_var = tk.StringVar()

        # Label mit dunklem Hintergrund - auf einer Zeile
        not_label = tk.Label(not_frame, text="Ausschließen:",
                            bg=self.colors['bg'], fg=self.colors['fg'])
        not_label.grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)

        not_entry = ttk.Entry(not_frame, textvariable=self.not_var, width=50)
        not_entry.grid(row=1, column=1, padx=5, pady=2, sticky=(tk.W, tk.E))

        # Grid-Konfiguration
        self.advanced_frame.columnconfigure(2, weight=1)
        and_frame.columnconfigure(2, weight=1)
        or_frame.columnconfigure(2, weight=1)
        not_frame.columnconfigure(1, weight=1)

    def on_date_filter_change(self, parsed_date, original_input):
        """
        Callback für Änderungen im Datums-Filter

        Args:
            parsed_date: datetime-Objekt oder None
            original_input: Original-Eingabe des Benutzers
        """
        self.current_date_filter = parsed_date

        if parsed_date:
            iso_date = parsed_date.strftime("%Y-%m-%d")
            self.status_label.config(text=f"Datums-Filter aktiv: {iso_date}")
        else:
            if hasattr(self, 'current_date_filter') and self.current_date_filter is not None:
                self.status_label.config(text="Datums-Filter entfernt")
            self.current_date_filter = None

    def on_field_change(self, idx, entry_type):
        """Handler für Feldtyp-Änderungen - zeigt passende Eingabe-Widgets"""
        entries = self.and_entries if entry_type == 'and' else self.or_entries
        entry = entries[idx]
        field = entry['field_var'].get()

        # Alle Widgets verstecken
        entry['value_entry'].grid_remove()
        entry['ext_combo'].grid_remove()

        if field == 'ext':
            # Zeige Extension Dropdown
            entry['ext_combo'].grid(row=0, column=0, sticky=(tk.W, tk.E))
        else:
            # Zeige normales Text-Entry
            entry['value_entry'].grid(row=0, column=0, sticky=(tk.W, tk.E))

    def on_all_types_toggle(self):
        """Handler für Dateityp-Checkboxen - Entfernt da keine 'Alle' Option mehr existiert"""
        pass  # Nicht mehr benötigt ohne "Alle Dateien" Option

    def parse_tsv_line_robust(self, line):
        """Robustes Parsen einer TSV-Zeile mit doppelten Tabs"""
        # Entferne trailing newlines
        line = line.rstrip('\n\r')

        # Splitze bei Tabs
        parts = line.split('\t')

        # Erwarte mindestens 8 Spalten, fülle fehlende auf
        while len(parts) < 8:
            parts.append('')

        return parts[:8]  # Nur die ersten 8 Spalten verwenden

    def line_matches_query(self, line, query_expr):
        """Wird nicht mehr verwendet - SQLite macht die Filterung"""
        # Diese Methode wird bei SQLite nicht mehr benötigt
        # Bleibt nur für Kompatibilität
        return True

    def build_query_from_gui(self):
        """Erstellt Query-String aus GUI-Eingaben - VEREINFACHT"""
        current_tab = self.get_current_tab()

        if current_tab == "Einfache Suche":
            return self.build_simple_query()
        else:
            return self.build_advanced_query()

    def get_current_tab(self):
        """Ermittelt den aktuellen Tab"""
        try:
            notebook = self.root.nametowidget(self.root.winfo_children()[0].winfo_children()[0])
            current_tab = notebook.select()
            return notebook.tab(current_tab, "text")
        except:
            return "Einfache Suche"

    def build_simple_query(self):
        """Erstellt Query für einfache Suche"""
        search_term = self.simple_search_var.get().strip()
        if not search_term:
            return ""

        # Für einfache Suche verwenden wir den Begriff direkt
        return search_term

    def build_advanced_query(self):
        """Erstellt Query für erweiterte Suche (vereinfacht)"""
        # Für jetzt vereinfachen wir das und sammeln alle Begriffe
        terms = []

        # UND-Bedingungen
        for entry in self.and_entries:
            field = entry['field_var'].get()
            if field == 'ext':
                value = entry['ext_var'].get()
            else:
                value = entry['value_var'].get().strip()

            if value:
                terms.append(value)

        # ODER-Bedingungen
        for entry in self.or_entries:
            field = entry['field_var'].get()
            if field == 'ext':
                value = entry['ext_var'].get()
            else:
                value = entry['value_var'].get().strip()

            if value:
                terms.append(value)

        return " ".join(terms)

    def remove_duplicates_by_md5(self, rows):
        """Entfernt Duplikate basierend auf MD5-Hash"""
        seen_md5 = set()
        unique_rows = []
        duplicates_count = 0

        for row in rows:
            md5_hash = row[7] if len(row) > 7 else ""  # MD5 ist in Spalte 7

            if md5_hash and md5_hash != "":
                if md5_hash in seen_md5:
                    duplicates_count += 1
                    continue
                seen_md5.add(md5_hash)

            unique_rows.append(row)

        return unique_rows, duplicates_count

    def start_search(self):
        """Startet die Suche in einem separaten Thread - ERWEITERT"""
        if self.search_running:
            self.stop_search()
            return

        query = self.build_query_from_gui()

        # Prüfe ob mindestens ein Filter aktiv ist
        has_text_query = bool(query.strip())
        has_date_filter = self.current_date_filter is not None
        has_type_filter = any([
            self.type_vars['text'].get(),
            self.type_vars['audio'].get(),
            self.type_vars['graphik'].get(),
            self.type_vars['video'].get(),
            self.type_vars['sonstige'].get()
        ])

        if not has_text_query and not has_date_filter and not has_type_filter:
            messagebox.showwarning("Keine Eingabe", "Bitte geben Sie einen Suchbegriff ein oder setzen Sie einen Filter.")
            return

        # Debug-Info anzeigen
        print(f"[DEBUG] Starte Suche mit Query: '{query}'")
        if has_date_filter:
            print(f"[DEBUG] Datums-Filter aktiv: {self.current_date_filter.strftime('%Y-%m-%d')}")
        if has_type_filter:
            active_types = [k for k, v in self.type_vars.items() if k != 'all' and v.get()]
            print(f"[DEBUG] Dateityp-Filter aktiv: {active_types}")

        self.search_running = True
        self.search_button.config(text="⏹️ STOPPEN", bg='#d73527')  # Rot für Stop
        self.progress.start()
        self.open_button.config(state='disabled')
        self.results_text.delete(1.0, tk.END)

        # Sofort Feedback geben
        filter_info = []
        if has_text_query:
            filter_info.append(f"Text: '{query}'")
        if has_date_filter:
            filter_info.append(f"Datum: {self.current_date_filter.strftime('%Y-%m-%d')}")
        if has_type_filter:
            active_types = [k.capitalize() for k, v in self.type_vars.items() if v.get()]
            filter_info.append(f"Typ: {'+'.join(active_types)}")

        filter_text = " + ".join(filter_info)
        self.status_label.config(text=f"Starte Suche mit: {filter_text}")
        self.results_text.insert(tk.END, f"🔍 Suche mit: {filter_text}\n")
        self.results_text.insert(tk.END, f"🚀 SQLite-DB bereit\n\n")

        # Suche in separatem Thread starten
        self.search_thread = threading.Thread(target=self.perform_search, args=(query,))
        self.search_thread.daemon = True
        self.search_thread.start()

    def stop_search(self):
        """Stoppt die laufende Suche"""
        self.search_running = False
        self.search_button.config(text="🔍 SUCHE STARTEN", bg=self.colors['highlight'])
        self.progress.stop()
        self.status_label.config(text="Suche gestoppt")

    def perform_search(self, query):
        """Führt die eigentliche Suche durch - KORRIGIERT für SQLite"""
        try:
            # Filter-Informationen sammeln
            has_text_query = bool(query.strip())
            has_date_filter = self.current_date_filter is not None
            has_type_filter = any([
                self.type_vars['text'].get(),
                self.type_vars['audio'].get(),
                self.type_vars['graphik'].get(),
                self.type_vars['video'].get(),
                self.type_vars['sonstige'].get()
            ])

            # Filter-Text für Anzeige erstellen
            filter_info = []
            if has_text_query:
                filter_info.append(f"Text: '{query}'")
            if has_date_filter:
                filter_info.append(f"Datum: {self.current_date_filter.strftime('%Y-%m-%d')}")
            if has_type_filter:
                active_types = [k.capitalize() for k, v in self.type_vars.items() if v.get()]
                filter_info.append(f"Typ: {'+'.join(active_types)}")

            filter_text = " + ".join(filter_info)

            self.root.after(0, lambda: self.status_label.config(text=f"Suche mit: {filter_text}"))
            self.root.after(0, lambda: self.results_text.insert(tk.END, f"🔍 Kombinierte Suche: {filter_text}\n"))

            # SQLite-Suche verwenden wenn verfügbar
            if self.db_ready:
                self.root.after(0, lambda: self.results_text.insert(tk.END, f"⚡ Ultra-schnelle SQLite-Suche\n\n"))

                # SQLite-Suche durchführen
                start_time = time.time()
                sqlite_results = self.search_sqlite(query, has_date_filter, has_type_filter)
                search_time = (time.time() - start_time) * 1000

                self.root.after(0, lambda: self.status_label.config(text=f"SQLite-Suche: {len(sqlite_results)} Ergebnisse in {search_time:.1f}ms"))

                # SQLite-Ergebnisse in das erwartete Format konvertieren
                found_rows = []
                for row in sqlite_results:
                    # SQLite: date_of_work, link, path, filename, extension, size, date, hash
                    # TSV:    datum, hyperlink, pfad, name, ext, größe, datum, md5
                    converted_row = [
                        row[0],  # date_of_work -> datum
                        row[1],  # link -> hyperlink
                        row[2],  # path -> pfad
                        row[3],  # filename -> name
                        row[4],  # extension -> ext
                        str(row[5]) if row[5] else "",  # size -> größe
                        row[6],  # date -> datum
                        row[7]   # hash -> md5
                    ]
                    found_rows.append(converted_row)

                # Zeige erste Treffer sofort an
                for i, row in enumerate(found_rows[:5]):
                    if not self.search_running:
                        break
                    date_str = row[0][:10] if len(row[0]) >= 10 else row[0]
                    self.root.after(0, lambda r=row, d=date_str:
                                self.results_text.insert(tk.END, f"✓ {d} - {r[3]}\n"))

            else:
                # Fallback: TSV-Datei durchsuchen
                self.root.after(0, lambda: self.results_text.insert(tk.END, f"📊 Durchsuche TSV-Datei: {INPUT_FILE}\n\n"))

                # Prüfe ob Input-Datei existiert
                if not os.path.exists(INPUT_FILE):
                    self.root.after(0, lambda: self.search_error(f"Input-Datei nicht gefunden: {INPUT_FILE}"))
                    return

                # TSV-Suche durchführen
                found_rows = []
                row_count = 0

                with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if not self.search_running:
                            break

                        row_count += 1
                        if row_count % 10000 == 0:
                            self.root.after(0, lambda c=row_count: self.status_label.config(text=f"Verarbeitet: {c:,} Zeilen"))
                            if row_count % 50000 == 0:
                                self.root.after(0, lambda c=row_count: self.results_text.insert(tk.END, f"⏳ {c:,} Zeilen verarbeitet...\n"))

                        # Robustes TSV-Parsing
                        try:
                            row = self.parse_tsv_line_robust(line)

                            if len(row) >= 4 and self.matches_all_filters(row, query, has_date_filter, has_type_filter):
                                found_rows.append(row)
                                # Zeige erste paar Treffer sofort an
                                if len(found_rows) <= 5:
                                    date_str = row[0][:10] if len(row[0]) >= 10 else row[0]
                                    self.root.after(0, lambda r=row, d=date_str:
                                                self.results_text.insert(tk.END, f"✓ {d} - {r[3]}\n"))
                        except Exception as e:
                            # Zeile überspringen bei Parse-Fehlern
                            continue

            if not self.search_running:
                return

            self.root.after(0, lambda: self.status_label.config(text="Verarbeite Ergebnisse..."))

            # Duplikate entfernen falls gewünscht
            original_count = len(found_rows)
            duplicates_removed = 0

            if self.remove_duplicates_var.get():
                found_rows, duplicates_removed = self.remove_duplicates_by_md5(found_rows)

            self.found_rows = found_rows

            if found_rows:
                self.root.after(0, lambda q=query, oc=original_count, dr=duplicates_removed:
                            self.create_ods_file(q, oc, dr))
            else:
                self.root.after(0, lambda: self.search_completed(0, 0, 0))

        except Exception as e:
            error_msg = f"Fehler bei der Suche: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda msg=error_msg: self.search_error(msg))


    def matches_all_filters(self, row, query, has_date_filter, has_type_filter):
        """Prüft ob eine Zeile alle Filter erfüllt (für TSV-Fallback)"""
        # Text-Filter
        if query.strip():
            search_text = f"{row[2]} {row[3]}".lower()  # Pfad + Dateiname
            if query.lower() not in search_text:
                return False

        # Datums-Filter
        if has_date_filter and self.current_date_filter:
            target_date = self.current_date_filter.strftime("%Y-%m-%d")
            if not row[0].startswith(target_date):
                return False

        # Dateityp-Filter
        if has_type_filter:
            ext = row[4].lower() if len(row) > 4 else ""

            type_matches = []
            if self.type_vars['text'].get():
                type_matches.append(ext in TAG_DEFS.get("#text", set()))
            if self.type_vars['audio'].get():
                type_matches.append(ext in TAG_DEFS.get("#audio", set()))
            if self.type_vars['graphik'].get():
                type_matches.append(ext in TAG_DEFS.get("#graphik", set()))
            if self.type_vars['video'].get():
                type_matches.append(ext in TAG_DEFS.get("#video", set()))
            if self.type_vars['sonstige'].get():
                # Sonstige = nicht in den anderen Kategorien
                all_known_exts = set()
                for tag_exts in TAG_DEFS.values():
                    all_known_exts.update(tag_exts)
                type_matches.append(ext not in all_known_exts)

            # Mindestens ein Typ muss zutreffen
            if not any(type_matches):
                return False

        return True

    def create_meaningful_filename(self, query, has_date_filter, has_type_filter):
        """Erstellt sprechenden Dateinamen basierend auf Suchparametern"""
        parts = ["ebib"]

        # Suchbegriff hinzufügen (bereinigt)
        if query.strip():
            clean_query = re.sub(r'[^\w\-_]', '_', query.strip())
            clean_query = clean_query[:20]  # Max 20 Zeichen
            parts.append(clean_query)

        # Datums-Filter hinzufügen
        if has_date_filter:
            date_str = self.current_date_filter.strftime("%Y%m%d")
            parts.append(f"date_{date_str}")

        # Dateityp-Filter hinzufügen
        if has_type_filter:
            active_types = []
            if self.type_vars['text'].get():
                active_types.append("text")
            if self.type_vars['audio'].get():
                active_types.append("audio")
            if self.type_vars['graphik'].get():
                active_types.append("graphik")
            if self.type_vars['video'].get():
                active_types.append("video")
            if self.type_vars['sonstige'].get():
                active_types.append("sonstige")

            if active_types:
                types_str = "+".join(active_types)
                parts.append(f"type_{types_str}")

        # Fallback: Timestamp wenn nichts spezifisches
        if len(parts) == 1:  # Nur "ebib"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            parts.append(timestamp)

        filename = "-".join(parts) + ".ods"

        # Dateiname kürzen falls zu lang
        if len(filename) > 100:
            filename = filename[:97] + ".ods"

        return filename

    def create_ods_file(self, query, original_count, duplicates_removed):
        """Erstellt die ODS-Datei mit Hyperlinks"""
        try:
            self.status_label.config(text="Erstelle ODS-Datei...")

            # Temporäre TSV-Datei erstellen
            temp_file = Path('/tmp/ebib-gui-search.tsv')

            # Sprechenden Dateinamen erstellen
            has_date_filter = self.current_date_filter is not None
            has_type_filter = any([
                self.type_vars['text'].get(),
                self.type_vars['audio'].get(),
                self.type_vars['graphik'].get(),
                self.type_vars['video'].get(),
                self.type_vars['sonstige'].get()
            ])

            filename = self.create_meaningful_filename(query, has_date_filter, has_type_filter)
            self.output_file = Path(OUTPUT_DIR) / filename

            with open(temp_file, 'w', encoding='utf-8') as f:
                for row in self.found_rows:
                    f.write('\t'.join(row) + '\n')

            # ODS erstellen mit fixierter Kopfzeile
            try:
                from eb import create_ods_with_hyperlinks
                # Erweiterte ODS-Erstellung mit fixierter Kopfzeile
                self.create_enhanced_ods(temp_file, self.output_file, query)
            except ImportError:
                # Fallback: Einfache ODS-Erstellung
                self.create_simple_ods(self.output_file)

            result_count = len(self.found_rows)
            self.root.after(0, lambda rc=result_count, oc=original_count, dr=duplicates_removed:
                          self.search_completed(rc, oc, dr))

        except Exception as e:
            error_msg = f"Fehler beim Erstellen der ODS-Datei: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self.search_error(msg))

    def create_enhanced_ods(self, temp_file, output_file, query):
        """Erstellt ODS mit fixierter Kopfzeile, korrekten Spaltenbreiten und Hyperlinks"""
        try:
            from odf.opendocument import OpenDocumentSpreadsheet
            from odf.table import Table, TableRow, TableCell, TableColumn
            from odf.text import P, A
            from odf.style import Style, TableProperties, TableRowProperties, TableCellProperties, TableColumnProperties
            from odf.number import NumberStyle, Number

            # Neues ODS-Dokument erstellen
            doc = OpenDocumentSpreadsheet()

            # KORREKTE Spaltenbreiten wie gewünscht
            column_widths = ["2.25cm", "2.25cm", "2.25cm", "12cm", "1cm", "2cm", "1cm", "2cm"]

            # Spalten-Styles für verschiedene Breiten - KORREKT erstellen
            col_styles = []
            for i, width in enumerate(column_widths):
                col_style = Style(name=f"col{i}", family="table-column")
                col_style.addElement(TableColumnProperties(columnwidth=width))
                doc.automaticstyles.addElement(col_style)  # WICHTIG: zu automaticstyles hinzufügen
                col_styles.append(col_style)

            # Style für fixierte Kopfzeile erstellen
            header_style = Style(name="HeaderStyle", family="table-cell")
            header_style.addElement(TableCellProperties(
                backgroundcolor="#4a9eff",
                border="0.05cm solid #000000",
                padding="0.1cm"
            ))
            doc.automaticstyles.addElement(header_style)  # WICHTIG: zu automaticstyles

            # Style für normale Zellen
            cell_style = Style(name="CellStyle", family="table-cell")
            cell_style.addElement(TableCellProperties(
                border="0.02cm solid #cccccc",
                padding="0.05cm"
            ))
            doc.automaticstyles.addElement(cell_style)  # WICHTIG: zu automaticstyles

            # Style für Hyperlink-Zellen (etwas breiter)
            link_style = Style(name="LinkStyle", family="table-cell")
            link_style.addElement(TableCellProperties(
                border="0.02cm solid #cccccc",
                padding="0.05cm"
            ))
            doc.automaticstyles.addElement(link_style)  # WICHTIG: zu automaticstyles

            # Tabelle erstellen
            table = Table(name="eBib Suchergebnisse")

            # WICHTIG: Spalten mit korrekten Breiten definieren - EXPLIZIT zuweisen
            for i, col_style in enumerate(col_styles):
                col = TableColumn(stylename=col_style.getAttribute("name"))
                table.addElement(col)
                print(f"[DEBUG] Spalte {i}: {column_widths[i]} Style: {col_style.getAttribute('name')}")

            # Kopfzeile mit korrekten deutschen Bezeichnungen
            headers = ["DocDatum", "Hyperlink", "Pfad", "Dateiname", "ext", "Größe", "Datum", "md5"]
            header_row = TableRow()

            for header in headers:
                cell = TableCell(stylename="HeaderStyle")
                cell.addElement(P(text=header))
                header_row.addElement(cell)

            table.addElement(header_row)

            # Datenzeilen hinzufügen
            for row_data in self.found_rows:
                row = TableRow()

                for i, cell_data in enumerate(row_data):
                    # Wähle passenden Style
                    if i == 1:  # Hyperlink-Spalte
                        cell = TableCell(stylename="LinkStyle")
                    else:
                        cell = TableCell(stylename="CellStyle")

                    # Spezielle Behandlung für Hyperlink-Spalte
                    if i == 1:  # Hyperlink-Spalte
                        hyperlink_text = str(cell_data).strip()

                        # WICHTIG: Hyperlink-Formel BEHALTEN für LibreOffice
                        if hyperlink_text.startswith('=HYPERLINK('):
                            # LibreOffice erwartet die Formel MIT dem führenden =
                            from odf.table import CellAddress
                            # Setze die Formel direkt
                            cell.setAttribute("formula", hyperlink_text)
                            # Zusätzlich auch als Text für Anzeige
                            cell.addElement(P(text=hyperlink_text))
                        else:
                            # Kein Hyperlink, normaler Text
                            cell.addElement(P(text=hyperlink_text))
                    else:
                        # Normale Zelle
                        cell_text = str(cell_data) if cell_data is not None else ""
                        cell.addElement(P(text=cell_text))

                    row.addElement(cell)

                table.addElement(row)

            # Tabelle zum Dokument hinzufügen
            doc.spreadsheet.addElement(table)

            # KRITISCH: Fixierte Kopfzeile - KORREKTE Methode für LibreOffice
            try:
                # LibreOffice verwendet spezielle Tabellen-Eigenschaften für fixierte Bereiche
                from odf.table import TableHeaderRows, TableHeaderColumns

                # Erstelle Header-Rows Element für die Kopfzeile
                header_rows = TableHeaderRows()

                # Verschiebe die bereits erstellte Kopfzeile in die Header-Sektion
                table.removeChild(header_row)  # Entferne aus normaler Position
                header_rows.addElement(header_row)  # Füge zu Header-Rows hinzu
                table.insertBefore(header_rows, table.firstChild)  # Füge am Anfang der Tabelle ein

                print("[INFO] Fixierte Kopfzeile aktiviert")

            except Exception as e:
                print(f"[WARNING] Konnte fixierte Kopfzeile nicht setzen: {e}")
                # Falls Header-Manipulation fehlschlägt, Kopfzeile normal belassen
                pass

            # Dokument speichern
            doc.save(str(output_file))
            print(f"[INFO] ODS erstellt mit {len(self.found_rows)} Zeilen: {output_file}")

        except ImportError as e:
            print(f"[WARNING] ODF-Library nicht verfügbar: {e}")
            # Fallback zur ursprünglichen Methode
            try:
                from eb import create_ods_with_hyperlinks
                create_ods_with_hyperlinks(temp_file, output_file, query, use_filter=False)
            except ImportError:
                # Letzter Fallback: CSV erstellen
                self.create_simple_ods(output_file)

        except Exception as e:
            print(f"[ERROR] Fehler beim Erstellen der ODS-Datei: {e}")
            import traceback
            traceback.print_exc()
            # Fallback
            self.create_simple_ods(output_file)

    def create_simple_ods(self, output_file):
        """Fallback: Einfache ODS-Erstellung ohne externe Abhängigkeiten"""
        # Hier könnten Sie eine einfache CSV-Datei erstellen als Fallback
        csv_file = output_file.with_suffix('.csv')
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["DocDatum", "Hyperlink", "Pfad", "Dateiname", "ext", "Größe", "Datum", "md5"])
            for row in self.found_rows:
                writer.writerow(row)
        self.output_file = csv_file

    def search_completed(self, result_count, original_count, duplicates_removed):
        """Wird aufgerufen wenn die Suche abgeschlossen ist - ERWEITERT"""
        self.search_running = False
        self.search_button.config(text="🔍 SUCHE STARTEN", bg=self.colors['highlight'])
        self.progress.stop()

        if result_count > 0:
            # **ERWEITERTE STATUS-MELDUNG mit ALLEN Filter-Infos**
            filter_info = []
            current_query = self.build_query_from_gui()
            if current_query.strip():
                filter_info.append(f"Text: '{current_query.strip()}'")
            if self.current_date_filter:
                date_str = self.current_date_filter.strftime("%Y-%m-%d")
                filter_info.append(f"Datum: {date_str}")

            # Dateityp-Filter Info
            if any([self.type_vars['text'].get(), self.type_vars['audio'].get(),
                   self.type_vars['graphik'].get(), self.type_vars['video'].get(),
                   self.type_vars['sonstige'].get()]):
                active_types = []
                if self.type_vars['text'].get():
                    active_types.append("Text")
                if self.type_vars['audio'].get():
                    active_types.append("Audio")
                if self.type_vars['graphik'].get():
                    active_types.append("Graphik")
                if self.type_vars['video'].get():
                    active_types.append("Video")
                if self.type_vars['sonstige'].get():
                    active_types.append("Sonstige")
                if active_types:
                    filter_info.append(f"Typ: {'+'.join(active_types)}")

            filter_text = " | ".join(filter_info) if filter_info else "keine Filter"
            self.status_label.config(text=f"✅ Suche abgeschlossen: {result_count:,} Ergebnisse ({filter_text})")

            # **ERWEITERTE Statistiken mit ALLEN Filter-Infos**
            stats_text = f"\n📊 STATISTIKEN:\n"
            stats_text += f"   • Gefundene Dateien: {original_count:,}\n"
            if duplicates_removed > 0:
                stats_text += f"   • Duplikate entfernt: {duplicates_removed:,}\n"
            stats_text += f"   • Eindeutige Dateien: {result_count:,}\n"

            # ALLE Filter-Infos hinzufügen
            if filter_info:
                stats_text += f"   • Aktive Filter: {', '.join(filter_info)}\n"

            stats_text += "\n"

            self.results_text.insert(tk.END, stats_text)

            # Erste Ergebnisse anzeigen
            self.results_text.insert(tk.END, "📁 ERSTE ERGEBNISSE:\n")
            for i, row in enumerate(self.found_rows[:10]):
                if len(row) >= 5:
                    result_line = f"   {i+1:2d}. {row[3]} ({row[4]}) - {row[0]}\n"
                    self.results_text.insert(tk.END, result_line)

            if result_count > 10:
                self.results_text.insert(tk.END, f"   ... und {result_count - 10:,} weitere Ergebnisse\n")

            self.results_text.insert(tk.END, f"\n💾 Ergebnisse gespeichert in: {self.output_file}\n")
            self.results_text.insert(tk.END, f"👆 Klicken Sie auf '📊 CALC ÖFFNEN' zum Anzeigen\n")

            # Button aktivieren - KRITISCH für CALC-ÖFFNEN!
            self.open_button.config(state='normal', bg=self.colors['highlight'])

        else:
            self.status_label.config(text="❌ Keine Ergebnisse gefunden")
            self.results_text.insert(tk.END, "\n❌ Keine Ergebnisse gefunden\n")
            self.results_text.insert(tk.END, "💡 Versuchen Sie andere Suchbegriffe oder weniger spezifische Kriterien\n")

    def search_error(self, error_msg):
        """Wird bei einem Suchfehler aufgerufen"""
        self.search_running = False
        self.search_button.config(text="🔍 SUCHE STARTEN", bg=self.colors['highlight'])
        self.progress.stop()
        self.status_label.config(text="❌ Fehler bei der Suche")
        self.results_text.insert(tk.END, f"\n❌ Fehler: {error_msg}\n")

    def open_results(self):
        """Öffnet die Ergebnisdatei mit LibreOffice Calc"""
        if not hasattr(self, 'output_file') or not self.output_file.exists():
            messagebox.showerror("Fehler", "Keine Ergebnisdatei verfügbar")
            return

        try:
            file_path = str(self.output_file)
            print(f"[DEBUG] Öffne Datei: {file_path}")

            # Verschiedene Methoden versuchen
            methods = [
                # LibreOffice Calc direkt
                ["libreoffice", "--calc", file_path],
                # LibreOffice allgemein
                ["libreoffice", file_path],
                # Fallback: Standard-Anwendung
                ["xdg-open", file_path],
                # KDE
                ["kde-open", file_path],
                # GNOME
                ["gnome-open", file_path]
            ]

            for method in methods:
                try:
                    print(f"[DEBUG] Versuche: {' '.join(method)}")
                    result = subprocess.Popen(method,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    # Warte kurz um zu sehen ob es funktioniert
                    result.poll()
                    print(f"[DEBUG] Erfolgreich gestartet mit: {method[0]}")

                    # Erfolgsmeldung anzeigen
                    self.results_text.insert(tk.END, f"\n✅ LibreOffice Calc gestartet\n")
                    self.results_text.insert(tk.END, f"📁 Datei: {file_path}\n")
                    return

                except FileNotFoundError:
                    print(f"[DEBUG] {method[0]} nicht gefunden")
                    continue
                except Exception as e:
                    print(f"[DEBUG] Fehler mit {method[0]}: {e}")
                    continue

            # Wenn alle Methoden fehlschlagen
            error_msg = f"Kann LibreOffice nicht starten.\n\nDatei manuell öffnen:\n{file_path}"
            messagebox.showwarning("Hinweis", error_msg)

            # Datei-Manager öffnen als Fallback
            try:
                subprocess.Popen(["nautilus", str(self.output_file.parent)])
            except:
                pass

        except Exception as e:
            error_msg = f"Fehler beim Öffnen: {e}\n\nDatei befindet sich hier:\n{self.output_file}"
            messagebox.showerror("Fehler", error_msg)
            print(f"[ERROR] {error_msg}")


def main():
    """Hauptfunktion - startet die GUI"""
    try:
        root = tk.Tk()
        app = EBibGUI(root)

        # Debug-Info
        print("eBib GUI gestartet")
        print(f"INPUT_FILE: {INPUT_FILE}")
        print(f"OUTPUT_DIR: {OUTPUT_DIR}")
        print(f"HAS_DATE_FILTER: {HAS_DATE_FILTER}")
        print(f"SQLite-DB: {app.sqlite_db}")

        root.mainloop()
    except Exception as e:
        print(f"FEHLER beim Starten der GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
