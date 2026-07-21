<p align="center">
  <img src="docs/logo.png" alt="SmartEV Logo" width="220">
</p>

<h1 align="center">
SmartEV Home Assistant Integration
</h1>

<p align="center">
A custom Home Assistant integration for SmartEV utility meters.
</p>

<p align="center">

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.7%2B-41BDF5)
![License](https://img.shields.io/badge/license-MIT-green)

</p>

---

# 🇬🇧 English

## About

SmartEV Home Assistant Integration connects Home Assistant to the SmartEV cloud platform and retrieves utility meter data from the SmartEV cloud.

The integration currently supports electricity meters and has been designed for future expansion to additional SmartEV devices, including water meters.

---

## Features

- Secure authentication
- Automatic session management
- Config Flow support
- Automatic apartment discovery
- Automatic migration of existing configurations
- DataUpdateCoordinator-based updates
- English and Czech localization
- Home Assistant Energy Dashboard compatible

---

## Supported meters

| Meter | Status |
|--------|--------|
| ⚡ Electricity | ✅ Supported |
| 🚰 Water | 🚧 Planned |

---

## Installation

### Option 1 – HACS (Recommended)

Before SmartEV is included in the official HACS repository, install it as a **Custom Repository**.

1. Open **HACS → Integrations**.
2. Click **⋮ → Custom repositories**.
3. Add:

```text
Repository:
https://github.com/stibinger/ha-smartev

Category:
Integration
```

4. Click **Add**.
5. Search for **SmartEV**.
6. Click **Download**.
7. Restart Home Assistant.
8. Add the integration via **Settings → Devices & Services**.

---

### Option 2 – Manual installation

Copy the `custom_components/smartev` directory into your Home Assistant configuration:

```text
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

The integration automatically discovers all apartments available for the authenticated SmartEV account.

- If exactly one apartment is available, it is selected automatically.
- If multiple apartments are available, Home Assistant lets you choose which apartment to add.
- Apartment IDs no longer need to be entered manually.
- Existing configuration entries are migrated automatically.

After setup, all supported entities are created automatically.

---

## Current entities

The integration currently creates sensors for:

- Total energy
- Yearly consumption
- Monthly consumption
- Today's consumption
- Last meter reading (diagnostic)

The list of entities will expand as new SmartEV functionality becomes available.

---

## Planned features

- Historical consumption sensors
- Consumption graphs
- Additional utility meters
- Instant power (if provided by SmartEV)
- Diagnostic entities

---

## Project structure

```text
custom_components/
└── smartev/
    ├── translations/
    ├── __init__.py
    ├── client.py
    ├── config_flow.py
    ├── coordinator.py
    ├── sensor.py
    └── manifest.json

docs/
└── logo.png
```

---

## Requirements

No additional Python packages need to be installed manually.

The integration uses only dependencies managed by Home Assistant through `manifest.json`.

---

## License

MIT License.

See the LICENSE file for details.

---

# 🇨🇿 Čeština

## O projektu

SmartEV Home Assistant Integration propojuje Home Assistant s cloudovou platformou SmartEV a načítá údaje z podporovaných měřidel.

Integrace aktuálně podporuje elektroměry a je připravena na budoucí rozšíření o další zařízení SmartEV, například vodoměry.

---

## Funkce

- Bezpečné přihlášení
- Automatická správa přihlášené relace
- Podpora Config Flow
- Automatické vyhledání bytů
- Automatická migrace existující konfigurace
- Aktualizace pomocí DataUpdateCoordinator
- Lokalizace (čeština / angličtina)
- Kompatibilita s Home Assistant Energy Dashboard

---

## Podporovaná měřidla

| Měřidlo | Stav |
|----------|------|
| ⚡ Elektroměr | ✅ Podporováno |
| 🚰 Vodoměr | 🚧 Připravuje se |

---

## Instalace

### Možnost 1 – HACS (doporučeno)

Dokud není SmartEV zařazen do oficiálního repozitáře HACS, nainstalujte jej jako **vlastní repozitář (Custom Repository)**.

1. Otevřete **HACS → Integrace**.
2. Klikněte na **⋮ → Vlastní repozitáře (Custom repositories)**.
3. Přidejte:

```text
Repozitář:
https://github.com/stibinger/ha-smartev

Kategorie:
Integration
```

4. Klikněte na **Přidat**.
5. Vyhledejte **SmartEV**.
6. Klikněte na **Stáhnout**.
7. Restartujte Home Assistant.
8. Přidejte integraci přes **Nastavení → Zařízení a služby**.

---

### Možnost 2 – Ruční instalace

Zkopírujte adresář `custom_components/smartev` do konfiguračního adresáře Home Assistant:

```text
config/
└── custom_components/
    └── smartev/
```

Restartujte Home Assistant.

## Konfigurace

1. Otevřete **Nastavení → Zařízení a služby**
2. Klikněte na **Přidat integraci**
3. Vyhledejte **SmartEV**
4. Zadejte:
   - e-mail
   - heslo

Integrace automaticky vyhledá všechny byty dostupné pro přihlášený účet SmartEV.

- Pokud je nalezen jeden byt, vybere jej automaticky.
- Pokud je nalezeno více bytů, Home Assistant nabídne jejich výběr.
- ID bytu již není potřeba zadávat ručně.
- Existující konfigurace se migruje automaticky.

Po dokončení konfigurace budou automaticky vytvořeny všechny podporované entity.

---

## Aktuální entity

Integrace automaticky vytváří entity pro podporovaná měřidla SmartEV.

Seznam entit se bude rozšiřovat spolu s podporou dalších funkcí platformy.

---

## Plánované funkce

- Historické senzory spotřeby
- Grafy spotřeby
- Další měřidla
- Okamžitý výkon (pokud jej SmartEV zpřístupní)
- Diagnostické entity
- Podpora HACS

---

## Struktura projektu

```text
custom_components/
└── smartev/
    ├── translations/
    ├── __init__.py
    ├── client.py
    ├── config_flow.py
    ├── coordinator.py
    ├── sensor.py
    └── manifest.json

docs/
└── logo.png
```

---

## Závislosti

Nejsou vyžadovány žádné další Python balíčky.

Integrace používá pouze závislosti spravované Home Assistantem prostřednictvím souboru `manifest.json`.

---

## Licence

MIT licence.

Podrobnosti naleznete v souboru LICENSE.