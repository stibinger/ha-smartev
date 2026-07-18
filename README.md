<p align="center">
  <img src="docs/logo.png" alt="SmartEV Logo" width="220">
</p>

<h1 align="center">
SmartEV Home Assistant Integration
</h1>

<p align="center">
Custom Home Assistant integration for SmartEV utility meters.
</p>

<p align="center">
Currently under active development.
</p>

---

# 🇬🇧 English

## About

SmartEV Home Assistant Integration allows Home Assistant to communicate with the SmartEV platform and retrieve utility meter data.

The integration currently supports electricity meters and has been designed with future support for additional utility meters, such as water meters.

---

## Features

- Secure authentication to SmartEV
- Automatic session management
- Config Flow support
- Automatic data updates
- English and Czech localization
- Home Assistant Energy Dashboard support
- Total Energy sensor
- Last Reading Timestamp sensor

---

## Installation

Copy the integration into your Home Assistant configuration directory.

```
config/
└── custom_components/
    └── smartev/
```

Restart Home Assistant.

---

## Configuration

1. Open **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **SmartEV**
4. Enter:

- Email
- Password
- Flat ID

The integration will automatically create the available entities.

---

## Current entities

| Entity | Description |
|---------|-------------|
| Total Energy | Total electricity consumption (kWh) |
| Last Reading Timestamp | Date and time of the latest meter reading |

---

## Planned features

- Consumption history
- Consumption graphs
- Additional utility meters (water, etc.)
- Instant power (if provided by SmartEV)
- Diagnostic entities
- HACS support

---

## Local development

For local testing create:

```
test_config.py
```

using the template:

```
test_config.example.py
```

This file contains personal credentials and is intentionally excluded from Git using `.gitignore`.

---

## Project structure

```
custom_components/
    smartev/

smartev/
    client.py
    parser.py
    models.py

docs/
    logo.png
```

---

## Requirements

The Home Assistant integration uses dependencies defined in `manifest.json`.

The included Python helper library and test utilities may additionally use `requirements.txt` during local development.

---

## License

The license will be specified before the first public release.

---

# 🇨🇿 Čeština

## O projektu

SmartEV Home Assistant Integration umožňuje propojit Home Assistant se službou SmartEV a zobrazovat údaje z podporovaných měřidel.

V současné době podporuje elektroměry a je navržena tak, aby bylo možné v budoucnu přidat také další měřidla, například vodoměry.

---

## Funkce

- Bezpečné přihlášení do SmartEV
- Automatická správa přihlášené relace
- Podpora Config Flow
- Automatická aktualizace dat
- Lokalizace (čeština / angličtina)
- Podpora Home Assistant Energy Dashboard
- Entita Celková energie
- Entita Čas posledního odečtu

---

## Instalace

Zkopírujte adresář

```
custom_components/smartev
```

do složky

```
config/custom_components/
```

a restartujte Home Assistant.

---

## Konfigurace

1. Otevřete **Nastavení → Zařízení a služby**
2. Klikněte na **Přidat integraci**
3. Vyhledejte **SmartEV**
4. Zadejte

- e-mail
- heslo
- ID bytu

Integrace automaticky vytvoří dostupné entity.

---

## Aktuálně podporované entity

| Entita | Popis |
|---------|-------|
| Celková energie | Celková spotřeba elektřiny (kWh) |
| Čas posledního odečtu | Datum a čas posledního odečtu elektroměru |

---

## Plánované funkce

- Historie spotřeby
- Grafy spotřeby
- Další měřidla (vodoměr a další podporovaná zařízení SmartEV)
- Okamžitý výkon (pokud jej SmartEV zpřístupní)
- Diagnostické entity
- Podpora HACS

---

## Lokální vývoj

Pro lokální testování vytvořte soubor

```
test_config.py
```

podle šablony

```
test_config.example.py
```

Soubor obsahuje přihlašovací údaje a je záměrně vyloučen z Gitu pomocí `.gitignore`.

---

## Struktura projektu

```
custom_components/
    smartev/

smartev/
    client.py
    parser.py
    models.py

docs/
    logo.png
```

---

## Závislosti

Samotná Home Assistant integrace používá závislosti definované v souboru `manifest.json`.

Pomocná Python knihovna a testovací skripty mohou při lokálním vývoji využívat také `requirements.txt`.

---

## Licence

Licence bude doplněna před prvním veřejným vydáním.