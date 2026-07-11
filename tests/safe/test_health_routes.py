from app import app


def test_liveness_is_minimal_and_not_cached():
    with app.test_client() as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["Cache-Control"] == "no-store"


def test_readiness_checks_database_without_exposing_details():
    with app.test_client() as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}
    assert response.headers["Cache-Control"] == "no-store"
