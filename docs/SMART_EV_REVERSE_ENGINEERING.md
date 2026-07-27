# SmartEV electricity endpoint reverse-engineering review

Review date: 2026-07-27  
Application: `https://jom.smartev.cz`

## Executive findings

The value shown continuously on every apartment card comes from:

```http
GET /data/buildingFlatsMeters.php?buildingId={buildingId}
```

The home page calls this endpoint immediately and every 20 seconds. The displayed
register is `flats[].meters[].value1`; for an electricity meter (`type: 0`) it is
the current cumulative import/register value in kWh. The card formats it with
`value1.toFixed(3)`.

This endpoint is not a production-report source. It returns the current meter
register and timestamp directly, along with fields the cards do not display:
meter ID, meter type, `value2`, unit, apartment identity, floor and owner names.
For bidirectional meters, `value2` is the cumulative export register. The backend
sometimes serializes missing numeric values as the JSON string `"NaN"` rather
than `null`, so clients must sanitize both.

The richer endpoint:

```http
GET /data/flatMetersState.php?flatId={flatId}
```

returns the same current register plus today/month/year consumption and import/
export values. It populates the selected-apartment detail panel, but is not the
source for the cards.

## Authentication

All reviewed application and data routes use the same PHP session authentication.

```http
POST /login.php
Content-Type: application/x-www-form-urlencoded

email={email}&password={password}&log_in=Přihlásit se
```

Successful login redirects away from `/login.php` and sets a session cookie in a
persistent HTTP session. Subsequent calls use that cookie; there is no bearer
token, API key or CSRF parameter on the reviewed read endpoints. An expired or
unauthenticated request redirects or returns the login HTML, so a client must not
assume every HTTP 200 response is JSON. Access is server-side account-scoped:
the same endpoint can return only the permitted apartment(s) for a normal user
and all apartments for an administrator.

## Confirmed JSON endpoints

### `GET /data/userOperatorsBuildings.php`

Parameters: none.

Purpose: topology used to select operator, JOM and building.

```json
[
  {
    "id": 1,
    "name": "Operator",
    "joms": [
      {
        "id": 123,
        "name": "JOM",
        "buildings": [{"id": 10, "name": "Building"}]
      }
    ]
  }
]
```

### `GET /data/buildingFlatsMeters.php?buildingId={int}`

Purpose: apartment cards on the post-login home page. Refreshed every 20 seconds.

```json
{
  "buildingId": 10,
  "flats": [
    {
      "id": 200,
      "name": "Apartment owner/name",
      "fname": "First",
      "lname": "Last",
      "storey": 3,
      "number": 13,
      "meters": [
        {
          "id": 13,
          "dt": 1785145297,
          "type": 0,
          "value1": 3289.2041015625,
          "value2": "NaN",
          "unit": "kWh"
        }
      ]
    }
  ]
}
```

Meter type mapping observed in the frontend:

- `0` (or `null`): electricity
- `1`: PV
- `2`: battery/inverter virtual meter
- `3`: cold water in apartment-card code, but battery charge/discharge in the
  JOM chart endpoint (the meaning is context-dependent)
- `4`: hot water
- `5`: heat-cost allocator (RTN)

For cards, electricity/PV values are displayed directly to three decimals.
Water values are divided by 1000. `dt` is Unix seconds. A no-meter placeholder
can contain `id: null`, `dt: null`, `type: null`, and `"NaN"` values.

### `GET /data/flatMetersState.php?flatId={int}`

Alternative form used by the JS module:

```http
GET /data/flatMetersState.php?buildingId={int}
```

The flat form returns full selected-apartment state:

