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
- Compatible with the Home Assistant Energy Dashboard
- Current electricity meter reading
- Daily, monthly and yearly electricity consumption
- Latest daily PV production
- Current month photovoltaic (PV) production
- Today's grid energy consumption
- Current month grid energy consumption
- Automatic PV allocation coefficient calibration
- Estimated apartment PV production
- Cumulative estimated PV production for the Home Assistant Energy Dashboard
- Cumulative grid energy import for the Home Assistant Energy Dashboard

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
- Latest daily PV production
- Current month photovoltaic (PV) production
- Today's grid energy consumption
- Current month grid energy consumption
- Estimated PV production
- Total estimated PV production
- Total grid energy
- Last meter reading (diagnostic)

The list of entities will expand as new SmartEV functionality becomes available.

SmartEV publishes daily PV production with a one-day delay. The latest daily PV
production sensor therefore shows the newest completed calendar day's value and
ignores today's placeholder row. Its `production_date` attribute identifies the
reported day.

---

## Home Assistant Energy Dashboard

Apartment accounts do not expose cumulative photovoltaic production through the
SmartEV API.

To provide Energy Dashboard compatibility, the integration automatically
calculates a stable apartment allocation coefficient from historical SmartEV
data and estimates live apartment PV production from the JOM photovoltaic
meter.

The calibration process is fully automatic and requires no user
configuration.

Days with zero grid import are excluded from calibration because they would
otherwise distort the calculated apartment allocation coefficient.

For the Home Assistant Energy Dashboard configure:

- Grid consumption → Total Grid Energy
- Solar production → Total Estimated PV Production

---

## Calibration diagnostics

The estimated PV entities expose diagnostic attributes including:

- allocation_coefficient
- used_calibration_samples
- skipped_zero_grid_samples
- coefficient_of_variation
- minimum_coefficient
- maximum_coefficient
- standard_deviation
- last_calibration

---

## Planned features

- Water meter support
- Historical charts and statistics
- Instant power (if provided by SmartEV)
- Additional SmartEV devices
- HACS official repository

---

## Project structure

```text
.
├── .github/
├── captures/
├── custom_components/
│   └── smartev/
├── docs/
├── tools/
├── CHANGELOG.md
├── hacs.json
├── LICENSE
└── README.md
```

---

## Requirements

No additional Python packages are required.

All dependencies are managed automatically by Home Assistant through the integration's `manifest.json`.

---

## License

MIT License.

See the LICENSE file for details.

---

# 🇨🇿 Čeština

## O projektu

SmartEV Home Assistant Integration propojuje Home Assistant s cloudovou platformou SmartEV a načítá údaje z podporovaných měřidel.

Integrace aktuálně podporuje elektroměry a je připravena na budoucí rozšíření o další zařízení SmartEV, včetně vodoměrů.

---

## Funkce

- Bezpečné ověřování
- Automatická správa relace
- Podpora průvodce konfigurací (Config Flow)
- Automatické vyhledání bytů
- Automatická migrace stávajících konfigurací
- Aktualizace založené na DataUpdateCoordinator
- Lokalizace do češtiny a angličtiny
- Kompatibilita s energetickým dashboardem Home Assistant
- Aktuální stav elektroměru
- Denní, měsíční a roční spotřeba elektřiny
- Poslední denní výroba FVE
- Výroba z fotovoltaiky za aktuální měsíc
- Dnešní odběr elektřiny ze sítě
- Odběr elektřiny ze sítě za aktuální měsíc
- Automatická kalibrace koeficientu přidělení výroby FVE
- Odhadovaná výroba FVE pro byt
- Kumulativní odhadovaná výroba FVE pro energetický dashboard Home Assistant
- Kumulativní odběr elektřiny ze sítě pro energetický dashboard Home Assistant

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

---

## Konfigurace

1. Otevřete **Nastavení → Zařízení a služby**
2. Klikněte na **Přidat integraci**
3. Vyhledejte **SmartEV**
4. Zadejte:
   - e-mail
   - heslo

Integrace automaticky vyhledá všechny byty dostupné pro přihlášený účet SmartEV.

- Pokud je nalezen právě jeden byt, bude vybrán automaticky.
- Pokud je nalezeno více bytů, Home Assistant umožní vybrat byt, který chcete přidat.
- ID bytu již není potřeba zadávat ručně.
- Existující konfigurace se migrují automaticky.

Po dokončení konfigurace budou automaticky vytvořeny všechny podporované entity.

---

## Aktuální entity

Integrace aktuálně vytváří následující senzory:

- Celková energie
- Roční spotřeba
- Měsíční spotřeba
- Dnešní spotřeba
- Poslední denní výroba FVE
- Výroba z fotovoltaiky za aktuální měsíc
- Dnešní odběr elektřiny ze sítě
- Odběr elektřiny ze sítě za aktuální měsíc
- Odhadovaná výroba FVE
- Celková odhadovaná výroba FVE
- Celková energie ze sítě
- Čas posledního odečtu (diagnostika)

Seznam entit se bude rozšiřovat spolu s podporou dalších funkcí platformy SmartEV.

SmartEV zveřejňuje denní výrobu FVE se zpožděním jednoho dne. Senzor **Poslední denní výroba FVE** proto zobrazuje hodnotu za nejnovější dokončený kalendářní den a ignoruje dnešní zástupný řádek. Atribut `production_date` určuje, ke kterému dni zobrazená hodnota patří.

---

## Energetický dashboard Home Assistant

Bytové účty neposkytují prostřednictvím rozhraní SmartEV API kumulativní údaje o výrobě z fotovoltaiky.

Pro zajištění kompatibility s energetickým dashboardem Home Assistant integrace automaticky vypočítá stabilní koeficient přidělení výroby FVE z historických dat SmartEV a na jeho základě odhaduje průběžnou výrobu FVE bytu z výrobního elektroměru JOM.

Kalibrace probíhá plně automaticky a nevyžaduje žádnou konfiguraci uživatelem.

Dny s nulovým odběrem elektřiny ze sítě jsou z kalibrace vyloučeny, protože by zkreslovaly vypočtený koeficient přidělení výroby.

Pro energetický dashboard Home Assistant nastavte:

- Spotřeba ze sítě → **Celková energie ze sítě**
- Výroba ze solární elektrárny → **Celková odhadovaná výroba FVE**

---

## Diagnostika kalibrace

Entity odhadované výroby FVE poskytují diagnostické atributy, například:

- `allocation_coefficient`
- `used_calibration_samples`
- `skipped_zero_grid_samples`
- `coefficient_of_variation`
- `minimum_coefficient`
- `maximum_coefficient`
- `standard_deviation`
- `last_calibration`

---

## Plánované funkce

- Podpora vodoměrů
- Historické grafy a statistiky
- Okamžitý výkon (pokud jej SmartEV zpřístupní)
- Podpora dalších zařízení SmartEV
- Zařazení do oficiálního repozitáře HACS

---

## Struktura projektu

```text
.
├── .github/
├── captures/
├── custom_components/
│   └── smartev/
├── docs/
├── tools/
├── CHANGELOG.md
├── hacs.json
├── LICENSE
└── README.md
```

---

## Závislosti

Nejsou vyžadovány žádné další Python balíčky.

Všechny závislosti jsou spravovány automaticky Home Assistantem prostřednictvím souboru `manifest.json` integrace.

---

## Licence

Licence MIT.

Podrobnosti naleznete v souboru LICENSE.

---
