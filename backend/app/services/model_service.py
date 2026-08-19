"""Model registry business logic: comparison table, activation, retraining."""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import ModelRegistry
from app.models.enums import PredictionTask
from app.schemas.model_registry import ModelComparisonRow

_PRIMARY_METRIC = {
    "risk_classification": "f1_macro",
    "gpa_regression": "r2",
    "course_score": "r2",
}


def list_models(session: Session) -> list[ModelRegistry]:
    return session.exec(select(ModelRegistry).order_by(ModelRegistry.task, ModelRegistry.algorithm)).all()


def get_comparison(session: Session) -> list[ModelComparisonRow]:
    rows = list_models(session)
    comparison = []
    for row in rows:
        metric_name = _PRIMARY_METRIC.get(row.task.value, "f1_macro")
        cv_metrics = row.metrics or {}
        comparison.append(
            ModelComparisonRow(
                task=row.task.value, algorithm=row.algorithm, is_active=row.is_active,
                primary_metric_name=metric_name, primary_metric_value=cv_metrics.get(metric_name),
                cv_std=None, train_test_gap=None, leakage_flag=bool(cv_metrics.get("leakage_flag", False)),
            )
        )
    return comparison


def get_model_by_version(session: Session, version: str) -> ModelRegistry | None:
    return session.exec(select(ModelRegistry).where(ModelRegistry.version == version)).first()


def activate_model(session: Session, version: str) -> ModelRegistry | None:
    """Promote `version` to production for its task, demoting any other active model of that task."""
    target = get_model_by_version(session, version)
    if target is None:
        return None
    siblings = session.exec(
        select(ModelRegistry).where(ModelRegistry.task == target.task, ModelRegistry.id != target.id)
    ).all()
    for sibling in siblings:
        if sibling.is_active:
            sibling.is_active = False
            session.add(sibling)
    target.is_active = True
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def retrain(tasks: list[str] | None = None) -> dict:
    """Retrain and re-persist the requested tasks (or all three) synchronously.

    There is no background job queue in this system, so this call blocks
    for as long as `ml.train` takes (minutes, not seconds) -- an honest
    trade-off for "no mocked predictions, no fake job status" over a
    responsive-looking but fabricated async response.
    """
    from ml.train import persist_task_results, train_task

    selected = tasks or list(PredictionTask)
    selected = [t.value if isinstance(t, PredictionTask) else t for t in selected]
    for task in selected:
        results = train_task(task)
        persist_task_results(task, results)
    return {"status": "completed", "message": f"Retrained: {', '.join(selected)}"}
