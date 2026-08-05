# API Reference (summary)

Full interactive documentation (Swagger UI) is always available at
`GET /docs` while the backend is running, and machine-readable OpenAPI JSON
at `GET /openapi.json`. This file is a quick human-readable summary.

Base path: `/api/v1`

## Authentication (`/auth`)

| Method | Path               | Description                                     | Auth         |
| ------ | ------------------ | ----------------------------------------------- | ------------ |
| POST   | `/auth/register` | Create a new user account                       | none         |
| POST   | `/auth/login`    | OAuth2 password login → access + refresh JWT   | none         |
| POST   | `/auth/refresh`  | Exchange a refresh token for a new access token | none         |
| GET    | `/auth/me`       | Current logged-in user's profile                | Bearer token |

## Users (`/users`)

| Method | Path                    | Description                 | Auth         |
| ------ | ----------------------- | --------------------------- | ------------ |
| GET    | `/users`              | List all users              | Admin        |
| PATCH  | `/users/{id}`         | Update role / active status | Admin        |
| GET    | `/users/me/activity`  | Your own activity log       | Bearer token |
| GET    | `/users/activity/all` | Every user's activity log   | Admin        |

## Datasets (`/datasets`)

| Method | Path                                 | Description                                        | Auth                       |
| ------ | ------------------------------------ | -------------------------------------------------- | -------------------------- |
| POST   | `/datasets/upload`                 | Upload CSV/Excel, validated & stored automatically | Bearer token               |
| GET    | `/datasets`                        | List your datasets (all datasets if Admin)         | Bearer token               |
| GET    | `/datasets/{id}`                   | Dataset detail                                     | Bearer token (owner/Admin) |
| GET    | `/datasets/{id}/validation-report` | Full validation report for a dataset               | Bearer token               |
| DELETE | `/datasets/{id}`                   | Delete a dataset and its file                      | Bearer token (owner/Admin) |

## Forecasting (`/forecast`)

| Method | Path                              | Description                                | Auth         |
| ------ | --------------------------------- | ------------------------------------------ | ------------ |
| GET    | `/forecast/algorithms`          | List supported algorithms                  | Bearer token |
| POST   | `/forecast/train`               | Train & compare algorithms for a dataset   | Bearer token |
| GET    | `/forecast/models/{dataset_id}` | Compare all trained models for a dataset   | Bearer token |
| POST   | `/forecast/predict`             | Generate a forecast with confidence scores | Bearer token |

## Business Intelligence (`/kpi`, `/overview`)

| Method | Path                            | Description                                        | Auth         |
| ------ | ------------------------------- | -------------------------------------------------- | ------------ |
| GET    | `/kpi/{dataset_id}/summary`   | KPI summary card values                            | Bearer token |
| GET    | `/kpi/{dataset_id}/dashboard` | Full dashboard payload (KPIs + trend + breakdowns) | Bearer token |
| GET    | `/overview`                   | Quick-glance summary across all your datasets      | Bearer token |

## Health

| Method | Path        | Description                                  |
| ------ | ----------- | -------------------------------------------- |
| GET    | `/`       | Service info                                 |
| GET    | `/health` | Liveness probe (used by Docker healthchecks) |
