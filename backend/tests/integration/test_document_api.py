"""Document Upload API 集成测试"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_document():
    resp = client.post(
        "/api/v1/documents",
        data={"project_id": "proj_001"},
        files={"file": ("test.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["document_id"]
    assert data["task_id"]


def test_list_documents():
    resp = client.get("/api/v1/documents?project_id=proj_001")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1
