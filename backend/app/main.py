"""
Smart Business Intelligence & AI Sales Forecasting Platform
FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs available at /docs (Swagger) and /redoc.
"""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import logger
from app.db.init_db import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-ready REST API for uploading sales data, training AI "
        "forecasting models (XGBoost / LightGBM / Prophet / scikit-learn), "
        "generating predictions with confidence scores, and serving "
        "business-intelligence KPIs to the dashboard."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
    return response


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info(f"{settings.PROJECT_NAME} started in '{settings.ENVIRONMENT}' mode.")


@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "running",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
