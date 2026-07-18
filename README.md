
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
Actively developed Home Assistant integration.
</p>

---

# 🇬🇧 English

## About

SmartEV Home Assistant Integration allows Home Assistant to communicate with the SmartEV platform and retrieve utility meter data.

SmartEV is a metering platform used for monitoring utility consumption in residential and commercial buildings.

The integration currently supports electricity meters and has been designed with future support for additional utility meters, such as water meters.

## Features

- Secure authentication to SmartEV
- Automatic session management
- Config Flow support
- Automatic data updates
- English and Czech localization
- Home Assistant Energy Dashboard support
- Total Energy sensor
- Last Reading Timestamp sensor

## Supported meters

| Meter | Status |
|--------|--------|
| ⚡ Electricity | ✅ Supported |
| 🚰 Water | 🚧 Planned |

## Installation

Copy the `custom_components/smartev` directory into your Home Assistant configuration:

```text
config/
└── custom_components/
    └── smartev/
```

Restart Home Assistant.

## Configuration

1. Open **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **SmartEV**
4. Enter:
   - Email
   - Password
   - Flat ID

The integration automatically creates all available entities.

## Current entities

| Entity | Description |
|---------|-------------|
| Total Energy | Total electricity consumption (kWh) |
| Last Reading Timestamp | Date and time of the latest meter reading |

## Planned features

- Consumption history
- Consumption graphs
- Additional utility meters (water, etc.)
- Instant power (if provided by SmartEV)
- Diagnostic entities
- HACS support

## Local development

Create `test_config.py` from `test_config.example.py`.

The file contains personal credentials and is intentionally excluded from Git using `.gitignore`.

## Project structure

```text
custom_components/
    smartev/

smartev/
    client.py
    parser.py
    models.py

docs/
    logo.png
```

## Requirements

The Home Assistant integration uses dependencies defined in `manifest.json`.

The included Python helper library and local test utilities may additionally use `requirements.txt`.

## License

The license will be specified before the first public release.

---

# 🇨🇿 Čeština

## O projektu

SmartEV Home Assistant Integration umožňuje propojit Home Assistant se službou SmartEV a zobrazovat údaje z podporovaných měřidel.

SmartEV je platforma pro sledování spotřeby energií a dalších médií v bytových i komerčních objektech.

Integrace nyní podporuje elektroměry a je připravena na budoucí rozšíření o další měřidla, například vodoměry.

## Funkce

- Bezpečné přihlášení do SmartEV
- Automatická správa přihlášené relace
- Podpora Config Flow
- Automatická aktualizace dat
- Lokalizace (čeština / angličtina)
- Podpora Home Assistant Energy Dashboard
- Entita Celková energie
- Entita Čas posledního odečtu

## Podporovaná měřidla

| Měřidlo | Stav |
|----------|------|
| ⚡ Elektroměr | ✅ Podporováno |
| 🚰 Vodoměr | 🚧 Připravuje se |

## Instalace

Zkopírujte adresář `custom_components/smartev` do `config/custom_components/` a restartujte Home Assistant.

## Konfigurace

1. Otevřete **Nastavení → Zařízení a služby**
2. Klikněte na **Přidat integraci**
3. Vyhledejte **SmartEV**
4. Zadejte:
   - e-mail
   - heslo
   - ID bytu

## Aktuálně podporované entity

| Entita | Popis |
|---------|-------|
| Celková energie | Celková spotřeba elektřiny (kWh) |
| Čas posledního odečtu | Datum a čas posledního odečtu elektroměru |

## Plánované funkce

- Historie spotřeby
- Grafy spotřeby
- Další měřidla (vodoměr a další podporovaná zařízení SmartEV)
- Okamžitý výkon (pokud jej SmartEV zpřístupní)
- Diagnostické entity
- Podpora HACS

## Lokální vývoj

Vytvořte `test_config.py` podle `test_config.example.py`.

Soubor obsahuje přihlašovací údaje a je záměrně vyloučen z Gitu pomocí `.gitignore`.

## Struktura projektu

```text
custom_components/
    smartev/

smartev/
    client.py
    parser.py
    models.py

docs/
    logo.png
```

## Závislosti

Home Assistant používá závislosti definované v `manifest.json`.

Pomocná Python knihovna a testovací skripty mohou při lokálním vývoji využívat také `requirements.txt`.

## Licence

Licence bude doplněna před prvním veřejným vydáním.
