"""Offline API/coordinator/entity regressions from anonymized SmartEV captures.

Minimal HA interface doubles allow these unit tests to run without installing
Home Assistant. They do not replace an in-HA platform lifecycle smoke test.
"""

import importlib
import json
import sys
import types
import unittest
from copy import deepcopy
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from unittest.mock import Mock, patch

import requests

SOURCE = Path(__file__).parents[1] / "custom_components" / "smartev"
FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)


class FakeCoordinator:
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, hass, **_kwargs):
        self.hass = hass
        self.data = None
        self.last_update_success = True
        self.listeners = []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)


class FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def available(self):
        return self.coordinator.last_update_success


class FakeStore:
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, *_args, **_kwargs):
        self.saved = None

    async def async_save(self, value):
        self.saved = deepcopy(value)


class FakeHass:
    async def async_add_executor_job(self, function, *args):
        return function(*args)


def load_modules():
    """Import production logic under an isolated package and temporary HA doubles."""
    modules = {}

    def module(name, **bindings):
        result = types.ModuleType(name)
        result.__dict__.update(bindings)
        modules[name] = result
        return result

    class DeviceClass(StrEnum):
        ENERGY = "energy"
        WATER = "water"
        TIMESTAMP = "timestamp"

    class StateClass(StrEnum):
        TOTAL = "total"
        TOTAL_INCREASING = "total_increasing"

    module("homeassistant", __path__=[])
    module("homeassistant.components", __path__=[])
    module("homeassistant.helpers", __path__=[])
    module(
        "homeassistant.components.sensor",
        SensorDeviceClass=DeviceClass,
        SensorStateClass=StateClass,
        SensorEntity=type("SensorEntity", (), {}),
    )
    module("homeassistant.config_entries", ConfigEntry=object)
    module(
        "homeassistant.const",
        EntityCategory=types.SimpleNamespace(DIAGNOSTIC="diagnostic"),
        UnitOfEnergy=types.SimpleNamespace(KILO_WATT_HOUR="kWh"),
        UnitOfVolume=types.SimpleNamespace(CUBIC_METERS="m³"),
    )
    module("homeassistant.core", HomeAssistant=FakeHass)
    module(
        "homeassistant.exceptions",
        ConfigEntryAuthFailed=type("ConfigEntryAuthFailed", (Exception,), {}),
    )
    module("homeassistant.helpers.storage", Store=FakeStore)
    module("homeassistant.helpers.device_registry", DeviceInfo=dict)
    module(
        "homeassistant.helpers.entity_platform", AddConfigEntryEntitiesCallback=object
    )
    module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=FakeCoordinator,
        CoordinatorEntity=FakeCoordinatorEntity,
        UpdateFailed=type("UpdateFailed", (Exception,), {}),
    )
    dt = module("homeassistant.util.dt", now=lambda: NOW)
    module("homeassistant.util", dt=dt)
    package = "_smartev_water_tests"
    module(package, __path__=[str(SOURCE)])
    stats = module(
        f"{package}.energy_statistics", async_publish_completed_day_statistics=Mock()
    )
    with patch.dict(sys.modules, modules):
        imported = {
            name: importlib.import_module(f"{package}.{name}")
            for name in ("meters", "client", "coordinator", "sensor")
        }
    imported["statistics"] = stats
    imported["ha_modules"] = modules
    return imported


MODULES = load_modules()
meters = MODULES["meters"]
client_module = MODULES["client"]
coordinator_module = MODULES["coordinator"]
sensor_module = MODULES["sensor"]


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def coordinator(building=None, water=None):
    api = Mock(spec=client_module.SmartEVClient)
    api.get_flat_info.side_effect = lambda **_kwargs: fixture("flat_chart.json")
    api.get_live_flat_info.return_value = client_module._validate_live_flat_info(
        building or fixture("building_meters_new.json"), 200
    )
    api.get_water_heating_state.return_value = water or fixture("water_heating.json")
    api.get_jom_pv_data.return_value = None
    with patch.dict(sys.modules, MODULES["ha_modules"]):
        result = coordinator_module.SmartEVCoordinator(
            FakeHass(), api, "test-entry", 200
        )
    return result


