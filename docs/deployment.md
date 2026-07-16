# Ubuntu VPS deployment

The recommended production address is `publisher.uboom.uz`. A subdomain avoids path-prefix problems with cookies, routing, static assets and CSRF boundaries.

## 1. DNS

Create an `A` record:

```text
publisher.uboom.uz -> YOUR_VPS_IPV4
```

Add an `AAAA` record only when IPv6 is correctly routed to the server.

## 2. Host preparation

Install Docker Engine and the Docker Compose plugin from Docker's official Ubuntu repository. Configure the firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
```

Create persistent directories owned by container UID/GID `10001`:

```bash
sudo mkdir -p /srv/kalibr-publisher/{storage,backups,tmp,logs}
sudo chown -R 10001:10001 /srv/kalibr-publisher
sudo chmod -R 750 /srv/kalibr-publisher
```

## 3. Application configuration

```bash
git clone YOUR_PRIVATE_REPOSITORY_URL /opt/kalibr-publisher
cd /opt/kalibr-publisher
cp .env.example .env
```

Set at minimum:

```dotenv
APP_ENV=production
APP_DOMAIN=publisher.uboom.uz
API_ALLOWED_HOSTS=publisher.uboom.uz,api
API_CORS_ORIGINS=https://publisher.uboom.uz
API_LOG_FORMAT=json
API_DOCS_ENABLED=false
CADDY_EMAIL=YOUR_ADMIN_EMAIL
KALIBR_DATA_DIR=/srv/kalibr-publisher
```

Protect the file:

```bash
chmod 600 .env
```

## 4. Start

```bash
docker compose -f docker-compose.production.yml up -d --build
```

Verify:

```bash
curl -fsS https://publisher.uboom.uz/api/v1/health/ready
curl -fsS https://publisher.uboom.uz/api/health
```

## 5. Updates

```bash
cd /opt/kalibr-publisher
git pull --ff-only
docker compose -f docker-compose.production.yml up -d --build --remove-orphans
docker image prune -f
```

Do not remove `/srv/kalibr-publisher` during deployments. Containers are disposable; that directory contains persistent data.

## 6. Operations

View logs:

```bash
docker compose -f docker-compose.production.yml logs -f --tail=200
```

Check container health:

```bash
docker compose -f docker-compose.production.yml ps
```

Caddy handles TLS certificates automatically. API and web ports are not published directly in production; only Caddy exposes ports 80 and 443.
