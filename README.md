# Smart Business Intelligence & AI Sales Forecasting Platform

A production-ready data science application for sales forecasting, KPI monitoring,
and business intelligence — built entirely in Python.

## What's included

| Area             | Technology                                                                       |
| ---------------- | -------------------------------------------------------------------------------- |
| Backend API      | FastAPI (REST, JWT auth, role-based access, auto-generated docs)                 |
| Machine Learning | Scikit-learn, XGBoost, LightGBM, Prophet (multi-algorithm training & comparison) |
| Database         | PostgreSQL (production) / SQLite (local dev, zero setup) via SQLAlchemy          |
| Dashboard        | Streamlit + Plotly (interactive charts & filters)                                |
| Deployment       | Docker, Docker Compose, GitHub Actions CI/CD                                     |

## Project structure

```
smart-bi-forecast/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── main.py          App entrypoint
│   │   ├── core/            Config, security (JWT/password hashing), logging
│   │   ├── db/               SQLAlchemy engine/session, table creation, seeding
│   │   ├── models/           ORM models (User, Dataset, SalesRecord, MLModel, Prediction, ActivityLog)
│   │   ├── schemas/          Pydantic request/response schemas
│   │   ├── api/v1/endpoints/ REST endpoints (auth, users, datasets, forecast, kpi, dashboard)
│   │   ├── services/         Business logic (data validation, feature engineering, forecasting, KPIs)
│   │   └── ml/                Model training, evaluation, and persistence
│   ├── scripts/               Sample data generator, DB seeding
│   ├── tests/                 Pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/                Streamlit BI dashboard (talks to the API)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── docs/                     Additional documentation
├── .github/workflows/        CI/CD pipeline
├── docker-compose.yml        Full stack: Postgres + Redis + backend + dashboard
└── .env.example
```

## Quick start (local, no Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Generate ~2 years of sample sales data + initialize the database
python scripts/generate_sample_csv.py
python scripts/seed_sample_data.py

# Start the API (creates tables + a default admin user automatically)
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs
Default admin login: `admin@salesbi.local` / `Admin@123` — **change this immediately**.

In a second terminal, start the dashboard:

```bash
cd dashboard
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Dashboard: http://localhost:8501

Then in the dashboard: **Upload Data** → select `backend/data/sample/sample_sales.csv` → **Forecasting** → Train Models → Get Forecast.

## Quick start (Docker Compose — full production-like stack)

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, the FastAPI backend (port 8000), and the Streamlit
dashboard (port 8501), fully wired together.

## Core features

- **Data Management**: CSV/Excel upload with flexible column-name detection,
  automated validation & cleaning, automated feature engineering (calendar,
  lag, rolling-window features), storage in PostgreSQL/SQLite.
- **Machine Learning**: trains and compares Gradient Boosting, Random Forest,
  XGBoost, LightGBM, and Prophet; picks the best model by MAE automatically;
  optional hyperparameter tuning; every prediction includes a confidence score.
- **Business Intelligence KPIs**: see `docs/KPI_DEFINITIONS.md` for the full list.
- **REST API**: FastAPI with interactive Swagger docs at `/docs`, JWT auth,
  dataset upload endpoint, prediction endpoint.
- **User Management**: registration/login, Admin vs User roles, per-user and
  platform-wide activity logs.
- **Deployment**: Dockerfiles for backend & dashboard, `docker-compose.yml`
  for the full stack, GitHub Actions CI/CD pipeline (lint → test → build → deploy).

## Reliability note (why this "just runs")

`backend/app/ml/trainer.py` imports `xgboost`, `lightgbm`, and `prophet` lazily,
inside try/except blocks. If any of those libraries aren't installed in your
environment, the platform automatically skips that algorithm (with a log
warning) and keeps training with whichever ones are available — it never
crashes the training endpoint. Install everything in `requirements.txt` to
enable all five algorithms.

## Documentation

- `docs/INSTALLATION_GUIDE.md` — step-by-step setup (local + Docker)
- `docs/DEPLOYMENT_GUIDE.md` — deploying to AWS / Azure / GCP
- `docs/DATABASE_SCHEMA.md` — full table/column reference
- `docs/API_REFERENCE.md` — endpoint summary (full interactive docs at `/docs`)
- `docs/KPI_DEFINITIONS.md` — every KPI, how it's calculated, and why it matters

## Default credentials (change immediately after first login)

- Email: `admin@salesbi.local`
- Password: `Admin@123`