def refresh(result):
    data, *_ = result._get_consumption_data(2026, 10, NOW.date(), False, False)
    result.data = data
    return data


class MeterCollectionTests(unittest.TestCase):
    def test_old_single_meter_and_new_mixed_collection(self):
        for filename, expected_count in (
            ("building_meters_old.json", 1),
            ("building_meters_new.json", 4),
        ):
            with self.subTest(filename=filename):
                flat = client_module._validate_live_flat_info(fixture(filename), 200)
                self.assertEqual(len(flat["meters"]), expected_count)
                self.assertEqual(meters.electricity_meter(flat["meters"])["id"], 13)

    def test_reordered_collection_and_unknown_type_keep_electricity(self):
        building = fixture("building_meters_new.json")
        flat = next(iter(building["flats"]))
        flat["meters"].reverse()
        flat["meters"].insert(0, {"type": 99, "id": "unknown", "value1": "NaN"})
        with self.assertLogs(meters._LOGGER, level="DEBUG") as log:
            data = refresh(coordinator(building))
        self.assertIn(
            "unsupported SmartEV apartment meter type 99", " ".join(log.output)
        )
        self.assertEqual(data["electricityMeter"]["id"], 13)
        self.assertEqual(data["electricityMeter"]["unit"], "kWh")
        self.assertEqual(
            set(data["onlineChannels"]), {"cold_water", "hot_water", "heating_rtn"}
        )

    def test_chart_accepts_additional_meter_types(self):
        chart = fixture("flat_chart.json")
        chart["meters"].extend(
            next(iter(fixture("building_meters_new.json")["flats"]))["meters"][-3:]
        )
        client_module._validate_flat_info(chart)
        self.assertEqual(
            coordinator_module.SmartEVCoordinator._period_value(chart, 2026),
            0.7919921875,
        )

    def test_legacy_null_electricity_type(self):
        flat = client_module._validate_live_flat_info(
            fixture("building_meters_old.json"), 200
        )
        for item in flat["meters"]:
            item["type"] = None
        self.assertEqual(meters.electricity_meter(flat["meters"])["id"], 13)

    def test_missing_and_invalid_optional_timestamps_do_not_break_electricity(self):
        building = fixture("building_meters_new.json")
        for item in next(iter(building["flats"]))["meters"]:
            if item["type"] in (3, 4, 5):
                item["dt"] = "NaN"
        data = refresh(coordinator(building))
        self.assertEqual(data["electricityMeter"]["id"], 13)
        self.assertTrue(
            all(
                channel["last_reading"] is None
                for channel in data["onlineChannels"].values()
            )
        )

    def test_invalid_list_and_duplicate_apartment_are_rejected(self):
        building = fixture("building_meters_new.json")
        building["flats"].append(deepcopy(next(iter(building["flats"]))))
        with self.assertRaises(client_module.SmartEVResponseError):
            client_module._validate_live_flat_info(building, 200)
        with self.assertRaises(client_module.SmartEVResponseError):
            client_module._validate_flat_info(
                {"buildingName": "Test", "number": 1, "meters": {}}
            )

    def test_multiple_electricity_records_require_identity(self):
        records = [{"type": 0, "id": 13}, {"type": 0, "id": 14}]
        self.assertEqual(meters.electricity_meter(records, 13)["id"], 13)
        with self.assertRaises(ValueError):
            meters.electricity_meter(records)

    def test_optional_multiple_records_do_not_invent_aggregate_timestamp(self):
        grouped = {
            5: [
                {"id": -1, "type": 5, "dt": 1790884813},
                {"id": -1, "type": 5, "dt": 1790884800},
            ]
        }
        channels = meters.online_channels(grouped, fixture("water_heating.json"))
        self.assertEqual(channels["heating_rtn"]["value"], 0)
        self.assertIsNone(channels["heating_rtn"]["last_reading"])


