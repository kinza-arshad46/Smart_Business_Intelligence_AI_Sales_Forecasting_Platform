# KPI Definitions

These are the Key Performance Indicators implemented in
`backend/app/services/kpi_service.py` and surfaced on the dashboard
(`GET /api/v1/kpi/{dataset_id}/summary` and `/dashboard`).

| #  | KPI                                                        | Formula / Method                                  | Why it matters                                             |
| -- | ---------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------- |
| 1  | **Total Revenue**                                    | Σ revenue over the selected dataset              | Headline business size metric                              |
| 2  | **Total Units Sold**                                 | Σ quantity                                       | Volume metric, independent of pricing changes              |
| 3  | **Average Order Value (AOV)**                        | Total Revenue ÷ Total Orders                     | Tracks whether customers are spending more per transaction |
| 4  | **Total Orders**                                     | Count of transaction rows                         | Demand/traffic indicator                                   |
| 5  | **Revenue Growth — Month over Month (MoM)**         | `(this_month - last_month) / last_month × 100` | Short-term momentum                                        |
| 6  | **Revenue Growth — Year over Year (YoY)**           | `(this_year - last_year) / last_year × 100`    | Long-term trend, seasonality-adjusted                      |
| 7  | **Average Daily Revenue**                            | Total Revenue ÷ number of days in range          | Normalizes revenue for period-length comparisons           |
| 8  | **Top Performing Product**                           | Product with highest summed revenue               | Focus for inventory/marketing                              |
| 9  | **Top Performing Category**                          | Category with highest summed revenue              | Portfolio-level insight                                    |
| 10 | **Top Performing Region**                            | Region with highest summed revenue                | Where to focus sales/marketing spend                       |
| 11 | **Forecast Accuracy %**                              | `100 - MAPE` of the currently active model      | How much to trust the AI forecast                          |
| 12 | **Sales Target Achievement %** (optional)            | `Total Revenue ÷ user-supplied target × 100`  | Progress toward a business goal                            |
| 13 | **Revenue Trend**                                    | Revenue resampled Daily / Weekly / Monthly        | Powers the main dashboard trend chart                      |
| 14 | **Revenue Breakdown by Category / Region / Product** | Grouped sum + % share of total                    | Powers pie/bar charts and highlights concentration risk    |

## Adding a new KPI

1. Add the calculation to `compute_kpis()` (or a new function) in
   `backend/app/services/kpi_service.py`.
2. Add the field to `KPISummary` in `backend/app/schemas/kpi.py`.
3. It will automatically appear in the `/kpi/{dataset_id}/summary` and
   `/kpi/{dataset_id}/dashboard` API responses.
4. Add a `st.metric(...)` for it in `dashboard/app.py` → `page_dashboard()`.
