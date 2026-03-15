# DishaSetu API – Azure VM deploy

After cloning the repo on the VM, run these in order.

## 1. System packages (one-time)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib
sudo apt install -y postgresql-16-pgvector   # Ubuntu 24; adjust version for your Postgres
```

## 2. PostgreSQL database (one-time)

```bash
sudo -u postgres psql << 'EOF'
CREATE DATABASE dishasetu;
CREATE USER dishasetu_user WITH PASSWORD 'YOUR_PASSWORD';
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

## 3. App setup (after each pull)

```bash
cd ~/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY, BACKEND_CORS_ORIGINS
nano .env
```

## 4. Migrations

```bash
cd ~/server && source venv/bin/activate
alembic upgrade head
```

## 5. Systemd service (one-time)

```bash
sudo cp ~/server/deploy/dishasetu-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dishasetu-api
sudo systemctl start dishasetu-api
sudo systemctl status dishasetu-api
```

## After future git pull

```bash
cd ~/server
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart dishasetu-api
```
