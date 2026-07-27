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
- Total energy
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

## Entities

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

Allocation coefficients and cumulative counter continuity are stored by the
stable SmartEV apartment ID. Existing config-entry-based storage is migrated
automatically on the first startup after upgrading.

The live cumulative apartment register is the primary consumption source.
Grid import is derived from cumulative apartment consumption minus cumulative
apartment PV allocation. SmartEV's CSV grid column is not used for live or
cumulative grid entities. It is used only to reject zero-grid report days from
PV allocation calibration, because SmartEV does not apply the normal allocation
ratio on those days.

For the Home Assistant Energy Dashboard configure:

- Grid consumption → Total Grid Energy
- Solar production → Total Estimated PV Production

### Migration note

Users upgrading from older integration versions may already have Energy
Dashboard statistics created before persistent counter continuity was migrated
to the stable SmartEV apartment ID.

If the first cumulative grid reading after migration is interpreted as energy
consumed during a single statistics interval, open **Developer Tools →
Statistics**, select the first affected interval and set its interval change to
**0 kWh**. This corrects the accumulated Energy Dashboard statistics without
changing the live cumulative sensor state.

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
- Support for additional SmartEV devices
- Publication in the official HACS repository

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

## O integraci

Integrace SmartEV pro Home Assistant propojuje Home Assistant s cloudovou platformou SmartEV a načítá data z měřidel energií ze služby SmartEV.

Integrace v současnosti podporuje elektroměry a je navržena pro budoucí rozšíření o další zařízení SmartEV, včetně vodoměrů.

---

## Funkce

- Bezpečné přihlášení
- Automatická správa relace
- Podpora Config Flow
- Automatické zjištění bytů
- Automatická migrace existujících konfigurací
- Aktualizace založené na DataUpdateCoordinator
- Lokalizace do češtiny a angličtiny
- Kompatibilita s Energy Dashboardem Home Assistantu
- Celková spotřeba energie
- Denní, měsíční a roční spotřeba elektřiny
- Poslední denní výroba FVE
- Výroba fotovoltaiky (FVE) za aktuální měsíc
- Dnešní odběr energie ze sítě
- Odběr energie ze sítě za aktuální měsíc
- Automatická kalibrace koeficientu přidělení výroby FVE
- Odhadovaná výroba FVE pro byt
- Celková odhadovaná výroba FVE pro Energy Dashboard Home Assistantu
- Celkový odběr energie ze sítě pro Energy Dashboard Home Assistantu

---

## Podporovaná měřidla

| Měřidlo | Stav |
|----------|------|
| ⚡ Elektřina | ✅ Podporováno |
| 🚰 Voda | 🚧 Plánováno |

---

## Instalace

### Varianta 1 – HACS (doporučeno)

Dokud nebude SmartEV zařazen do oficiálního repozitáře HACS, nainstalujte jej jako **Custom Repository**.

1. Otevřete **HACS → Integrations**.
2. Klikněte na **⋮ → Custom repositories**.
3. Přidejte:

```text
Repository:
https://github.com/stibinger/ha-smartev

Category:
Integration
```

4. Klikněte na **Add**.
5. Vyhledejte **SmartEV**.
6. Klikněte na **Download**.
7. Restartujte Home Assistant.
8. Přidejte integraci přes **Nastavení → Zařízení a služby**.

---

### Varianta 2 – Ruční instalace

Zkopírujte adresář `custom_components/smartev` do konfigurace Home Assistantu:

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
   - E-mail
   - Heslo

Integrace automaticky vyhledá všechny byty dostupné pro přihlášený účet SmartEV.

- Pokud je dostupný právě jeden byt, bude vybrán automaticky.
- Pokud je dostupných více bytů, Home Assistant umožní vybrat byt, který chcete přidat.
- Identifikátor bytu již není nutné zadávat ručně.
- Existující konfigurační záznamy jsou automaticky migrovány.

