## Overview

This guide describes how to deploy the **DishaSetu API** (FastAPI backend) to a Linux server (Azure VM or similar) using:

- Python virtual environment
- PostgreSQL 16 + pgvector
- Uvicorn
- systemd
- Nginx reverse proxy

## 1. Connect to the Server

```bash
ssh dishasetu@135.235.182.119
dishasetu@1234
cd ~/server
```

Make sure the repo is cloned in `~/server`.

---

## 2. Pull Latest Code

From `~/server`:

```bash
source venv/bin/activate  # if venv already exists

git status

# If there are local changes you don't want to keep
git stash

# Pull latest changes from main
git pull origin main

# If Git reports divergent branches, you can choose merge strategy once:
git config pull.rebase false   # merge
git pull origin main
```

On pure deployment servers, it's usually best to **avoid local commits** and keep the branch identical to `origin/main`.

---

## 3. System Packages (one‑time)

Install Python, PostgreSQL, and pgvector:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib
sudo apt install -y postgresql-16-pgvector   # adjust version to match your Postgres
```

Optional (for HTTPS reverse proxy):

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

---

## 4. PostgreSQL Setup (one‑time)

Create database, user, and enable pgvector:

```bash
sudo -u postgres psql << 'EOF'
CREATE DATABASE dishasetu;
CREATE USER dishasetu_user WITH PASSWORD 'YOUR_STRONG_PASSWORD';
ALTER ROLE dishasetu_user SET client_encoding TO 'utf8';
ALTER ROLE dishasetu_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dishasetu_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE dishasetu TO dishasetu_user;
\c dishasetu
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO dishasetu_user;
GRANT CREATE ON SCHEMA public TO dishasetu_user;
ALTER SCHEMA public OWNER TO dishasetu_user;
EOF
```

Database URL used by the app:

```text
postgresql://dishasetu_user:YOUR_STRONG_PASSWORD@localhost:5432/dishasetu
```

---

## 5. Application Setup / Virtualenv

From `~/server`:

```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` (once) based on `env_production.md`:

```bash
cp env_production.md .env   # or cp .env.example .env if you prefer
nano .env
```

Set at least:

```env
DATABASE_URL=postgresql://dishasetu_user:YOUR_STRONG_PASSWORD@localhost:5432/dishasetu
APP_NAME="DishaSetu API"
APP_ENV=production
APP_DEBUG=false
DEBUG=false
APP_URL=https://api.dishasetu.in        # or http://SERVER_IP:8000 if not using HTTPS yet
LOG_LEVEL=INFO

SECRET_KEY=your-very-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440

MAIL_MAILER=smtp
MAIL_HOST=smtp.zeptomail.in
MAIL_PORT=587
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=noreply@dishasetu.in
MAIL_FROM_NAME="dishasetu"

REDIS_HOST=localhost
REDIS_PORT=6379

BACKEND_CORS_ORIGINS=["https://dishasetu.in","https://api.dishasetu.in","http://localhost:3000"]

CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```


## 6. Database Migrations

From `~/server` with the venv activated:

```bash
source venv/bin/activate

# Optional: confirm DB URL the app will use
echo $DATABASE_URL

# Check current Alembic revision
alembic current

# Run migrations
alembic upgrade head

# Verify again
alembic current
```


## 7. Systemd Service

Service file (in repo): `deploy/dishasetu-api.service`

```ini
[Unit]
Description=DishaSetu FastAPI
After=network.target postgresql.service

[Service]
User=dishasetu
Group=dishasetu
WorkingDirectory=/home/dishasetu/server
Environment="PATH=/home/dishasetu/server/venv/bin"
ExecStart=/home/dishasetu/server/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Install and enable it:

```bash
sudo cp ~/server/deploy/dishasetu-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dishasetu-api
sudo systemctl start dishasetu-api
sudo systemctl status dishasetu-api
```

The API should now be reachable at `http://SERVER_IP:8000` (or via nginx domain if configured).

---

## 8. Nginx Reverse Proxy (Optional but Recommended)

### 8.1 Basic HTTP proxy

Create an Nginx site for the API:

```bash
sudo nano /etc/nginx/sites-available/api.dishasetu.in
```

```nginx
server {
    listen 80;
    server_name api.dishasetu.in;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/api.dishasetu.in /etc/nginx/sites-enabled/api.dishasetu.in
sudo nginx -t
sudo systemctl reload nginx
```

### 8.2 HTTPS with Let’s Encrypt

Assuming DNS `api.dishasetu.in` points to the server IP:

```bash
sudo certbot --nginx -d api.dishasetu.in
```

Choose the option to **redirect HTTP to HTTPS**. After this, the public URL for the API is:

```text
https://api.dishasetu.in
```

---

## 9. Frontend Configuration (Next.js)

In the frontend project (`client`), configure production env vars so the browser talks to HTTPS:

