from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, datasets, forecast, kpi, dashboard

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(datasets.router)
api_router.include_router(forecast.router)
api_router.include_router(kpi.router)
api_router.include_router(dashboard.router)
