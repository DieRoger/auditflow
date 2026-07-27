#!/bin/bash
# AuditFlow PostgreSQL Backup Script
# Usage: ./scripts/backup.sh [output_dir]
set -e

OUTPUT_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-auditflow}"
DB_USER="${DB_USER:-auditflow}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"

mkdir -p "$OUTPUT_DIR"

echo "Backing up $DB_NAME@$DB_HOST:$DB_PORT to $OUTPUT_DIR/auditflow_$TIMESTAMP.sql.gz"
PGPASSWORD="${DB_PASSWORD}" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --no-owner --no-acl --format=custom | gzip > "$OUTPUT_DIR/auditflow_$TIMESTAMP.sql.gz"

echo "Cleaning backups older than $RETENTION_DAYS days..."
find "$OUTPUT_DIR" -name "auditflow_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete

echo "Backup complete: $(ls -lh "$OUTPUT_DIR/auditflow_$TIMESTAMP.sql.gz" | awk '{print $5}')"
