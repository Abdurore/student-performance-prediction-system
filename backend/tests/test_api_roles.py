"""Phase 5 role-enforcement tests: one forbidden-access case per role (Section H).

Runs the real FastAPI app against the isolated small test DB (not the demo
database), with every module that binds its own `engine` name monkeypatched
to match -- app.db.session backs the get_session dependency every router
uses; ml.explain/ml.fairness/ml.preprocessing/ml.train are imported
directly by the prediction/analytics/model services.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import hash_password
from app.db import session as db_session_module
from app.main import app
from app.models import Student, User
from app.models.enums import Accommodation, Gender, UserRole
from ml import explain as explain_module
from ml import fairness as fairness_module
from ml import preprocessing as preprocessing_module
from ml import train as train_module


@pytest.fixture()
def api_client(trained_registry, small_db_engine):
    mp = pytest.MonkeyPatch()
    for module in (db_session_module, preprocessing_module, explain_module, fairness_module, train_module):
        mp.setattr(module, "engine", small_db_engine)
    yield TestClient(app)
    mp.undo()


@pytest.fixture(scope="module")
def demo_users(small_db_engine):
    """One user per role, plus a second student to test cross-student access."""
    with Session(small_db_engine) as session:
        pwd = hash_password("Password123!")
        admin = User(email="role-admin@university.edu.ng", password_hash=pwd, full_name="Role Admin", role=UserRole.ADMIN)
        lecturer = User(email="role-lecturer@university.edu.ng", password_hash=pwd, full_name="Role Lecturer", role=UserRole.LECTURER)
        adviser = User(email="role-adviser@university.edu.ng", password_hash=pwd, full_name="Role Adviser", role=UserRole.ADVISER)

        other_student_row = Student(
            matric_no="ROLE/24/00099", first_name="Other", last_name="Student", gender=Gender.MALE,
            date_of_birth=date(2003, 1, 1), department="Computer Science", programme="B.Sc. CS", level=100,
            entry_mode="UTME", entry_score=200, state_of_origin="Lagos", accommodation=Accommodation.ON_CAMPUS,
            enrolment_session="2024/2025",
        )
        session.add(other_student_row)
        session.commit()
        session.refresh(other_student_row)

        student_user = User(
            email="role-student@university.edu.ng", password_hash=pwd, full_name="Role Student",
            role=UserRole.STUDENT, student_id=other_student_row.id,
        )
        session.add_all([admin, lecturer, adviser, student_user])
        session.commit()
        for u in (admin, lecturer, adviser, student_user):
            session.refresh(u)
        users = {"admin": admin, "lecturer": lecturer, "adviser": adviser, "student": student_user}
        users["other_student_id"] = other_student_row.id
    return users


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
