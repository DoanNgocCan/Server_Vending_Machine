# Cloudflare Tunnel Setup Guide

This guide explains how to expose your Vending Machine server to the internet using Cloudflare Tunnel — no port forwarding or static IP required.

## Prerequisites

- A Cloudflare account (free tier works)
- A domain added to Cloudflare (or use Cloudflare's free `*.trycloudflare.com` subdomain)
- Docker Compose up and running

---

## Step-by-Step Setup

### 1. Create a Cloudflare Account

Go to [https://dash.cloudflare.com](https://dash.cloudflare.com) and sign up for a free account.

### 2. Add Your Domain to Cloudflare

If you have a domain, add it to Cloudflare and update your domain registrar's nameservers. If you don't have a domain yet, you can use [Cloudflare Tunnel's free subdomain](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/).

### 3. Create a Tunnel in Zero Trust Dashboard

1. Go to [https://one.dash.cloudflare.com](https://one.dash.cloudflare.com)
2. Navigate to **Networks → Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as the connector type
5. Give your tunnel a name (e.g., `vending-machine`)
6. Click **Save tunnel**

### 4. Get Your Tunnel Token

After creating the tunnel, Cloudflare will display a token. It looks like:

```
eyJhIjoiMWVjZmM3...
```

Copy this token — you'll need it in the next step.

### 5. Configure the Public Hostname

In the tunnel configuration:
1. Click **Public Hostname** tab
2. Click **Add a public hostname**
3. Fill in:
   - **Subdomain**: e.g., `api`
   - **Domain**: your domain (e.g., `yourdomain.com`)
   - **Service Type**: `HTTP`
   - **URL**: `web:5000`
4. Click **Save hostname**

Your API will be accessible at `https://api.yourdomain.com`.

### 6. Add the Token to `.env`

Copy `.env.example` to `.env` and add your token:

```bash
cp .env.example .env
```

Edit `.env`:
```
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiMWVjZmM3...
```

### 7. Uncomment the Tunnel Service in `docker-compose.yml`

Edit `docker-compose.yml` and uncomment the `tunnel` service block:

```yaml
  tunnel:
    image: cloudflare/cloudflared:latest
    container_name: vending-tunnel
    restart: always
    command: tunnel run
    environment:
      TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      - web
```

### 8. Start Everything

```bash
docker compose up -d
```

Check the tunnel is connected:

```bash
docker logs vending-tunnel
```

You should see `Connection established` in the logs.

---

## Verify

Visit `https://api.yourdomain.com/` — you should see:

```json
{"message": "Vending Machine Central Server is running", "status": "OK"}
```

---

## Troubleshooting

- **Tunnel not connecting**: Check `docker logs vending-tunnel` for errors.
- **502 Bad Gateway**: Make sure the `web` service is healthy (`docker ps`).
- **Token invalid**: Regenerate the token in the Cloudflare dashboard.
