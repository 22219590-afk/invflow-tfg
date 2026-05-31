#!/bin/bash
# ══════════════════════════════════════════════════════════════════
#  InvFlow — Script de despliegue en producción
#  Uso: ./deploy.sh [DOMINIO]
#  Ejemplo: ./deploy.sh app.miempresa.com
# ══════════════════════════════════════════════════════════════════

set -e

DOMAIN=${1:-""}
COMPOSE="docker compose -f docker-compose.prod.yml"

# ── Colores para output ────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── 1. Verificaciones previas ──────────────────────────────────────
info "Verificando requisitos..."

command -v docker >/dev/null 2>&1 || error "Docker no está instalado"
docker compose version >/dev/null 2>&1 || error "Docker Compose v2 no está instalado"

[ -f ".env" ] || error "Falta el archivo .env — copia .env.example y rellénalo"

# Advertir si JWT_SECRET_KEY sigue siendo el valor por defecto
if grep -q "CAMBIA_ESTO" .env; then
    error "El archivo .env todavía tiene valores por defecto. Edítalo antes de continuar."
fi

# ── 2. Configurar HTTPS (si se proporciona dominio) ────────────────
if [ -n "$DOMAIN" ]; then
    info "Configurando HTTPS para el dominio: $DOMAIN"

    # Reemplazar DOMINIO_AQUI en nginx.prod.conf
    sed -i "s/DOMINIO_AQUI/$DOMAIN/g" nginx/nginx.prod.conf

    # Obtener certificado SSL con Let's Encrypt
    if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        info "Obteniendo certificado SSL..."
        # Levantar nginx en modo HTTP para validación
        $COMPOSE up -d nginx certbot
        docker run --rm \
            -v /etc/letsencrypt:/etc/letsencrypt \
            -v certbot-webroot:/var/www/certbot \
            certbot/certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email "admin@$DOMAIN" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN"
        info "Certificado SSL obtenido correctamente"
    else
        info "Certificado SSL ya existe, omitiendo"
    fi

    # Actualizar CORS_ORIGINS en .env si no está ya configurado para este dominio
    if ! grep -q "$DOMAIN" .env; then
        warn "Recuerda añadir 'https://$DOMAIN' a CORS_ORIGINS en tu .env"
    fi
else
    warn "No se proporcionó dominio. Desplegando sin HTTPS (solo HTTP en puerto 80)."
    warn "Para HTTPS ejecuta: ./deploy.sh tu-dominio.com"
    # Usar la config HTTP simple en lugar de la HTTPS
    sed -i 's|nginx/nginx.prod.conf|nginx/default.conf|' docker-compose.prod.yml 2>/dev/null || true
fi

# ── 3. Construir imágenes ──────────────────────────────────────────
info "Construyendo imágenes Docker..."
$COMPOSE build --no-cache

# ── 4. Levantar servicios ──────────────────────────────────────────
info "Iniciando servicios..."
$COMPOSE up -d

# ── 5. Verificar que todo arrancó ─────────────────────────────────
info "Esperando que el backend esté listo..."
MAX_WAIT=60
WAITED=0
until docker compose -f docker-compose.prod.yml exec -T backend curl -sf http://localhost:8000/health >/dev/null 2>&1; do
    sleep 3
    WAITED=$((WAITED + 3))
    if [ $WAITED -ge $MAX_WAIT ]; then
        error "El backend no arrancó en ${MAX_WAIT}s. Revisa los logs: docker compose -f docker-compose.prod.yml logs backend"
    fi
done

info "Despliegue completado."
echo ""
if [ -n "$DOMAIN" ]; then
    echo -e "  ${GREEN}App disponible en:${NC} https://$DOMAIN"
else
    IP=$(hostname -I | awk '{print $1}')
    echo -e "  ${GREEN}App disponible en:${NC} http://$IP"
fi
echo ""
echo "  Comandos útiles:"
echo "    Ver logs:     docker compose -f docker-compose.prod.yml logs -f"
echo "    Ver estado:   docker compose -f docker-compose.prod.yml ps"
echo "    Parar todo:   docker compose -f docker-compose.prod.yml down"
echo "    Backup DB:    ./backup.sh"
echo ""