class WaterClientTests(unittest.TestCase):
    def test_exact_dashboard_context_and_original_flat_name(self):
        api = client_module.SmartEVClient("unused@example.invalid", "unused", 200)
        with patch.object(
            api, "_get_json", return_value=fixture("water_heating.json")
        ) as get:
            result = api.get_water_heating_state(
                jom_id=2304501, building_id=10, flat_name=" Test apartment "
            )
        get.assert_called_once_with(
            "/data/waterHeatingMetersState.php",
            action="getWaterHeatingMetersStateData",
            flatId=200,
            jomId=2304501,
            buildingId=10,
            flatName=" Test apartment ",
        )
        self.assertEqual(
            result["currentMetersStateData"], {"RTN": 0, "SV": 83, "TUV": 7}
        )
        api.close()

    def test_incomplete_context_does_not_send_guessed_parameters(self):
        api = client_module.SmartEVClient("unused@example.invalid", "unused", 200)
        with (
            patch.object(api, "_get_json") as get,
            self.assertRaises(client_module.SmartEVResponseError),
        ):
            api.get_water_heating_state(jom_id=None, building_id=10, flat_name="Test")
        get.assert_not_called()
        api.close()

    def test_malformed_payload_is_rejected(self):
        api = client_module.SmartEVClient("unused@example.invalid", "unused", 200)
        for payload in (None, [], {}, {"currentMetersStateData": []}):
            with (
                self.subTest(payload=payload),
                patch.object(api, "_get_json", return_value=payload),
                self.assertRaises(client_module.SmartEVResponseError),
            ):
                api.get_water_heating_state(
                    jom_id=2304501, building_id=10, flat_name="Test"
                )
        api.close()


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    def test_http_request_budget_with_real_client_and_cached_topology(self):
        for supported, expected in (((0,), 5), ((0, 3, 4), 6), ((0, 3, 4, 5), 6)):
            with self.subTest(supported=supported):
                building = fixture("building_meters_new.json")
                building["flats"][0]["meters"] = [
                    item for item in building["flats"][0]["meters"]
                    if item["type"] in supported
                ]
                result = coordinator(building)
                api = client_module.SmartEVClient("unused@example.invalid", "unused", 200)
                api._jom_id = 2304501
                payloads = {
                    "/data/flatMetersChart.php": fixture("flat_chart.json"),
                    "/data/buildingFlatsMeters.php": building,
                    "/data/jomMetersChart.php": {"id": 2304501, "meters": []},
                    "/data/waterHeatingMetersState.php": fixture("water_heating.json"),
                }

                def response(url, **_kwargs):
                    reply = Mock()
                    reply.url = url
                    reply.headers = {"Content-Type": "application/json"}
                    reply.json.return_value = deepcopy(payloads[url.removeprefix(api.BASE_URL)])
                    return reply

                with (
                    patch.object(api.session, "get", side_effect=response) as get,
                    patch.object(api.session, "post") as post,
                ):
                    result.client = api
                    refresh(result)
                    self.assertEqual(get.call_count, expected)
                    refresh(result)
                    self.assertEqual(get.call_count, 2 * expected)
                    post.assert_not_called()
                api.close()

    def test_routine_request_budget_for_supported_installations(self):
        for supported, expected_channels, expected_calls in (
            ((0,), set(), 5),
            ((0, 3, 4), {"cold_water", "hot_water"}, 6),
            ((0, 3, 4, 5), {"cold_water", "hot_water", "heating_rtn"}, 6),
            ((0, 99), set(), 5),
        ):
            with self.subTest(supported=supported):
                building = fixture("building_meters_new.json")
                records = building["flats"][0]["meters"]
                building["flats"][0]["meters"] = [
                    item for item in records if item["type"] in supported
                ]
                if 99 in supported:
                    building["flats"][0]["meters"].append({"type": 99})
                result = coordinator(building)
                data = refresh(result)
                self.assertEqual(set(data["onlineChannels"]), expected_channels)
                self.assertEqual(len(result.client.method_calls), expected_calls)
                self.assertEqual(result.client.get_flat_info.call_count, 3)
                result.client.login.assert_not_called()
                result.client.get_production_report.assert_not_called()

    def test_missing_water_endpoint_preserves_electrical_refresh_budget(self):
        result = coordinator()
        response = requests.Response()
        response.status_code = 404
        result.client.get_water_heating_state.side_effect = requests.HTTPError(
            response=response
        )
        data = refresh(result)
        self.assertEqual(data["electricityMeter"]["id"], 13)
        self.assertEqual(len(result.client.method_calls), 6)
        self.assertTrue(all(v["value"] is None for v in data["onlineChannels"].values()))
        result.client.login.assert_not_called()

    def test_history_reuses_current_month_report(self):
        result = coordinator()
        result.client.get_production_report.return_value = {
            "pv": {"total": 1, "daily": {"2026-10-01": 1}},
            "grid": {"total": 2, "daily": {"2026-10-01": 2}},
        }
        result._get_consumption_data(2026, 10, NOW.date(), True, True)
        self.assertEqual(result.client.get_production_report.call_count, 10)
        self.assertEqual(len(result.client.method_calls), 16)
        self.assertFalse(result._daily_report_due(NOW))
        self.assertFalse(result._history_refresh_due(NOW))

    def test_values_use_current_summary_not_building_or_period_fields(self):
        summary = fixture("water_heating.json")
        summary["currentMetersStateData"] = {"SV": 5000, "TUV": 12000, "RTN": 42}
        channels = refresh(coordinator(water=summary))["onlineChannels"]
        self.assertEqual(channels["cold_water"]["value"], 5)
        self.assertEqual(channels["hot_water"]["value"], 12)
        self.assertEqual(channels["heating_rtn"]["value"], 42)

    def test_additional_electric_meter_cannot_replace_chart_identity(self):
        building = fixture("building_meters_new.json")
        records = next(iter(building["flats"]))["meters"]
        records.insert(0, {"id": 99, "type": 0, "value1": 900, "dt": 1790884813})
        self.assertEqual(refresh(coordinator(building))["electricityMeter"]["id"], 13)
        for item in records:
            if item["id"] == 13:
                item["id"] = 14
        data = refresh(coordinator(building))
        self.assertIsNone(data["electricityMeter"])
        self.assertEqual(data["onlineChannels"]["cold_water"]["value"], 0.083)

    def test_current_state_conversion_and_rtn_zero(self):
        result = coordinator()
        data = refresh(result)
        channels = data["onlineChannels"]
        self.assertEqual(channels["cold_water"]["value"], 0.083)
        self.assertEqual(channels["hot_water"]["value"], 0.007)
        self.assertEqual(channels["heating_rtn"]["value"], 0)
        self.assertNotEqual(channels["heating_rtn"]["value"], 698)
        self.assertEqual(
            channels["cold_water"]["last_reading"],
            datetime.fromtimestamp(1790883965, UTC),
        )
        result.client.get_water_heating_state.assert_called_once_with(
            jom_id=2304501, building_id=10, flat_name="Test apartment"
        )
        result.client.get_live_flat_info.assert_called_once_with(10)

    def test_electricity_only_skips_optional_request_and_entities(self):
        result = coordinator(fixture("building_meters_old.json"))
        data = refresh(result)
        self.assertEqual(data["onlineChannels"], {})
        result.client.get_water_heating_state.assert_not_called()

    def test_partial_channels_and_missing_values(self):
        building = fixture("building_meters_new.json")
        flat = next(iter(building["flats"]))
        flat["meters"] = [item for item in flat["meters"] if item["type"] in (0, 3)]
        data = refresh(coordinator(building, {"currentMetersStateData": {"SV": 0}}))
        self.assertEqual(set(data["onlineChannels"]), {"cold_water"})
        self.assertEqual(data["onlineChannels"]["cold_water"]["value"], 0)
        result = coordinator(water={"currentMetersStateData": {"SV": 83}})
        data = refresh(result)
        self.assertIsNone(data["onlineChannels"]["hot_water"]["value"])
        self.assertIsNone(data["onlineChannels"]["heating_rtn"]["value"])

    def test_water_failure_clears_values_but_preserves_source_timestamp(self):
        result = coordinator()
        refresh(result)
        for error in (
            requests.Timeout(),
            requests.HTTPError(),
            client_module.SmartEVResponseError(),
            client_module.SmartEVAuthenticationError(),
        ):
            with self.subTest(error=type(error).__name__):
                result.client.get_water_heating_state.side_effect = error
                data = refresh(result)
                self.assertEqual(data["electricityMeter"]["id"], 13)
                self.assertIsNone(data["onlineChannels"]["cold_water"]["value"])
                self.assertIsNotNone(
                    data["onlineChannels"]["cold_water"]["last_reading"]
                )
        result.client.get_water_heating_state.side_effect = None
        self.assertEqual(
            refresh(result)["onlineChannels"]["cold_water"]["value"], 0.083
        )

    async def test_optional_failure_does_not_fail_whole_async_refresh(self):
        result = coordinator()
        result._official_year_grid = {"2026-10-01": 1.0}
        result._last_history_refresh = NOW
        result._last_daily_report_refresh = NOW
        result.client.get_water_heating_state.side_effect = requests.Timeout()
        with patch.object(
            coordinator_module, "async_publish_completed_day_statistics"
        ) as publish:
            data = await result._async_update_data()
        self.assertEqual(data["electricityMeter"]["id"], 13)
        self.assertIsNone(data["onlineChannels"]["cold_water"]["value"])
        self.assertEqual(data["gridAccounting"]["total"], 1.0)
        publish.assert_called_once()

    def test_water_only_does_not_require_electricity_or_energy_reports(self):
        building = fixture("building_meters_new.json")
        flat = next(iter(building["flats"]))
        flat["meters"] = [item for item in flat["meters"] if item["type"] != 0]
        result = coordinator(building)
        chart = fixture("flat_chart.json")
        chart["meters"] = []
        result.client.get_flat_info.side_effect = None
        result.client.get_flat_info.return_value = chart
        data = refresh(result)
        self.assertIsNone(data["electricityMeter"])
        self.assertEqual(data["onlineChannels"]["cold_water"]["value"], 0.083)
        result.client.get_production_report.assert_not_called()
        result.client.get_jom_pv_data.assert_not_called()

    def test_invalid_values_make_only_affected_channel_unavailable(self):
        for invalid in (None, True, "NaN", float("nan"), float("inf"), "83"):
            with self.subTest(value=invalid):
                result = coordinator(
                    water={
                        "currentMetersStateData": {"SV": invalid, "TUV": 7, "RTN": 0}
                    }
                )
                channels = refresh(result)["onlineChannels"]
                self.assertIsNone(channels["cold_water"]["value"])
                self.assertEqual(channels["hot_water"]["value"], 0.007)


