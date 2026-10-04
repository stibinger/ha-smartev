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

The integration supports electricity meters and online apartment channels for cold water, hot water and heating cost allocators (RTN).

Release **0.7.4** supports the updated responses used by the SmartEV web
application. It uses the application's existing endpoints; these are not the
promised new public API.

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
- Completed-day PV production total for the Home Assistant Energy Dashboard
- Authoritative completed-day grid and PV statistics for the Home Assistant Energy Dashboard

---

## Supported meters

| Meter | Status |
|--------|--------|
| ⚡ Electricity | ✅ Supported |
| 🚰 Cold and hot water | ✅ Online readings |
| ♨️ Heating RTN | ✅ Online readings in allocator units |

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

Available apartments also get **Cold water**, **Hot water**, **Heating RTN** and
separate last-reading timestamp sensors. Water values use m³; RTN uses allocator
units (dílky), not energy. Channels are discovered from the apartment's live meter
types, so absent channels create no entities. A temporarily failed water/heating
request makes its value sensors unavailable while electricity and valid source
timestamps continue to update. New channels can appear on a later refresh.

Water and RTN sensors have no state class: cumulative behavior and reset rules
are not yet confirmed. They do not supply long-term statistics for the Energy/Water
Dashboard. Values represent the dashboard's current readings; RTN value2 is not
interpreted. Multiple records of the same type do not produce guessed physical
devices or an aggregate timestamp. Existing electrical entity unique IDs are preserved.

SmartEV publishes daily PV production with a one-day delay. The latest daily PV
production sensor therefore shows the newest completed calendar day's value and
ignores today's placeholder row. Its `production_date` attribute identifies the
reported day.

---

## Home Assistant Energy Dashboard

SmartEV publishes the apartment production report only for completed days. The
integration follows the same accounting boundary for long-term energy
statistics.

Today's apartment PV production is estimated live from the JOM PV meter using
the automatically calibrated allocation coefficient. Today's grid estimate is
`max(0, apartment consumption - estimated apartment PV)`. Both are
informational live sensors and may change while the day is open.

Long-term Energy Dashboard data is written as authoritative **completed-day
statistics**. On a fresh installation the integration downloads the apartment
production reports from January through the current month and backfills every
completed day on its actual calendar date. The authoritative history is then
persisted locally, so Home Assistant restarts do not repeat the full backfill.
The current-month production report is refreshed at most once per day after
09:00 local time, while a full-year refresh runs at most once per week to pick
up historical SmartEV corrections. When SmartEV corrects a historical row, the
statistic for that date is updated; the correction is not charged to the day on
which Home Assistant receives it.

Today's estimates are never written to long-term statistics. This is important
because SmartEV can change the apartment allocation while the day is open.

The stable statistics are:

- `smartev:grid_import_flat_<flat_id>` — authoritative apartment grid import
- `smartev:pv_production_flat_<flat_id>` — authoritative apartment PV production

For a date-correct Energy Dashboard, select **SmartEV grid import** for grid
consumption and **SmartEV PV production** for solar production. The cumulative
sensor entities remain available as informational completed-day totals, but the
external SmartEV statistics are the authoritative Energy Dashboard source.

The calibration process is fully automatic and requires no user configuration.

Normal cloud polling runs once per hour. Expensive completed-day and historical
reports use the slower schedules described above to minimize SmartEV server load.

A successful routine refresh uses **5 HTTP requests** for electricity/PV, or
**6** when any cold-water, hot-water or RTN channel exists. All optional channels
share one request; absent channels cause no optional request or entity creation.
The authenticated session is reused without an hourly login. One daily CSV adds
one request; a weekly history refresh downloads January through the current
month and reuses its current-month CSV. Startup also logs in and resolves the
production topology once per session. Counts exclude HTTP redirects, manual
refreshes and retries after failures. See [the release audit](docs/RELEASE_0.7.3.md)
for endpoint counts, startup behavior and failure handling.

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

Integrace podporuje elektroměry a online bytové odečty studené vody, teplé vody a rozdělovačů topných nákladů (RTN).

Verze **0.7.4** podporuje aktualizované odpovědi používané webovou aplikací
SmartEV. Využívá její stávající endpointy; nejde o slíbené nové veřejné API.

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
- Celková výroba FVE z dokončených dnů pro Energy Dashboard Home Assistantu
- Autoritativní statistiky odběru ze sítě a výroby FVE z dokončených dnů pro Energy Dashboard Home Assistantu

---

## Podporovaná měřidla

