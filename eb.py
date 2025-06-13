#!/usr/bin/env python3
import sys
import csv
import subprocess
from pathlib import Path
import os
import odf.opendocument
from odf.table import Table, TableRow, TableCell, TableColumn
from odf.text import P, A
from odf.style import Style, TextProperties, TableColumnProperties
import time
import shlex
from boolean import BooleanAlgebra
import re

# Konfiguration
INPUT_FILE = '/media/synology/files/projekte/kd0089 my eBib & DMS/Compare-n-Share/s_250518-list-of-all-files-in-eBib-HDD-v032.tsv'
OUTPUT_DIR = Path.home() / 'Downloads'

algebra = BooleanAlgebra()

FIELD_MAP = {
    "datum": 0,
    "name": 3,
    "ext": 4,
}

FIELD_ALIASES = {
    "dateiname": "name",
    "docdatum": "datum",
}

TAG_DEFS = {
    "#text": {"pdf", "doc", "docx", "txt", "djvu", "odt"},
    "#audio": {"mp3", "wav", "flac", "ogg", "m4a"},
    "#image": {"jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff"},
}

def validate_and_sanitize_query(query):
    """
    Validiert und bereinigt die Suchanfrage für bessere Kompatibilität
    """
    print(f"[DEBUG] Original Query: '{query}'")

    # Problematische Zeichen identifizieren
    problematic_chars = ['-', '"', "'", ':', '(', ')', '#']
    found_issues = []

    # Check für problematische Patterns
    if '"' in query or "'" in query:
        found_issues.append("Anführungszeichen werden nicht unterstützt. Verwenden Sie stattdessen Leerzeichen oder Unterstriche.")

    if '-' in query and not any(op in query.upper() for op in ['AND', 'OR', 'NOT']):
        found_issues.append("Bindestriche (-) sind in einfachen Suchen problematisch. Verwenden Sie Leerzeichen oder boolesche Operatoren.")

    # Sanitize: Entferne Anführungszeichen
    sanitized = query.replace('"', '').replace("'", "")

    # Warnung bei komplexen Queries mit Sonderzeichen
    if found_issues:
        print("\n⚠️  EINGABE-WARNUNG:")
        for issue in found_issues:
            print(f"   - {issue}")
        print(f"\n📝 Bereinigte Query: '{sanitized}'")
        print("\n💡 Tipps für bessere Suchen:")
        print("   ✓ Einfach: eb ark")
        print("   ✓ Feld-Suche: eb 'name:archive'")
        print("   ✓ Boolean: eb '(name:ark OR name:arc) AND ext:pdf'")
        print("   ✓ Tags: eb '#text AND name:manual'")
        print("   ✗ Problematisch: eb 'name:\"ark-bruch\"'")
        print()

        response = input("Möchten Sie mit der bereinigten Query fortfahren? (j/N): ")
        if response.lower() not in ['j', 'ja', 'y', 'yes']:
            print("Suche abgebrochen.")
            sys.exit(0)

    return sanitized

def test_query_parsing(query):
    """
    Testet ob eine Query erfolgreich geparst werden kann
    """
    try:
        # Test mit #tag preprocessing
        processed_query = query
        for tag in TAG_DEFS.keys():
            if tag in processed_query:
                processed_query = processed_query.replace(tag, "TRUE")

        expr = algebra.parse(processed_query)
        print(f"✓ Query erfolgreich geparst: {expr}")
        return True, None
    except Exception as e:
        return False, str(e)

def line_matches_query(line, query_expr):
    # Vorverarbeitung für #tags - ersetze sie vor dem Parsing
    processed_query = query_expr
    for tag in TAG_DEFS.keys():
        if tag in processed_query:
            # Erstelle eine temporäre OR-Klausel für die Extensions
            ext = line[FIELD_MAP["ext"]].lower()
            tag_match = ext in TAG_DEFS[tag]
            # Ersetze #tag durch einen booleschen Wert basierend auf Extension
            if tag_match:
                processed_query = processed_query.replace(tag, "TRUE")
            else:
                processed_query = processed_query.replace(tag, "FALSE")

    # Wenn die Query TRUE oder FALSE enthält, verwende einfache Auswertung
    if "TRUE" in processed_query or "FALSE" in processed_query:
        # Einfache Ersetzung für boolesche Ausdrücke
        processed_query = processed_query.replace("TRUE", "1").replace("FALSE", "0")
        try:
            return eval(processed_query.replace("OR", "or").replace("AND", "and").replace("NOT", "not"))
        except:
            pass

    expr = algebra.parse(processed_query)
    values = set(c.lower() for c in line)

    ext = line[FIELD_MAP["ext"]].lower()
    for tag, extensions in TAG_DEFS.items():
        if ext in extensions:
            values.add(tag.lower())

    # Spezialbehandlung für einfache Symbole
    if isinstance(expr, algebra.Symbol):
        lit = expr.obj.lower()
        if ':' in lit:
            field, val = lit.split(':', 1)
            field = FIELD_ALIASES.get(field, field)
            idx = FIELD_MAP.get(field)
            if idx is not None:
                return val.lower() in line[idx].lower()
            return False
        else:
            return lit in values

    # Für komplexere Ausdrücke: Rekursive Auswertung
    def evaluate_expr(node):
        if isinstance(node, algebra.Symbol):
            lit_raw = node.obj
            lit = lit_raw.lower()

            if ':' in lit:
                field, val = lit.split(':', 1)
                field = FIELD_ALIASES.get(field, field)
                idx = FIELD_MAP.get(field)
                if idx is not None:
                    return val.lower() in line[idx].lower()
                else:
                    return False
            else:
                return lit in values

        elif hasattr(node, 'args'):  # AND, OR, NOT Operationen
            if node.__class__.__name__ == 'AND':
                return all(evaluate_expr(arg) for arg in node.args)
            elif node.__class__.__name__ == 'OR':
                return any(evaluate_expr(arg) for arg in node.args)
            elif node.__class__.__name__ == 'NOT':
                return not evaluate_expr(node.args[0])

        return False

    return evaluate_expr(expr)