class SensorTests(unittest.IsolatedAsyncioTestCase):
    async def test_timestamp_discovered_on_later_refresh(self):
        building = fixture("building_meters_new.json")
        for record in next(iter(building["flats"]))["meters"]:
            if record["type"] in (3, 4, 5):
                record["dt"] = None
        result = coordinator(building)
        refresh(result)
        entities, _ = await self.entities(result)
        self.assertEqual(len(entities), 15)
        result.client.get_live_flat_info.return_value = (
            client_module._validate_live_flat_info(
                fixture("building_meters_new.json"), 200
            )
        )
        refresh(result)
        for listener in result.listeners:
            listener()
        self.assertEqual(len(entities), 18)

    async def entities(self, result):
        collected = []
        entry = types.SimpleNamespace(
            runtime_data=result, data={"flat_id": 200}, async_on_unload=Mock()
        )
        await sensor_module.async_setup_entry(result.hass, entry, collected.extend)
        return collected, entry

    async def test_electrical_unique_ids_are_unchanged(self):
        expected = {
            "meter_13_energy",
            "meter_13_current_year_consumption",
            "meter_13_current_month_consumption",
            "meter_13_today_consumption",
            "meter_13_current_month_production",
            "meter_13_latest_daily_production",
            "meter_13_estimated_pv_production",
            "meter_13_estimated_pv_energy_total",
            "meter_13_current_month_grid_energy",
            "meter_13_today_grid_energy",
            "meter_13_total_grid_energy",
            "meter_13_last_reading",
        }
        for name in ("building_meters_old.json", "building_meters_new.json"):
            with self.subTest(name=name):
                result = coordinator(fixture(name))
                refresh(result)
                entities, _ = await self.entities(result)
                electrical = {
                    e._attr_unique_id
                    for e in entities
                    if e._attr_unique_id.startswith("meter_")
                }
                self.assertEqual(electrical, expected)
                for entity in entities:
                    if entity._attr_unique_id == "meter_13_energy":
                        self.assertEqual(
                            entity.native_value,
                            result.data["electricityMeter"]["value1"],
                        )
                        self.assertEqual(
                            entity._attr_device_info["identifiers"],
                            {("smartev", "meter_13")},
                        )

    async def test_online_sensor_metadata_and_timezone_aware_timestamps(self):
        result = coordinator()
        refresh(result)
        entities, _ = await self.entities(result)
        online = {
            e._attr_unique_id: e
            for e in entities
            if e._attr_unique_id.startswith("flat_")
        }
        self.assertEqual(len(online), 6)
        for key, value in (
            ("cold_water", 0.083),
            ("hot_water", 0.007),
            ("heating_rtn", 0),
        ):
            entity = online[f"flat_200_{key}"]
            self.assertEqual(entity.native_value, value)
            self.assertTrue(entity.available)
            self.assertIsNone(entity._attr_state_class)
            self.assertEqual(
                entity._attr_device_class, None if key == "heating_rtn" else "water"
            )
            self.assertEqual(
                entity._attr_native_unit_of_measurement,
                "dílky" if key == "heating_rtn" else "m³",
            )
            timestamp = online[f"flat_200_{key}_last_reading"]
            self.assertEqual(timestamp._attr_device_class, "timestamp")
            self.assertIsNone(timestamp._attr_state_class)
            self.assertIsNone(timestamp._attr_native_unit_of_measurement)
            self.assertEqual(timestamp.native_value.tzinfo, UTC)

    async def test_discovery_after_failure_or_later_meter_addition_is_idempotent(self):
        result = coordinator(fixture("building_meters_old.json"))
        refresh(result)
        entities, entry = await self.entities(result)
        self.assertEqual(len(entities), 12)
        result.client.get_live_flat_info.return_value = (
            client_module._validate_live_flat_info(
                fixture("building_meters_new.json"), 200
            )
        )
        result.client.get_water_heating_state.side_effect = requests.Timeout()
        refresh(result)
        for listener in result.listeners:
            listener()
            listener()
        self.assertEqual(len(entities), 18)
        cold = next(e for e in entities if e._attr_unique_id == "flat_200_cold_water")
        stamp = next(
            e
            for e in entities
            if e._attr_unique_id == "flat_200_cold_water_last_reading"
        )
        self.assertFalse(cold.available)
        self.assertTrue(stamp.available)
        result.client.get_water_heating_state.side_effect = None
        refresh(result)
        self.assertTrue(cold.available)
        # Disappearance clears availability without destroying registry identity.
        result.client.get_live_flat_info.return_value = (
            client_module._validate_live_flat_info(
                fixture("building_meters_old.json"), 200
            )
        )
        refresh(result)
        self.assertFalse(cold.available)
        self.assertFalse(stamp.available)
        entry.async_on_unload.assert_called_once()

    async def test_water_only_setup_does_not_create_electrical_entities(self):
        result = coordinator()
        refresh(result)
        result.data["electricityMeter"] = None
        entities, _ = await self.entities(result)
        self.assertEqual(len(entities), 6)
        self.assertTrue(
            all(e._attr_unique_id.startswith("flat_200_") for e in entities)
        )


if __name__ == "__main__":
    unittest.main()