```env
NEXT_PUBLIC_API_BASE_URL=https://api.dishasetu.in
NEXT_PUBLIC_API_VERSION=v1
NEXT_PUBLIC_API_URL=https://api.dishasetu.in/api/v1
```

Rebuild and redeploy the frontend. This avoids mixed‑content warnings when the page is loaded over `https://dishasetu.in`.

For local development you can keep:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## 10. Routine Deployments (After Each Push)

On the server:

```bash
cd ~/server
source venv/bin/activate

git pull origin main
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart dishasetu-api
sudo systemctl status dishasetu-api
```

If you changed Nginx configuration:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 11. Monitoring and Logs

### API service logs

```bash
sudo journalctl -u dishasetu-api -f --lines=50
```

### Nginx logs

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Service status

```bash
sudo systemctl status dishasetu-api
sudo systemctl status nginx
sudo systemctl status postgresql

ps aux | grep uvicorn
ps aux | grep nginx
```

---

## 12. Troubleshooting

### Database connection

```bash
sudo systemctl status postgresql

sudo -u postgres psql -d dishasetu -c "SELECT version();"
sudo -u postgres psql -d dishasetu -c "\du"
```

### Alembic migrations

```bash
alembic history --verbose
alembic current
```

### Service issues

```bash
sudo journalctl -u dishasetu-api --lines=50
sudo systemctl restart dishasetu-api
sudo ss -tlnp | grep 8000
```

---

## 13. Quick Reference

```bash
cd ~/server
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart dishasetu-api
sudo systemctl status dishasetu-api
```

A. Server (Azure VM) – expose API as https://api.dishasetu.in
1. DNS
In your DNS provider for dishasetu.in:

Add an A record:

Name: api
Type: A
Value: 135.235.182.119
Wait a few minutes so api.dishasetu.in resolves to your VM (you can check later with ping api.dishasetu.in from your PC).

2. Install nginx + certbot (if not already)
On the VM:

sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
Check nginx:

sudo systemctl status nginx
(It should be active (running).)

3. Create nginx site for the API
On the VM:

sudo nano /etc/nginx/sites-available/api.dishasetu.in
Paste this:

server {
    listen 80;
    server_name api.dishasetu.in;
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
Save and exit.

Enable and reload:

sudo ln -s /etc/nginx/sites-available/api.dishasetu.in /etc/nginx/sites-enabled/api.dishasetu.in
sudo nginx -t
sudo systemctl reload nginx
Now http://api.dishasetu.in should show your API (same as http://135.235.182.119:8000).

4. Add HTTPS with Let’s Encrypt
Run:

sudo certbot --nginx -d api.dishasetu.in
Enter email.
Agree to terms.
When asked, choose the option to redirect HTTP to HTTPS.
Certbot will update the nginx config to serve https://api.dishasetu.in with a valid certificate.

Test from the VM:

curl -k https://api.dishasetu.in/
You should see your API root JSON (e.g. "Welcome to DishaSetu API").

5. Adjust server .env (VM)
On the VM, edit ~/server/.env:

nano ~/server/.env
Make sure you have:

APP_URL=https://api.dishasetu.in
# CORS
BACKEND_CORS_ORIGINS=["https://dishasetu.in","https://api.dishasetu.in"]
Save, then restart the service:

sudo systemctl restart dishasetu-api
sudo systemctl status dishasetu-api
Backend is now ready to accept HTTPS traffic via https://api.dishasetu.in.

B. Frontend – point to the HTTPS API
Your local dev file client/.env.locals is:

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_VERSION=v1
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
Keep that for local development.

For production (where https://dishasetu.in is deployed), set the environment variables there to:

NEXT_PUBLIC_API_BASE_URL=https://api.dishasetu.in
NEXT_PUBLIC_API_VERSION=v1
NEXT_PUBLIC_API_URL=https://api.dishasetu.in/api/v1
Exactly how you set this depends on where your frontend is hosted:

If on Vercel: Project → Settings → Environment Variables → add the above under “Production”, then redeploy.
If served by nginx on a server: Edit the prod .env used at build time, then run npm run build && npm run start (or your deploy script) again.
If built locally and uploaded: Rebuild with these envs set, then redeploy.
Your apiClient / axios code should already be using NEXT_PUBLIC_API_URL (or base + version). If it’s hard‑coded anywhere to http://135.235.182.119:8000, replace that with the env variable.

C. After deployment – what should happen
Page: https://dishasetu.in/auth/login
API calls: https://api.dishasetu.in/api/v1/auth/login (HTTPS)
nginx on VM: proxies to http://127.0.0.1:8000/api/v1/auth/login
No more “Mixed Content” warning; CORS already allows https://dishasetu.in and https://api.dishasetu.in.
If you tell me where your frontend is deployed (Vercel / some server / same Azure VM), I can give the exact command(s) or config snippet for setting those NEXT_PUBLIC_* variables in that place.