from pathlib import Path

from fastapi.testclient import TestClient

from backend.sqlmap_gui.api.app import create_app


def test_health_and_task_creation(tmp_path: Path):
    app = create_app(data_dir=tmp_path / "data", artifacts_dir=tmp_path / "artifacts", start_worker=False)
    client = TestClient(app)

    health = client.get("/api/health")
    created = client.post("/api/tasks", json={"target": "http://example.test/?id=1", "input_type": "url"})
    listed = client.get("/api/tasks")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert created.status_code == 200
    assert created.json()["status"] == "queued"
    assert listed.json()[0]["id"] == created.json()["id"]
