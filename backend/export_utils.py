import csv
import io
import json


def export_json_bytes(payload, filename=None):
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def export_csv_bytes(rows, filename=None):
    if not rows:
        rows = [{"message": "No records available"}]
    output = io.StringIO()
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return output.getvalue().encode("utf-8")
