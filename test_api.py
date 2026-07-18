"""SmartEV API analyser."""

from pprint import pprint

from smartev.client import SmartEVClient

from test_config import EMAIL, PASSWORD, FLAT_ID

# -----------------------------------------------------
# Nastavení testu
# -----------------------------------------------------

YEAR = 2026
MONTH = 7
DAY = 16

# -----------------------------------------------------

client = SmartEVClient(
    email=EMAIL,
    password=PASSWORD,
    flat_id=FLAT_ID,
)

print("Logging in...")
client.login()
print("OK")

data = client.get_flat_info(
    year=YEAR,
    month=MONTH,
    day=DAY,
)

meter = data["meters"][0]

print()
print("=" * 70)
print("SMARTEV API ANALYSIS")
print("=" * 70)
print(f"YEAR  : {YEAR}")
print(f"MONTH : {MONTH}")
print(f"DAY   : {DAY}")
print()

print(f"value1        : {meter.get('value1')}")
print(f"value2        : {meter.get('value2')}")
print(f"type          : {meter.get('type')}")
print(f"unit          : {meter.get('unit')}")
print(f"dt            : {meter.get('dt')}")
print(f"dtStr         : {meter.get('dtStr')}")
print(f"chartInterval : {meter.get('chartInterval')}")

history = meter.get("chartData", [])

print(f"history rows  : {len(history)}")

if history:
    print()
    print("FIRST RECORD")
    pprint(history[0])

    print()
    print("LAST RECORD")
    pprint(history[-1])