# 🏢 GUÍA DE INSTALACIÓN EN SERVIDOR EMPRESARIAL
### InvFlow — Sistema de Gestión de Inventario

---

## 📋 REQUISITOS PREVIOS

Antes de empezar, necesitas:

| Requisito | Detalle |
|---|---|
| **Servidor** | Linux Ubuntu 22.04 LTS (recomendado) |
| **RAM mínima** | 2 GB (recomendado 4 GB) |
| **Disco** | 20 GB libres mínimo |
| **Acceso** | Usuario con permisos `sudo` |
| **Puertos abiertos** | 80 (HTTP) y 443 (HTTPS si vas a usar dominio) |

> El servidor puede ser una máquina física de la empresa, una máquina virtual (VMware, Hyper-V), o un VPS en la nube (AWS, Azure, Google Cloud, Hetzner, etc.).

---

## 🖥️ PASO 1 — Conectarse al Servidor

Desde tu ordenador personal, abre una terminal y conecta al servidor por SSH:

```bash
ssh usuario@IP_DEL_SERVIDOR
# Ejemplo:
ssh admin@192.168.10.50
```

> Si la empresa te da un usuario y contraseña, el sistema te la pedirá tras ejecutar este comando.

---

## 🐳 PASO 2 — Instalar Docker en el Servidor

Una vez dentro del servidor, ejecuta estos comandos **uno a uno**:

```bash
# 1. Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependencias necesarias
sudo apt install -y ca-certificates curl gnupg

# 3. Añadir la clave oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4. Añadir el repositorio de Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. Añadir tu usuario al grupo docker (para no necesitar sudo cada vez)
sudo usermod -aG docker $USER
newgrp docker

# 7. Verificar que Docker funciona
docker --version
docker compose version
```

✅ Si ves algo como `Docker version 25.x.x` y `Docker Compose version v2.x.x`, Docker está instalado correctamente.

---

## 📁 PASO 3 — Subir el Proyecto al Servidor

Tienes dos opciones para transferir los archivos del proyecto:

### Opción A — Usando Git (recomendado si tienes repositorio)
```bash
# En el servidor, crear carpeta y clonar el proyecto
mkdir ~/invflow && cd ~/invflow
git clone https://github.com/tu-usuario/tu-repo.git .
```

### Opción B — Subiendo archivos manualmente desde tu Mac
Abre una **nueva terminal en tu Mac** (sin cerrar la del servidor) y ejecuta:
```bash
# Reemplaza usuario e IP con los datos de tu servidor
scp -r "/Users/vic/Desktop/carpeta sin título 3/." usuario@IP_DEL_SERVIDOR:~/invflow/
```

---

## 🔐 PASO 4 — Configurar las Variables de Entorno

En el servidor, entra a la carpeta del proyecto y crea el archivo `.env`:

```bash
cd ~/invflow
nano .env
```

Copia y pega la siguiente plantilla, **sustituyendo los valores con los datos reales**:

```env
# --- CONEXIÓN A ODOO ---
ODOO_URL=https://tu-instancia.odoo.com
ODOO_DB=nombre_de_tu_base_de_datos
ODOO_USER=admin@tuempresa.com
ODOO_PASSWORD=tu_api_key_de_odoo

# --- BASE DE DATOS INTERNA ---
POSTGRES_USER=admin
POSTGRES_PASSWORD=CambiaEstaContraseña123!
POSTGRES_DB=inventory_db
DATABASE_URL=postgresql://admin:CambiaEstaContraseña123!@db/inventory_db

# --- SEGURIDAD ---
# Genera una clave aleatoria segura con: openssl rand -hex 32
JWT_SECRET_KEY=pon-aqui-una-clave-secreta-muy-larga-y-aleatoria
```

Para guardar en `nano`: pulsa `CTRL+X`, luego `Y`, luego `ENTER`.

> ⚠️ **IMPORTANTE**: Nunca compartas este archivo `.env`. Contiene contraseñas y claves de acceso.

Para generar una `JWT_SECRET_KEY` segura, ejecuta:
```bash
openssl rand -hex 32
```
Copia el resultado y pégalo como valor de `JWT_SECRET_KEY` en el `.env`.

