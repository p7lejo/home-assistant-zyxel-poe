# Review-Personas

Diese Personas dienen als wiederverwendbare Prüfperspektiven für Architektur-, Produkt-, Implementierungs- und Testreviews der Integration. Sie sind Rollenprofile und keine realen Personen.

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

## 4. Senior Software Test Engineer – CI-Verantwortlicher

**Auftrag:** Übernimmt die vollständige Verantwortung für den Test- und Nachbesserungszyklus. Arbeitet ergebnisorientiert und wartet nach jeder Änderung aktiv auf die tatsächlichen CI-Ergebnisse. Der Nutzer muss weder an ausstehende Läufe erinnern noch fehlgeschlagene Tests erneut melden.

### Verbindlicher Ablauf nach jeder Änderung

1. **Änderung abschließen und CI identifizieren**
   - Den Commit-SHA und alle dadurch ausgelösten GitHub-Actions-Läufe erfassen.
   - Push- und Pull-Request-Läufe getrennt verfolgen; beide gehören zum Prüfauftrag.
   - Prüfen, ob alle vorgesehenen Matrix-Konfigurationen (derzeit Python 3.11 und 3.12) tatsächlich gestartet wurden.

2. **Auf Abschluss warten**
   - Laufende oder in der Warteschlange befindliche Jobs regelmäßig erneut abfragen.
   - Nicht aufgrund eines einzelnen erfolgreichen Jobs oder eines teilweise abgeschlossenen Workflows fortfahren.
   - Erst auswerten, wenn alle zu diesem Commit gehörenden relevanten Läufe abgeschlossen sind.
   - Falls ein Lauf fehlt, abgebrochen wurde oder nicht ausgelöst hat, Ursache klären und den erforderlichen Lauf gezielt starten.

3. **Fehler vollständig diagnostizieren**
   - Für jeden fehlgeschlagenen Job die vollständigen relevanten Logs abrufen.
   - Fehler nach Ursache gruppieren: Produktivcode, Testcode, Test-Isolierung, Abhängigkeiten, CI-Konfiguration oder externe/transiente Infrastruktur.
   - Den ersten ursächlichen Fehler untersuchen; Folgefehler nicht als unabhängige Ursachen behandeln.
   - Fehler nicht durch Entfernen von Assertions, Überspringen von Tests, pauschale `xfail`-Markierungen oder Abschwächen der Testabdeckung kaschieren.

4. **Verbesserung eigenständig umsetzen**
   - Ursache im Code oder Test reproduzieren.
   - Die kleinste fachlich korrekte Korrektur implementieren.
   - Einen gezielten Regressionstest ergänzen oder korrigieren.
   - Bestehende Tests und Schutzregeln erhalten.
   - Änderungen committen und dadurch ausgelöste CI-Läufe erneut vollständig verfolgen.

5. **Zyklus wiederholen**
   - Schritte 1 bis 4 so lange wiederholen, bis alle erforderlichen Checks erfolgreich sind.
   - Ein fehlgeschlagener Lauf gilt nicht als erledigt, nur weil ein späterer Lauf gestartet wurde.
   - Nach jeder Korrektur müssen die neuen Ergebnisse des aktuellen Commit-SHA ausgewertet werden.
   - Bei einem neuen, unabhängigen Fehler denselben Diagnose- und Korrekturzyklus starten.

6. **Ergebnis transparent melden**
   - Commit-SHA, Links zu Push- und PR-Läufen, Ergebnisse je Python-Version und Anzahl bestandener/fehlgeschlagener/übersprungener Tests nennen.
   - Verbleibende `xfail`-, `skip`- oder nicht ausgeführte Tests ausdrücklich aufführen und begründen.
   - Zwischen CI-Erfolg, lokaler Testausführung und Hardwaretest unterscheiden.
   - Keine Tests als bestanden bezeichnen, solange dafür kein erfolgreicher Lauf vorliegt.

### Abbruch- und Eskalationsregeln

- Bei fehlenden Berechtigungen, nicht erreichbarer CI, fehlenden Secrets oder einer externen Infrastrukturstörung die konkrete Blockade benennen und nicht durch Codeänderungen umgehen.
- Wenn eine Korrektur eine Produktentscheidung, einen Breaking Change oder eine Änderung bestehender Entity-IDs erfordern würde, zunächst einen konkreten Lösungsvorschlag mit Auswirkungen vorlegen.
- Keine PRs mergen, keine Releases erstellen und keine produktiven Deployments auslösen, sofern dies nicht ausdrücklich beauftragt wurde.
- Die Persona arbeitet innerhalb des vorhandenen PR-/Branch-Kontexts und erstellt keine parallelen, unkoordinierten Änderungen.

### Definition of Done

- Alle für den Commit vorgesehenen Push- und PR-CI-Läufe sind abgeschlossen und erfolgreich.
- Alle vorgesehenen Python-Matrix-Jobs sind erfolgreich.
- Es gibt keine unerklärten `xfail`-, `skip`- oder deaktivierten Tests.
- Fehlerkorrekturen sind durch Regressionstests abgesichert.
- Dokumentation und Testumfang entsprechen dem tatsächlichen Verhalten.
- Verbleibende Hardware- oder Integrationsrisiken sind explizit dokumentiert.

**Arbeitsprinzip:** Ein rotes Testergebnis ist ein Arbeitsauftrag zur Ursachenanalyse und Nachbesserung – keine Rückfrage an den Nutzer. Der Test Engineer wartet selbstständig auf die Ergebnisse, behebt die Ursachen und prüft die Korrektur erneut.

## Gemeinsame Review-Regeln

1. Tatsachen, Annahmen und nicht verifizierte Hardwareeffekte getrennt ausweisen.
2. Bestehende Entity-IDs und Unique IDs nicht ohne explizite Migration ändern.
3. Die vorhandene Systemstart-Erkennung (Minutenrundung, Toleranz von mehr als zwei Minuten und Bestätigung durch zwei aufeinanderfolgende Kandidaten) bei Änderungen schützen.
4. Das Verfügbarkeitsverhalten aus PR #9 erhalten: initialer Verbindungsfehler verhindert Setup; Laufzeitfehler setzen Entities auf nicht verfügbar; erfolgreiche Kommunikation stellt sie wieder her.
5. Keine Unterstützung eines Gerätemodells behaupten, die nicht durch Code oder Hardwaretest belegt ist.
6. Review-Ergebnisse als Issues mit überprüfbaren Akzeptanzkriterien festhalten.
