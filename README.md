[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# ZyXEL PoE for Home Assistant

Diese Custom Integration steuert die Power-over-Ethernet-Ports kompatibler ZyXEL-Switches über deren lokale HTTP-Weboberfläche. Zusätzlich stellt sie den Leistungsbedarf je Port und den letzten Systemstart des Switches bereit.

Die Integration benötigt administrative Zugangsdaten. Die Kommunikation erfolgt derzeit unverschlüsselt über HTTP im lokalen Netzwerk. Verwende sie daher nur in einem vertrauenswürdigen LAN und stelle die Weboberfläche des Switches nicht ungeschützt ins Internet.

## Kompatibilität

### Home Assistant

- Mindestversion: **Home Assistant 2023.1.0**
- Integrationstyp: lokale Abfrage (Polling)
- Konfiguration: über den Home-Assistant-Config-Flow

### Gerätemodelle

Die ursprüngliche Integration wurde mit folgenden Modellen getestet:

- ZyXEL GS1900-8HP
- ZyXEL GS1900-10HP
- ZyXEL GS1900-24EP

Die Fork-Version wurde vom Maintainer mit einem **GS1900-8HP** getestet. Die Unterstützung weiterer GS1900-Modelle ist plausibel, aber nicht für jedes Modell und jede Firmware-Version durch eigene Tests belegt.

## Installation

### HACS

1. HACS öffnen.
2. Unter **Integrationen** nach **ZyXEL PoE** suchen.
3. Integration installieren.
4. Home Assistant neu starten.

### Manuelle Installation

1. Das Verzeichnis `custom_components/zyxel_poe` dieses Repositories herunterladen.
2. In das Verzeichnis `config/custom_components/zyxel_poe` kopieren.
3. Home Assistant neu starten.

## Konfiguration

1. **Einstellungen → Geräte & Dienste** öffnen.
2. **Integration hinzufügen** auswählen.
3. Nach **ZyXEL PoE** suchen.
4. Hostname oder IP-Adresse, Benutzername und Passwort des Switch-Administrators eingeben.
5. Konfiguration abschließen.

Die aktuelle Implementierung verwendet einen Config Entry. Eine Konfiguration über `configuration.yaml` bzw. einen YAML-Plattform-Eintrag wird nicht angeboten.

## Bereitgestellte Entities

Für jeden erkannten PoE-Port werden zwei Entities angelegt:

| Entity | Funktion |
| --- | --- |
| Switch „Port N“ | Aktiviert bzw. deaktiviert PoE am physischen Port |
| Sensor „Port N consuming power“ | Aktuelle Leistungsaufnahme in Watt |

Zusätzlich wird ein Sensor **Systemstart** als Zeitstempel-Entity bereitgestellt. Er zeigt den aus der Switch-Uptime abgeleiteten letzten Neustart an und gehört zur Diagnosekategorie.

Die bestehenden Unique IDs folgen den Mustern `<host>_port_<port>`, `<host>_port_<port>_power` und `<host>_system_start`. Entity-Namen können in Home Assistant an die angeschlossenen Geräte angepasst werden.

## Verfügbarkeit und Aktualisierung

Der Portstatus wird regelmäßig aus der Weboberfläche des Switches gelesen. Bei einem Fehler während der ersten Abfrage schlägt die Einrichtung fehl. Nach erfolgreicher Einrichtung werden die Entities bei Kommunikationsproblemen als **nicht verfügbar** markiert. Sobald die Kommunikation wieder funktioniert, werden sie wieder verfügbar.

Die Switch-Weboberfläche liefert die Leistungsaufnahme in Milliwatt; die Integration stellt sie in Watt dar. Die angezeigten Werte hängen von den Mess- und Aktualisierungseigenschaften des Switches ab.

## Hinweise und Einschränkungen

- Die Integration verwendet die HTTP-Weboberfläche des Switches, keine SNMP-PoE-Steuerung.
- Benutzername und Passwort müssen für die Weboberfläche gültig sein und ausreichende Rechte besitzen.
- HTML-Struktur und Login-Verhalten können je nach Modell und Firmware variieren.
- Die Integration wurde nicht mit jeder Firmware-Version und nicht mit jedem genannten Modell der ursprünglichen Integration erneut getestet.
- Bei Problemen bitte Modell, Hardware-Revision, Firmware-Version und relevante Home-Assistant-Logs angeben. Keine Passwörter oder Session-Cookies in Issues veröffentlichen.

## Entwicklung und Tests

Review-Rollen und Prüfkriterien stehen in [docs/REVIEW_PERSONAS.md](docs/REVIEW_PERSONAS.md). Die Testsuite wird mit pytest ausgeführt:

```bash
python -m pip install -r requirements_test.txt
pytest
```
