"""Unit tests for app.services.model_service: comparison rows, activation,
and the retrain dispatcher.

`retrain()` itself is not run end-to-end here -- it's a thin wrapper around
`ml.train.train_task`/`persist_task_results`, which test_train.py already
exercises with a real (small) GridSearchCV run; re-running that here would
just duplicate several minutes of training for no new coverage. Instead the
dispatcher logic (task-list resolution, per-task calls, response message) is
tested with those two functions monkeypatched to cheap stubs.
"""

from sqlmodel import Session, select

from app.models import ModelRegistry
from app.services.model_service import activate_model, get_comparison, get_model_by_version, list_models


def test_list_models_orders_by_task_then_algorithm(small_db_engine, trained_registry) -> None:
    with Session(small_db_engine) as session:
        models = list_models(session)
    assert len(models) == 3
    tasks = [m.task for m in models]
    assert tasks == sorted(tasks)


def test_get_comparison_picks_the_right_primary_metric_per_task(small_db_engine, trained_registry) -> None:
    with Session(small_db_engine) as session:
        # trained_registry fits models but doesn't populate real metrics, so
        # give the active risk-classification row a metrics dict to read back.
        row = session.exec(
            select(ModelRegistry).where(ModelRegistry.task == "risk_classification")
        ).first()
        row.metrics = {"f1_macro": 0.9, "leakage_flag": False}
        session.add(row)
        session.commit()

        comparison = get_comparison(session)
    by_task = {row.task: row for row in comparison}
    assert by_task["risk_classification"].primary_metric_name == "f1_macro"
    assert by_task["risk_classification"].primary_metric_value == 0.9
    assert by_task["gpa_regression"].primary_metric_name == "r2"
    assert by_task["course_score"].primary_metric_name == "r2"


def test_get_comparison_surfaces_leakage_flag(small_db_engine, trained_registry) -> None:
    with Session(small_db_engine) as session:
        row = session.exec(select(ModelRegistry).where(ModelRegistry.task == "gpa_regression")).first()
        row.metrics = {"leakage_flag": True}
        session.add(row)
        session.commit()

        comparison = get_comparison(session)
    by_task = {row.task: row for row in comparison}
    assert by_task["gpa_regression"].leakage_flag is True


def test_get_model_by_version_returns_none_for_unknown_version(small_db_engine, trained_registry) -> None:
    with Session(small_db_engine) as session:
        assert get_model_by_version(session, "not_a_real_version") is None


def test_activate_model_demotes_siblings_of_the_same_task(small_db_engine, trained_registry) -> None:
    with Session(small_db_engine) as session:
        risk_models = session.exec(select(ModelRegistry).where(ModelRegistry.task == "risk_classification")).all()
        assert len(risk_models) == 1  # trained_registry only fits one algorithm per task

        # Add a second risk-classification row sharing the same artifact, purely
        # to exercise the sibling-demotion branch.
        original = risk_models[0]
        sibling = ModelRegistry(
            version="risk_classification__stub", task=original.task, algorithm="stub",
            trained_at=original.trained_at, training_rows=original.training_rows,
            feature_list=original.feature_list, hyperparameters={}, metrics={},
            artifact_path=original.artifact_path, is_active=True,
        )
        session.add(sibling)
        session.commit()

        activated = activate_model(session, original.version)
        session.refresh(sibling)
        assert activated.is_active is True
        assert sibling.is_active is False


def test_activate_model_returns_none_for_unknown_version(small_db_engine, trained_registry) -> None:
    with Session(small_db_engine) as session:
        assert activate_model(session, "not_a_real_version") is None


def test_retrain_dispatches_to_train_task_for_each_requested_task(monkeypatch) -> None:
    from app.services import model_service

    calls = []

    def fake_train_task(task):
        calls.append(task)
        return {"task": task}

    def fake_persist_task_results(task, results):
        calls.append(f"persisted:{task}")

    monkeypatch.setattr("ml.train.train_task", fake_train_task)
    monkeypatch.setattr("ml.train.persist_task_results", fake_persist_task_results)

    result = model_service.retrain(["risk_classification", "gpa_regression"])

    assert calls == ["risk_classification", "persisted:risk_classification", "gpa_regression", "persisted:gpa_regression"]
    assert result["status"] == "completed"
    assert "risk_classification" in result["message"]
    assert "gpa_regression" in result["message"]


def test_retrain_defaults_to_every_task_when_none_specified(monkeypatch) -> None:
    from app.services import model_service

    calls = []
    monkeypatch.setattr("ml.train.train_task", lambda task: calls.append(task) or {})
    monkeypatch.setattr("ml.train.persist_task_results", lambda task, results: None)

    result = model_service.retrain(None)

    assert set(calls) == {"risk_classification", "gpa_regression", "course_score"}
    assert result["status"] == "completed"
