"""Phase 5 role-enforcement tests: one forbidden-access case per role (Section H).

Runs the real FastAPI app against the isolated small test DB (not the demo
database) via the shared `api_client`/`demo_users` fixtures in conftest.py.
"""

from fastapi.testclient import TestClient


def _login(client: TestClient, email: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_unauthenticated_request_is_401(api_client) -> None:
    response = api_client.get("/api/v1/students")
    assert response.status_code == 401


def test_student_forbidden_from_creating_students(api_client, demo_users) -> None:
    headers = _login(api_client, "role-student@university.edu.ng")
    response = api_client.post("/api/v1/students", headers=headers, json={})
    assert response.status_code == 403


def test_student_forbidden_from_viewing_another_students_record(api_client, demo_users) -> None:
    headers = _login(api_client, "role-student@university.edu.ng")
    # student_id=1 comes from the small dataset seeded by the trained_registry
    # fixture and is guaranteed to exist but not belong to this student user
    # (whose own record is demo_users["other_student_id"], a freshly created row).
    assert demo_users["other_student_id"] != 1
    response = api_client.get("/api/v1/students/1", headers=headers)
    assert response.status_code == 403


def test_student_can_view_own_record(api_client, demo_users) -> None:
    headers = _login(api_client, "role-student@university.edu.ng")
    own_id = demo_users["other_student_id"]
    response = api_client.get(f"/api/v1/students/{own_id}", headers=headers)
    assert response.status_code == 200


def test_lecturer_forbidden_from_activating_models(api_client, demo_users) -> None:
    headers = _login(api_client, "role-lecturer@university.edu.ng")
    response = api_client.post("/api/v1/models/risk_classification__logistic_regression/activate", headers=headers, json={})
    assert response.status_code == 403


def test_lecturer_forbidden_from_creating_interventions(api_client, demo_users) -> None:
    headers = _login(api_client, "role-lecturer@university.edu.ng")
    response = api_client.post(
        "/api/v1/interventions", headers=headers,
        json={"student_id": demo_users["other_student_id"], "action_type": "counselling"},
    )
    assert response.status_code == 403


def test_adviser_forbidden_from_writing_scores(api_client, demo_users) -> None:
    headers = _login(api_client, "role-adviser@university.edu.ng")
    response = api_client.put("/api/v1/enrolments/1/scores", headers=headers, json={"ca_score": 20})
    assert response.status_code == 403


def test_adviser_forbidden_from_retraining_models(api_client, demo_users) -> None:
    headers = _login(api_client, "role-adviser@university.edu.ng")
    response = api_client.post("/api/v1/models/retrain", headers=headers, json={})
    assert response.status_code == 403


def test_admin_is_not_forbidden_from_admin_only_action(api_client, demo_users) -> None:
    """Sanity check the other direction: admin isn't accidentally caught by the same 403s."""
    headers = _login(api_client, "role-admin@university.edu.ng")
    response = api_client.post("/api/v1/models/risk_classification__logistic_regression/activate", headers=headers, json={})
    assert response.status_code == 200