def create_ods_with_hyperlinks(input_file, output_file, search_term, use_filter=True):
    print("Starte ODS-Erstellung...")
    print(f"[DEBUG] Filter aktiv? {use_filter}")
    start_time = time.time()
    doc = odf.opendocument.OpenDocumentSpreadsheet()

    header_style = Style(name="Header", family="table-cell")
    header_style.addElement(TextProperties(fontweight="bold"))
    doc.styles.addElement(header_style)

    hyperlink_style = Style(name="Hyperlink", family="text")
    hyperlink_style.addElement(TextProperties(color="#0000FF", textunderlinestyle="solid", textunderlinewidth="auto"))
    doc.styles.addElement(hyperlink_style)

    table = Table(name="Sheet1")

    column_widths = ["2.25cm", "2.25cm", "2.25cm", "12cm", "1cm", "2cm", "1cm", "2cm"]
    for i, width in enumerate(column_widths):
        col_style = Style(name=f"ColStyle{i}", family="table-column")
        col_style.addElement(TableColumnProperties(columnwidth=width))
        doc.automaticstyles.addElement(col_style)
        table.addElement(TableColumn(stylename=col_style))

    header = ["DocDatum", "Hyperlink", "Pfad", "Dateiname", "ext", "Größe", "Datum", "md5"]
    header_row = TableRow()
    for cell_content in header:
        cell = TableCell(stylename=header_style)
        cell.addElement(P(text=cell_content))
        header_row.addElement(cell)
    table.addElement(header_row)

    found_rows = []
    row_count = 0
    print("Verarbeite Zeilen...")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if not use_filter or line_matches_query(row, search_term):
                table_row = TableRow()
                found_rows.append(row)

                for i, cell_content in enumerate(row):
                    cell = TableCell()
                    if i == 1:
                        path = row[2]
                        filename = row[3]
                        full_path = os.path.join(path, filename)
                        href = f"file://{full_path}"
                        p = P()
                        p.addElement(A(href=href, text=filename, stylename=hyperlink_style))
                        cell.addElement(p)
                    else:
                        cell.addElement(P(text=cell_content))
                    table_row.addElement(cell)

                table.addElement(table_row)

    doc.spreadsheet.addElement(table)
    print(f"Speichere ODS-Datei: {output_file}")
    doc.save(output_file)

    end_time = time.time()
    print(f"ODS-Erstellung abgeschlossen. Dauer: {end_time - start_time:.2f} Sekunden")
    print(f"Gefundene Zeilen: {len(found_rows)}")
    return found_rows

