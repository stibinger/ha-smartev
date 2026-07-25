# Changelog

All notable changes to this project will be documented in this file.

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
