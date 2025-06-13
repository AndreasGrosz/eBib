# 🧪 eBib GUI - Vollständige Testliste

## 📋 Test-Checkliste (vor und nach den Fixes)

### 🚀 **Grundfunktionen**

#### ✅ **GUI-Start**
- [ ] GUI startet ohne Fehler: `python eb-gui.py`
- [ ] Fenster ist sichtbar und hat korrekte Größe (1000x900)
- [ ] Dark Theme ist aktiv (dunkler Hintergrund)
- [ ] Beide Tabs sind sichtbar: "Einfache Suche" + "Erweiterte Suche"

#### ✅ **Layout & Sichtbarkeit**
- [ ] Suchfeld ist sichtbar und fokussiert
- [ ] Datums-Filter ist unter dem Suchfeld sichtbar
- [ ] Dateityp-Filter ist sichtbar (4 Checkboxen)
- [ ] **SUCH-BUTTON ist sichtbar und groß** 🔍
- [ ] **CALC ÖFFNEN Button ist sichtbar** 📊
- [ ] Fortschrittsbalken ist sichtbar
- [ ] Status-Label ist sichtbar
- [ ] Ergebnisse-Textfeld ist sichtbar

---

### 🔍 **Such-Funktionen**

#### ✅ **Einfache Textsuche**
1. **Test 1: Grundsuche**
   - [ ] Eingabe: `pdf` → Suche startet
   - [ ] Ergebnisse werden angezeigt
   - [ ] Status zeigt Anzahl Ergebnisse

2. **Test 2: Kombinierte Begriffe**
   - [ ] Eingabe: `archive 2023` → Nur Dateien mit BEIDEN Begriffen

3. **Test 3: Leere Suche** 
   - [ ] Leeres Suchfeld → Warnung: "Bitte Suchbegriff eingeben"

#### ✅ **Datums-Referenz-Filter**
4. **Test 4: Gültiges Datum (neues Jahrhundert)**
   - [ ] Eingabe: `15.03.25` 
   - [ ] Anzeige: `✓ 15.03.25 → 2025-03-15`
   - [ ] Suche findet Dateien vom 2025-03-15

5. **Test 5: Gültiges Datum (altes Jahrhundert)**
   - [ ] Eingabe: `10.08.73`
   - [ ] Anzeige: `✓ 10.08.73 → 1973-08-10`
   - [ ] Suche findet Dateien vom 1973-08-10

6. **Test 6: Ungültiges Datum**
   - [ ] Eingabe: `32.13.99`
   - [ ] Anzeige: `✗ Ungültiges Datum`

7. **Test 7: Datum + Text kombiniert**
   - [ ] Datum: `15.03.25` + Text: `pdf`
   - [ ] Findet nur PDFs vom 15.03.2025

8. **Test 8: Nur Datums-Filter**
   - [ ] Datum: `10.08.73`, Text: leer
   - [ ] Findet alle Dateien vom 10.08.1973

9. **Test 9: Datums-Filter löschen**
   - [ ] "❌ Löschen" Button → Filter wird entfernt

#### ✅ **Dateityp-Filter** 
10. **Test 10: Alle Dateien (Standard)**
    - [ ] "Alle Dateien" aktiv → Alle Dateitypen werden gefunden

11. **Test 11: Nur Text-Dateien**
    - [ ] "Alle Dateien" deaktivieren
    - [ ] "📄 Text" aktivieren 
    - [ ] Suche: `test` → Nur PDF, DOC, TXT etc.

12. **Test 12: Nur Audio-Dateien**
    - [ ] "🎵 Audio" aktivieren
    - [ ] Suche: `music` → Nur MP3, WAV etc.

13. **Test 13: Nur Bilder**
    - [ ] "🖼️ Bilder" aktivieren  
    - [ ] Suche: `photo` → Nur JPG, PNG etc.

14. **Test 14: Mehrere Typen kombiniert**
    - [ ] "Text" + "Audio" aktivieren
    - [ ] Findet beide Dateitypen

#### ✅ **Duplikat-Filter**
15. **Test 15: Duplikate entfernen**
    - [ ] "🔄 Duplikate entfernen" aktiviert
    - [ ] Statistik zeigt: "X Duplikate entfernt"

16. **Test 16: Duplikate behalten**
    - [ ] "🔄 Duplikate entfernen" deaktiviert
    - [ ] Alle Dateien bleiben erhalten

---

### 📊 **Export & Anzeige**

#### ✅ **ODS-Export**
17. **Test 17: ODS-Datei wird erstellt**
    - [ ] Nach Suche: Status zeigt "Erstelle ODS-Datei..."
    - [ ] Datei wird in Downloads erstellt: `ebib-search-YYYYMMDD_HHMMSS.ods`

