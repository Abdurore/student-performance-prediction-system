"""Unit tests for app.services.intervention_service: scoped listing, status
transitions, and the admin/adviser management boundary."""

from sqlmodel import Session

from app.models import Intervention
from app.models.enums import InterventionActionType, InterventionStatus
from app.services.intervention_service import (
    can_manage_intervention,
    create_intervention,
    list_interventions,
    update_intervention,
)


def test_create_intervention_persists_with_the_creating_user(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        intervention = create_intervention(
            session, demo_users["admin"], demo_users["other_student_id"], None,
            InterventionActionType.COUNSELLING, "Discussed attendance.",
        )
    assert intervention.id is not None
    assert intervention.created_by == demo_users["admin"].id
    assert intervention.status == InterventionStatus.PLANNED
    assert intervention.resolved_at is None


def test_list_interventions_scopes_to_adviser_advisees(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        create_intervention(
            session, demo_users["admin"], demo_users["other_student_id"], None,
            InterventionActionType.TUTORIAL, None,
        )
        # This adviser has no advisees assigned, so their scope is empty.
        results = list_interventions(session, demo_users["adviser"])
    assert results == []


def test_list_interventions_admin_sees_everything(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        create_intervention(
            session, demo_users["admin"], demo_users["other_student_id"], None,
            InterventionActionType.REFERRAL, None,
        )
        results = list_interventions(session, demo_users["admin"])
    assert any(i.student_id == demo_users["other_student_id"] for i in results)


def test_list_interventions_filters_by_student_id(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        create_intervention(
            session, demo_users["admin"], demo_users["other_student_id"], None,
            InterventionActionType.WORKLOAD_REVIEW, None,
        )
        results = list_interventions(session, demo_users["admin"], student_id=demo_users["other_student_id"])
    assert all(i.student_id == demo_users["other_student_id"] for i in results)
    assert len(results) > 0


def test_update_intervention_completed_status_sets_resolved_at(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        intervention = create_intervention(
            session, demo_users["admin"], demo_users["other_student_id"], None,
            InterventionActionType.OTHER, None,
        )
        assert intervention.resolved_at is None

        updated = update_intervention(session, intervention, InterventionStatus.COMPLETED, None, "Resolved.")
        assert updated.status == InterventionStatus.COMPLETED
        assert updated.resolved_at is not None
        assert updated.outcome_note == "Resolved."


def test_update_intervention_planned_status_does_not_set_resolved_at(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        intervention = create_intervention(
            session, demo_users["admin"], demo_users["other_student_id"], None,
            InterventionActionType.OTHER, None,
        )
        updated = update_intervention(session, intervention, InterventionStatus.IN_PROGRESS, "note", None)
        assert updated.status == InterventionStatus.IN_PROGRESS
        assert updated.resolved_at is None
        assert updated.notes == "note"


def test_can_manage_intervention_admin_always_true(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        intervention = Intervention(
            student_id=demo_users["other_student_id"], created_by=demo_users["admin"].id,
            action_type=InterventionActionType.OTHER,
        )
        assert can_manage_intervention(session, demo_users["admin"], intervention) is True


def test_can_manage_intervention_lecturer_always_false(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        intervention = Intervention(
            student_id=demo_users["other_student_id"], created_by=demo_users["admin"].id,
            action_type=InterventionActionType.OTHER,
        )
        assert can_manage_intervention(session, demo_users["lecturer"], intervention) is False


def test_can_manage_intervention_adviser_only_for_their_advisees(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        intervention = Intervention(
            student_id=demo_users["other_student_id"], created_by=demo_users["admin"].id,
            action_type=InterventionActionType.OTHER,
        )
        # This adviser has no advisees, so even though the intervention exists,
        # they may not manage it.
        assert can_manage_intervention(session, demo_users["adviser"], intervention) is False