Po dokončení nastavení jsou automaticky vytvořeny všechny podporované entity.

---

## Entity

Integrace aktuálně vytváří následující senzory:

- Celková spotřeba energie
- Roční spotřeba
- Měsíční spotřeba
- Dnešní spotřeba
- Poslední denní výroba FVE
- Výroba fotovoltaiky (FVE) za aktuální měsíc
- Dnešní odběr energie ze sítě
- Odběr energie ze sítě za aktuální měsíc
- Odhadovaná výroba FVE
- Celková odhadovaná výroba FVE
- Celkový odběr energie ze sítě
- Poslední odečet elektroměru (diagnostický)

SmartEV zveřejňuje denní výrobu FVE s jednodenním zpožděním. Senzor poslední denní výroby FVE proto zobrazuje hodnotu za poslední dokončený kalendářní den a ignoruje dnešní zástupný řádek. Atribut `production_date` určuje datum, ke kterému se zobrazená hodnota vztahuje.

---

## Energy Dashboard Home Assistantu

Účty jednotlivých bytů neposkytují prostřednictvím rozhraní SmartEV API kumulativní výrobu fotovoltaiky.

Aby byla zajištěna kompatibilita s Energy Dashboardem, integrace automaticky vypočítává stabilní koeficient přidělení výroby FVE z historických dat SmartEV a z výroby fotovoltaického měřidla JOM odhaduje aktuální výrobu FVE pro daný byt.

Proces kalibrace je plně automatický a nevyžaduje žádnou konfiguraci uživatelem.

Koeficient přidělení i kontinuita kumulativních čítačů jsou ukládány podle stabilního identifikátoru bytu SmartEV. Při prvním spuštění po aktualizaci jsou stávající data uložená podle identifikátoru konfigurační položky automaticky migrována.

Živý kumulativní stav bytového elektroměru je primárním zdrojem údajů o spotřebě. Odběr ze sítě je odvozen jako rozdíl mezi kumulativní spotřebou bytu a kumulativně přidělenou výrobou FVE. Sloupec odběru ze sítě v CSV reportech SmartEV se nepoužívá pro živé ani kumulativní entity odběru ze sítě. Používá se pouze k vyřazení dnů s nulovým odběrem při kalibraci přidělení výroby FVE, protože SmartEV v těchto dnech nepoužívá běžný přidělovací poměr.

Pro Energy Dashboard Home Assistantu nastavte:

- Spotřeba ze sítě → Celkový odběr energie ze sítě
- Výroba ze solárních panelů → Celková odhadovaná výroba FVE

### Poznámka k migraci

Uživatelé, kteří přecházejí ze starších verzí integrace, již mohou mít vytvořené statistiky Energy Dashboardu ještě před migrací ukládání kontinuity kumulativních čítačů na stabilní identifikátor bytu SmartEV.

Pokud je první kumulativní odečet odběru ze sítě po migraci interpretován jako energie spotřebovaná během jednoho statistického intervalu, otevřete **Vývojářské nástroje → Statistiky**, vyberte první ovlivněný interval a nastavte jeho změnu na **0 kWh**. Tím dojde k opravě statistik Energy Dashboardu bez změny aktuální hodnoty kumulativního senzoru.

---

## Diagnostické údaje kalibrace

Entity odhadované výroby FVE zpřístupňují následující diagnostické atributy:

- allocation_coefficient
- used_calibration_samples
- skipped_zero_grid_samples
- coefficient_of_variation
- minimum_coefficient
- maximum_coefficient
- standard_deviation
- last_calibration

---

## Plánované funkce

- Podpora vodoměrů
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

## Požadavky

Nejsou vyžadovány žádné další balíčky Pythonu.

Veškeré závislosti jsou spravovány automaticky Home Assistantem prostřednictvím souboru `manifest.json` integrace.

---

## Licence

Licence MIT.

Podrobnosti naleznete v souboru LICENSE.

---