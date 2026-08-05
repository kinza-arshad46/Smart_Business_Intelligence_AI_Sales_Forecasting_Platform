"""
Smart Business Intelligence & AI Sales Forecasting Platform - Dashboard
A pure-Python (Streamlit + Plotly) frontend that talks to the FastAPI
backend over its REST API. Run with:

    streamlit run dashboard/app.py

Configure the backend URL via the BACKEND_URL environment variable
(defaults to http://localhost:8000).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
import sys
from pathlib import Path

# Project root folder ko Python path mein add karein
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# Aapke baaki imports niche waise hi rahain ge...
from backend.app.models import user
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from backend.app.models import user

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API = f"{BACKEND_URL}/api/v1"

st.set_page_config(
    page_title="Smart BI & Sales Forecasting",
    page_icon="📊",
    layout="wide",
)

# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
for key, default in {
    "access_token": None,
    "refresh_token": None,
    "user": None,
    "selected_dataset_id": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


def api_get(path, **kwargs):
    r = requests.get(f"{API}{path}", headers=auth_headers(), timeout=60, **kwargs)
    return r


def api_post(path, json=None, files=None, data=None, headers_override=None):
    headers = headers_override if headers_override is not None else auth_headers()
    r = requests.post(f"{API}{path}", json=json, files=files, data=data, headers=headers, timeout=120)
    return r


def api_patch(path, json=None):
    r = requests.patch(f"{API}{path}", json=json, headers=auth_headers(), timeout=60)
    return r


def api_delete(path):
    r = requests.delete(f"{API}{path}", headers=auth_headers(), timeout=60)
    return r


# ----------------------------------------------------------------------
# Auth screens
# ----------------------------------------------------------------------
def login_screen():
    st.title("📊 Smart Business Intelligence & AI Sales Forecasting Platform")
    st.caption("Sign in to continue")

    try:
        requests.get(BACKEND_URL, timeout=5)
    except requests.exceptions.ConnectionError:
        st.error(
            f"Cannot reach the API backend at {BACKEND_URL}. "
            f"Make sure it's running: `uvicorn app.main:app --reload` (from the backend/ folder)."
        )

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", value="admin@salesbi.local")
            password = st.text_input("Password", type="password", value="Admin@123")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            resp = api_post("/auth/login", data={"username": email, "password": password},
                             headers_override={})
            if resp.status_code == 200:
                body = resp.json()
                st.session_state.access_token = body["access_token"]
                st.session_state.refresh_token = body["refresh_token"]
                me = requests.get(f"{API}/auth/me", headers=auth_headers()).json()
                st.session_state.user = me
                st.rerun()
            else:
                st.error(f"Login failed: {resp.json().get('detail', resp.text)}")

        st.info("Default admin account: **admin@salesbi.local** / **Admin@123** "
                "(seeded automatically on first backend startup). Change this password in production.")

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password (min 8 chars)", type="password", key="reg_password")
            reg_submitted = st.form_submit_button("Create account", use_container_width=True)

        if reg_submitted:
            resp = api_post("/auth/register", json={
                "full_name": full_name, "email": reg_email, "password": reg_password,
            }, headers_override={})
            if resp.status_code == 201:
                st.success("Account created. Please log in from the Login tab.")
            else:
                st.error(f"Registration failed: {resp.json().get('detail', resp.text)}")


# ----------------------------------------------------------------------
# Sidebar / navigation
# ----------------------------------------------------------------------
def sidebar_nav():
    user = st.session_state.user
    st.sidebar.title("📊 Sales BI Platform")
  
# New Fixed Line:
    user_name = user.get('full_name') or user.get('name') or user.get('username') or "User"
    user_email = user.get('email', '')
    user_role = user.get('role', 'User')

    st.sidebar.markdown(f"**{user_name}**  \n{user_email}  \nRole: `{user_role}`")
    st.sidebar.divider()

    pages = ["Dashboard", "Upload Data", "Forecasting", "My Activity"]
    if user.get("role", "").lower() == "admin":
        pages.append("User Management")

    page = st.sidebar.radio("Navigate", pages, label_visibility="collapsed")

    st.sidebar.divider()
    if st.sidebar.button("Log out", use_container_width=True):
        for key in ("access_token", "refresh_token", "user", "selected_dataset_id"):
            st.session_state[key] = None
        st.rerun()

    return page


def dataset_selector():
    resp = api_get("/datasets")
    if resp.status_code != 200:
        st.warning("Could not load datasets.")
        return None
    datasets = resp.json()
    if not datasets:
        st.info("No datasets yet. Go to **Upload Data** to add your sales history.")
        return None

    options = {f"#{d['id']} — {d['original_filename']} ({d['row_count']} rows)": d["id"] for d in datasets}
    label = st.selectbox("Dataset", list(options.keys()))
    return options[label]


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------
def page_dashboard():
    st.header("Business Intelligence Dashboard")

    dataset_id = dataset_selector()
    if not dataset_id:
        return

    col_freq, col_target = st.columns([1, 1])
    with col_freq:
        freq_label = st.radio("Trend granularity", ["Daily", "Weekly", "Monthly"], horizontal=True)
        freq = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}[freq_label]
    with col_target:
        target = st.number_input("Sales target (optional, for target-achievement KPI)", min_value=0.0, value=0.0, step=1000.0)

    params = {"freq": freq}
    if target > 0:
        params["sales_target"] = target

    resp = api_get(f"/kpi/{dataset_id}/dashboard", params=params)
    if resp.status_code != 200:
        st.error(f"Failed to load dashboard data: {resp.text}")
        return

    data = resp.json()
    kpis = data["kpis"]

    st.subheader("Key Performance Indicators")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}",
               f"{kpis['revenue_growth_mom_pct']}% MoM" if kpis['revenue_growth_mom_pct'] is not None else None)
    c2.metric("Total Units Sold", f"{kpis['total_units_sold']:,.0f}")
    c3.metric("Avg Order Value", f"${kpis['average_order_value']:,.2f}")
    c4.metric("Total Orders", f"{kpis['total_orders']:,}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Avg Daily Revenue", f"${kpis['average_daily_revenue']:,.0f}")
    c6.metric("YoY Growth", f"{kpis['revenue_growth_yoy_pct']}%" if kpis['revenue_growth_yoy_pct'] is not None else "N/A")
    c7.metric("Forecast Accuracy", f"{kpis['forecast_accuracy_pct']}%" if kpis['forecast_accuracy_pct'] is not None else "Train a model first")
    if kpis.get("sales_target_achievement_pct") is not None:
        c8.metric("Target Achievement", f"{kpis['sales_target_achievement_pct']}%")
    else:
        c8.metric("Top Category", kpis["top_category"] or "—")

    st.caption(f"Top Product: **{kpis['top_product']}** | Top Category: **{kpis['top_category']}** | "
               f"Top Region: **{kpis['top_region']}**")

    st.divider()
    st.subheader("Revenue Trend")
    trend_df = pd.DataFrame(data["revenue_trend"])
    if not trend_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_df["period"], y=trend_df["revenue"], mode="lines", name="Revenue", fill="tozeroy"))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350)
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.subheader("By Category")
        cat_df = pd.DataFrame(data["by_category"])
        if not cat_df.empty:
            fig = px.pie(cat_df, names="label", values="revenue", hole=0.4)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.subheader("By Region")
        reg_df = pd.DataFrame(data["by_region"])
        if not reg_df.empty:
            fig = px.bar(reg_df, x="label", y="revenue")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
    with col_c:
        st.subheader("Top Products")
        prod_df = pd.DataFrame(data["by_product"])
        if not prod_df.empty:
            fig = px.bar(prod_df, x="revenue", y="label", orientation="h")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)


def page_upload():
    st.header("Upload & Manage Datasets")

    st.subheader("Upload a new file")
    uploaded_file = st.file_uploader("CSV or Excel file with your sales history", type=["csv", "xlsx", "xls"])
    st.caption(
        "Expected columns (flexible naming accepted): Date, Product, Category, Region, "
        "Quantity, Unit Price, Revenue. Missing Revenue is auto-calculated from Quantity × Unit Price."
    )

    if uploaded_file is not None and st.button("Upload & Validate", type="primary"):
        with st.spinner("Uploading, validating and processing your file..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            resp = api_post("/datasets/upload", files=files)
        if resp.status_code == 200:
            body = resp.json()
            st.success(f"Uploaded successfully: {body['row_count']} rows processed.")
            st.session_state.selected_dataset_id = body["id"]
        else:
            st.error("Upload failed:")
            st.json(resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text)

    st.divider()
    st.subheader("Your datasets")
    resp = api_get("/datasets")
    if resp.status_code == 200:
        datasets = resp.json()
        if datasets:
            df = pd.DataFrame(datasets)[["id", "original_filename", "row_count", "status", "uploaded_at"]]
            st.dataframe(df, use_container_width=True, hide_index=True)

            del_id = st.number_input("Dataset ID to delete", min_value=0, step=1, value=0)
            if st.button("Delete dataset") and del_id > 0:
                d = api_delete(f"/datasets/{del_id}")
                if d.status_code == 200:
                    st.success("Deleted.")
                    st.rerun()
                else:
                    st.error(d.text)
        else:
            st.info("No datasets uploaded yet.")


def page_forecasting():
    st.header("AI Sales Forecasting")

    dataset_id = dataset_selector()
    if not dataset_id:
        return

    tab_train, tab_predict, tab_compare = st.tabs(["Train Models", "Get Forecast", "Compare Models"])

    with tab_train:
        st.write("Train and automatically compare multiple algorithms; the best one (lowest MAE) "
                 "is activated for predictions.")
        algo_options = ["gradient_boosting", "random_forest", "xgboost", "lightgbm", "prophet"]
        chosen = st.multiselect("Algorithms to train", algo_options, default=algo_options)
        tune = st.checkbox("Enable hyperparameter tuning (slower, more accurate)", value=False)
        test_size = st.slider("Test set size", 0.1, 0.4, 0.2, 0.05)

        if st.button("Train Models", type="primary"):
            with st.spinner("Training models... this can take a while for large datasets."):
                resp = api_post("/forecast/train", json={
                    "dataset_id": dataset_id, "algorithms": chosen,
                    "tune_hyperparameters": tune, "test_size": test_size,
                })
            if resp.status_code == 200:
                results = resp.json()
                st.success("Training complete.")
                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            else:
                st.error(resp.json().get("detail", resp.text))

    with tab_predict:
        horizon = st.slider("Forecast horizon (days)", 7, 180, 30)
        col1, col2 = st.columns(2)
        category = col1.text_input("Filter by category (optional)")
        region = col2.text_input("Filter by region (optional)")

        if st.button("Generate Forecast", type="primary"):
            with st.spinner("Generating forecast..."):
                resp = api_post("/forecast/predict", json={
                    "dataset_id": dataset_id, "horizon_days": horizon,
                    "category": category or None, "region": region or None,
                })
            if resp.status_code == 200:
                body = resp.json()
                st.success(f"Forecast generated using **{body['algorithm']}** "
                           f"(MAE={body['evaluation']['mae']:.2f}, MAPE={body['evaluation']['mape']:.1f}%)")
                pts = pd.DataFrame(body["points"])
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=pts["date"], y=pts["upper_bound"], line=dict(width=0),
                                          showlegend=False, hoverinfo="skip"))
                fig.add_trace(go.Scatter(x=pts["date"], y=pts["lower_bound"], line=dict(width=0),
                                          fill="tonexty", fillcolor="rgba(99,110,250,0.2)",
                                          name="Confidence band", hoverinfo="skip"))
                fig.add_trace(go.Scatter(x=pts["date"], y=pts["predicted_revenue"], mode="lines+markers",
                                          name="Predicted Revenue", line=dict(color="royalblue")))
                fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(pts, use_container_width=True, hide_index=True)
            else:
                st.error(resp.json().get("detail", resp.text))

    with tab_compare:
        resp = api_get(f"/forecast/models/{dataset_id}")
        if resp.status_code == 200:
            models = resp.json()
            if models:
                df = pd.DataFrame(models)
                st.dataframe(df, use_container_width=True, hide_index=True)
                fig = px.bar(df, x="algorithm", y="mae", color="version",
                             title="Model comparison by MAE (lower is better)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No models trained yet for this dataset.")


def page_activity():
    st.header("My Activity Log")
    resp = api_get("/users/me/activity")
    if resp.status_code == 200:
        logs = resp.json()
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("No activity recorded yet.")


def page_user_management():
    st.header("User Management (Admin)")

    resp = api_get("/users")
    if resp.status_code == 200:
        users = resp.json()
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

        st.subheader("Update a user")
        user_id = st.number_input("User ID", min_value=1, step=1)
        col1, col2 = st.columns(2)
        new_role = col1.selectbox("Role", ["user", "admin"])
        new_active = col2.selectbox("Active", [True, False])
        if st.button("Apply update"):
            r = api_patch(f"/users/{user_id}", json={"role": new_role, "is_active": new_active})
            if r.status_code == 200:
                st.success("Updated.")
                st.rerun()
            else:
                st.error(r.text)

    st.divider()
    st.subheader("All Users' Activity Log")
    resp = api_get("/users/activity/all")
    if resp.status_code == 200:
        logs = resp.json()
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    if not st.session_state.access_token:
        login_screen()
        return

    page = sidebar_nav()

    if page == "Dashboard":
        page_dashboard()
    elif page == "Upload Data":
        page_upload()
    elif page == "Forecasting":
        page_forecasting()
    elif page == "My Activity":
        page_activity()
    elif page == "User Management":
        page_user_management()


if __name__ == "__main__":
    main()
