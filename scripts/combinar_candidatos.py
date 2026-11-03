import csv
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Combina CSV de candidatos conservando cada fuente y variante.")
parser.add_argument("sources", nargs="+", type=Path)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
paths = args.sources
target = args.out
all_rows = []
fields = None
for path in paths:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if fields is None:
            fields = reader.fieldnames
        assert reader.fieldnames == fields
        all_rows.extend(reader)

target.parent.mkdir(parents=True, exist_ok=True)
with target.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(all_rows)
print(f"{len(all_rows)} rows: {target}")
