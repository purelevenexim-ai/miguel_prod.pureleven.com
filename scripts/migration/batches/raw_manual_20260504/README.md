# Raw Manual Batch 2026-05-04

This batch was prepared from the 4-row raw sheet shared in chat.

## Input
- raw_input.csv

## Generated outputs
- out/create_orders_api.jsonl
- out/update_tracking_upload.csv
- out/hold_rows.csv
- out/ingest_report.csv

## Current classification
- create: 1 row (Philomina Davis)
- update: 2 rows (Chandrika Ratees, Dr.B.Suresh Babu)
- hold: 1 row (Lathika sasidharan)

## Regenerate outputs
```bash
python3 scripts/migration/raw_manual_ingest.py \
  --input scripts/migration/batches/raw_manual_20260504/raw_input.csv \
  --out-dir scripts/migration/batches/raw_manual_20260504/out
```

## Execute create rows via API
```bash
export MIGUEL_API_TOKEN="<your_bearer_token>"
python3 scripts/migration/execute_create_orders_api.py \
  --input-jsonl scripts/migration/batches/raw_manual_20260504/out/create_orders_api.jsonl \
  --base-url https://prod.pureleven.com
```

Use `--dry-run` first to inspect payloads.

## Apply tracking updates
Use out/update_tracking_upload.csv in the Manual Orders India Post XLSX upload flow.
Recommended order:
1. Run preview endpoint/UI preview first.
2. Apply upload after preview matches expected rows.

## Hold row handling
out/hold_rows.csv contains rows intentionally blocked from create/update based on issue notes.
For this batch, row 4 is held because issue contains: "eppo venda ,parayam".
