"""Manual SmartEV login check."""

from smartev.client import SmartEVClient
from smartev.parser import parse_meter

from test_config import EMAIL, PASSWORD, FLAT_ID


client = SmartEVClient(
    email=EMAIL,
    password=PASSWORD,
    flat_id=FLAT_ID,
)

print("Logging in...")
client.login()
print("OK")

meter = parse_meter(client.get_flat_info())

print()
print("===== ELECTRICITY METER =====")
print(f"ID           : {meter.id}")
print(f"Reading      : {meter.total_energy:.3f} {meter.unit}")
print(f"Last update  : {meter.last_update}")
print(f"Interval     : {meter.interval}")