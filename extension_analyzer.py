#!/usr/bin/env python3
"""
extension_analyzer.py - Analysiert alle Dateierweiterungen in der eBib TSV-Datei
"""

import csv
import os
from collections import Counter, defaultdict
from pathlib import Path

# Konfiguration
INPUT_FILE = '/media/synology/files/projekte/kd0089 my eBib & DMS/Compare-n-Share/s_250518-list-of-all-files-in-eBib-HDD-v032.tsv'

def parse_tsv_line_robust(line):
    """Robustes Parsen einer TSV-Zeile mit doppelten Tabs"""
    line = line.rstrip('\n\r')

    # Ersetze mehrfache Tabs durch einzelne Tabs
    while '\t\t' in line:
        line = line.replace('\t\t', '\t')

    parts = line.split('\t')

    # Erwarte mindestens 8 Spalten, fülle fehlende auf
    while len(parts) < 8:
        parts.append('')

    return parts[:8]

def is_valid_extension(ext):
    """Prüft ob eine Erweiterung gültig ist"""
    if not ext:
        return False

    # Entferne Punkte und Whitespace
    ext = ext.strip(' .')

    # Leer nach Bereinigung
    if not ext:
        return False

    # Zu lang (wahrscheinlich kein Extension)
    if len(ext) > 10:
        return False

    # Enthält Pfad-Zeichen (wahrscheinlich Teil eines Pfades)
    if any(char in ext for char in ['/', '\\', ':', '|', '*', '?', '<', '>', '"']):
        return False

    # Enthält nur Zahlen oder Sonderzeichen (wahrscheinlich Müll)
    if ext.isdigit() or all(not c.isalnum() for c in ext):
        return False

    # Bekannte Müll-Patterns
    trash_patterns = [
        'html_cmp_corporat110_hbtn_a',  # Aus Ihrem Screenshot
        'htm_cmp_corporat110_hbtn_a',
        'files/vcm_s_kf_repr_423x651',
        'torrent',
        'nix',
        'lnk'
    ]

    for pattern in trash_patterns:
        if pattern in ext.lower():
            return False

    # Nur alphanumerische Zeichen (mit wenigen Ausnahmen)
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789._-')
    if not all(c.lower() in allowed_chars for c in ext):
        return False

    return True

