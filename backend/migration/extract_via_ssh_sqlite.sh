#!/usr/bin/env bash
set -euo pipefail

# Extract source customer/order rows from remote SQLite DB over SSH.
# Usage:
#   bash scripts/migration/extract_via_ssh_sqlite.sh \
#     --ssh-host root@172.235.6.48 \
#     --sqlite-db /opt/shipping_label/shipping_label.db \
#     --output /tmp/migration/raw_extract.csv \
#     --date-from 2026-03-01 \
#     --date-to 2026-04-30

SSH_HOST=""
SQLITE_DB=""
OUTPUT=""
DATE_FROM=""
DATE_TO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssh-host) SSH_HOST="$2"; shift 2 ;;
    --sqlite-db) SQLITE_DB="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --date-from) DATE_FROM="$2"; shift 2 ;;
    --date-to) DATE_TO="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SSH_HOST" || -z "$SQLITE_DB" || -z "$OUTPUT" ]]; then
  echo "Missing required args. Required: --ssh-host --sqlite-db --output" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

SQL="SELECT
  name,
  address,
  pincode,
  phone,
  phone_display,
  payment_type,
  amount,
  order_id,
  tracking_id,
  items,
  notes,
  _id,
  created_ts,
  printed_count
FROM customers
WHERE ('${DATE_FROM}' = '' OR substr(created_ts,1,10) >= '${DATE_FROM}')
  AND ('${DATE_TO}' = '' OR substr(created_ts,1,10) <= '${DATE_TO}')
ORDER BY created_ts ASC;"

ssh "$SSH_HOST" "sqlite3 -header -csv '$SQLITE_DB' \"$SQL\"" > "$OUTPUT"

echo "Extracted CSV: $OUTPUT"