```json
{
  "id": 200,
  "name": "Apartment",
  "storey": 3,
  "number": 13,
  "buildingId": 10,
  "buildingName": "Building",
  "jomId": 123,
  "dt": 1785145315,
  "dtStr": "27.07.2026 11:41:55",
  "meters": [
    {
      "id": 13,
      "dt": 1785145297,
      "dtStr": "27.07.2026 11:41:37",
      "type": 0,
      "value1": 3289.2041015625,
      "value2": "NaN",
      "unit": "kWh",
      "rev": false,
      "today": {
        "dt": 1785103188,
        "dtStr": "26.07.2026 23:59:48",
        "value1": 3289.2041015625,
        "value2": "NaN"
      },
      "consToday": {"dt": 1785103200, "dtStr": "...", "cons1": 0, "cons2": "NaN"},
      "consMonth": {"dt": 1785145274, "dtStr": "...", "cons1": 0.2512, "cons2": "NaN"},
      "consYear": {"dt": 1785145274, "dtStr": "...", "cons1": 0.4631, "cons2": "NaN"}
    }
  ],
  "kWhTotal": {"today": 0, "month": 0.2512, "year": 0.4631},
  "pv": []
}
```

`cons1` is import/consumption and `cons2` is the second/export channel. `today`
is the baseline register used for the day calculation. For a JOM/building
response the meter list can include grid (`type: 0`), battery (`type: 2`) and PV
(`type: 1`), and `pv` repeats the PV meter object. The selected-apartment panel
uses only types 0 and 1 and displays current, today, month and year values.

The captured building form returns a JOM aggregate object rather than an array
of flats. This endpoint should therefore be treated as a polymorphic response,
not as apartment discovery.

### `GET /data/flatMetersChart.php`

Parameters:

- `flatId` (integer, required)
- `y`, `m`, `d` (integers; `0` means the next coarser/default level)

Drill-down mapping:

- `y=0&m=0&d=0`: yearly totals, `chartInterval: "Y"`, `idx` is year
- `y=YYYY&m=0&d=0`: monthly totals, `chartInterval: "m"`, `idx` is month
- `y=YYYY&m=MM&d=0`: daily totals, `chartInterval: "d"`, `idx` is day
- `y=YYYY&m=MM&d=DD`: hourly totals, `chartInterval: "H"`, `idx` is hour

```json
{
  "id": 200,
  "name": "Apartment",
  "storey": 3,
  "number": 13,
  "buildingId": 10,
  "buildingName": "Building",
  "jomId": 123,
  "dt": 1785145324,
  "dtStr": "...",
  "meters": [
    {
      "id": 13,
      "dt": 1785145297,
      "dtStr": "...",
      "type": 0,
      "value1": 3289.2041015625,
      "value2": 0,
      "unit": "kWh",
      "chartInterval": "H",
      "chartData": [
        {
          "dt0": "27.07.2026 00:59:38",
          "dt1": "27.07.2026 01:59:02",
          "dt": 1785110342,
          "idx": "01",
          "val1": 0
        }
      ]
    }
  ]
}
```

At coarser levels each chart row is normally `{dt, idx, val1}`. Hourly rows add
the textual interval boundaries `dt0` and `dt1`. This is the confirmed source
for hourly and daily apartment consumption. The top-level/current `value1` is
also cumulative and live, although the home cards use `buildingFlatsMeters.php`.

### `GET /data/jomMeters.php?jomId={int}`

Purpose: live JOM energy-flow diagram. Refreshed every 20 seconds.

```json
{
  "jomId": 123,
  "meters": [
    {
      "id": 1,
      "dt": 1785145308,
      "dtStr": "...",
      "type": 0,
      "value1": 49552.87890625,
      "value2": 14123.3466796875,
      "unit": "kWh",
      "power": -11320.27,
      "soc": null
    },
    {
      "id": 225,
      "dt": 1785145308,
      "dtStr": "...",
      "type": 2,
      "value1": "NaN",
      "value2": "NaN",
      "unit": "kWh",
      "power": 477.99,
      "soc": 92
    },
    {
      "id": 23,
      "dt": 1785145308,
      "dtStr": "...",
      "type": 1,
      "value1": 62480.3,
      "value2": 138.785,
      "unit": "kWh",
      "power": 15985.19,
      "soc": null
    }
  ]
}
```

