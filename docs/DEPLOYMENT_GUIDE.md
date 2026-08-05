# Deployment Guide

## 1. Containerize (already done for you)

Both services ship with production Dockerfiles:

- `backend/Dockerfile` — FastAPI + Uvicorn, exposes port 8000, includes a healthcheck.
- `dashboard/Dockerfile` — Streamlit, exposes port 8501, includes a healthcheck.

Build and test locally before deploying:

```bash
docker compose up --build
```

## 2. Environment configuration for production

Set these as environment variables / secrets in your cloud provider (never commit them):

```
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<db>
USE_REDIS=true
REDIS_URL=redis://<redis-host>:6379/0
CORS_ORIGINS=["https://your-dashboard-domain.com"]
```

## 3. CI/CD (GitHub Actions)

`.github/workflows/ci-cd.yml` already runs on every push/PR to `main`/`develop`:

1. **test-backend** — installs dependencies, lints with flake8, runs the pytest suite.
2. **build-images** — builds both Docker images to confirm they build cleanly.
3. **deploy** — placeholder job that only runs on pushes to `main`. Fill in the
   provider-specific commands below and store credentials as GitHub Actions
   **repository secrets** (Settings → Secrets and variables → Actions).

## 4. Cloud deployment options

### AWS (ECS Fargate + RDS)

1. Push images to Amazon ECR:
   ```bash
   aws ecr create-repository --repository-name sales-bi-backend
   docker tag sales-bi-backend:ci <account>.dkr.ecr.<region>.amazonaws.com/sales-bi-backend
   docker push <account>.dkr.ecr.<region>.amazonaws.com/sales-bi-backend
   ```
2. Provision a PostgreSQL instance with **RDS**; use its endpoint as `DATABASE_URL`.
3. Create an **ECS Fargate service** per container (backend, dashboard) behind an
   **Application Load Balancer**; put secrets in **AWS Secrets Manager** and
   reference them from the task definition.
4. Optional: **ElastiCache (Redis)** for caching, **CloudWatch** for logs/monitoring.

### Azure (Container Apps + Azure Database for PostgreSQL)

1. Push images to **Azure Container Registry**.
2. Provision **Azure Database for PostgreSQL - Flexible Server**.
3. Deploy each container with `az containerapp up`, wiring `DATABASE_URL` and
   `SECRET_KEY` as Container Apps secrets.
4. Use **Azure Monitor / Log Analytics** for logging.

### GCP (Cloud Run + Cloud SQL)

1. Push images to **Artifact Registry**.
2. Provision **Cloud SQL for PostgreSQL**; connect via the Cloud SQL Auth Proxy
   or a private IP.
3. `gcloud run deploy sales-bi-backend --image ... --set-env-vars ...`
4. Use **Cloud Logging** / **Cloud Monitoring** for observability.

## 5. Database migrations in production

The app auto-creates tables on startup via `init_db()` for convenience in
development. For production, adopt **Alembic** (already in `requirements.txt`)
for versioned, reviewable migrations instead of relying on `create_all`:

```bash
alembic init alembic
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## 6. Scheduled model retraining

`APScheduler` is included in `requirements.txt`. To enable periodic retraining,
add a scheduler in `app/main.py`'s startup event that calls
`forecasting.train_models_for_dataset(...)` for each active dataset on the
cron expression in `settings.MODEL_RETRAIN_CRON` (default: daily at 2 AM).
In a multi-instance deployment, run this in a single dedicated worker
process (not in every API replica) to avoid duplicate training jobs.

## 7. Logging & monitoring

- Application logs are written to `backend/logs/app.log` (rotating, 5MB × 5 files)
  and to stdout — capture stdout in your platform's log aggregator
  (CloudWatch / Azure Monitor / Cloud Logging / ELK).
- `/health` endpoint is wired to each Dockerfile's `HEALTHCHECK` and can be
  used as a load balancer / orchestrator liveness probe.
- Every request is logged with method, path, status code, and duration.

## 8. Security checklist before going live

- [ ] Change the default admin password (`admin@salesbi.local` / `Admin@123`)
- [ ] Set a strong, unique `SECRET_KEY`
- [ ] Set `DEBUG=false`
- [ ] Restrict `CORS_ORIGINS` to your actual dashboard domain
- [ ] Use HTTPS/TLS termination (load balancer or reverse proxy)
- [ ] Put the database behind a private network / security group
- [ ] Rotate JWT secret and enforce token expiry (already defaulted to 60 min access / 7 day refresh)