def main():
    if len(sys.argv) < 2:
        print("""
🔍 EB - eBib Search Tool

Verwendung: eb 'Suchbegriff oder Ausdruck'

📖 BEISPIELE:

Einfache Suche:
  eb ark                     # Findet "ark" in allen Feldern
  eb archive                 # Findet "archive" in allen Feldern

Feld-spezifische Suche:
  eb 'name:archive'          # Nur im Dateinamen
  eb 'ext:pdf'               # Nur PDF-Dateien
  eb 'datum:2023'            # Dateien von 2023

Boolean-Operatoren:
  eb 'name:ark OR name:arc'              # ODER-Verknüpfung
  eb 'ext:pdf AND name:manual'           # UND-Verknüpfung
  eb '(name:ark OR name:arc) AND ext:pdf' # Mit Klammern

Spezial-Tags:
  eb '#text'                 # Alle Text-Dateien (pdf, doc, txt...)
  eb '#audio'                # Alle Audio-Dateien (mp3, wav...)
  eb '#image'                # Alle Bild-Dateien (jpg, png...)

Komplexe Beispiele:
  eb '#text AND name:manual AND NOT name:backup'
  eb '(ext:pdf OR ext:doc) AND name:2023'

⚠️  VERMEIDEN SIE:
  ✗ eb 'name:"ark-bruch"'    # Anführungszeichen problematisch
  ✗ eb 'ark-bruch'           # Bindestriche in einfacher Suche

✅ VERWENDEN SIE STATTDESSEN:
  ✓ eb 'name:ark AND name:bruch'
  ✓ eb 'arkbruch'            # Ohne Bindestrich
  ✓ eb 'ark bruch'           # Mit Leerzeichen

Feldnamen: datum, name, ext
Operatoren: AND, OR, NOT (Groß-/Kleinschreibung egal)
        """)
        sys.exit(1)

    search_term = ' '.join(sys.argv[1:]).strip()
    if not search_term:
        print("❌ Fehler: Der Suchbegriff darf nicht leer sein.")
        sys.exit(1)

    # Eingabevalidierung und Bereinigung
    search_term = validate_and_sanitize_query(search_term)

    # Test der Query bevor wir anfangen
    success, error = test_query_parsing(search_term)
    if not success:
        print(f"\n❌ PARSE-FEHLER in Query '{search_term}':")
        print(f"   {error}")
        print("\n💡 Mögliche Lösungen:")
        print("   - Entfernen Sie Sonderzeichen wie -, \", '")
        print("   - Verwenden Sie einfachere Begriffe")
        print("   - Nutzen Sie Boolean-Operatoren: AND, OR, NOT")
        print("   - Beispiel: statt 'ark-bruch' → 'ark AND bruch'")
        sys.exit(1)

    output_file = Path(OUTPUT_DIR) / 'ebib-search.ods'
    temp_file = Path('/tmp/ebib-search-temp.tsv')

    USE_GREP = not any(op in search_term.upper() for op in ["AND", "OR", "NOT", ":", "(", ")", "#"])

    if USE_GREP:
        escaped_search_term = shlex.quote(search_term)
        grep_command = f"grep -i {escaped_search_term} '{INPUT_FILE}'"
        print(f"🔍 Führe grep-Befehl aus: {grep_command}")
        try:
            start_time = time.time()
            result = subprocess.run(grep_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            end_time = time.time()

            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)

            found_lines = result.stdout.count('\n')
            print(f"✅ grep-Befehl abgeschlossen. Dauer: {end_time - start_time:.2f} Sekunden")
            print(f"📊 Anzahl gefundener Zeilen: {found_lines}")

            if found_lines == 0:
                print(f"🔍 Keine Ergebnisse gefunden für '{search_term}'.")
                sys.exit(0)

        except subprocess.CalledProcessError as e:
            if e.returncode == 1 and not e.stdout:
                print(f"🔍 Keine Ergebnisse gefunden für '{search_term}'.")
            else:
                print(f"❌ Fehler beim Ausführen des grep-Befehls: {e}")
                print(f"Stderr: {e.stderr}")
            sys.exit(1)

    else:
        print("🧠 Schalte auf internen Filtermodus (boolesche Suche)...")
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        filtered = []
        reader = csv.reader(lines, delimiter='\t')

        row_total = 0
        row_matched = 0

        print("⚙️  Starte boolesche Filterung...")

        for row in reader:
            row_total += 1
            if row_total % 100000 == 0:
                print(f"🔄 Verarbeitet: {row_total} Zeilen")
            try:
                if line_matches_query(row, search_term):
                    row_matched += 1
                    filtered.append('\t'.join(row))
                    if row_matched <= 10:
                        print(f"✔️  {row[0]} | {row[3]} | {row[4]}")
            except Exception as e:
                if row_total == 1:  # Nur beim ersten Fehler anzeigen
                    print(f"⚠️  Fehler beim Verarbeiten von Zeile {row_total}: {e}")
                    print("   (Weitere Fehler werden unterdrückt)")

        print(f"✅ Boolesche Suche abgeschlossen. Geprüfte Zeilen: {row_total}, Treffer: {row_matched}")

        if not filtered:
            print(f"🔍 Keine Ergebnisse gefunden für '{search_term}'.")
            print("\n💡 Versuchen Sie:")
            print("   - Andere Suchbegriffe")
            print("   - Weniger spezifische Kriterien")
            print("   - Boolean-Operatoren: OR statt AND")
            sys.exit(0)

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(filtered))

        print(f"📝 {row_matched} Zeilen nach boolescher Suche übernommen.")

    found_rows = create_ods_with_hyperlinks(temp_file, output_file, search_term, use_filter=False)

    print(f"\n🎉 Suchergebnisse gespeichert in {output_file}")
    print("\n📋 Quickview der gefundenen Zeilen:")
    for row in found_rows[:10]:
        print(" | ".join(row))

    if len(found_rows) > 10:
        print(f"... und {len(found_rows) - 10} weitere Zeilen")

    if output_file.exists():
        print("🚀 Öffne LibreOffice...")
        subprocess.Popen(["libreoffice", "--calc", str(output_file)])

if __name__ == "__main__":
    main()