---

## 🌐 PASO 5 — Configurar el Nombre de Dominio (Opcional)

Si la empresa tiene un dominio (por ejemplo, `invflow.miempresa.com`), edita el archivo de Nginx:

```bash
nano ~/invflow/nginx/default.conf
```

Cambia la línea `server_name localhost;` por tu dominio:

```nginx
server_name invflow.miempresa.com;
```

Guarda con `CTRL+X`, `Y`, `ENTER`.

> Si no tienes dominio, la aplicación será accesible directamente por la IP del servidor (ej: `http://192.168.10.50`).

---

## 🚀 PASO 6 — Arrancar la Aplicación

Desde la carpeta del proyecto en el servidor, ejecuta:

```bash
cd ~/invflow
docker compose up -d --build
```

Este comando tardará varios minutos la primera vez (descarga imágenes, instala dependencias, compila el frontend). Las siguientes veces será mucho más rápido.

### Verificar que todo está correcto:
```bash
# Ver el estado de todos los servicios (todos deben estar "Up" o "healthy")
docker compose ps

# Ver los logs en tiempo real (Ctrl+C para salir)
docker compose logs -f
```

✅ Cuando veas `Application startup complete` en los logs del backend, la aplicación está lista.

---

## ✅ PASO 7 — Acceder a la Aplicación

Abre un navegador y entra a:

- **Por IP**: `http://192.168.10.50` (usa la IP real de tu servidor)
- **Por dominio** (si tienes uno): `http://invflow.miempresa.com`

Cualquier persona de la empresa con acceso a la red podrá usar la aplicación desde su ordenador o móvil.

---

## 🔄 PASO 8 — Mantenimiento Habitual

### Apagar la aplicación temporalmente:
```bash
cd ~/invflow
docker compose down
```

### Volver a encenderla:
```bash
cd ~/invflow
docker compose up -d
```

### Actualizar la aplicación con nuevos cambios:
```bash
cd ~/invflow
git pull                        # Si usas Git, obtener últimos cambios
docker compose up -d --build   # Reconstruir e reiniciar
```

### Hacer una copia de seguridad de la base de datos:
```bash
cd ~/invflow
docker compose exec db pg_dump -U admin inventory_db > backup_$(date +%F).sql
```

### Ver los logs si algo falla:
```bash
docker compose logs backend --tail=50    # Logs del backend
docker compose logs nginx --tail=20      # Logs del servidor web
docker compose logs frontend --tail=20   # Logs del frontend
```

---

## 🔒 PASO 9 — HTTPS con Certificado SSL (Recomendado para Producción)

Instala Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx

# Parar Nginx de Docker temporalmente
cd ~/invflow && docker compose stop nginx

# Generar el certificado (reemplaza con tu dominio y email)
sudo certbot certonly --standalone -d invflow.miempresa.com --email admin@miempresa.com --agree-tos

# Volver a arrancar Nginx
docker compose start nginx
```

Una vez tengas el certificado, contacta con el administrador de sistemas para configurarlo en Nginx (actualizar `nginx/default.conf` para escuchar en el puerto 443 y referenciar los certificados).

---

## ❓ SOLUCIÓN DE PROBLEMAS COMUNES

| Problema | Causa probable | Solución |
|---|---|---|
| Error 502 Bad Gateway | El frontend aún está arrancando | Espera 30 segundos y recarga |
| No conecta a Odoo | Credenciales incorrectas en `.env` | Revisa `ODOO_URL`, `ODOO_USER` y `ODOO_PASSWORD` |
| La web no carga desde otro equipo | Puerto 80 bloqueado por firewall | Ejecuta: `sudo ufw allow 80/tcp` |
| Error de base de datos | Contraseña no coincide | Asegúrate de que `POSTGRES_PASSWORD` y `DATABASE_URL` son iguales en el `.env` |
| Cambios en el código no aparecen | Caché de Docker | Ejecuta: `docker compose up -d --build --force-recreate` |

### Abrir el puerto 80 en el firewall del servidor (si es necesario):
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp   # Si usas HTTPS
sudo ufw status
```

---

*Guía elaborada para el proyecto InvFlow — TFG*
*Última actualización: Abril 2026*