Types are grid (`0`), PV (`1`) and battery (`2`). `power` is instantaneous W.
`soc` is battery state of charge in percent. The frontend derives building load
as:

```text
load power = grid power + PV power - battery power
```

This derived load is not returned as its own backend field. Sign direction must
be preserved and validated against the UI; positive/negative grid and battery
power represent opposite directions.

### `GET /data/jomEnergyChart.php?jomId={int}`

Purpose: compact current-day JOM energy-flow summary, refreshed every 20 seconds.

```json
{
  "jomId": 123,
  "emDt": 1785145308,
  "emIm": 16.30078125,
  "emEx": 13.2060546875,
  "pvDt": 1785145308,
  "pvIm": 55.95703125,
  "pvEx": 0.0410003662109375,
  "viDt": 1785145308,
  "viIm": 23.01171875,
  "viEx": 1.8154296875
}
```

Field semantics established from the frontend labels and comparison with other
responses:

- `emIm`: grid import today
- `emEx`: grid export today
- `pvIm`: PV production today
- `pvEx`: PV meter reverse/second channel
- `viIm`: energy charged into the battery today
- `viEx`: energy discharged from the battery today (returned but currently not
  plotted by `jomEnergyChart.js`)
- each `*Dt`: source meter timestamp

All energies are kWh.

### `GET /data/jomMetersChart.php`

Parameters:

- `jomId` (integer)
- `meterType`: `0` grid, `1` PV, `3` battery energy
- `y`, `m`, `d`: same drill-down rules as `flatMetersChart.php`

```json
{
  "id": 123,
  "dt": 1785145333,
  "dtStr": "...",
  "meters": [
    {
      "id": 1,
      "dt": 1785145308,
      "dtStr": "...",
      "type": 0,
      "value1": 49552.87890625,
      "value2": 14123.3466796875,
      "unit": "kWh",
      "chartInterval": "H",
      "chartData": [
        {
          "dt0": "...",
          "dt1": "...",
          "dt": 1785139174,
          "idx": "09",
          "val1": 0.29296875,
          "val2": 0.119140625
        }
      ]
    }
  ]
}
```

For grid, `val1` is import and `val2` export. For battery type 3, `val1` is
charge and `val2` discharge; the chart renders discharge as a negative bar.
For PV, the backend may return the actual meter plus an `id: "sum"` aggregate;
the aggregate `type` is 1, `val1` is PV production and `val2` the second/reverse
channel. The response can also include other meter objects with empty
`chartData`, so select by type/ID instead of relying on array position.

This endpoint supplies yearly, monthly, daily and hourly JOM grid, PV and battery
energy. An observed day-level historical query timed out once while current-day
and month-level calls succeeded; clients need a normal timeout/retry strategy.

### `GET /reports/prehled-vyroby-data.php?action=getJoms`

Purpose: report topology, including flats (unlike the lean dashboard topology).

```json
[
  {
    "id": 1,
    "name": "Operator",
    "joms": [
      {
        "id": 123,
        "name": "JOM",
        "buildings": [
          {
            "id": 10,
            "name": "Building",
            "flats": [{"id": 200, "name": "Apartment", "no": 13}]
          }
        ]
      }
    ]
  }
]
```

The two other actions return HTML or CSV rather than JSON:

```http
GET /reports/prehled-vyroby-data.php?action=getReport&jomId={int}&flatId={int}&month={1..12}&year={YYYY}
GET /reports/prehled-vyroby-data.php?action=getReportCsv&jomId={int}&flatId={int}&month={1..12}&year={YYYY}
```

`flatId=0` means the complete JOM. The CSV fields are `Datum`,
`Celkem [kWh]`, `FVE [kWh]`, `Síť [kWh]`, with a final `Celkem` row.
This report is allocation/accounting output, not live meter data.

## Confirmed non-JSON electricity report endpoints

