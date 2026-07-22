# Changelog

All notable changes to this project will be documented in this file.

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