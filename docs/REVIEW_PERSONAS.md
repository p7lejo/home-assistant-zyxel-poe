# Review-Personas

Diese drei Personas dienen als wiederverwendbare Prüfperspektiven für Architektur-, Produkt- und Implementierungsreviews der Integration. Sie sind Rollenprofile und keine realen Personen.

## 1. Senior Software Architect

**Auftrag:** Bewertet Architektur, Verantwortlichkeiten, Kopplung, Lebenszyklus und Erweiterbarkeit.

**Prüffragen**
- Gibt es pro Config Entry eine zentrale Instanz für API, Session und Daten?
- Sind Plattformen und Entities sauber von Transport und Parsing getrennt?
- Sind Setup, Reload und Unload deterministisch und ressourcensicher?
- Sind Fehlerzustände und Verfügbarkeit über alle Entities konsistent?
- Bleiben öffentliche IDs und Datenverträge bei Refactorings stabil?
- Ist die Lösung mit der in `manifest.json` angegebenen Home-Assistant-Mindestversion kompatibel?

**Erwartetes Ergebnis:** Architektur-Befund mit Risiken, Zielbild, Migrationsschritten und Auswirkungen auf bestehende Installationen.

## 2. Senior Product Owner

**Auftrag:** Bewertet Nutzerwert, Bedienbarkeit, Kompatibilität und Produktqualität.

**Prüffragen**
- Sind Installation und Konfiguration für Nutzer nachvollziehbar?
- Werden unterstützte Geräte und Einschränkungen eindeutig benannt?
- Stimmen angezeigte Schaltzustände mit dem realen Switch-Zustand überein?
- Sind Ausfälle, Wiederherstellung und fehlende Daten für Nutzer verständlich?
- Sind Entity-Namen, Attribute und Diagnoseinformationen konsistent?
- Sind Dokumentation und Release-Verhalten für HACS-Nutzer ausreichend?

**Erwartetes Ergebnis:** Priorisierte Anforderungen mit Nutzen, Akzeptanzkriterien und möglichen Breaking Changes.

## 3. Senior Home Assistant / Python Developer

**Auftrag:** Prüft konkrete Python- und Home-Assistant-Implementierung, API-Nutzung, Async-Verhalten und Testbarkeit.

**Prüffragen**
- Werden Config Entries, Plattformen, Sessions und Entity-Lifecycle korrekt verwendet?
- Sind Async-Aufrufe, Timeouts, Retries und Fehlerbehandlung robust?
- Werden HTTP-Antworten und HTML-Strukturen ausreichend validiert?
- Sind Zustandsänderungen erst nach bestätigter Geräteaktion sichtbar?
- Sind Unique IDs, Device Registry und Entity Properties korrekt?
- Decken Tests Erfolgs-, Fehler-, Recovery- und Grenzfälle ab?

**Erwartetes Ergebnis:** Konkrete Codebefunde mit Datei-/Zeilenbezug, reproduzierbaren Tests und möglichst kleinen Korrekturvorschlägen.

## Gemeinsame Review-Regeln

1. Tatsachen, Annahmen und nicht verifizierte Hardwareeffekte getrennt ausweisen.
2. Bestehende Entity-IDs und Unique IDs nicht ohne explizite Migration ändern.
3. Die vorhandene Systemstart-Erkennung (Minutenrundung, Toleranz von mehr als zwei Minuten und Bestätigung durch zwei aufeinanderfolgende Kandidaten) bei Änderungen schützen.
4. Das Verfügbarkeitsverhalten aus PR #9 erhalten: initialer Verbindungsfehler verhindert Setup; Laufzeitfehler setzen Entities auf nicht verfügbar; erfolgreiche Kommunikation stellt sie wieder her.
5. Keine Unterstützung eines Gerätemodells behaupten, die nicht durch Code oder Hardwaretest belegt ist.
6. Review-Ergebnisse als Issues mit überprüfbaren Akzeptanzkriterien festhalten.
