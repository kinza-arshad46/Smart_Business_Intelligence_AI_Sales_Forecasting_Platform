import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Use an isolated temp SQLite DB for the test session
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db.init_db import init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_database():
    init_db()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def admin_token(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@salesbi.local", "password": "Admin@123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
