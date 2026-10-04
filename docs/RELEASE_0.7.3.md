# SmartEV 0.7.3 release audit

Audit date: 2026-10-04. Counts describe one configured apartment/integration
entry, successful responses without redirects, hourly automatic polling and
valid production history. No live SmartEV requests were made for this audit.

## Routine refresh

The coordinator interval is `timedelta(hours=1)` (3,600 seconds). Entities share
the coordinator and do not poll independently.

| Endpoint | Requests per routine refresh | Purpose |
|---|---:|---|
| `/data/flatMetersChart.php` | 3 | All years (`y=m=d=0`), current year's months (`y=year,m=d=0`), current month's days (`y=year,m=month,d=0`) |
| `/data/buildingFlatsMeters.php` | 1 | Live electricity, optional meter discovery and source timestamps |
| `/data/jomMetersChart.php` | 1 | JOM PV register and current-month daily history (`meterType=1`) |
| `/data/waterHeatingMetersState.php` | 0 or 1 | Shared current SV/TUV/RTN values, only for discovered supported channels |

Totals: **5** for electricity/PV; **6** for electricity/PV with SV/TUV or with
SV/TUV/RTN. Relative to the previous code, optional channel support adds only
the shared water/heating request. The building request already supplied live
electricity. Water-only entries stop before electricity/PV reports and use
3 routine requests. Unknown types alone do not trigger the optional endpoint.

The three chart requests have different periods and supply different electrical
sensors. There is no duplicate request in the successful routine path and no
login during it. The existing `requests.Session` retains authentication.

## Daily and weekly requests

`/reports/prehled-vyroby-data.php?action=getReportCsv` adds one current-month
request on the first refresh after 09:00 local time each day. On a successful
weekly history refresh it fetches January through the current month (M requests)
and reuses the current-month result for the daily report.

| Installation | Routine requests/hour | Routine requests/24 h | Normal day including daily CSV | Weekly history day |
|---|---:|---:|---:|---:|
| Electricity/PV | 5 | 120 | 121 | 120 + M |
| Electricity/PV + water and/or RTN | 6 | 144 | 145 | 144 + M |

For a stable month, weekly average totals are `120 + (M+6)/7` or
`144 + (M+6)/7` per day, respectively. In October (M=10): **122.29/day,
5.10/hour**, or **146.29/day, 6.10/hour**. An October weekly history day uses
130 or 154 requests. These are schedule estimates, not measured wire counts;
restarts, month transitions, manual refreshes and failures can alter totals.

## Initialization and configuration

- Each integration setup creates a session and calls `POST /login.php` once.
  Its redirects can generate additional HTTP requests; their exact number
  depends on the server and cannot be established from source code alone.
- The first production access in each session adds one
  `/reports/prehled-vyroby-data.php?action=getJoms` topology request. Its JOM ID
  is then cached in memory. Water support adds no separate topology lookup.
- A fresh installation without authoritative cached history downloads M CSVs
  immediately. Startup therefore uses **M+7** requests for electricity/PV or
  **M+8** with water/RTN, including login and topology, excluding redirects.
  In October: 17 or 18. The daily CSV is reused from this history download.
- A restart with valid, not-due persisted history uses 7 or 8 requests including
  login/topology. A due daily CSV adds 1; due weekly history adds M instead.
- Configuration discovery uses a separate login, one
  `/data/userOperatorsBuildings.php`, and one building request per discovered
  building. Explicit selection in the multiple-apartment flow separately
  validates access using a login and one flat chart request. Reauthentication
  also validates via login plus flat chart and subsequently reloads the entry.
  These are configuration operations, not recurring polling.

## Errors and retries

There is no client retry loop, automatic repeated login or custom retry adapter.
Required-request failures abort that refresh; Home Assistant controls subsequent
refresh/setup retries. Each repeated setup authenticates once in a new session.
Expired required authentication is reported for reauthentication.

Optional water/heating and JOM failures are isolated and are tried again at the
next refresh. Failed daily reports do not advance their cache timestamp and
can be attempted at each subsequent hourly refresh after 09:00. With no valid
authoritative history, the January-to-current-month bootstrap is retried hourly;
if the current-month history CSV fails after 09:00, the daily branch can attempt
that same CSV once more in the cycle. Failed topology lookup is not cached and
may repeat for subsequent production calls. These are failure-path overheads,
not successful routine traffic. HTTP redirects can also add requests.

## Compatibility and release scope

Electricity/PV behavior and entity IDs are preserved. Offline regression tests
cover electricity only, electricity plus SV/TUV, electricity plus SV/TUV/RTN,
unknown meter types and a missing optional endpoint. Absent channels create no
water/RTN entities. Optional endpoint failure leaves electricity working and
makes optional values unavailable instead of retaining stale readings.

SV/TUV/RTN long-term statistics remain disabled: accumulation and reset semantics
have not been confirmed. RTN uses allocator units, not energy. The integration
uses the SmartEV web application's existing endpoints, not an official new
public API. Routine traffic is modest; no polling redesign is included.

Real Home Assistant verification supplied by the maintainer: two days with
electricity/PV, cold water, hot water and RTN; readings matched the SmartEV web
application and no functional problem was observed. Offline tests use minimal
Home Assistant doubles and complement this live verification.
