# Valer-Sync Pro

A production-ready full-stack application demonstrating web scraping, REST API architecture, and human-in-the-loop data management. This project provides a Flask REST API backend with a Single Page App (SPA) frontend for managing healthcare portal automation and patient authorization data.

## What This Does

The application provides a modern dashboard interface where administrators can:
- Trigger asynchronous portal scraping jobs
- View all patient authorization records in a responsive table
- Manually edit records to fix data integrity issues (human-in-the-loop)
- Monitor scrape metrics (duration, success rate) and system health
- Track which records have been manually edited

The scraper logs into a portal (using the-internet.herokuapp.com for demo purposes), extracts table data, and stores it in a PostgreSQL database. Everything runs in Docker containers with proper health checks and error handling.

## Architecture

Full-stack REST API + SPA architecture:

**Backend:**
- `app.py` - Flask REST API server with async job handling
- `scraper.py` - Selenium automation for portal interaction
- `database.py` - SQLAlchemy session management and utilities
- `models.py` - Database schema definitions (PatientAuth, ScrapeRun)

**Frontend:**
- `templates/index.html` - Single Page App with Tailwind CSS and vanilla JavaScript

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

4. Access the dashboard:
   Open your browser and navigate to `http://localhost:5000`

The app will:
- Spin up a PostgreSQL container
- Wait for the DB to be healthy (health checks are important!)
- Initialize the schema (including new `is_manually_edited` column and `scrape_run` table)
- Start the Flask API server on port 5000
- Serve the SPA dashboard at the root URL

## Environment Variables

Check `.env.example` for the full list. Main ones:

- `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database credentials
- `PORTAL_USERNAME`, `PORTAL_PASSWORD` - Portal login (defaults work for the-internet.herokuapp.com)
- `SELENIUM_HEADLESS` - Set to `true` for headless mode (default)
- `FLASK_PORT` - Flask server port (default: 5000)
- `FLASK_ENV` - Flask environment (`production` or `development`)

## Database Schema

### `patient_auth` table:
- `id` - Primary key
- `patient_name` - Patient name
- `auth_number` - Unique authorization number
- `status` - Status (Pending/Approved/Denied/Expired)
- `is_manually_edited` - Boolean flag indicating manual edits
- `created_at` - Timestamp
- `updated_at` - Timestamp (auto-updated on changes)

### `scrape_run` table:
- `id` - Primary key
- `started_at` - Job start timestamp
- `completed_at` - Job completion timestamp
- `duration_seconds` - Scrape duration in seconds
- `records_found` - Number of records extracted
- `records_saved` - Number of records successfully saved
- `status` - Job status (running/success/failed)
- `error_message` - Error details if failed

Uses upsert logic for `patient_auth`, so running scrapes multiple times won't create duplicates.

## API Endpoints

### Dashboard
- `GET /` - Serves the SPA frontend

### Health & Stats
- `GET /health` - Health check endpoint (returns DB status, last sync time)
- `GET /api/stats` - Dashboard statistics (total records, last sync metrics)

### Authorizations
- `GET /api/authorizations` - Get all patient authorization records
- `PATCH /api/authorizations/<id>` - Update a record (marks `is_manually_edited=True`)

### Scraping
- `POST /api/scrape` - Trigger asynchronous scraping job (returns job ID)
- `GET /api/scrape/status/<job_id>` - Poll for scrape job status

## Running Locally (Without Docker)

If you want to run it directly:

```bash
pip install -r requirements.txt
# Make sure PostgreSQL is running and update .env
python app.py
```

The Flask server will start on `http://localhost:5000` (or the port specified in `FLASK_PORT`).

## Project Structure

```
.
├── app.py               # Flask REST API server
├── main.py              # Legacy CLI entry point (optional)
├── scraper.py           # Selenium automation
├── database.py          # Database operations
├── models.py            # SQLAlchemy models
├── templates/
│   └── index.html       # SPA frontend
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Container setup
├── requirements.txt     # Dependencies
├── .env.example         # Env template
└── README.md            # This file
```

## Key Features

- **RESTful API**: Clean, RESTful endpoints following best practices
- **Asynchronous Scraping**: Background job processing prevents UI blocking
- **Human-in-the-Loop**: Edit modal allows manual data correction with visual indicators
- **Instrumentation**: Scrape duration and success rate tracked in database
- **SPA Frontend**: Single page app with Fetch API, no framework overhead
- **Production-Ready**: Error handling, logging, health checks, type hints throughout
- **Schema Extension**: Added `is_manually_edited` column demonstrates database evolution

## Notes

- Uses explicit waits throughout (WebDriverWait) to handle slow portals
- Multi-stage Dockerfile for smaller image size
- Health checks ensure the app waits for DB to be ready
- Error handling with retry logic for stale elements
- All secrets live in `.env` (never committed)
- Scrape jobs run asynchronously using Python threading
- Frontend polls job status until completion
- UI updates without page refresh using Fetch API

## Troubleshooting

If the build fails with `apt-key` errors, make sure you're using the latest Dockerfile - it uses the modern GPG keyring method.

To check if data was saved:
```bash
docker compose exec postgres psql -U postgres -d valer_db -c "SELECT * FROM patient_auth;"
```

If the dashboard doesn't load:
- Verify the Flask server is running: `docker compose logs app`
- Check that port 5000 is not already in use
- Ensure the database is healthy: `docker compose ps`

To view scrape run metrics:
```bash
docker compose exec postgres psql -U postgres -d valer_db -c "SELECT * FROM scrape_run ORDER BY started_at DESC LIMIT 5;"
```

### Seeding Mock Data for Demo

To populate the `scrape_run` table with sample historical data for demonstration purposes:

```bash
# Run the seed script inside the app container
docker compose exec app python seed_scrape_runs.py

# Or if running locally (without Docker)
python seed_scrape_runs.py
```

This will create 5 mock scrape runs with varying success rates, durations, and timestamps to demonstrate the instrumentation dashboard.
