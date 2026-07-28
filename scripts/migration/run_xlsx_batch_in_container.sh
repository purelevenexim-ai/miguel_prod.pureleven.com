#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run_xlsx_batch_in_container.sh \
    --batch-tag <tag> \
    --input <file1.xlsx> [--input <file2.xlsx> ...] \
    [--tenant-id <uuid>] \
    [--tenant-slug <slug>] \
    [--created-by-id <uuid>] \
    [--db-url <sqlalchemy_url>] \
    [--alias-map <path>] \
    [--dry-run-only]

Notes:
- XLSX files must exist on the server filesystem.
- This script runs extraction/normalization/import inside container: pureleven_backend.
- Unknown item names and missing-phone rows are exported as review files.
- Rows with unresolved item mappings are held for follow-up; fully resolved rows continue to import.
USAGE
}

BATCH_TAG=""
INPUT_FILES=()
TENANT_ID="4374ad45-76b5-405b-8a3d-de49710fbdc3"
TENANT_SLUG="pureleven"
CREATED_BY_ID="8f65eba5-ba5f-43c2-8c31-7614595b2600"
DB_URL="postgresql+psycopg2://pureleven_user:pureleven_password@pureleven_db:5432/pureleven_db"
ALIAS_MAP="/opt/pureleven/scripts/migration/product_alias_map_xlsx_batch.csv"
DRY_RUN_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch-tag)
      BATCH_TAG="$2"
      shift 2
      ;;
    --input)
      INPUT_FILES+=("$2")
      shift 2
      ;;
    --tenant-id)
      TENANT_ID="$2"
      shift 2
      ;;
    --tenant-slug)
      TENANT_SLUG="$2"
      shift 2
      ;;
    --created-by-id)
      CREATED_BY_ID="$2"
      shift 2
      ;;
    --db-url)
      DB_URL="$2"
      shift 2
      ;;
    --alias-map)
      ALIAS_MAP="$2"
      shift 2
      ;;
    --dry-run-only)
      DRY_RUN_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$BATCH_TAG" ]]; then
  echo "--batch-tag is required" >&2
  usage
  exit 1
fi

