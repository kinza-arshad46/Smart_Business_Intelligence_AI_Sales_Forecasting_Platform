import io


def test_upload_valid_csv(client, admin_token):
    csv_content = (
        "Order Date,Product,Category,Region,Quantity,Unit Price,Revenue\n"
        "2024-01-01,Widget,Gadgets,North,5,10,50\n"
        "2024-01-02,Widget,Gadgets,North,3,10,30\n"
        "2024-01-03,Gizmo,Gadgets,South,2,20,40\n"
    )
    files = {"file": ("test_sales.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["row_count"] == 3
    assert body["status"] == "processed"


def test_upload_rejects_bad_extension(client, admin_token):
    files = {"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")}
    resp = client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


def test_list_datasets_requires_auth(client):
    resp = client.get("/api/v1/datasets")
    assert resp.status_code == 401