def analyze_extensions():
    """Analysiert alle Dateierweiterungen in der TSV-Datei - VERBESSERT"""

    print("🔍 Analysiere Dateierweiterungen (bereinigt)...")
    print(f"📁 Datei: {INPUT_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"❌ Datei nicht gefunden: {INPUT_FILE}")
        return

    # Zähler für Erweiterungen
    ext_counter = Counter()
    ext_samples = defaultdict(list)  # Beispiel-Dateinamen pro Erweiterung
    invalid_extensions = Counter()   # Müll-Extensions zum Debugging

    row_count = 0
    valid_ext_count = 0

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                row = parse_tsv_line_robust(line)
                row_count += 1

                if len(row) >= 5:
                    extension = row[4].strip().lower()  # Spalte 4 ist extension
                    filename = row[3].strip()           # Spalte 3 ist filename

                    if extension:
                        if is_valid_extension(extension):
                            # Bereinige Extension
                            clean_ext = extension.strip(' .')
                            ext_counter[clean_ext] += 1
                            valid_ext_count += 1

                            # Sammle Beispiel-Dateinamen (max 3 pro Erweiterung)
                            if len(ext_samples[clean_ext]) < 3:
                                ext_samples[clean_ext].append(filename)
                        else:
                            # Sammle ungültige Extensions für Debugging
                            invalid_extensions[extension] += 1

                # Progress alle 50k Zeilen
                if row_count % 50000 == 0:
                    print(f"   📊 {row_count:,} Zeilen verarbeitet, {valid_ext_count:,} gültige Extensions...")

            except Exception as e:
                continue  # Fehlerhafte Zeilen überspringen

    print(f"✅ {row_count:,} Zeilen verarbeitet")
    print(f"📊 {len(ext_counter)} gültige Dateierweiterungen gefunden")
    print(f"🗑️ {len(invalid_extensions)} ungültige/Müll-Extensions ignoriert\n")

    # Zeige Top 10 Müll-Extensions zum Debugging
    if invalid_extensions:
        print("🚮 TOP 10 IGNORIERTE MÜLL-EXTENSIONS:")
        print("-" * 60)
        for ext, count in invalid_extensions.most_common(10):
            print(f"  {ext[:30]:30} → {count:6,} mal")
        print()

    # Rest der Funktion bleibt gleich...
    sorted_extensions = ext_counter.most_common()

    # Verbesserte Kategorien basierend auf echten Extensions
    categories = {
        "📄 Text": {"pdf", "doc", "docx", "txt", "djvu", "odt", "rtf", "html", "htm", "epub", "mobi", "tex", "md", "chm"},
        "🎵 Audio": {"mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus", "mp2", "ra", "au", "mid", "midi"},
        "🖼️ Bilder": {"jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff", "tif", "webp", "ico", "psd", "raw", "cr2", "nef"},
        "🎬 Video": {"mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ogv", "rm", "asf", "vob"},
        "📦 Archive": {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "ace", "arj", "deb", "rpm"},
        "💻 Code": {"py", "js", "html", "css", "php", "java", "cpp", "c", "h", "xml", "json", "yaml", "sql", "cs", "vb"},
        "📊 Daten": {"csv", "tsv", "xls", "xlsx", "ods", "db", "sqlite", "mdb", "dbf"},
        "🔧 System": {"exe", "dll", "sys", "bat", "sh", "reg", "ini", "cfg", "conf", "log"},
    }
    # Ausgabe der TOP Extensions (nur die häufigsten)
    print("=" * 80)
    print("📊 TOP 50 HÄUFIGSTE DATEIERWEITERUNGEN")
    print("=" * 80)

    total_files = sum(ext_counter.values())

    print(f"Extension  │ Anzahl     │ Prozent │ Kategorie          │ Beispiele")
    print("─" * 80)

    for i, (ext, count) in enumerate(sorted_extensions[:50], 1):
        percentage = (count / total_files) * 100

        # Finde Kategorie
        category = "❓ Unbekannt"
        for cat, extensions in categories.items():
            if ext in extensions:
                category = cat
                break

        examples = ", ".join(ext_samples[ext][:2])
        print(f"{ext:10} │ {count:9,} │ {percentage:6.1f}% │ {category:18} │ {examples[:30]}...")

    print(f"\n... und {len(sorted_extensions)-50} weitere Extensions")

    # Kategorisierte Zusammenfassung
    categorized = defaultdict(list)
    uncategorized = []

    for ext, count in sorted_extensions:
        found_category = None
        for category, extensions in categories.items():
            if ext in extensions:
                categorized[category].append((ext, count))
                found_category = category
                break

        if not found_category:
            uncategorized.append((ext, count))

    print(f"\n📈 KATEGORIEN-ZUSAMMENFASSUNG")
    print("-" * 50)

    for category, exts in categorized.items():
        if exts:
            category_total = sum(count for _, count in exts)
            percentage = (category_total / total_files) * 100
            print(f"{category:20} │ {category_total:8,} │ {percentage:5.1f}% │ {len(exts):3} Types")

    if uncategorized:
        uncategorized_total = sum(count for _, count in uncategorized[:20])  # Top 20
        uncategorized_percentage = (uncategorized_total / total_files) * 100
        print(f"{'❓ Top20 Unbekannt':20} │ {uncategorized_total:8,} │ {uncategorized_percentage:5.1f}% │ {len(uncategorized[:20]):3} Types")

    # Empfehlungen für häufige unbekannte Extensions
    if uncategorized:
        print(f"\n💡 HÄUFIGE UNBEKANNTE EXTENSIONS (sollten kategorisiert werden):")
        print("-" * 70)
        for ext, count in uncategorized[:15]:
            if count > 100:  # Nur häufige Extensions
                examples = ", ".join(ext_samples[ext][:2])
                print(f"  {ext:12} → {count:6,} Dateien  (z.B. {examples[:40]}...)")

    # Statistiken
    print(f"\n📈 BEREINIGTES ERGEBNIS")
    print("-" * 50)
    print(f"Gültige Extensions: {len(ext_counter)} (statt {len(invalid_extensions) + len(ext_counter)})")
    print(f"Gültige Dateien: {total_files:,}")
    print(f"Ignorierte Müll-Extensions: {len(invalid_extensions)}")
    print(f"Kategorisiert: {sum(len(exts) for exts in categorized.values())}")
    print(f"Unkategorisiert: {len(uncategorized)}")

    # Export nur der relevanten Extensions
    output_file = "extensions_analysis_clean.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Extension", "Count", "Percentage", "Category", "Examples"])

        # Nur Extensions mit >10 Dateien exportieren
        for ext, count in sorted_extensions:
            if count > 10:  # Filter für relevante Extensions
                percentage = (count / total_files) * 100
                examples = "; ".join(ext_samples[ext][:3])

                # Finde Kategorie
                category = "Unkategorisiert"
                for cat, extensions in categories.items():
                    if ext in extensions:
                        category = cat
                        break

                writer.writerow([ext, count, f"{percentage:.2f}%", category, examples])

    print(f"📄 Bereinigte Analyse exportiert nach: {output_file}")
    print(f"    (Nur Extensions mit >10 Dateien)")

if __name__ == "__main__":
    analyze_extensions()
