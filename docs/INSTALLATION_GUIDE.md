# Installation Guide

## Prerequisites

- Python 3.11+ (3.10 also works)
- pip
- (Optional, for full production setup) Docker & Docker Compose
- (Optional) PostgreSQL 14+ if not using Docker for the database
- (Optional) Redis if you want caching / background scheduling enabled

## Option A — Local development (SQLite, fastest to try)

1. **Clone/extract the project**, then set up the backend:

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate          # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Configure environment variables**:

   ```bash
   cp .env.example .env
   ```

   The defaults work out of the box (SQLite database file, debug mode on).
   For anything beyond local testing, generate a real secret key:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   and put it in `.env` as `SECRET_KEY=...`.
3. **Generate sample data and initialize the database**:

   ```bash
   python scripts/generate_sample_csv.py
   python scripts/seed_sample_data.py
   ```
4. **Run the API**:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Tables are created automatically on startup, and a default admin account
   is seeded: `admin@salesbi.local` / `Admin@123`.

   Visit http://localhost:8000/docs for interactive Swagger documentation.
5. **Run the dashboard** (separate terminal):

   ```bash
   cd dashboard
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

   Visit http://localhost:8501.
6. **Run the test suite**:

   ```bash
   cd backend
   pytest -v
   ```

## Option B — Docker Compose (recommended for a production-like setup)

Requires Docker + Docker Compose installed.

```bash
docker compose up --build
```

This launches:

- `postgres` — PostgreSQL 16 database
- `redis` — Redis cache
- `backend` — FastAPI app on port **8000**
- `dashboard` — Streamlit dashboard on port **8501**

The backend automatically connects to the `postgres` container using the
`DATABASE_URL` set in `docker-compose.yml` — no manual DB setup required.

To stop:

```bash
docker compose down
```

To also remove stored data volumes:

```bash
docker compose down -v
```

## Option C — Connect to your own PostgreSQL instance (no Docker)

1. Create a database and user:

   ```sql
   CREATE DATABASE sales_bi;
   CREATE USER sales_bi_user WITH PASSWORD 'strong_password';
   GRANT ALL PRIVILEGES ON DATABASE sales_bi TO sales_bi_user;
   ```
2. In `backend/.env`, set:

   ```
   DATABASE_URL=postgresql+psycopg2://sales_bi_user:strong_password@localhost:5432/sales_bi
   ```
3. Start the backend as in Option A step 4 — tables are created automatically.

## Troubleshooting

| Problem                                              | Fix                                                                                                                                                             |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError` for xgboost/lightgbm/prophet | These are optional;`pip install -r requirements.txt` installs them. If install fails on your OS, the platform still works using scikit-learn algorithms only. |
| `externally-managed-environment` pip error (Linux) | Use a virtual environment (`python -m venv venv`) as shown above, rather than installing system-wide.                                                         |
| Dashboard shows "Cannot reach the API backend"       | Make sure the backend is running and `BACKEND_URL` (dashboard env var) matches its address — defaults to `http://localhost:8000`.                          |
| Prophet fails to install (needs a C++ compiler)      | On Linux:`apt install build-essential`. On Windows, installing via `conda install -c conda-forge prophet` is usually more reliable than pip.                |
| Upload rejected as "invalid"                         | Check the returned `validation_report` — it lists missing/unrecognized columns and any dropped rows so you can fix the source file.                          |
