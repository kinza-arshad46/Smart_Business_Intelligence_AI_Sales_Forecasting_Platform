"""
Declarative base + a place that imports every ORM model so that
Base.metadata.create_all() (used by init_db.py) knows about all tables.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so Alembic / create_all can discover them.
# from app.models.user import User          # noqa: E402,F401
# from ..models.user import User
# from ..models.dataset import Dataset
# from ..models.sales import SalesRecord
# from ..models.ml_model import MLModel
# from ..models.prediction import Prediction