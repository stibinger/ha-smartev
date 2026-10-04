# Changelog

All notable changes to this project will be documented in this file.

## [0.7.4] - 2026-10-04

### Release

- Ship the implementation verified in a real Home Assistant installation against the updated SmartEV web application's responses.
- Include cold water (SV), hot water (TUV), and heating RTN readings alongside preserved electricity/PV support and existing electrical entity IDs.
- Include robust handling of mixed meter types, unknown meters, and optional water/heating endpoint failures.
- Retain the tested polling, caching, and completed-day electricity/PV accounting behavior without functional Python changes.
- Add HACS validation and hassfest to GitHub Actions.
- Water/RTN accumulation and reset semantics remain unconfirmed; long-term statistics for these channels remain disabled.

## [0.7.3] - 2026-10-04

### Added

- Online cold-water and hot-water readings in m³ and heating RTN readings in allocator units.
- Separate source timestamps and English/Czech names for available apartment channels.
- Offline regression tests using anonymized captures, including optional endpoint failures and existing electrical entity IDs.

### Fixed

- Preserve electricity/PV support and existing electrical entity IDs while adapting to the updated SmartEV web application's API responses (not an official new public API).
- Accept mixed meter collections and select electricity by type and identity instead of array order.
- Pass the full dashboard context to the water/heating endpoint and isolate its failures from electricity updates.
- Ignore unknown meter types and discover newly available supported channels during later refreshes.

### Limitations

- Water/RTN cumulative behavior and reset semantics remain unconfirmed. These sensors have no state class and do not publish TOTAL_INCREASING or Energy/Water dashboard statistics.
- RTN value2, individual physical report channels, and the malformed annual water report are not used.

### Changed

- Reduced the main SmartEV polling interval from once per minute to once per hour.
- Limited the apartment production CSV to at most one refresh per day after 09:00 local time, matching SmartEV's delayed completed-day publication.
- Added persistent server-side data caching so Home Assistant restarts reuse authoritative history instead of downloading the full year again.
- Limited full-year production-history refreshes to once per week to detect historical SmartEV corrections without repeatedly loading old reports.
- Removed repeated previous-month JOM/report requests from normal polling; persisted calibration and authoritative daily data are reused across month boundaries.

### Fixed

- Prevented minute-by-minute downloads of yearly, monthly, JOM PV, and production-report data that could unnecessarily load SmartEV servers.
- Preserved v0.7.2 completed-day Energy Dashboard statistics and accounting behavior while reducing cloud requests.

## [0.7.2] - 2026-08-02

### Added

- Added authoritative Home Assistant long-term statistics for apartment grid import and PV production.
- Added automatic backfill of SmartEV apartment production reports from January through the current month.
- Added stable external statistics `smartev:grid_import_flat_<flat_id>` and `smartev:pv_production_flat_<flat_id>` so completed SmartEV days are recorded on their actual calendar dates.

### Changed

- Reworked completed-day accounting to recompute totals directly from authoritative SmartEV daily rows instead of carrying continuity or pending-estimate offsets.
- Current-day PV and grid values remain live estimates only and are never written into long-term statistics.
- Historical SmartEV corrections update the matching historical statistic instead of being counted on the day when the correction is received.

### Fixed

- Fixed completed values being attributed to the following day when SmartEV published them after midnight.
- Fixed a newly published completed day appearing as one large current-day Energy Dashboard increment.
- Fixed incomplete cumulative totals after a clean integration installation by rebuilding the current year from SmartEV reports.


### Changed

- Separated live current-day estimates from completed SmartEV accounting.
- Made cumulative PV production and grid-import sensors use only completed days
  published by SmartEV; today's estimates are excluded from Energy Dashboard
  totals until SmartEV publishes the completed day.
- Kept today's estimated PV and grid import as informational live sensors.
- Made today's grid estimate follow SmartEV accounting semantics with
  `max(0, consumption - allocated PV)`.
- Renamed the cumulative PV sensor display name from estimated production to
  total PV production because it now contains completed SmartEV values only.

### Fixed

- Prevented falling current-day grid estimates from producing negative grid
  consumption in the Home Assistant Energy Dashboard.
- Removed pending-estimate carry-over from cumulative grid accounting; a day is
  added to long-term totals only after SmartEV publishes its authoritative row.

## [0.7.0] - 2026-07-25

### Added

- Added estimated apartment PV production based on automatic calibration against the JOM PV meter.
- Added cumulative estimated PV production sensor compatible with the Home Assistant Energy Dashboard.
- Added cumulative total grid energy sensor compatible with the Home Assistant Energy Dashboard.
- Added automatic calibration diagnostics, including:
  - allocation coefficient
  - calibration sample count
  - skipped zero-grid sample count
  - coefficient of variation
  - calibration statistics

### Changed

- Introduced automatic PV allocation coefficient calibration using historical SmartEV data.
- Excluded zero-grid days from coefficient calibration because they distort apartment allocation calculations.
- Shared the daily cumulative counter implementation between estimated PV production and cumulative grid energy.
- Improved Energy Dashboard integration for apartment accounts by providing cumulative production and grid import sensors.
- Preserved cumulative counters across Home Assistant restarts and midnight rollovers.

### Fixed

- Prevented calibration drift caused by days with zero grid import.
- Prevented cumulative counters from decreasing after temporary missing data or SmartEV corrections.
- Prevented duplicate daily accumulation after Home Assistant restarts.

## [0.6.1] - 2026-07-22

### Added

- Reintroduced daily PV production as the latest completed daily record reported by SmartEV.
- Added the `production_date` attribute to identify the calendar day represented by the sensor.
- Added month-boundary handling so the latest completed day can be read from the previous month's report.

### Changed

- Renamed the sensor to "Latest daily PV production" in English and "Poslední denní výroba FVE" in Czech.
- Documented SmartEV's one-day delay for daily PV production.
- Left the sensor state class unset because the value is neither cumulative nor a current measurement.

### Fixed

- Excluded today's zero-value placeholder row when selecting the latest completed daily PV record.
- Ensured the selected record's date is exposed through the `production_date` attribute.

## [0.6.0] - 2026-07-22

### Added
- Added photovoltaic (PV) production support for apartment accounts.
- Added current month PV production sensor.
- Added today's grid energy sensor.
- Added current month grid energy sensor.
- Added CSV parsing for the SmartEV production report.

### Changed
- Improved Energy Dashboard compatibility by using `SensorStateClass.TOTAL_INCREASING` for cumulative energy sensors.
- Isolated PV report failures from the main coordinator update so consumption sensors remain available if the production report is unavailable.
- Reused a single CSV download for all PV and grid energy values without increasing the number of HTTP requests.

### Removed
- Removed the "Today's PV production" sensor because SmartEV publishes PV production with a one-day delay, making the sensor permanently misleading.

## [0.5.0] - 2026-07-20

### Added

- Initial public release
- Home Assistant Config Flow
- Automatic apartment discovery
- Automatic migration of existing configurations
- Electricity meter support
- Home Assistant Energy Dashboard compatibility
- English and Czech translations

### Changed

- Simplified configuration process
- Improved administrator apartment selection
- Repository cleaned for public release
