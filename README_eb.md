# `eb` – eBib-Suchtool mit ODS-Export

Dieses Tool durchsucht eine große TSV-Datei nach einem Suchbegriff, extrahiert die passenden Zeilen und erstellt daraus eine ODS-Datei mit klickbaren Hyperlinks.

---

## 🔧 Voraussetzungen

- Python 3
- `pyinstaller`
- Fish-Shell
- Optional: Virtualenv (nur bei Entwicklung)

---

## 📁 Verzeichnisstruktur (Beispiel)

```
/media/synology/files/projekte/kd0241-py/eb/
├── eb.py
├── dist/
│   └── eb                # kompiliertes Binary
├── build/                # temporär von pyinstaller
├── venv/                 # optional
```

---

## 🚀 Kompilieren als Binary

Damit `eb` schnell startet (ohne Python-Interpreter oder venv), erstelle eine Binärdatei mit [PyInstaller](https://pyinstaller.org/).

### Schritt-für-Schritt:

1. **Virtualenv aktivieren (optional nur für die Entwicklung):**

```bash
source venv/bin/activate.fish
```

2. **PyInstaller installieren:**

```bash
pip install pyinstaller
```

3. **Kompilieren:**

```bash
cd /media/synology/files/projekte/kd0241-py/eb/
pyinstaller --onefile eb.py
```

Die fertige Datei liegt danach unter:

```bash
dist/eb
```

---

## 🐟 Dauerhafte Einrichtung in Fish-Shell

Damit der `eb`-Befehl dauerhaft zur Verfügung steht, lege ihn als Alias oder Funktion an.

### Variante 1 – **Empfohlen**: Alias

```fish
alias eb='/media/synology/files/projekte/kd0241-py/eb/dist/eb'
funcsave eb
```

→ Dies speichert die Definition dauerhaft in  
`~/.config/fish/functions/eb.fish`

### Variante 2 – Funktion (wenn mehr Kontrolle nötig ist)

```fish
function eb
    /media/synology/files/projekte/kd0241-py/eb/dist/eb $argv
end
funcsave eb
```

---

## 🧪 Verwendung

```bash
eb "Suchbegriff"
```

Das Programm:
- durchsucht die große TSV-Datei
- zeigt gefundene Treffer im Terminal
- erzeugt eine Datei `~/Downloads/ebib-search.ods` mit klickbaren Hyperlinks

---

## 🧹 Aufräumen

Vor dem erneuten Kompilieren kannst Du alte Build-Dateien löschen:

```bash
rm -rf build/ dist/ __pycache__ eb.spec
```

---

## 📝 Lizenz & Autor

(c) Andreas Groß  
Nutzung für private Archivzwecke erlaubt.
