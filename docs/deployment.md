# Deployment guide

## Render Blueprint deployment

The repository includes `render.yaml` for two Docker services:

- `kalibr-books-api`
- `kalibr-books-web`

The Blueprint creates one shared generated `INTERNAL_API_KEY`, connects the web service to the API through Render's private service address, and mounts API data at `/data`.

### Required operator values

When creating or updating the Blueprint, enter these secret values when Render requests them:

- `TELEGRAM_BOT_TOKEN`
- `ADMIN_BASIC_PASSWORD`

Keep `ADMIN_BASIC_USERNAME=admin` or change it after deployment. The bot must be an administrator in the target channel.

### Deployment steps

1. Push this fixed source tree to the private Git repository connected to Render.
2. In Render, create a Blueprint from the repository, or update the existing Blueprint.
3. Confirm that both services use the repository root as Docker context and their respective Dockerfiles.
4. Enter the required secret values.
5. Deploy the API first, then the web service if Render does not order them automatically.
6. Verify:

```text
https://kalibr-books-api.onrender.com/
https://kalibr-books-api.onrender.com/api/v1/health/ready
https://kalibr-books-web.onrender.com/api/health
https://kalibr-books-web.onrender.com/uz
```

The API root now returns service metadata. It should no longer return `{"detail":"Not Found"}`.

### Existing manually created Render services

A manually configured pair does not automatically inherit every Blueprint value. Ensure:

**API**

```dotenv
PORT=10000
APP_ENV=production
APP_VERSION=0.1.1
INTERNAL_API_KEY=<same long random value as web>
STORAGE_ROOT=/data/storage
BACKUP_ROOT=/data/backups
TEMP_ROOT=/data/tmp
LOG_ROOT=/data/logs
API_ALLOWED_HOSTS=kalibr-books-api.onrender.com,kalibr-books-api,localhost,127.0.0.1
API_CORS_ORIGINS=https://kalibr-books-web.onrender.com
TELEGRAM_BOT_TOKEN=<secret>
TELEGRAM_DEFAULT_CHANNEL=@kalibr_books
```

Attach a persistent disk mounted at `/data`.

**Web**

```dotenv
PORT=10000
API_INTERNAL_URL=<Render private API host:port, or https://kalibr-books-api.onrender.com>
INTERNAL_API_KEY=<same long random value as API>
ADMIN_BASIC_USERNAME=admin
ADMIN_BASIC_PASSWORD=<strong secret>
NEXT_PUBLIC_APP_NAME=Kalibr Publisher
NEXT_PUBLIC_DEFAULT_LOCALE=uz
```

Do not append `/api/v1` to `API_INTERNAL_URL`.

### Render operating constraint

The current JSON store requires exactly one API instance and one API worker. Do not enable autoscaling or multiple API instances until the SQLAlchemy database phase is complete.

## Ubuntu VPS deployment

The recommended production URL is:

```text
publisher.uboom.uz
```

### DNS

Create an `A` record pointing `publisher.uboom.uz` to the VPS IPv4 address.

### Host preparation

Install Docker Engine and Docker Compose, then configure the firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
```

Create persistent directories:

```bash
sudo mkdir -p /srv/kalibr-publisher/{storage,backups,tmp,logs}
sudo chmod 750 /srv/kalibr-publisher
```

The API entrypoint prepares ownership for its non-root runtime user on first start.

### Configuration

```bash
git clone YOUR_PRIVATE_REPOSITORY_URL /opt/kalibr-publisher
cd /opt/kalibr-publisher
cp .env.example .env
chmod 600 .env
```

At minimum, change:

```dotenv
APP_ENV=production
APP_DOMAIN=publisher.uboom.uz
API_ALLOWED_HOSTS=publisher.uboom.uz,api,localhost,127.0.0.1
API_CORS_ORIGINS=https://publisher.uboom.uz
API_LOG_FORMAT=json
API_DOCS_ENABLED=false
KALIBR_DATA_DIR=/srv/kalibr-publisher
INTERNAL_API_KEY=<long random value>
ADMIN_BASIC_USERNAME=admin
ADMIN_BASIC_PASSWORD=<strong password>
TELEGRAM_BOT_TOKEN=<secret>
TELEGRAM_DEFAULT_CHANNEL=@kalibr_books
CADDY_EMAIL=<operator email>
```

### Start and verify

```bash
docker compose -f docker-compose.production.yml up -d --build
curl -fsS https://publisher.uboom.uz/api/health
curl -u admin:YOUR_PASSWORD -fsS https://publisher.uboom.uz/api/v1/health/ready
```

### Updates

```bash
cd /opt/kalibr-publisher
git pull --ff-only
docker compose -f docker-compose.production.yml up -d --build --remove-orphans
docker image prune -f
```

Never delete `/srv/kalibr-publisher` during deployment.
