# SmartEV Home Assistant Integration

> Custom Home Assistant integration for SmartEV electricity meters.

> **Project status:** Early development (pre-release)

---

# 🇬🇧 English

## Features

- Secure login to SmartEV
- Automatic session handling
- Config Flow support
- Automatic data updates
- Localization (English / Czech)
- Home Assistant Energy Dashboard support
- Total energy sensor (kWh)
- Last meter reading timestamp

---

## Installation

Currently the integration is intended for manual installation.

Copy the `custom_components/smartev` directory into your Home Assistant configuration folder:

```
config/
└── custom_components/
    └── smartev/
```

Restart Home Assistant.

---

## Configuration

1. Open **Settings → Devices & Services**.
2. Click **Add Integration**.
3. Search for **SmartEV**.
4. Enter:
   - e-mail
   - password
   - Flat ID

The integration automatically creates the required sensors.

---

## Local development

For local testing create a file named:

```
test_config.py
```

using the template provided in:

```
test_config.example.py
```

This file contains personal credentials and is intentionally ignored by Git.

---

## Current entities

| Entity | Description |
|---------|-------------|
| Total Energy | Total electricity consumption (kWh) |
| Last Reading | Timestamp of the latest meter reading |

---

## Planned features

- Consumption history
- Consumption graphs
- Multiple electricity meters
- Instant power (if provided by SmartEV)
- Diagnostic entities
- HACS support

---

# 🇨🇿 Čeština

## Funkce

- Bezpečné přihlášení do SmartEV
- Automatická správa přihlášené relace
- Podpora Config Flow
- Automatická aktualizace dat
- Lokalizace (čeština / angličtina)
- Podpora Home Assistant Energy Dashboard
- Senzor celkové spotřeby (kWh)
- Čas posledního odečtu elektroměru

---

## Instalace

Momentálně je integrace určena pro ruční instalaci.

Zkopírujte adresář:

```
custom_components/smartev
```

do složky:

```
config/custom_components/
```

a restartujte Home Assistant.

---

## Konfigurace

1. Otevřete **Nastavení → Zařízení a služby**.
2. Klikněte na **Přidat integraci**.
3. Vyhledejte **SmartEV**.
4. Zadejte:
   - e-mail
   - heslo
   - ID bytu

Integrace automaticky vytvoří potřebné entity.

---

## Lokální vývoj

Pro testování vytvořte soubor:

```
test_config.py
```

podle šablony:

```
test_config.example.py
```

Soubor obsahuje přihlašovací údaje a je záměrně uveden v `.gitignore`.

---

## Vytvářené entity

| Entita | Popis |
|---------|-------|
| Celková energie | Celková spotřeba elektřiny (kWh) |
| Čas posledního odečtu | Datum a čas posledního odečtu |

---

## Plánované funkce

- Historie spotřeby
- Grafy spotřeby
- Podpora více elektroměrů
- Okamžitý výkon (pokud jej SmartEV zpřístupní)
- Diagnostické entity
- Podpora HACS

---

## Licence

This project is currently under development.

License will be specified before the first public release.