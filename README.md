# Valer Automation POC

Production-ready Python-based automation proof-of-concept demonstrating web scraping, portal automation, and containerization. This project simulates logging into a healthcare provider portal, extracting patient authorization data, and persisting it to a PostgreSQL database.

## Architecture

The project follows a modular architecture with clear separation of concerns:

- **main.py**: Entry point and orchestration
- **scraper.py**: Selenium-based web automation
- **database.py**: SQLAlchemy session management and persistence
- **models.py**: Database schema definitions

## Prerequisites

- Docker and Docker Compose
- Git

## Quick Start

1. Clone the repository and navigate to the project directory.

2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` if you need to customize database credentials or portal settings.

4. Build and run the application:
   ```bash
   docker-compose up --build
   ```

The application will:
- Start a PostgreSQL container
- Wait for the database to be healthy
- Initialize the database schema
- Execute the automation workflow (login → extract → persist)
- Log all operations to stdout

## Environment Variables

See `.env.example` for all available configuration options:

- **Database**: `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_HOST`, `DB_PORT`
- **Portal**: `PORTAL_USERNAME`, `PORTAL_PASSWORD`
- **Selenium**: `SELENIUM_HEADLESS` (true/false)

## Database Schema

The `patient_auth` table stores patient authorization records:

- `id`: Primary key
- `patient_name`: Patient name
- `auth_number`: Unique authorization number
- `status`: Authorization status (Pending/Approved)
- `created_at`: Timestamp

## Development

To run locally without Docker:

1. Install Python 3.11+
2. Install dependencies: `pip install -r requirements.txt`
3. Set up PostgreSQL and configure `.env`
4. Run: `python main.py`

## Project Structure

```
.
├── main.py              # Entry point
├── scraper.py           # Selenium automation
├── database.py          # Database operations
├── models.py            # SQLAlchemy models
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Container orchestration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md            # This file
```

## Notes

- The scraper uses `the-internet.herokuapp.com` for demonstration purposes
- All database operations use upsert logic (merge on conflict)
- Chrome runs in headless mode by default in Docker
- The application includes comprehensive error handling and logging

