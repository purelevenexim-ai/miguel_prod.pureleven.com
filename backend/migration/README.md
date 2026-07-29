# Source -> Miguel Migration Toolkit

This folder contains the first implementation of the migration pipeline:

1. extract_via_ssh_sqlite.sh (for shipping_label SQLite source)
2. extract_via_ssh_psql.sh (for Postgres source)
3. extract_source_data.py (SQLAlchemy-based alternative)
4. normalize_and_map.py
5. import_to_miguel.py

## 1) Extract from source DB (detected source app: shipping_label + SQLite)

```bash
bash scripts/migration/extract_via_ssh_sqlite.sh \
  --ssh-host root@172.235.6.48 \
  --sqlite-db /opt/shipping_label/shipping_label.db \
  --output /tmp/migration/raw_extract.csv \
  --date-from 2026-03-01 \
  --date-to 2026-04-30
```

## 2) Extract from source DB (Postgres variant, if needed)

```bash
bash scripts/migration/extract_via_ssh_psql.sh \
  --ssh-host root@172.235.6.48 \
  --db-container pureleven_db \
  --db-user pureleven_user \
  --db-name pureleven_db \
  --output /tmp/migration/raw_extract.csv \
  --date-from 2026-03-01 \
  --date-to 2026-04-30
```

## 3) Extract from source DB (SQLAlchemy alternative)

```bash
python scripts/migration/extract_source_data.py \
  --source-db-url "$SOURCE_DB_URL" \
  --output /tmp/migration/raw_extract.csv \
  --date-from 2026-03-01 \
  --date-to 2026-04-30
```

Notes:
- Default SQL expects a `customers` table with columns similar to the attached sample.
- Use `--sql-file` to provide a custom source SQL query.

## 4) Normalize and map products

```bash
python scripts/migration/normalize_and_map.py \
  --input /tmp/migration/raw_extract.csv \
  --normalized-output /tmp/migration/normalized_ready.csv \
  --reject-output /tmp/migration/rejects.csv \
  --mapping-report /tmp/migration/product_mapping_report.csv \
  --target-db-url "$MIGUEL_DB_URL" \
  --target-tenant-id "$MIGUEL_TENANT_ID" \
  --target-tenant-slug "$MIGUEL_TENANT_SLUG" \
  --alias-map scripts/migration/product_alias_map.csv
```

Output fields include:
- name, address, pincode, phone, payment_type, amount
- source_order_id, source_order_date, source_order_seq
- suggested_miguel_order_number
- tracking_id
- items_mapped_json
- mapping_confidence_min, mapping_unresolved_count

## 5) Import into Miguel (dry-run first)

```bash
python scripts/migration/import_to_miguel.py \
  --input /tmp/migration/normalized_ready.csv \
  --target-db-url "$MIGUEL_DB_URL" \
  --target-tenant-id "$MIGUEL_TENANT_ID" \
  --created-by-id "$MIGUEL_EMPLOYEE_ID" \
  --dry-run
```

Then execute actual import:

```bash
python scripts/migration/import_to_miguel.py \
  --input /tmp/migration/normalized_ready.csv \
  --target-db-url "$MIGUEL_DB_URL" \
  --target-tenant-id "$MIGUEL_TENANT_ID" \
  --created-by-id "$MIGUEL_EMPLOYEE_ID"
```

## Optional alias map file

Create `scripts/migration/product_alias_map.csv` with:

```csv
source_name,target_name
cardamom 100gm,Cardamom 100gm
black pepper 250,Black Pepper 250
```

## Safety notes

- Import is idempotent by searching for `SOURCE_ORDER_ID=<id>` marker in order notes.
- Rows with unresolved product mappings are skipped unless `--allow-unresolved-products` is supplied.
- Always run dry-run and inspect rejects/mapping report before live import.
