# SOFORTIGER DEBUG-CODE für eb-gui.py

def debug_search_comparison(self, query):
    """
    Vergleicht SQLite vs TSV Ergebnisse um den Bug zu finden
    """
    print(f"\n=== DEBUG SEARCH COMPARISON ===")
    print(f"Query: '{query}'")
    
    # Filter-Status
    has_text_query = bool(query.strip())
    has_date_filter = self.current_date_filter is not None
    has_type_filter = any([
        self.type_vars['text'].get(),
        self.type_vars['audio'].get(),
        self.type_vars['graphik'].get(),
        self.type_vars['video'].get(),
        self.type_vars['sonstige'].get()
    ])
    
    print(f"Filter: Text={has_text_query}, Datum={has_date_filter}, Typ={has_type_filter}")
    
    if has_date_filter:
        print(f"Datums-Filter: {self.current_date_filter.strftime('%Y-%m-%d')}")
    
    if has_type_filter:
        active_types = [k for k, v in self.type_vars.items() if v.get()]
        print(f"Aktive Typen: {active_types}")
    
    # 1. SQLite-Suche
    try:
        print(f"\n--- SQLite-Suche ---")
        sqlite_start = time.time()
        sqlite_results = self.search_sqlite(query, has_date_filter, has_type_filter)
        sqlite_time = (time.time() - sqlite_start) * 1000
        print(f"SQLite: {len(sqlite_results)} Ergebnisse in {sqlite_time:.1f}ms")
        
        # Zeige erste 5 SQLite Ergebnisse
        print("Erste 5 SQLite-Ergebnisse:")
        for i, row in enumerate(sqlite_results[:5]):
            print(f"  {i+1}. {row[3]} ({row[4]}) - {row[0]}")
            
    except Exception as e:
        print(f"SQLite-Fehler: {e}")
        sqlite_results = []
    
    # 2. TSV-Suche zum Vergleich
    try:
        print(f"\n--- TSV-Suche (Referenz) ---")
        tsv_start = time.time()
        tsv_results = []
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    row = self.parse_tsv_line_robust(line)
                    if len(row) >= 4 and self.matches_all_filters(row, query, has_date_filter, has_type_filter):
                        tsv_results.append(row)
                        if len(tsv_results) > 2000:  # Limit für Debug
                            break
                except Exception:
                    continue
        
        tsv_time = (time.time() - tsv_start) * 1000
        print(f"TSV: {len(tsv_results)} Ergebnisse in {tsv_time:.1f}ms")
        
        # Zeige erste 5 TSV Ergebnisse
        print("Erste 5 TSV-Ergebnisse:")
        for i, row in enumerate(tsv_results[:5]):
            print(f"  {i+1}. {row[3]} ({row[4]}) - {row[0]}")
            
    except Exception as e:
        print(f"TSV-Fehler: {e}")
        tsv_results = []
    
    # 3. VERGLEICH
    print(f"\n--- VERGLEICH ---")
    print(f"SQLite: {len(sqlite_results):4} Ergebnisse")
    print(f"TSV:    {len(tsv_results):4} Ergebnisse")
    print(f"Diff:   {len(tsv_results) - len(sqlite_results):4} FEHLENDE!")
    
    if len(sqlite_results) != len(tsv_results):
        print(f"🚨 KRITISCHER BUG: {len(tsv_results) - len(sqlite_results)} Ergebnisse gehen verloren!")
        
        # Analysiere was fehlt
        if len(sqlite_results) > 0 and len(tsv_results) > 0:
            sqlite_filenames = {row[3] for row in sqlite_results}
            tsv_filenames = {row[3] for row in tsv_results}
            
            missing_in_sqlite = tsv_filenames - sqlite_filenames
            print(f"Beispiele für fehlende Dateien in SQLite:")
            for i, filename in enumerate(list(missing_in_sqlite)[:10]):
                print(f"  - {filename}")
    
    print(f"===============================\n")
    
    return sqlite_results, tsv_results


def search_sqlite_with_debug(self, query, has_date_filter, has_type_filter):
    """
    SQLite-Suche mit detailliertem Debugging
    """
    if not self.db_ready:
        return []

    conn = sqlite3.connect(self.sqlite_db)
    cursor = conn.cursor()

    # SQL-Query dynamisch aufbauen - MIT DEBUG
    conditions = []
    params = []

    print(f"\n[DEBUG] SQLite Query-Aufbau:")
    
    # Text-Suche (falls vorhanden)
    if query.strip():
        conditions.append("filename_lower LIKE ?")
        params.append(f"%{query.lower()}%")
        print(f"  Text-Filter: filename_lower LIKE '%{query.lower()}%'")

    # Datums-Filter
    if has_date_filter and self.current_date_filter:
        date_str = self.current_date_filter.strftime("%Y-%m-%d")
        conditions.append("date_of_work LIKE ?")
        params.append(f"{date_str}%")
        print(f"  Datum-Filter: date_of_work LIKE '{date_str}%'")

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
            type_filter = f"({' OR '.join(type_conditions)})"
            conditions.append(type_filter)
            print(f"  Typ-Filter: {type_filter}")

    # SQL zusammensetzen
    base_query = """
        SELECT date_of_work, link, path, filename, extension, size, date, hash
        FROM files
    """

    if conditions:
        sql = base_query + " WHERE " + " AND ".join(conditions)
    else:
        sql = base_query

    # WICHTIG: Limit entfernen für Debugging!
    # sql += " LIMIT 50000"  # <-- AUSKOMMENTIERT!

    print(f"  Final SQL: {sql}")
    print(f"  Parameters: {params}")

    start_time = time.time()
    cursor.execute(sql, params)
    results = cursor.fetchall()
    query_time = (time.time() - start_time) * 1000

    print(f"  SQLite-Ergebnis: {len(results)} Zeilen in {query_time:.1f}ms")
    
    conn.close()
    return results


# SOFORTIGER ERSATZ FÜR perform_search:

def perform_search_debug(self, query):
    """
    DEBUG-Version der Suche mit Vergleich
    """
    try:
        # DEBUGGING: Vergleiche SQLite vs TSV
        sqlite_results, tsv_results = self.debug_search_comparison(query)
        
        # Verwende TSV-Ergebnisse als REFERENZ bis Bug gefixed
        if len(sqlite_results) < len(tsv_results) * 0.9:  # Wenn SQLite >10% weniger hat
            print(f"🚨 Verwende TSV-Ergebnisse wegen SQLite-Bug!")
            found_rows = tsv_results
            search_method = "TSV (SQLite-Bug)"
        else:
            # SQLite-Ergebnisse konvertieren
            found_rows = []
            for row in sqlite_results:
                converted_row = [
                    row[0], row[1], row[2], row[3], row[4],
                    str(row[5]) if row[5] else "",
                    row[6], row[7]
                ]
                found_rows.append(converted_row)
            search_method = "SQLite"
        
        # Filter-Info für Anzeige
        filter_info = self.get_filter_info(query)
        filter_text = " + ".join(filter_info)
        
        self.root.after(0, lambda: self.status_label.config(text=f"DEBUG: {search_method} - {len(found_rows)} Ergebnisse"))
        self.root.after(0, lambda: self.results_text.insert(tk.END, f"🔍 DEBUG-Suche ({search_method}): {filter_text}\n"))
        
        # Rest der Verarbeitung
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
        error_msg = f"Fehler bei der DEBUG-Suche: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        self.root.after(0, lambda msg=error_msg: self.search_error(msg))