| Měřidlo | Stav |
|----------|------|
| ⚡ Elektřina | ✅ Podporováno |
| 🚰 Studená a teplá voda | ✅ Online odečty |
| ♨️ Topení RTN | ✅ Online odečty v dílcích |

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

Podle dostupných typů měřidel se vytvářejí také senzory **Studená voda**,
**Teplá voda**, **Topení RTN** a samostatné timestampy posledních odečtů.
Voda se zobrazuje v m³, RTN v dílcích. Výpadek endpointu vody a RTN znepřístupní
jeho hodnotové senzory, ale neblokuje elektřinu ani dostupné zdrojové timestampy.
Nově dostupné kanály se přidají při další aktualizaci. Integrace podporuje seznam
s více typy měřidel a zachovává původní identifikátory elektrických entit.

Kumulativnost vody a RTN ani pravidla resetů nejsou potvrzena. Nové senzory proto
nemají state_class a neposkytují dlouhodobé statistiky pro Energy/Water dashboard.
RTN value2 se neinterpretuje. U více záznamů stejného typu se neodhaduje identita
fyzických zařízení ani společný timestamp.

SmartEV zveřejňuje denní výrobu FVE s jednodenním zpožděním. Senzor poslední denní výroby FVE proto zobrazuje hodnotu za poslední dokončený kalendářní den a ignoruje dnešní zástupný řádek. Atribut `production_date` určuje datum, ke kterému se zobrazená hodnota vztahuje.

---

## Energy Dashboard Home Assistantu

SmartEV zveřejňuje bytový přehled výroby až pro dokončené dny. Integrace proto
pro dlouhodobé energetické statistiky používá stejnou účetní hranici.

Dnešní výroba FVE pro byt se průběžně odhaduje z FVE měřidla JOM pomocí
automaticky kalibrovaného alokačního koeficientu. Dnešní odhad odběru ze sítě
je `max(0, spotřeba bytu - odhadovaná výroba FVE)`. Oba senzory jsou pouze
informativní a jejich hodnota se může během otevřeného dne měnit.

Dlouhodobá data Energy Dashboardu se zapisují jako autoritativní statistiky
**dokončených dnů**. Při nové instalaci integrace se načtou bytové přehledy
SmartEV od ledna do aktuálního měsíce a každý dokončený den se zpětně zapíše ke
svému skutečnému kalendářnímu datu. Autoritativní historie se potom ukládá
lokálně, takže restart Home Assistantu celý backfill neopakuje. Přehled za
aktuální měsíc se obnovuje nejvýše jednou denně po 09:00 místního času a celý
rok nejvýše jednou týdně kvůli případným historickým opravám SmartEV. Pokud
SmartEV historický řádek opraví, opraví se statistika příslušného dne; změna se
nezapočítá do dne, kdy ji Home Assistant obdržel.

Dnešní odhady se do dlouhodobých statistik nikdy nezapisují. Je to důležité,
protože SmartEV může alokaci bytu během otevřeného dne měnit.

Stabilní statistiky jsou:

- `smartev:grid_import_flat_<flat_id>` — autoritativní odběr bytu ze sítě
- `smartev:pv_production_flat_<flat_id>` — autoritativní výroba FVE pro byt

Pro datumově správný Energy Dashboard vyberte pro spotřebu ze sítě **SmartEV
grid import** a pro solární výrobu **SmartEV PV production**. Kumulativní
senzorové entity zůstávají k dispozici jako informativní součty dokončených
dnů, ale autoritativním zdrojem Energy Dashboardu jsou externí statistiky
SmartEV.

Proces kalibrace je plně automatický a nevyžaduje žádnou konfiguraci uživatelem.

Běžné cloudové dotazování probíhá jednou za hodinu. Náročnější přehledy
dokončených dnů a historie používají výše popsané pomalejší intervaly, aby se
minimalizovala zátěž serverů SmartEV.

Běžný úspěšný refresh provede **5 HTTP requestů** pro elektřinu/FVE nebo **6**,
pokud je dostupná voda či RTN. SV/TUV/RTN sdílejí jediný dodatečný request.
Chybějící kanály nevytvářejí entity ani dodatečný request. Přihlášená relace se
opakovaně používá bez hodinového loginu. Denní CSV přidává jeden request;
týdenní historie načte leden až aktuální měsíc a využije stejné aktuální CSV.
Počty nezahrnují HTTP přesměrování, ruční aktualizace a opakování po chybě.
Podrobnosti jsou v [release auditu](docs/RELEASE_0.7.3.md).

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
