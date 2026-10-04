import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(PROJECT_ROOT / "database"))

from traceability_store import load_traceability


records = load_traceability()

print("TRACEABILITY STORE")
print("==================")

print(f"Total records: {len(records)}")


# ---------------------------------------------------------
# Search example
# ---------------------------------------------------------

search_term = "WatchdogInterface"

matches = [
    record
    for record in records
    if record["entity"].lower() == search_term.lower()
]


print(f"\nSearch: {search_term}")
print("--------------------------")


for record in matches:

    print(
        f"Entity: {record['entity']}\n"
        f"Type:   {record['type']}\n"
        f"Page:   {record['page']}\n"
    )