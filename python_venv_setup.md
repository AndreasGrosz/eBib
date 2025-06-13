# Python Virtual Environment Setup (Kubuntu + Fish)

## Neues Projekt erstellen

```fish
# 1. Projektordner erstellen und wechseln
mkdir mein-projekt
cd mein-projekt

# 2. Virtual Environment erstellen
python3 -m venv venv

# 3. Virtual Environment aktivieren (Fish-spezifisch)
source venv/bin/activate.fish

# 4. Pip upgraden
pip install --upgrade pip

# 5. Requirements installieren (falls vorhanden)
pip install -r requirements.txt

# Oder einzelne Pakete installieren
pip install odfpy boolean.py
```

## Fish-spezifische Befehle

```fish
# venv aktivieren
source venv/bin/activate.fish

# venv deaktivieren
deactivate

# Aktuell installierte Pakete anzeigen
pip list

# Requirements.txt erstellen
pip freeze > requirements.txt
```

## Projekt-Struktur

```
mein-projekt/
├── venv/           # Virtual Environment
├── src/            # Quellcode
├── tests/          # Tests
├── requirements.txt # Abhängigkeiten
└── README.md       # Dokumentation
```

## Nützliche Fish-Aliase (optional)

Fügen Sie diese zu `~/.config/fish/config.fish` hinzu:

```fish
# Python venv shortcuts
alias venv-create='python3 -m venv venv'
alias venv-activate='source venv/bin/activate.fish'
alias venv-requirements='pip freeze > requirements.txt'
```

## Für Ihr eb.py Projekt

```fish
cd /media/synology/files/projekte/kd0241-py/eb/
source venv/bin/activate.fish
pip install --upgrade boolean.py odfpy
python eb.py "(name:ark OR name:arc)"
```