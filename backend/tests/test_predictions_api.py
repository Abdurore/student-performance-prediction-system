"""Endpoint-level tests for the predictions router that aren't about the
role-permission boundary (test_api_roles.py) or a single service function
in isolation (test_prediction_service.py) -- specifically, that
POST /predictions/batch's predicted_gpa is real inference consistent with
POST /predictions/student/{id}, not a leftover null.
"""

import pytest
from fastapi.testclient import TestClient

from app.services.prediction_service import bulk_risk_scores


def _login(client: TestClient, email: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_batch_predicted_gpa_matches_single_student_prediction(api_client, demo_users) -> None:
    headers = _login(api_client, "role-admin@university.edu.ng")
    student_id = int(bulk_risk_scores()["student_id"].iloc[0])

    batch_response = api_client.post("/api/v1/predictions/batch", headers=headers, json={"student_ids": [student_id]})
    assert batch_response.status_code == 200, batch_response.text
    batch_row = batch_response.json()["results"][0]
    assert batch_row["student_id"] == student_id
    assert batch_row["error"] is None
    assert batch_row["predicted_gpa"] is not None

    single_response = api_client.post(f"/api/v1/predictions/student/{student_id}", headers=headers)
    assert single_response.status_code == 200, single_response.text
    single_gpa = single_response.json()["gpa"]["predicted_gpa"]

    assert batch_row["predicted_gpa"] == pytest.approx(single_gpa, abs=1e-6)


def test_batch_predicted_gpa_is_null_only_for_rows_that_error(api_client, demo_users) -> None:
    headers = _login(api_client, "role-admin@university.edu.ng")
    ongoing_ids = bulk_risk_scores()["student_id"].tolist()
    # A mix of real ongoing-enrolment students (should succeed) and one
    # unknown id (should error).
    requested_ids = ongoing_ids[:5] + [999_999]

    response = api_client.post("/api/v1/predictions/batch", headers=headers, json={"student_ids": requested_ids})
    assert response.status_code == 200, response.text

    results = response.json()["results"]
    assert any(row["error"] is not None for row in results)
    assert any(row["error"] is None for row in results)
    for row in results:
        if row["error"] is None:
            assert row["predicted_gpa"] is not None
        else:
            assert row["predicted_gpa"] is None


def test_batch_with_null_student_ids_predicts_for_every_student_as_admin(api_client, demo_users, small_db_engine) -> None:
    """`student_ids: null` means "predict everyone in scope" per docs/api.md.
    For an admin (unrestricted scope), that path used to build the id list
    with `[s.id for s in session.exec(select(Student.id)).all()]` -- but
    selecting a single column already returns plain ints, not Student rows,
    so `s.id` raised AttributeError on every call. Asserts the endpoint now
    succeeds and covers every seeded student rather than a subset.
    """
    from sqlmodel import Session, select

    from app.models import Student

    headers = _login(api_client, "role-admin@university.edu.ng")

    response = api_client.post("/api/v1/predictions/batch", headers=headers, json={"student_ids": None})
    assert response.status_code == 200, response.text

    body = response.json()
    with Session(small_db_engine) as session:
        total_students = len(session.exec(select(Student.id)).all())
    assert body["total_requested"] == total_students
    assert len(body["results"]) == total_students