Each report data endpoint also has `action=getJoms`, which returns the same
operator/JOM topology shape used by that report.

### Energy flows over a period

```http
GET /reports/toky-energii-za-obdobi-data.php?action=getJoms
GET /reports/toky-energii-za-obdobi-data.php?action=getReport&jomId={int}&dateFrom={YYYY-MM-DD}&dateTo={YYYY-MM-DD}
GET /reports/toky-energii-za-obdobi-data.php?action=getReportCsv&jomId={int}&dateFrom={YYYY-MM-DD}&dateTo={YYYY-MM-DD}
```

`getReport` returns an HTML fragment; `getReportCsv` returns a semicolon CSV.
Daily and total fields are:

- date
- grid import (`Síť nákup`)
- grid export (`Síť přetoky`)
- PV production (`FVE výroba`)
- energy charged into battery (`Uloženo do baterie`)

The CSV does not include battery discharge even though `viEx`/battery `val2`
exist in JSON endpoints.

### Meter state at a date

```http
GET /reports/stav-elektromeru-data.php?action=getJoms
GET /reports/stav-elektromeru-data.php?action=getReport&jomId={int}&date={YYYY-MM-DD}
GET /reports/stav-elektromeru-data.php?action=getReportCsv&jomId={int}&date={YYYY-MM-DD}
```

`getReport` returns HTML and `getReportCsv` returns semicolon CSV. The CSV has:

- JOM main meter and PV meter: type, total state, import, export, ID, serial
  number
- every apartment: apartment number, name, total state, optional import and
  export, ID, serial number

This is a point-in-time historical register report, useful for reconciliation
but less efficient than JSON for polling.

## Other reviewed dashboard endpoints

These are related to electrical equipment but did not expose additional
electricity measurements in the captured account:

```http
GET /data/jomChargers.php?action=getChargers&jomId={int}
GET /data/jomChargers.php?action=getCardData&cardId={int}
GET /data/smartSockets.php?action=getJomSocketsState&jomId={int}
```

Observed charger response:

```json
{"error": false, "response": []}
```

Observed smart-socket response:

```json
false
```

`getCardData` is called only after a charger-card click, so no valid card ID was
available in this account and its success schema could not be confirmed without
inventing an identifier. The charger module shows that returned charger/card
objects may include charging-session information, but this endpoint should not
be represented as confirmed energy-meter data from the current captures.

The water/heating endpoint is not an electricity source:

```http
GET /data/waterHeatingMetersState.php?action=getWaterHeatingMetersStateData&flatId={int}
```

It returns:

```json
{
  "currentMetersStateData": {"RTN": 0, "SV": 0, "TUV": 0},
  "monthMetersStateData": {"RTN": 0, "SV": 0, "TUV": 0},
  "yearMetersStateData": {"RTN": 0, "SV": 0, "TUV": 0}
}
```

## Frontend request audit

First-party files inspected:

- dashboard HTML and inline JS
- `ajax.js`
- `operatorsBuildings.js`
- `flatsMeters2.js`
- `flatMetersState2.js`
- `flatMetersChart.js`
- `jomMeters.js`
- `jomEnergyChart.js`
- `jomMetersChart.js`
- `jomChargers.js`
- `smartSockets.js`
- `waterHeatingMetersState.js`
- inline JS for the production, energy-flow and electricity-state reports

The frontend uses the shared `getData`/`postData` AJAX helper. No first-party
`fetch()`, WebSocket, EventSource/SSE, or direct application-level
`XMLHttpRequest` call was found outside that helper. No dynamically generated
hostnames were found. Dynamic URLs are string concatenations of same-origin PHP
paths and the IDs/date selectors documented above.

The dashboard polling loop runs every 20 seconds and calls:

- `buildingFlatsMeters.php` (apartment cards/current cumulative readings)
- `jomMeters.php` (instantaneous grid/PV/battery power and SoC)
- `jomEnergyChart.php` (today’s energy totals)
- `jomChargers.php?action=getChargers`
- `smartSockets.php?action=getJomSocketsState`

