# Changelog

All notable changes to this project will be documented in this file.

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