18. **Test 18: CALC ÖFFNEN funktioniert**
    - [ ] **"📊 CALC ÖFFNEN" Button wird aktiviert** 
    - [ ] **Klick öffnet LibreOffice Calc**
    - [ ] **ODS-Datei wird korrekt angezeigt**
    - [ ] Hyperlinks sind klickbar

#### ✅ **Ergebnisse-Anzeige**
19. **Test 19: Sofort-Feedback**
    - [ ] Erste 5 Treffer werden sofort angezeigt
    - [ ] Fortschrittsbalken läuft während Suche

20. **Test 20: Statistiken**
    - [ ] "📊 Statistiken anzeigen" zeigt Details
    - [ ] Anzahl gefundener Dateien
    - [ ] Anzahl eindeutiger Dateien  
    - [ ] Aktive Filter werden aufgelistet

21. **Test 21: Filter-Status**
    - [ ] Status-Label zeigt aktive Filter korrekt an
    - [ ] z.B. "Text: 'test' | Datum: 2025-03-15 | Typ: Text+Audio"

---

### ⚙️ **Benutzerfreundlichkeit**

#### ✅ **Keyboard-Shortcuts**
22. **Test 22: Enter-Taste**
    - [ ] Enter im Suchfeld → Suche startet
    - [ ] Enter im Datums-Feld → Filter wird angewendet

23. **Test 23: Weitere Shortcuts**
    - [ ] `Ctrl+Enter` → Suche startet
    - [ ] `F5` → Suche startet  
    - [ ] `Escape` → Suche stoppen (falls laufend)

#### ✅ **Such-Stopp**
24. **Test 24: Suche stoppen**
    - [ ] Lange Suche starten
    - [ ] "⏹️ STOPPEN" Button → Suche bricht ab
    - [ ] Button wird wieder zu "🔍 SUCHE STARTEN"

#### ✅ **Erweiterte Suche (Tab 2)**
25. **Test 25: Tab-Wechsel**
    - [ ] "Erweiterte Suche" Tab funktioniert
    - [ ] UND/ODER-Bedingungen sind sichtbar
    - [ ] Jahres-Filter ist sichtbar

---

### 🚨 **Fehlerbehandlung**

#### ✅ **Input-Validierung**
26. **Test 26: Keine Filter gesetzt**
    - [ ] Kein Text, kein Datum, "Alle Dateien" → Warnung

27. **Test 27: Ungültige Eingaben**
    - [ ] Datum: "abc" → Fehler-Anzeige
    - [ ] Jahr: "abc" → Ignoriert oder Fehler

28. **Test 28: Datei nicht gefunden**
    - [ ] INPUT_FILE existiert nicht → Klare Fehlermeldung

#### ✅ **Stabilität**
29. **Test 29: Große Dateien**
    - [ ] Suche in großer CSV (>1GB) funktioniert
    - [ ] Progress-Updates erscheinen regelmäßig

30. **Test 30: Memory-Usage**
    - [ ] GUI bleibt responsiv bei langer Suche
    - [ ] Kein Memory-Leak bei wiederholten Suchen

---

## 📝 **Test-Protokoll Template**

```
=== eBib GUI Test-Protokoll ===
Datum: ___________
Version: Before/After Fixes
Tester: ___________

GRUNDFUNKTIONEN:
☐ GUI Start         ☐ Layout OK        ☐ Buttons sichtbar

SUCH-FUNKTIONEN: 
☐ Textsuche        ☐ Datums-Filter    ☐ Dateityp-Filter
☐ Kombinationen    ☐ Duplikat-Filter  

EXPORT & ANZEIGE:
☐ ODS-Export       ☐ CALC-Öffnen      ☐ Statistiken

BENUTZERFREUNDLICHKEIT:
☐ Shortcuts        ☐ Suche stoppen     ☐ Tab-Wechsel

FEHLERBEHANDLUNG:
☐ Validierung      ☐ Stabilität        ☐ Große Dateien

KRITISCHE PROBLEME GEFUNDEN:
- Problem 1: ________________
- Problem 2: ________________
- Problem 3: ________________

FAZIT: ☐ Alle Tests bestanden  ☐ Fixes erforderlich
```

---

## 🎯 **Fokus-Tests für aktuelle Probleme**

**VOR den Fixes - Diese sollten FEHLSCHLAGEN:**
- [ ] Test 18: CALC ÖFFNEN Button aktiviert ❌
- [ ] Test 11-14: Dateityp-Filter funktioniert ❌  
- [ ] Layout-Test: Alle Buttons sichtbar ❌

**NACH den Fixes - Diese sollten BESTEHEN:**
- [ ] Test 18: CALC ÖFFNEN funktioniert ✅
- [ ] Test 11-14: Dateityp-Filter funktioniert ✅
- [ ] Layout-Test: Alle Buttons sichtbar ✅

Führen Sie erst ein paar **Fokus-Tests** durch, dann wenden wir die Fixes an!