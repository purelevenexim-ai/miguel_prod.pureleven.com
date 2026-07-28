#!/usr/bin/env bash
set -euo pipefail

# Extract source customer/order rows from a remote host using ssh + dockerized psql.
# Usage:
#   bash scripts/migration/extract_via_ssh_psql.sh \
#     --ssh-host root@172.235.6.48 \
#     --db-container pureleven_db \
#     --db-user pureleven_user \
#     --db-name pureleven_db \
#     --output /tmp/migration/raw_extract.csv

SSH_HOST=""
DB_CONTAINER=""
DB_USER=""
DB_NAME=""
OUTPUT=""
DATE_FROM=""
DATE_TO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssh-host) SSH_HOST="$2"; shift 2 ;;
    --db-container) DB_CONTAINER="$2"; shift 2 ;;
    --db-user) DB_USER="$2"; shift 2 ;;
    --db-name) DB_NAME="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --date-from) DATE_FROM="$2"; shift 2 ;;
    --date-to) DATE_TO="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SSH_HOST" || -z "$DB_CONTAINER" || -z "$DB_USER" || -z "$DB_NAME" || -z "$OUTPUT" ]]; then
  echo "Missing required args. Required: --ssh-host --db-container --db-user --db-name --output" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

SQL="COPY (
SELECT
  c.name,
  c.address,
  c.pincode,
  c.phone,
  c.phone_display,
  c.payment_type,
  c.amount,
  c.order_id,
  c.tracking_id,
  c.items,
  c.notes,
  c._id,
  c.created_ts,
  c.printed_count
FROM customers c
WHERE ('${DATE_FROM}' = '' OR c.created_ts::date >= '${DATE_FROM}'::date)
  AND ('${DATE_TO}' = '' OR c.created_ts::date <= '${DATE_TO}'::date)
ORDER BY c.created_ts ASC
) TO STDOUT WITH CSV HEADER"

ssh "$SSH_HOST" "docker exec -i '$DB_CONTAINER' psql -U '$DB_USER' -d '$DB_NAME' -c \"$SQL\"" > "$OUTPUT"

echo "Extracted CSV: $OUTPUT"
