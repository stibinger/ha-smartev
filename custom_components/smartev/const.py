# Copyright (c) 2026 Petr Štibinger
# SPDX-License-Identifier: MIT

DOMAIN = "smartev"

CONF_EMAIL = "email"
CONF_FLAT_ID = "flat_id"
CONF_PASSWORD = "password"

# Apartment PV allocation calibration. Keep these thresholds in code until
# enough installations exist to justify user-facing options.
PV_ALLOCATION_MIN_SAMPLES = 3
PV_ALLOCATION_MAX_COEFFICIENT_OF_VARIATION = 0.01
PV_ALLOCATION_MAX_RELATIVE_RANGE = 0.03
PV_ALLOCATION_SIGNIFICANT_CHANGE = 0.01
PV_ALLOCATION_HISTORY_DAYS = 90
PV_ALLOCATION_MIN_JOM_PRODUCTION = 0.1
# The apartment report is rounded to 0.001 kWh. Values below half that
# precision are indistinguishable from zero grid import and identify allocation
# samples that SmartEV does not calculate using the normal PV ratio.
PV_ALLOCATION_ZERO_GRID_IMPORT = 0.0005

MANUFACTURER = "SmartEV"

NAME = "SmartEV"
