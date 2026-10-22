from fastapi.testclient import TestClient
from app.main import app

def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["ok"] is True

def test_create_and_read_project():
    with TestClient(app) as client:
        payload = {"title": "Mia Forest", "premise": "A woman finds a mysterious glowing object in a forest.", "style": "cinematic realism", "aspect_ratio": "16:9", "duration_seconds": 5}
        created = client.post("/api/projects", json=payload)
        assert created.status_code == 200
        project = created.json()
        assert project["status"] == "draft"
        fetched = client.get(f"/api/projects/{project['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["title"] == payload["title"]

def test_project_validation():
    with TestClient(app) as client:
        response = client.post("/api/projects", json={"title": "", "premise": "short"})
        assert response.status_code == 422
