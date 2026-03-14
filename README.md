# Vending Machine Central Server

A central server for managing vending machines, built with Flask + PostgreSQL, containerized with Docker.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Vending Machine │────▶│  Flask API        │────▶│  PostgreSQL DB     │
│  (ESP32 client)  │     │  (port 5000)      │     │  (port 5432)       │
└─────────────────┘     └──────────────────┘     └────────────────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Streamlit        │
                         │  Dashboard        │
                         │  (port 8501)      │
                         └──────────────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Cloudflare       │
                         │  Tunnel           │
                         │  (optional)       │
                         └──────────────────┘
```

## Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/DoanNgocCan/Server_Vending_Machine.git
cd Server_Vending_Machine

# 2. Copy environment variables
cp .env.example .env

# 3. Start all services
docker compose up -d
```

- API Server: http://localhost:5000
- Dashboard: http://localhost:8501

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/users` | List users |
| POST | `/api/user/register` | Register user |
| POST | `/api/user/login` | Login user |
| GET | `/api/user/<user_id>` | Get user by ID |
| POST | `/api/user/sync_profile` | Sync user profile from device |
| GET | `/api/products` | List products (add `X-Device-ID` header for stock) |
| POST | `/api/products/batch_sync` | Sync products from device |
| POST | `/api/products/set_custom` | Set custom price for device |
| POST | `/api/admin/update_product` | Admin: update product info |
| POST | `/api/transactions/record` | Record a transaction |
| GET | `/api/transactions` | List transactions |
| GET | `/api/inventory/stats` | Inventory sales stats |

See [docs/api_curl_commands.md](docs/api_curl_commands.md) for detailed examples.

## Project Structure

```
Server_Vending_Machine/
├── .env.example          # Environment variable template
├── docker-compose.yml    # Main entry point
├── server/               # Flask API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py            # Entry point: Flask setup & blueprint registration
│   ├── database.py       # DB connection helpers & table creation
│   ├── utils.py
│   └── routes/           # API route modules (Flask Blueprints)
│       ├── users.py      # /api/user* endpoints
│       ├── products.py   # /api/products* & /api/admin/* endpoints
│       └── transactions.py # /api/transactions* & /api/inventory/stats
├── dashboard/            # Streamlit Dashboard
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── services.py
│   ├── utils.py
│   └── pages/
│       └── 1_Admin_Panel.py
└── docs/                 # Reference documentation
    ├── api_curl_commands.md
    └── cloudflare_setup.md
```

## Configuration

Copy `.env.example` to `.env` and adjust values:

```env
POSTGRES_DB=vending_machine
POSTGRES_USER=vending
POSTGRES_PASSWORD=vending123
DATABASE_URL=postgresql://vending:vending123@db:5432/vending_machine
API_URL=http://web:5000
```

## Cloudflare Tunnel (Public Access)

To expose the server to the internet without port forwarding, see [docs/cloudflare_setup.md](docs/cloudflare_setup.md).

## Development

To run individual services:

```bash
# Run only the database
docker compose up db -d

# Run API server locally (requires PostgreSQL running)
cd server
pip install -r requirements.txt
DATABASE_URL=postgresql://vending:vending123@localhost:5432/vending_machine python app.py

# Run dashboard locally
cd dashboard
pip install -r requirements.txt
API_URL=http://localhost:5000 streamlit run main.py
```

## License

See [LICENSE.txt](LICENSE.txt).
