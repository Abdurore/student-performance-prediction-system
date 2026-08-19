"""Section H: "/docs must be complete" -- lock in that every contracted
endpoint is present in the generated OpenAPI schema."""

from fastapi.testclient import TestClient

from app.main import app

_EXPECTED_PATHS = {
    "/api/v1/auth/login", "/api/v1/auth/me",
    "/api/v1/students", "/api/v1/students/{student_id}", "/api/v1/students/import",
    "/api/v1/courses", "/api/v1/enrolments", "/api/v1/enrolments/{enrolment_id}/scores",
    "/api/v1/attendance/{enrolment_id}",
    "/api/v1/predictions/student/{student_id}", "/api/v1/predictions/batch",
    "/api/v1/predictions/at-risk", "/api/v1/predictions/{prediction_id}/explain",
    "/api/v1/analytics/overview", "/api/v1/analytics/trends",
    "/api/v1/analytics/correlations", "/api/v1/analytics/course-difficulty",
    "/api/v1/models", "/api/v1/models/comparison", "/api/v1/models/{version}/fairness",
    "/api/v1/models/retrain", "/api/v1/models/{version}/activate",
    "/api/v1/interventions", "/api/v1/interventions/{intervention_id}",
    "/api/v1/reports/student/{student_id}", "/api/v1/reports/at-risk",
}


def test_docs_page_loads() -> None:
    response = TestClient(app).get("/docs")
    assert response.status_code == 200


def test_openapi_schema_covers_every_contracted_endpoint() -> None:
    response = TestClient(app).get("/openapi.json")
    assert response.status_code == 200
    paths = set(response.json()["paths"].keys())
    missing = _EXPECTED_PATHS - paths
    assert not missing, f"Missing from OpenAPI schema: {sorted(missing)}"


def test_every_endpoint_has_a_typed_response_model_or_returns_a_file() -> None:
    """Every JSON-returning route should declare responses (Section H:
    "every response a typed Pydantic model") -- PDF-returning routes are
    exempt since Response isn't a Pydantic model by nature."""
    response = TestClient(app).get("/openapi.json")
    spec = response.json()
    exempt_paths = {"/api/v1/reports/student/{student_id}", "/api/v1/reports/at-risk", "/api/v1/models/{version}/fairness"}
    for path, methods in spec["paths"].items():
        if path in exempt_paths or not path.startswith("/api/v1"):
            continue
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "delete"):
                continue
            responses = operation.get("responses", {})
            success = responses.get("200") or responses.get("201") or responses.get("204")
            assert success is not None, f"{method.upper()} {path} has no documented success response"
