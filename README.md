# 📦 InvFlow - Intelligent Inventory Optimization

Professional inventory management system integrated with Odoo. It uses ABC/XYZ analysis to predict stock levels and automate purchase orders.

## 🏗️ Project Structure
- **/backend**: FastAPI server + Analytics Engine (Python).
- **/frontend**: React + Vite dashboard with modern UI.
- **/nginx**: Reverse proxy configuration for secure access.
- **/docs**: Technical and functional documentation.
- **docker-compose.yml**: Full orchestration for services.
- **.env**: Environment secrets and credentials.

## 🚀 Quick Start
1. Configure your `.env` file with Odoo and Database credentials.
2. Run `docker-compose up -d --build`.
3. Open `http://localhost` to access the dashboard.

## 🛠 Features
- **Odoo Sync**: Real-time product and stock synchronization.
- **ABC/XYZ Analytics**: Automatic classification based on turnover and volatility.
- **One-Click PO**: Generate Purchase Orders directly in Odoo.
- **Inventory Simulation**: Test different scenarios before applying changes.

---
*Created with focus on efficiency and scalability.*