if [[ ${#INPUT_FILES[@]} -eq 0 ]]; then
  echo "At least one --input is required" >&2
  usage
  exit 1
fi

for f in "${INPUT_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Input XLSX not found: $f" >&2
    exit 1
  fi
done

if [[ ! -f "$ALIAS_MAP" ]]; then
  echo "Alias map not found: $ALIAS_MAP" >&2
  exit 1
fi

BASE_DIR="/opt/pureleven/scripts/migration"
BATCH_DIR="$BASE_DIR/batches/$BATCH_TAG"
mkdir -p "$BATCH_DIR"

CONTAINER="pureleven_backend"
DB_CONTAINER="pureleven_db"
C_INPUT_DIR="/tmp/xlsx_inputs/$BATCH_TAG"
C_OUT_DIR="/tmp/xlsx_batch/$BATCH_TAG"

echo "[1/8] Syncing migration scripts to container"
docker cp "$BASE_DIR/common.py" "$CONTAINER:/app/migration/common.py"
docker cp "$BASE_DIR/extract_xlsx_data.py" "$CONTAINER:/app/migration/extract_xlsx_data.py"
docker cp "$BASE_DIR/normalize_and_map.py" "$CONTAINER:/app/migration/normalize_and_map.py"
docker cp "$BASE_DIR/import_to_miguel.py" "$CONTAINER:/app/migration/import_to_miguel.py"
docker cp "$ALIAS_MAP" "$CONTAINER:/app/migration/product_alias_map_xlsx_batch.csv"

echo "[2/9] Copying XLSX files into container"
docker exec -i "$CONTAINER" mkdir -p "$C_INPUT_DIR" "$C_OUT_DIR"
SAFE_INPUTS=()
for src in "${INPUT_FILES[@]}"; do
  bn="$(basename "$src")"
  safe_bn="${bn// /_}"
  docker cp "$src" "$CONTAINER:$C_INPUT_DIR/$safe_bn"
  SAFE_INPUTS+=("$C_INPUT_DIR/$safe_bn")
  echo "  - $src -> $C_INPUT_DIR/$safe_bn"
done

INPUT_ARGS=()
for f in "${SAFE_INPUTS[@]}"; do
  INPUT_ARGS+=(--input "$f")
done

echo "[3/9] Extracting XLSX rows"
docker exec -i "$CONTAINER" python3 /app/migration/extract_xlsx_data.py \
  "${INPUT_ARGS[@]}" \
  --output "$C_OUT_DIR/raw_extract_xlsx.csv" \
  --unknown-items-output "$C_OUT_DIR/unknown_items_xlsx.csv" \
  --batch-tag "$BATCH_TAG"

echo "[4/9] Normalizing and product mapping"
docker exec -i "$CONTAINER" python3 /app/migration/normalize_and_map.py \
  --input "$C_OUT_DIR/raw_extract_xlsx.csv" \
  --normalized-output "$C_OUT_DIR/normalized_ready.csv" \
  --reject-output "$C_OUT_DIR/rejects.csv" \
  --mapping-report "$C_OUT_DIR/product_mapping_report.csv" \
  --pending-translation-output "$C_OUT_DIR/pending_translation.csv" \
  --target-db-url "$DB_URL" \
  --target-tenant-id "$TENANT_ID" \
  --target-tenant-slug "$TENANT_SLUG" \
  --alias-map /app/migration/product_alias_map_xlsx_batch.csv

echo "[5/9] Copying artifacts back to host"
docker cp "$CONTAINER:$C_OUT_DIR/raw_extract_xlsx.csv" "$BATCH_DIR/raw_extract_xlsx.csv"
docker cp "$CONTAINER:$C_OUT_DIR/normalized_ready.csv" "$BATCH_DIR/normalized_ready.csv"
docker cp "$CONTAINER:$C_OUT_DIR/rejects.csv" "$BATCH_DIR/rejects.csv"
docker cp "$CONTAINER:$C_OUT_DIR/product_mapping_report.csv" "$BATCH_DIR/product_mapping_report.csv"
docker cp "$CONTAINER:$C_OUT_DIR/pending_translation.csv" "$BATCH_DIR/pending_translation.csv"
docker cp "$CONTAINER:$C_OUT_DIR/unknown_items_xlsx.csv" "$BATCH_DIR/unknown_items_xlsx.csv"

echo "[6/9] Splitting normalized rows (importable vs held unresolved)"
python3 - <<PY > "$BATCH_DIR/split_counts.txt"
import csv
from pathlib import Path

batch = Path('$BATCH_DIR')
src = batch / 'normalized_ready.csv'
resolved = batch / 'normalized_ready_importable.csv'
held = batch / 'normalized_held_unresolved.csv'

with src.open('r', encoding='utf-8', newline='') as f:
  reader = csv.DictReader(f)
  fieldnames = reader.fieldnames or []
  rows = list(reader)

resolved_rows = [r for r in rows if int(r.get('mapping_unresolved_count') or 0) == 0]
held_rows = [r for r in rows if int(r.get('mapping_unresolved_count') or 0) > 0]

if fieldnames:
  with resolved.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(resolved_rows)

  with held.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(held_rows)
else:
  resolved.write_text('', encoding='utf-8')
  held.write_text('', encoding='utf-8')

print(f"{len(rows)} {len(resolved_rows)} {len(held_rows)}")
PY

read -r NORMALIZED_COUNT RESOLVED_COUNT HELD_COUNT < "$BATCH_DIR/split_counts.txt"
echo "Normalized rows total: $NORMALIZED_COUNT"
echo "Importable rows (resolved): $RESOLVED_COUNT"
echo "Held rows (unresolved mappings): $HELD_COUNT"

docker cp "$BATCH_DIR/normalized_ready_importable.csv" "$CONTAINER:$C_OUT_DIR/normalized_ready_importable.csv"

PENDING_COUNT=$(python3 - <<PY
import csv
from pathlib import Path
p=Path('$BATCH_DIR/pending_translation.csv')
rows=list(csv.DictReader(p.open('r',encoding='utf-8',newline='')))
print(len(rows))
PY
)
REJECT_COUNT=$(python3 - <<PY
import csv
from pathlib import Path
p=Path('$BATCH_DIR/rejects.csv')
rows=list(csv.DictReader(p.open('r',encoding='utf-8',newline='')))
print(len(rows))
PY
)

echo "Pending translation rows: $PENDING_COUNT"
echo "Rejected rows: $REJECT_COUNT"
echo "Review pending translations: $BATCH_DIR/pending_translation.csv"
echo "Held unresolved rows:      $BATCH_DIR/normalized_held_unresolved.csv"

if [[ "$RESOLVED_COUNT" -eq 0 ]]; then
  echo "[STOP] No fully resolved rows available for import in this pass."
  echo "Provide mappings and rerun after updating alias map: $ALIAS_MAP"
  exit 0
fi

echo "[7/9] Dry-run import (resolved rows only)"
docker exec -i "$CONTAINER" python3 /app/migration/import_to_miguel.py \
  --input "$C_OUT_DIR/normalized_ready_importable.csv" \
  --target-db-url "$DB_URL" \
  --target-tenant-id "$TENANT_ID" \
  --created-by-id "$CREATED_BY_ID" \
  --dry-run | tee "$BATCH_DIR/dry_run_summary.txt"

if [[ "$DRY_RUN_ONLY" -eq 1 ]]; then
  echo "Dry-run only requested. Stopping before live import."
  exit 0
fi

echo "[8/9] Live import (resolved rows only)"
docker exec -i "$CONTAINER" python3 /app/migration/import_to_miguel.py \
  --input "$C_OUT_DIR/normalized_ready_importable.csv" \
  --target-db-url "$DB_URL" \
  --target-tenant-id "$TENANT_ID" \
  --created-by-id "$CREATED_BY_ID" | tee "$BATCH_DIR/import_summary.txt"

echo "[9/9] Post-import finalize (Delivered+Paid, historical dates, printed_count)"
docker cp "$BATCH_DIR/raw_extract_xlsx.csv" "$DB_CONTAINER:/tmp/raw_extract_xlsx.csv"

docker exec -i "$DB_CONTAINER" psql -h localhost -U pureleven_user -d pureleven_db <<SQL
BEGIN;

UPDATE orders
SET status='delivered'::orderstatus,
    payment_status='paid'::paymentstatus,
    updated_at=NOW()
WHERE tenant_id=CAST('$TENANT_ID' AS UUID)
  AND notes LIKE '%BATCH_TAG=$BATCH_TAG%';

WITH target AS (
  SELECT id, order_number, created_at,
         substring(notes from 'SOURCE_ORDER_ID=([^| ]+)') AS source_order_id,
         substring(notes from 'SOURCE_CREATED_TS=([^| ]+)') AS source_created_ts
  FROM orders
  WHERE tenant_id=CAST('$TENANT_ID' AS UUID)
    AND notes LIKE '%BATCH_TAG=$BATCH_TAG%'
), dated AS (
  SELECT id,
         COALESCE(
           CASE
             WHEN source_order_id ~ '^[A-Za-z]{2,5}_\\d{8,}$' THEN
               to_timestamp(
                 '20' || substring(source_order_id from '^[A-Za-z]{2,5}_(\\d{2})') || '-' ||
                 substring(source_order_id from '^[A-Za-z]{2,5}_\\d{2}(\\d{2})') || '-' ||
                 substring(source_order_id from '^[A-Za-z]{2,5}_\\d{4}(\\d{2})') || ' 00:00:00',
                 'YYYY-MM-DD HH24:MI:SS'
               )
             ELSE NULL
           END,
           CASE
             WHEN source_created_ts IS NOT NULL AND source_created_ts <> ''
             THEN replace(source_created_ts, 'Z', '+00:00')::timestamptz
             ELSE NULL
           END,
           created_at
         ) AS base_ts,
         row_number() OVER (ORDER BY order_number) AS rn
  FROM target
)
UPDATE orders o
SET created_at = d.base_ts + (d.rn * interval '20 seconds'),
    updated_at = NOW()
FROM dated d
WHERE o.id = d.id;

CREATE TEMP TABLE tmp_printed_count_map (
  order_id text PRIMARY KEY,
  printed_count integer NOT NULL
);
\copy tmp_printed_count_map(order_id, printed_count) FROM '/tmp/raw_extract_xlsx.csv' WITH (FORMAT csv, HEADER true);

UPDATE orders o
SET printed_count = t.printed_count,
    updated_at = NOW()
FROM tmp_printed_count_map t
WHERE o.tenant_id=CAST('$TENANT_ID' AS UUID)
  AND o.notes LIKE '%BATCH_TAG=$BATCH_TAG%'
  AND substring(o.notes from 'SOURCE_ORDER_ID=([^| ]+)') = t.order_id;

COMMIT;
SQL

echo "Done. Batch artifacts: $BATCH_DIR"
