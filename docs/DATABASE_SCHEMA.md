# Database Schema

Works identically on SQLite (dev) and PostgreSQL (production) via SQLAlchemy.

## `users`

| Column          | Type                     | Notes                                  |
| --------------- | ------------------------ | -------------------------------------- |
| id              | Integer, PK              |                                        |
| full_name       | String(120)              |                                        |
| email           | String(255), unique      | login identifier                       |
| hashed_password | String(255)              | bcrypt (or PBKDF2 fallback)            |
| role            | Enum(`admin`,`user`) | role-based access control              |
| is_active       | Boolean                  | disable an account without deleting it |
| created_at      | DateTime                 |                                        |

## `datasets`

| Column            | Type                                                                  | Notes                              |
| ----------------- | --------------------------------------------------------------------- | ---------------------------------- |
| id                | Integer, PK                                                           |                                    |
| owner_id          | FK → users.id                                                        |                                    |
| filename          | String(255)                                                           | stored filename on disk            |
| original_filename | String(255)                                                           | as uploaded by the user            |
| file_path         | String(500)                                                           |                                    |
| row_count         | Integer                                                               | rows successfully ingested         |
| status            | Enum(`uploaded`,`validating`,`valid`,`invalid`,`processed`) |                                    |
| validation_report | Text (JSON)                                                           | detected columns, warnings, errors |
| uploaded_at       | DateTime                                                              |                                    |

## `sales_records`

| Column     | Type                 | Notes                                          |
| ---------- | -------------------- | ---------------------------------------------- |
| id         | Integer, PK          |                                                |
| dataset_id | FK → datasets.id    |                                                |
| order_date | Date, indexed        |                                                |
| product    | String(255), indexed |                                                |
| category   | String(120), indexed |                                                |
| region     | String(120), indexed |                                                |
| quantity   | Float                |                                                |
| unit_price | Float                |                                                |
| revenue    | Float                | derived if missing from quantity × unit_price |
| cost       | Float, nullable      | used for potential margin KPIs                 |
| created_at | DateTime             |                                                |

## `ml_models`

Model registry: one row per trained algorithm per training run.

| Column              | Type                                                 | Notes                                                                                |
| ------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| id                  | Integer, PK                                          |                                                                                      |
| dataset_id          | FK → datasets.id                                    |                                                                                      |
| algorithm           | String(50)                                           | `xgboost` / `lightgbm` / `prophet` / `random_forest` / `gradient_boosting` |
| version             | String(20)                                           | timestamp + random suffix, groups models trained together                            |
| file_path           | String(500)                                          | serialized model on disk (joblib/pickle)                                             |
| status              | Enum(`training`,`ready`,`failed`,`archived`) |                                                                                      |
| mae, rmse, mape, r2 | Float                                                | evaluation metrics on held-out test split                                            |
| hyperparameters     | Text (JSON)                                          |                                                                                      |
| is_active           | Boolean                                              | the model currently used by `/forecast/predict`                                    |
| trained_at          | DateTime                                             |                                                                                      |

## `predictions`

| Column                    | Type               | Notes                                         |
| ------------------------- | ------------------ | --------------------------------------------- |
| id                        | Integer, PK        |                                               |
| model_id                  | FK → ml_models.id |                                               |
| target_date               | Date, indexed      |                                               |
| predicted_revenue         | Float              |                                               |
| lower_bound / upper_bound | Float              | confidence interval                           |
| confidence_score          | Float              | 0-1, derived from model MAPE                  |
| segment                   | String(120)        | which category/region filter was used, if any |
| created_at                | DateTime           |                                               |

## `activity_logs`

| Column     | Type                 | Notes                                                                    |
| ---------- | -------------------- | ------------------------------------------------------------------------ |
| id         | Integer, PK          |                                                                          |
| user_id    | FK → users.id       |                                                                          |
| action     | String(100)          | e.g.`login`, `dataset_upload`, `model_train`, `forecast_predict` |
| details    | Text (JSON)          | action-specific metadata                                                 |
| ip_address | String(64), nullable |                                                                          |
| created_at | DateTime             |                                                                          |

## Entity relationships

```
users 1───* datasets 1───* sales_records
                    │
                    └──* ml_models 1───* predictions

users 1───* activity_logs
```