`flatMetersState.php` is called when a flat is selected, not by that recurring
loop. Chart endpoints are called when their iframe is opened or the user drills
into a period.

## Data availability matrix

| Requested data | Best confirmed endpoint | Resolution/scope |
|---|---|---|
| Apartment cumulative reading | `buildingFlatsMeters.php` | live-ish, 20 s card polling |
| Apartment current/detail totals | `flatMetersState.php` | live register; today/month/year |
| Apartment hourly consumption | `flatMetersChart.php` | hourly |
| Apartment daily/monthly/yearly consumption | `flatMetersChart.php` | daily/monthly/yearly |
| Live grid/PV/battery power | `jomMeters.php` | instantaneous W |
| Battery state of charge | `jomMeters.php` | live percent |
| Today grid import/export, PV, battery charge/discharge | `jomEnergyChart.php` | current-day cumulative |
| JOM hourly/daily grid import/export | `jomMetersChart.php?meterType=0` | hourly through yearly |
| JOM hourly/daily PV | `jomMetersChart.php?meterType=1` | hourly through yearly |
| JOM hourly/daily battery charge/discharge | `jomMetersChart.php?meterType=3` | hourly through yearly |
| Apartment PV allocation | production report | daily allocation/accounting |
| Daily JOM energy flow report | `toky-energii-za-obdobi-data.php` | daily HTML/CSV |
| Historical register at a date | `stav-elektromeru-data.php` | point-in-time HTML/CSV |

No JSON endpoint was found that returns **live per-apartment PV allocation**.
The production report provides delayed/settled apartment PV allocation; JOM
JSON endpoints provide live total PV, not an authoritative per-apartment split.

## Home Assistant Energy Dashboard recommendation

For apartment grid/consumption, the cumulative electricity register from
`buildingFlatsMeters.php` (or the equivalent current `value1` from
`flatMetersState.php`/`flatMetersChart.php`) is a materially better Energy
Dashboard source than reconstructing consumption from the production CSV:

- it is a real monotonic cumulative meter register;
- it updates during the day;
- it maps directly to Home Assistant `total_increasing` energy semantics;
- it avoids report delay and allocation/report rounding.

`buildingFlatsMeters.php` is most efficient when discovering/updating several
authorized flats in one building. `flatMetersState.php` is better when one flat
also needs today/month/year values. `flatMetersChart.php` is best for historical
backfill and hourly statistics, not for the normal polling hot path.

For JOM-level grid import/export and PV, `jomMeters.php` exposes cumulative
registers and `jomMetersChart.php` exposes clean interval deltas. The cumulative
register is preferable for long-lived Energy Dashboard entities; chart data is
valuable for backfill and validation. Battery charge/discharge and SoC are also
available, but they are JOM-level, not apartment-level.

The current production CSV remains the best confirmed source for authoritative
**apartment PV allocation**, because no live apartment-allocation JSON endpoint
was found. It should not be replaced with total JOM PV unless the integration
deliberately implements and labels an allocation estimate.

Implementation caveats for any future work:

- reject/sanitize `"NaN"` strings and non-finite numbers;
- use `dt`, not response time, as the measurement timestamp;
- preserve import/export channels separately;
- handle meter resets/replacements before exposing `total_increasing`;
- do not assume meter array order;
- scope topology and IDs to what the authenticated account returns;
- detect login HTML/redirects even on HTTP 200;
- retry timeouts conservatively, especially deep historical chart requests.

## Completeness boundary

This is a complete review of electricity-related requests referenced by the
authenticated dashboard, its loaded first-party JavaScript, the apartment and
JOM chart iframes, and the electricity/production/energy-flow report pages
available to the reviewed account. It is not a blind brute-force scan of
unreferenced server filenames. One conditional endpoint,
`jomChargers.php?action=getCardData`, could not have its success response schema
confirmed because the account returned no charger cards.
