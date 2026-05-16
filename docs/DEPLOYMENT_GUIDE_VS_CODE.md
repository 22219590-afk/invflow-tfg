# 🚀 Deployment Guide: InvFlow Enterprise Setup

This guide walks you through the process of deploying the InvFlow system on a remote server using **Visual Studio Code** and **Docker Compose**.

## 📋 Prerequisites
Before starting, ensure the target server (Ubuntu 22.04 LTS recommended) has:
1. **Docker Engine** (v20.10+)
2. **Docker Compose** (v2.0+)
3. **VS Code** installed on your local machine with the **Remote - SSH** extension.

---

## 🏗️ Phase 1: Remote Connection
1. Open VS Code and click the **Remote Explorer** icon (bottom left).
2. Connect to your server via SSH: `ssh user@your-server-ip`.
3. Once connected, open a terminal in VS Code and create the project directory:
   ```bash
   mkdir ~/invflow && cd ~/invflow
   ```

---

## 📦 Phase 2: Project Upload
Transfer your project files to the server. You can:
- **Git**: `git clone <your-repo-url>`
- **SFTP**: Drag and drop folders directly into the VS Code explorer.

**Required Structure:**
```text
/invflow
├── backend/
├── frontend/
├── nginx/
├── docker-compose.yml
└── .env (Manual creation)
```

---

## 🔐 Phase 3: Environment Configuration
Create the `.env` file in the root folder of the server:
```bash
nano .env
```
Copy and paste the following template, replacing with your real credentials:
```env
ODOO_URL=https://your-instance.odoo.com
ODOO_DB=your_db
ODOO_USER=admin@email.com
ODOO_PASSWORD=your_api_key

POSTGRES_USER=admin
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=inventory_db
DATABASE_URL=postgresql://admin:secure_password@db/inventory_db

JWT_SECRET_KEY=generate_a_random_string
```

---

## 🚀 Phase 4: Launching the System
In the VS Code terminal, run the following command to build and start all services:

```bash
docker-compose up -d --build
```

### 🔍 Verification Commands:
- **Check Status**: `docker-compose ps` (All services should be `Up`).
- **Check Health**: `docker-compose logs -f --tail=50` (Look for "Application startup complete").
- **Inspect DB**: `docker-compose exec db pg_isready -U admin`

---

## 🌐 Phase 5: Domain & Nginx Setup
If you have a domain (e.g., `invflow.com`):
1. Edit `nginx/default.conf` and update `server_name`:
   ```nginx
   server_name invflow.com;
   ```
2. Restart Nginx:
   ```bash
   docker-compose restart nginx
   ```

---

## 💾 Phase 6: Maintenance & Backups
### Database Backup
To backup your PostgreSQL data:
```bash
docker-compose exec db pg_dump -U admin inventory_db > backup_$(date +%F).sql
```

### System Updates
To apply code changes:
```bash
git pull                   # Get new code
docker-compose up -d --build  # Rebuild and restart
```

---
*Manual generated for InvFlow - TFG Project*
