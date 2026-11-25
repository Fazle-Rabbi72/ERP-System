# Linux Production Deployment Guide (No Docker)

Target OS: Ubuntu 22.04/24.04 LTS or Debian 12 with PostgreSQL 16, Redis 7, Python 3.12, Node.js 20+, and Nginx.

## 1. System user & directories
```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin nexzen
sudo mkdir -p /opt/nexzen-erp /etc/nexzen-erp /var/log/nexzen-erp
sudo chown -R nexzen:nexzen /opt/nexzen-erp /var/log/nexzen-erp
```

## 2. Environment file
Place the production `.env` at `/etc/nexzen-erp/.env` with `chmod 600` owned by `nexzen:nexzen`:
- `APP_ENV=production`
- `DEPLOYMENT_MODE=cloud` (SaaS) or `DEPLOYMENT_MODE=onprem` + `ONPREM_TENANT_ID=<uuid>`
- Strong random `JWT_SECRET_KEY` (>= 32 chars), `DB_APP_PASSWORD`, `DB_MIGRATOR_PASSWORD`
- TLS enabled for any remote PostgreSQL (`DB_SSL_MODE=verify-full`) and remote Redis (`REDIS_SSL=true`)

## 3. Install, bootstrap DB, migrate, build frontend
```bash
cd /opt/nexzen-erp
sudo -u nexzen bash scripts/setup.sh
sudo -u nexzen bash scripts/db-bootstrap.sh
sudo -u nexzen bash scripts/migrate.sh
sudo -u nexzen bash -c 'cd frontend && npm ci && npm run build'
```

## 4. Enable systemd services
```bash
sudo cp infra/systemd/nexzen-api.service /etc/systemd/system/
sudo cp infra/systemd/nexzen-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nexzen-api nexzen-worker
sudo systemctl status nexzen-api nexzen-worker
```

## 5. Enable Nginx + HTTPS
```bash
sudo cp infra/nginx/nexzen-erp.conf /etc/nginx/sites-available/nexzen-erp
# Edit server_name and certificate paths (use certbot for Let's Encrypt)
sudo ln -sf /etc/nginx/sites-available/nexzen-erp /etc/nginx/sites-enabled/nexzen-erp
sudo nginx -t && sudo systemctl reload nginx
```
