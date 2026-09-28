import os

os.environ["DATABASE_URL"] = "sqlite:///./test_fitbuddy.db"
os.environ["DEMO_MODE"] = "true"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Build your plan" in response.text


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_and_feedback():
    payload = {
        "user_id": "TEST100",
        "name": "Test User",
        "age": 21,
        "weight": 70,
        "goal": "muscle gain",
        "intensity": "medium",
        "experience_level": "beginner",
        "days_per_week": 5,
    }
    response = client.post("/api/generate-workout", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "DAY 1" in data["workout_plan"]

    response = client.post(
        "/api/feedback",
        json={"user_id": "TEST100", "feedback": "Add more cardio and one recovery day."},
    )
    assert response.status_code == 200
    assert "UPDATED USING FEEDBACK" in response.json()["updated_plan"]


def test_admin_page():
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "Test User" in response.text
