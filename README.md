# Culver's Store Explorer

A data pipeline and web dashboard for exploring Culver's restaurant locations, daily Flavor of the Day, and full menu details across the United States.

## Overview

This project has two main components:

1. **Data Pipeline** -- An Airflow-orchestrated ETL that scrapes Culver's public APIs daily to collect store locations, operating details, and menu data, storing everything as local CSV and JSON files.
2. **Web Interface** -- A FastAPI-powered single-page app with an interactive map, filterable store table, and a live menu browser with pricing, calories, and customization options.

## Features

- **Dashboard** with store counts, state distribution chart, Flavor of the Day rankings, and a mini-map of all locations
- **Interactive map** (Leaflet.js) with clickable markers showing store info, today's flavor, and quick links to the menu
- **Store table** with search, state filter, open/closed toggle, and pagination across 1,000+ locations
- **Menu browser** that fetches live category, item, and modifier data from Culver's public Next.js data routes, including pricing, calorie counts, and nested customization options

## Project Structure

```
culvers/
├── dags/
│   └── culvers_pipeline.py      # Airflow DAG definition
├── scripts/
│   ├── get_locations.py          # Fetch all store locations -> stores.csv
│   ├── get_store_details.py      # Fetch per-store details -> store_details.csv
│   ├── get_categories.py         # Fetch menu categories for a store
│   ├── get_category_items.py     # Fetch items in a category
│   ├── get_item_details.py       # Fetch full item detail (modifiers, nutrition)
│   ├── master_hydrator.py        # Orchestrate full menu scrape -> data/menus/*.json
│   └── download_mongo.py         # Combine per-store JSONs into culvers_full.json
├── web/
│   ├── app.py                    # FastAPI backend (store API + menu proxy)
│   ├── Dockerfile                # Container image for the web service
│   ├── templates/
│   │   └── index.html            # Single-page app shell
│   └── static/
│       ├── style.css             # Dark-themed UI styles
│       └── app.js                # Client-side logic (map, table, modals, menu)
├── data/                         # Generated at runtime (git-ignored)
│   ├── stores.csv
│   ├── store_details.csv
│   └── menus/                    # Per-store menu JSON files
├── docker-compose.yaml           # Airflow cluster + web service
├── requirements.txt              # Python dependencies
├── .env.example                  # Template for required environment variables
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for Airflow pipeline)

### Run the Web Interface Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Populate store data (run once)
cd scripts
python get_locations.py
python get_store_details.py
cd ..

# Start the web server
uvicorn web.app:app --host 127.0.0.1 --port 3000
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

Menu data is fetched live from Culver's public website when browsing. To pre-cache menus locally:

```bash
cd scripts
python master_hydrator.py
```

### Run with Docker Compose

```bash
# Copy and fill in secrets
cp .env.example .env
# Edit .env and replace all CHANGE_ME values

# Start everything (Airflow + web interface)
docker compose up -d

# Or just the web interface
docker compose up -d culvers-web
```

- Web interface: [http://localhost:3000](http://localhost:3000)
- Airflow UI: [http://localhost:8080](http://localhost:8080) (if running the full stack)

## Data Pipeline

The Airflow DAG (`culvers_data_pipeline`) runs daily and executes:

1. **fetch_store_locations** -- Calls the Culver's location API and writes `data/stores.csv`
2. **check_stores_csv_exists** -- Validates the output file
3. **fetch_store_details** -- Enriches each store with hours, flavor, owner info into `data/store_details.csv`
4. **check_store_details_csv_exists** -- Validates the enriched file

The optional `master_hydrator.py` script scrapes full menu data (categories, items, modifiers, pricing) for every store and saves per-store JSON files to `data/menus/`.

## Tech Stack

- **Backend**: Python, FastAPI, Pandas, httpx
- **Frontend**: Vanilla HTML/CSS/JS, Leaflet.js
- **Pipeline**: Apache Airflow, requests, tqdm
- **Infrastructure**: Docker, Docker Compose, PostgreSQL (Airflow metadata), Redis (Celery broker)

## Data Sources

All data is sourced from Culver's publicly accessible website and APIs. No authentication or API keys are required.

## License

This project is for personal/educational use.
