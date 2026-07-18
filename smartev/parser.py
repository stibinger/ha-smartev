from smartev.models import Meter


def parse_meter(data):

    meter = data["meters"][0]

    return Meter(
        id=meter["id"],
        total_energy=meter["value1"],
        unit=meter["unit"],
        last_update=meter["dtStr"],
        interval=meter["chartInterval"],
    )