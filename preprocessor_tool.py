#!/usr/bin/env python3
"""
ebib_preprocessor.py - Preprocessing für 2.5M Records
Erstellt optimierte Such-Indizes für ultra-schnelle Suche
"""

import os
import json
import pickle
import sqlite3
from pathlib import Path
import re
from collections import defaultdict
import time

INPUT_FILE = '/media/synology/files/projekte/kd0089 my eBib & DMS/Compare-n-Share/s_250518-list-of-all-files-in-eBib-HDD-v032.tsv'
PROCESSED_DB = '/tmp/ebib_search.db'

def parse_tsv_line_robust(line):
    """Robustes TSV-Parsing"""
    line = line.rstrip('\n\r')
    while '\t\t' in line:
        line = line.replace('\t\t', '\t')
    parts = line.split('\t')
    while len(parts) < 8:
        parts.append('')
    return parts[:8]

def preprocess_to_sqlite():
    """Erstellt SQLite-DB mit Indizes für ultra-schnelle Suche"""
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input-Datei nicht gefunden: {INPUT_FILE}")
        return
    
    print("🔄 Preprocessing 2.5M Records zu SQLite...")
    start_time = time.time()
    
    # SQLite-DB erstellen
    conn = sqlite3.connect(PROCESSED_DB)
    cursor = conn.cursor()
    
    # Tabelle erstellen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            date_of_work TEXT,
            link TEXT,
            path TEXT,
            filename TEXT,
            extension TEXT,
            size TEXT,
            date TEXT,
            hash TEXT,
            filename_lower TEXT,  -- Für case-insensitive Suche
            year INTEGER,         -- Für Jahr-Filter
            file_type TEXT        -- Kategorisiert: text, audio, graphik, video, sonstige
        )
    ''')
    
    # Indizes für schnelle Suche
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_filename_lower ON files(filename_lower)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_of_work ON files(date_of_work)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_extension ON files(extension)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_type ON files(file_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_year ON files(year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON files(hash)')
    
    # Extension-Kategorien
    TAG_DEFS = {
        "text": {"pdf", "doc", "docx", "txt", "djvu", "odt", "rtf", "html", "htm", "epub", "mobi", 
                "tex", "md", "chm", "shtml", "mht", "url", "memo", "wps", "hlp", "man", "info", 
                "rst", "ods", "xls", "xlsx", "csv", "tsv"},
        "audio": {"mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus", "mp2", "ra", "au", 
                 "mid", "midi", "frf", "m3u", "ram", "aiff", "cda"},
        "graphik": {"jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff", "tif", "webp", "ico", 
                   "psd", "raw", "cr2", "nef", "pcx", "emz", "thm", "eps", "wmf", "emf", "pct", "pic"},
        "video": {"mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ogv", "rm", 
                 "asf", "vob", "bup", "ifo", "mpg", "mpeg", "divx", "xvid", "ogm"}
    }
    
    def get_file_type(extension):
        ext = extension.lower()
        for file_type, extensions in TAG_DEFS.items():
            if ext in extensions:
                return file_type
        return "sonstige"
    
    def extract_year(date_str):
        if date_str and len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except:
                pass
        return None
    
    # Daten einlesen und verarbeiten
    row_count = 0
    batch_size = 10000
    batch_data = []
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                row = parse_tsv_line_robust(line)
                if len(row) >= 5:
                    date_of_work, link, path, filename, extension = row[:5]
                    size = row[5] if len(row) > 5 else ""
                    date = row[6] if len(row) > 6 else ""
                    hash_val = row[7] if len(row) > 7 else ""
                    
                    # Preprocessing
                    filename_lower = filename.lower()
                    year = extract_year(date_of_work)
                    file_type = get_file_type(extension)
                    
                    batch_data.append((
                        date_of_work, link, path, filename, extension, size, date, hash_val,
                        filename_lower, year, file_type
                    ))
                    
                    row_count += 1
                    
                    # Batch-Insert für Performance
                    if len(batch_data) >= batch_size:
                        cursor.executemany('''
                            INSERT INTO files (date_of_work, link, path, filename, extension, 
                                             size, date, hash, filename_lower, year, file_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', batch_data)
                        conn.commit()
                        batch_data = []
                        
                        if row_count % 100000 == 0:
                            elapsed = time.time() - start_time
                            print(f"📊 {row_count:,} Records verarbeitet ({elapsed:.1f}s)")
            
            except Exception as e:
                continue
    
    # Letzte Batch
    if batch_data:
        cursor.executemany('''
            INSERT INTO files (date_of_work, link, path, filename, extension, 
                             size, date, hash, filename_lower, year, file_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch_data)
        conn.commit()
    
    # Statistiken
    cursor.execute('SELECT COUNT(*) FROM files')
    total_records = cursor.fetchone()[0]
    
    cursor.execute('SELECT file_type, COUNT(*) FROM files GROUP BY file_type ORDER BY COUNT(*) DESC')
    type_stats = cursor.fetchall()
    
    elapsed = time.time() - start_time
    
    print(f"✅ Preprocessing abgeschlossen!")
    print(f"📊 {total_records:,} Records in {elapsed:.1f}s verarbeitet")
    print(f"⚡ {total_records/elapsed:.0f} Records/Sekunde")
    print(f"💾 DB-Größe: {os.path.getsize(PROCESSED_DB)/1024/1024:.1f} MB")
    
    print(f"\n📈 DATEITYP-VERTEILUNG:")
    for file_type, count in type_stats:
        percentage = (count / total_records) * 100
        print(f"  {file_type:10}: {count:8,} ({percentage:5.1f}%)")
    
    conn.close()

def test_search_performance():
    """Testet die Such-Performance"""
    if not os.path.exists(PROCESSED_DB):
        print("❌ Erst preprocessing ausführen!")
        return
    
    conn = sqlite3.connect(PROCESSED_DB)
    cursor = conn.cursor()
    
    test_queries = [
        ("Text-Suche", "SELECT * FROM files WHERE filename_lower LIKE '%pdf%' LIMIT 100"),
        ("Extension-Filter", "SELECT * FROM files WHERE extension = 'mp3' LIMIT 100"),
        ("Dateityp-Filter", "SELECT * FROM files WHERE file_type = 'audio' LIMIT 100"),
        ("Datums-Filter", "SELECT * FROM files WHERE date_of_work LIKE '2023%' LIMIT 100"),
        ("Kombiniert", "SELECT * FROM files WHERE filename_lower LIKE '%test%' AND file_type = 'text' LIMIT 100")
    ]
    
    print("🚀 PERFORMANCE-TEST:")
    for name, query in test_queries:
        start = time.time()
        cursor.execute(query)
        results = cursor.fetchall()
        elapsed = (time.time() - start) * 1000
        print(f"  {name:15}: {len(results):3} Ergebnisse in {elapsed:6.1f}ms")
    
    conn.close()

if __name__ == "__main__":
    print("=== eBib Preprocessor ===")
    print("1. Preprocessing ausführen")
    print("2. Performance testen")
    
    choice = input("Auswahl (1/2): ").strip()
    
    if choice == "1":
        preprocess_to_sqlite()
    elif choice == "2":
        test_search_performance()
    else:
        print("Führe beide aus...")
        preprocess_to_sqlite()
        test_search_performance()
