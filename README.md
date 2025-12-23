# Valer Automation POC

A Python automation proof-of-concept that demonstrates web scraping, portal automation, and containerization. This project simulates logging into a healthcare provider portal, extracting patient authorization data, and persisting it to PostgreSQL.

## What This Does

The scraper logs into a portal (using the-internet.herokuapp.com for demo purposes), extracts table data, and stores it in a PostgreSQL database. Everything runs in Docker containers with proper health checks and error handling.

## Architecture

Pretty straightforward modular setup:

- `main.py` - Entry point that orchestrates everything
- `scraper.py` - Selenium automation for portal interaction
- `database.py` - SQLAlchemy session management
- `models.py` - Database schema definitions

## Prerequisites

- Docker and Docker Compose
- Git (obviously)

## Quick Start

1. Clone the repo:
   ```bash
   git clone https://github.com/DakodaStemen/valer_prep.git
   cd valer_prep
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` if you need to change any defaults.

3. Build and run:
   ```bash
   docker compose up --build
   ```

The app will:
- Spin up a PostgreSQL container
- Wait for the DB to be healthy (health checks are important!)
- Initialize the schema
- Run the scraper (login → extract → save to DB)
- Log everything to stdout

## Environment Variables

Check `.env.example` for the full list. Main ones:

- `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database credentials
- `PORTAL_USERNAME`, `PORTAL_PASSWORD` - Portal login (defaults work for the-internet.herokuapp.com)
- `SELENIUM_HEADLESS` - Set to `true` for headless mode (default)

## Database Schema

The `patient_auth` table has:
- `id` - Primary key
- `patient_name` - Patient name
- `auth_number` - Unique authorization number
- `status` - Status (Pending/Approved)
- `created_at` - Timestamp

Uses upsert logic, so running it multiple times won't create duplicates.

## Running Locally (Without Docker)

If you want to run it directly:

```bash
pip install -r requirements.txt
# Make sure PostgreSQL is running and update .env
python main.py
```

## Project Structure

```
.
├── main.py              # Entry point
├── scraper.py           # Selenium automation
├── database.py          # Database operations
├── models.py            # SQLAlchemy models
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Container setup
├── requirements.txt     # Dependencies
├── .env.example         # Env template
└── README.md            # This file
```

## Notes

- Uses explicit waits throughout (WebDriverWait) to handle slow portals
- Multi-stage Dockerfile for smaller image size
- Health checks ensure the app waits for DB to be ready
- Error handling with retry logic for stale elements
- All secrets live in `.env` (never committed)

## Troubleshooting

If the build fails with `apt-key` errors, make sure you're using the latest Dockerfile - it uses the modern GPG keyring method.

To check if data was saved:
```bash
docker compose exec postgres psql -U postgres -d valer_db -c "SELECT * FROM patient_auth;"
```
