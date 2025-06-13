# 📄 README1st – `eb.py`

## 🔍 Was ist `eb.py`?

`eb.py` ist ein leistungsfähiges Such- und Exportwerkzeug für große, tabulatorgetrennte Listen (TSV), das Ergebnisse als `.ods` (OpenDocument Spreadsheet) mit klickbaren Hyperlinks ausgibt. Es unterstützt sowohl einfache Stichwortsuchen als auch komplexe **boolesche Suchausdrücke mit Feldfiltern und Tags**.

---

## ⚙️ Voraussetzungen

- Python 3.9+
- Pakete:
  - `odfpy`
  - `boolean.py`
- LibreOffice (für automatisches Öffnen von `.ods`-Dateien)

Installation im venv:
```bash
python3 -m venv venv
source venv/bin/activate
pip install odfpy boolean.py
```

---

## 🚀 Ausführung

```bash
python eb.py [SUCHBEGRIFF oder AUSDRUCK]
```

---

## 🔎 Beispiele

### ✅ Einfache Volltextsuche:
```bash
python eb.py ark
```
→ entspricht intern `grep -i ark ...`  
→ schnelle Suche in allen Feldern, ODS ohne Zusatzfilter

### ✅ Boolesche Filterlogik:
```bash
python eb.py 'name:ark AND ext:pdf'
python eb.py '(name:ark OR name:arc) AND NOT ext:mp3'
```

### ✅ Mit Tags wie `#text`, `#audio`, `#image`:
```bash
python eb.py '#text AND name:ron'
```

---

## 🧠 Unterstützte Feldnamen

| Feldname    | Beschreibung              | Spalte |
|-------------|---------------------------|--------|
| `datum`     | Datum des Dokuments       | 0      |
| `name`      | Dateiname (ohne Pfad)     | 3      |
| `ext`       | Dateiendung (z. B. `pdf`) | 4      |

**Aliasnamen:**
- `dateiname:` → wird intern zu `name:`
- `docdatum:` → wird intern zu `datum:`

---

## 🏷 Unterstützte Tags

| Tag        | Enthält u. a.                                |
|------------|----------------------------------------------|
| `#text`    | pdf, doc, docx, txt, djvu, odt               |
| `#audio`   | mp3, wav, flac, ogg, m4a                     |
| `#image`   | jpg, jpeg, png, gif, bmp, svg, tiff          |

---

## 📄 Ausgabe

- Das Ergebnis wird als `ebib-search.ods` in deinem `Downloads`-Verzeichnis gespeichert.
- Jede Zeile enthält klickbare Hyperlinks zum lokalen Dateipfad.
- Wenn installiert, wird LibreOffice Calc automatisch geöffnet.

---

## ⚠️ Hinweise

- Bei komplexen Ausdrücken achte auf korrekte Klammerung:
  ```bash
  (name:ark OR name:arc) AND NOT ext:mp3
  ```
- Ungültige Ausdrücke wie `name:(ark OR arc)` führen zu Parserfehlern.
