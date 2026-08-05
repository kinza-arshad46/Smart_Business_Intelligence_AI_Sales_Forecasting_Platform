import io
from datetime import date, timedelta


def _upload_60_days(client, token):
    rows = ["Order Date,Product,Category,Region,Quantity,Unit Price,Revenue"]
    start = date(2024, 1, 1)
    for i in range(60):
        d = start + timedelta(days=i)
        rev = 100 + (i % 7) * 10
        rows.append(f"{d.isoformat()},Widget,Gadgets,North,5,{rev/5},{rev}")
    csv_content = "\n".join(rows)
    files = {"file": ("sixty_days.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post("/api/v1/datasets/upload", files=files,
                        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_train_and_predict_flow(client, admin_token):
    dataset_id = _upload_60_days(client, admin_token)

    train_resp = client.post(
        "/api/v1/forecast/train",
        json={"dataset_id": dataset_id, "algorithms": ["gradient_boosting", "random_forest"],
              "tune_hyperparameters": False, "test_size": 0.2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert train_resp.status_code == 200, train_resp.text
    models = train_resp.json()
    assert len(models) >= 1
    assert any(m["is_active"] for m in models)

    predict_resp = client.post(
        "/api/v1/forecast/predict",
        json={"dataset_id": dataset_id, "horizon_days": 7},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert predict_resp.status_code == 200, predict_resp.text
    body = predict_resp.json()
    assert len(body["points"]) == 7


def test_kpi_summary(client, admin_token):
    dataset_id = _upload_60_days(client, admin_token)
    resp = client.get(f"/api/v1/kpi/{dataset_id}/summary",
                       headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_revenue"] > 0
    assert body["total_orders"] == 60
