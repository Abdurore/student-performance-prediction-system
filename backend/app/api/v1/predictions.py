"""Prediction endpoints: real inference from trained artifacts (never mocked)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_session, require_any_staff
from app.models import ModelRegistry, Prediction, Student
from app.models.enums import PredictionTask, RiskTier, UserRole
from app.schemas.prediction import (
    AtRiskItem,
    AtRiskResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    BatchPredictionRow,
    Contributor,
    CourseScorePrediction,
    ExplanationResponse,
    GpaPrediction,
    RiskPrediction,
    StudentPredictionResponse,
)
from app.services.prediction_service import (
    bulk_gpa_scores,
    bulk_risk_scores,
    contributors_for_role,
    persist_prediction,
    predict_student_detail,
)
from app.services.student_service import StudentAccessError, scope_student_ids, assert_can_view_student

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _model_version(session: Session, task: str) -> str:
    row = session.exec(
        select(ModelRegistry).where(ModelRegistry.task == task, ModelRegistry.is_active == True)  # noqa: E712
    ).first()
    return row.version if row else "unknown"


@router.post("/student/{student_id}", response_model=StudentPredictionResponse)
def predict_student(
    student_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StudentPredictionResponse:
    try:
        assert_can_view_student(session, current_user, student_id)
    except StudentAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    result = predict_student_detail(session, student_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or has no ongoing enrolment to predict for.",
        )

    role = current_user.role
    risk_version = _model_version(session, "risk_classification")
    gpa_version = _model_version(session, "gpa_regression")
    course_version = _model_version(session, "course_score")

    # Persisted feature_contributions are always the staff-canonical top-5,
    # regardless of who requested this prediction -- the student-facing
    # filter is applied only when a student later *views* it (here and in
    # GET /predictions/{id}/explain), never baked into storage.
    risk_contributors, risk_sentences = contributors_for_role(result["risk"]["contributors"], "risk_classification", role)
    staff_risk_contributors, _ = contributors_for_role(result["risk"]["contributors"], "risk_classification", UserRole.ADMIN)
    persist_prediction(
        session, student_id=student_id, task=PredictionTask.RISK_CLASSIFICATION,
        predicted_value=result["risk"]["probability"], predicted_class=result["risk"]["risk_tier"],
        risk_tier=RiskTier(result["risk"]["risk_tier"]), confidence=max(result["risk"]["probability"], 1 - result["risk"]["probability"]),
        probability=result["risk"]["probability"], feature_contributions=staff_risk_contributors,
        input_snapshot={"session": result["session"], "semester": result["semester"]}, model_version=risk_version,
    )

    gpa_contributors, gpa_sentences = contributors_for_role(result["gpa"]["contributors"], "gpa_regression", role)
    staff_gpa_contributors, _ = contributors_for_role(result["gpa"]["contributors"], "gpa_regression", UserRole.ADMIN)
    persist_prediction(
        session, student_id=student_id, task=PredictionTask.GPA_REGRESSION,
        predicted_value=result["gpa"]["predicted_gpa"], predicted_class=None, risk_tier=None, confidence=None,
        probability=None, feature_contributions=staff_gpa_contributors,
        input_snapshot={"session": result["session"], "semester": result["semester"]}, model_version=gpa_version,
    )

    course_scores = []
    for course_pred in result["course_scores"]:
        course_contributors, _sentences = contributors_for_role(course_pred["contributors"], "course_score", role)
        staff_course_contributors, _ = contributors_for_role(course_pred["contributors"], "course_score", UserRole.ADMIN)
        persist_prediction(
            session, student_id=student_id, task=PredictionTask.COURSE_SCORE,
            predicted_value=course_pred["predicted_score"], predicted_class=None, risk_tier=None, confidence=None,
            probability=None, feature_contributions=staff_course_contributors,
            input_snapshot={"course_id": course_pred["course_id"]}, model_version=course_version,
        )
        course_scores.append(
            CourseScorePrediction(
                course_id=course_pred["course_id"], course_code=course_pred["course_code"],
                predicted_score=course_pred["predicted_score"], algorithm=course_pred["algorithm"],
                top_factors=[Contributor(**c) for c in course_contributors],
            )
        )

    return StudentPredictionResponse(
        student_id=student_id, session=result["session"], semester=result["semester"],
        risk=RiskPrediction(
            probability=result["risk"]["probability"], risk_tier=RiskTier(result["risk"]["risk_tier"]),
            algorithm=result["risk"]["algorithm"], top_factors=[Contributor(**c) for c in risk_contributors],
        ),
        gpa=GpaPrediction(
            predicted_gpa=result["gpa"]["predicted_gpa"], predicted_cgpa=result["gpa"]["predicted_cgpa"],
            interval_low=result["gpa"]["interval_low"], interval_high=result["gpa"]["interval_high"],
            algorithm=result["gpa"]["algorithm"], top_factors=[Contributor(**c) for c in gpa_contributors],
        ),
        course_scores=course_scores,
    )


@router.post("/batch", response_model=BatchPredictionResponse, dependencies=[Depends(require_any_staff)])
def predict_batch(
    payload: BatchPredictionRequest,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> BatchPredictionResponse:
    scope = scope_student_ids(session, current_user)
    requested_ids = payload.student_ids
    if requested_ids is None:
        requested_ids = list(scope) if scope is not None else [s.id for s in session.exec(select(Student.id)).all()]
    elif scope is not None:
        requested_ids = [i for i in requested_ids if i in scope]

    scores = bulk_risk_scores(requested_ids)
    gpa_scores = bulk_gpa_scores(requested_ids)
    risk_version = _model_version(session, "risk_classification")
    gpa_version = _model_version(session, "gpa_regression")
    found_ids = set(scores["student_id"]) if not scores.empty else set()
    gpa_by_student = (
        dict(zip(gpa_scores["student_id"], gpa_scores["predicted_gpa"])) if not gpa_scores.empty else {}
    )
    students_by_id = {s.id: s for s in session.exec(select(Student).where(Student.id.in_(requested_ids))).all()}

    rows: list[BatchPredictionRow] = []
    for student_id in requested_ids:
        student = students_by_id.get(student_id)
        if student is None:
            rows.append(BatchPredictionRow(student_id=student_id, matric_no="?", risk_tier=None, probability=None, predicted_gpa=None, error="Student not found."))
            continue
        if student_id not in found_ids:
            rows.append(BatchPredictionRow(student_id=student_id, matric_no=student.matric_no, risk_tier=None, probability=None, predicted_gpa=None, error="No ongoing enrolment."))
            continue
        record = scores[scores["student_id"] == student_id].iloc[0]
        persist_prediction(
            session, student_id=student_id, task=PredictionTask.RISK_CLASSIFICATION,
            predicted_value=float(record["probability"]), predicted_class=record["risk_tier"],
            risk_tier=RiskTier(record["risk_tier"]), confidence=max(record["probability"], 1 - record["probability"]),
            probability=float(record["probability"]), feature_contributions=[],
            input_snapshot={"session": record["session"], "semester": record["semester"]}, model_version=risk_version,
        )

        predicted_gpa = gpa_by_student.get(student_id)
        if predicted_gpa is not None:
            predicted_gpa = float(predicted_gpa)
            persist_prediction(
                session, student_id=student_id, task=PredictionTask.GPA_REGRESSION,
                predicted_value=predicted_gpa, predicted_class=None, risk_tier=None, confidence=None,
                probability=None, feature_contributions=[],
                input_snapshot={"session": record["session"], "semester": record["semester"]}, model_version=gpa_version,
            )

        rows.append(
            BatchPredictionRow(
                student_id=student_id, matric_no=student.matric_no, risk_tier=RiskTier(record["risk_tier"]),
                probability=float(record["probability"]), predicted_gpa=predicted_gpa,
            )
        )

    return BatchPredictionResponse(
        total_requested=len(requested_ids), total_succeeded=sum(1 for r in rows if r.error is None), results=rows
    )


@router.get("/at-risk", response_model=AtRiskResponse)
def get_at_risk(
    tier: str | None = Query(default=None),
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AtRiskResponse:
    scope = scope_student_ids(session, current_user)
    student_ids = list(scope) if scope is not None else None
    scores = bulk_risk_scores(student_ids)
    if tier is not None:
        scores = scores[scores["risk_tier"] == tier]
    scores = scores.sort_values("probability", ascending=False)

    students_by_id = {s.id: s for s in session.exec(select(Student).where(Student.id.in_(scores["student_id"].tolist()))).all()}
    items = []
    for _, record in scores.iterrows():
        student = students_by_id.get(int(record["student_id"]))
        if student is None:
            continue
        items.append(
            AtRiskItem(
                student_id=student.id, matric_no=student.matric_no,
                full_name=f"{student.first_name} {student.last_name}", department=student.department,
                level=student.level, risk_tier=RiskTier(record["risk_tier"]), probability=float(record["probability"]),
                adviser_id=student.adviser_id,
            )
        )
    return AtRiskResponse(items=items, total=len(items))


@router.get("/{prediction_id}/explain", response_model=ExplanationResponse)
def explain_prediction(
    prediction_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ExplanationResponse:
    prediction = session.get(Prediction, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found.")
    try:
        assert_can_view_student(session, current_user, prediction.student_id)
    except StudentAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    stored_contributors = (prediction.feature_contributions or {}).get("contributors", [])
    contributors, sentences = contributors_for_role(stored_contributors, prediction.task.value, current_user.role)
    return ExplanationResponse(
        student_id=prediction.student_id, task=prediction.task.value, algorithm=prediction.model_version,
        sentences=sentences, contributors=[Contributor(**c) for c in contributors],
    )
