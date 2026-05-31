#!/bin/bash
# Backup de la base de datos de InvFlow
# Uso: ./backup.sh
# Recomendado: añadir al cron del servidor (diario a las 2:00)
#   0 2 * * * /ruta/a/invflow/backup.sh

set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/invflow_$DATE.sql.gz"

mkdir -p "$BACKUP_DIR"

# Leer credenciales del .env
source .env 2>/dev/null || true
PGUSER=${POSTGRES_USER:-admin}
PGDB=${POSTGRES_DB:-invflow_db}

echo "Creando backup: $FILE"
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U "$PGUSER" "$PGDB" | gzip > "$FILE"

echo "Backup completado: $FILE ($(du -h "$FILE" | cut -f1))"

# Borrar backups de más de 30 días
find "$BACKUP_DIR" -name "invflow_*.sql.gz" -mtime +30 -delete
echo "Backups antiguos (>30 días) eliminados"
