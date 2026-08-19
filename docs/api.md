# API Reference

All routes are mounted under `/api/v1`. Interactive, always-current docs
(generated from the same Pydantic models this file describes) are served at
`http://127.0.0.1:8000/docs` whenever the backend is running — that's the
source of truth for exact field types; this document is the narrative
version, organised by resource with the role requirement made explicit for
every route.

## Authentication

Every route except `POST /auth/login` requires an `Authorization: Bearer
<token>` header. Tokens are issued by `/auth/login`, carry the user's id and
role, and don't expire mid-session (no refresh flow — restart by logging in
again). A missing/invalid token returns `401`; a valid token whose role
isn't permitted for the route returns `403`.

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/auth/login` | none | `{email, password}` | `{access_token, token_type, role, user_id, full_name}` |
| GET | `/auth/me` | any authenticated user | — | `{id, email, full_name, role, student_id, is_active}` |

## Role model

Two layers, both real (see `docs/architecture.md` §6):

1. **Coarse role check** (`app.core.deps`) — a dependency attached to the
   route itself. Below, "Auth" names the roles that pass this check; anyone
   else gets `403` before any query runs.
2. **Row-level scoping** (`app.services.student_service.scope_student_ids`
   and callers) — for routes marked "scoped" below, an admin sees
   everything, a lecturer only students in courses they teach, an adviser
   only their assigned advisees, and a student only themself. This applies
   *inside* an allowed role, not instead of the coarse check.

## Students

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/students` | any role, **scoped** | query: `level, department, risk_tier, adviser_id, search, page, page_size` | `PaginatedStudents {items[], total, page, page_size}` |
| GET | `/students/{id}` | any role, **scoped** (403 outside scope) | — | `StudentProfile` (profile + `academic_history[]` + `enrolments[]`) |
| POST | `/students` | admin | `StudentCreate` (matric_no, name, DOB, department, programme, level, entry_mode/score, state_of_origin, accommodation, scholarship, employment_status, adviser_id, enrolment_session) | `StudentRead`, `201` |
| PUT | `/students/{id}` | admin | `StudentUpdate` (any subset of the writable fields) | `StudentRead` |
| DELETE | `/students/{id}` | admin | — | `204` |
| POST | `/students/import` | admin | multipart CSV file | `ImportReportResponse {total_rows, valid_rows, invalid_rows, inserted, skipped_duplicate_matric_no[], errors[{row, field, message}]}` |

`GET /students` computes each row's `risk_tier` from that student's most
recent risk-classification `Prediction`, not a stored column — a student
with no prediction yet shows `null`.

## Courses, enrolments, attendance

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/courses` | any role | query: `department, level, semester` | `CourseRead[]` |
| POST | `/courses` | admin | `CourseCreate` | `CourseRead`, `201` |
| GET | `/enrolments` | any role, **scoped** | query: `student_id, course_id` | `EnrolmentRead[]` |
| POST | `/enrolments` | admin | `EnrolmentCreate {student_id, course_id, session, semester}` | `EnrolmentRead`, `201` |
| PUT | `/enrolments/{id}/scores` | admin or the course's own lecturer | `ScoreUpdate {ca_score?, exam_score?}` | `EnrolmentRead` |
| PUT | `/attendance/{enrolment_id}` | admin or the course's own lecturer | `AttendanceUpdate {sessions_held, sessions_attended}` | `AttendanceRead` |

`PUT .../scores` recomputes `total_score`, `grade`, `grade_point`, `status`,
and `is_carryover` the moment both `ca_score` and `exam_score` are present
(`app.core.academic_config.grade_for_score` — the single source of truth
for grade bands, never duplicated elsewhere). A lecturer who doesn't teach
the enrolment's course gets `403`, checked in
`course_service.assert_can_manage_enrolment`.

## Predictions

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/predictions/student/{id}` | any role, **scoped** | — | `StudentPredictionResponse {student_id, session, semester, risk, gpa, course_scores[]}` |
| POST | `/predictions/batch` | admin, lecturer, or adviser | `{student_ids: int[]  \| null}` (null = every student in scope) | `BatchPredictionResponse {total_requested, total_succeeded, results[{student_id, matric_no, risk_tier, probability, predicted_gpa, error}]}` |
| GET | `/predictions/at-risk` | any role, **scoped** | query: `tier` | `AtRiskResponse {items[{student_id, matric_no, full_name, department, level, risk_tier, probability, adviser_id}], total}` |
| GET | `/predictions/{prediction_id}/explain` | any role, **scoped** to the prediction's student | — | `ExplanationResponse {student_id, task, algorithm, sentences[], contributors[]}` |

Every prediction call runs the active `.joblib` pipeline for that task —
there is no cached or mocked value (Section C). `POST /predictions/student/
{id}` returns `404` if the student has no ongoing enrolment to predict for
(that's the normal state for a graduated or inactive student, not an
error). Each call also **persists** a `Prediction` row with the full,
unfiltered staff-canonical `feature_contributions`; the Section I
student-facing filter (only modifiable factors, forward-looking language)
is applied when *serving* the response to a student caller, never when
writing the row — see `docs/architecture.md` §5.

`predicted_gpa` in `BatchPredictionResponse` is real GPA-regression
inference (`prediction_service.bulk_gpa_scores`, the same vectorized-predict-
only pattern as `bulk_risk_scores` — no SHAP, since a batch call doesn't need
per-row explanations), populated for every row that doesn't have an `error`.
Both the risk and GPA predictions for a batch row are also persisted as
`Prediction` rows with empty `feature_contributions`, matching how bulk
scoring elsewhere in this API never carries an explanation.

## Analytics

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/analytics/overview` | any authenticated user | `{total_students, active_students, at_risk_low/moderate/high/critical, average_cgpa, total_interventions_open}` |
| GET | `/analytics/trends` | any authenticated user | `{points: [{session, average_gpa, average_cgpa, n_students}]}` |
| GET | `/analytics/correlations` | any authenticated user | `{features: string[], matrix: number[][]}` — Pearson correlation over every numeric T1/T2 training feature |
| GET | `/analytics/course-difficulty` | any authenticated user | `{items: [{course_id, course_code, title, department, n_completed, average_score, failure_rate}]}` |
| GET | `/analytics/gpa-distribution` | any authenticated user | `{buckets: [{range_low, range_high, count}], n_students}` — histogram of each student's most recent-semester GPA in fixed 0.5-wide buckets across the full `[0, GPA_SCALE]` range |
| GET | `/analytics/attendance-performance` | any authenticated user | `{points: [{attendance_rate, total_score}], slope, intercept, n_total, n_sampled}` — per-enrolment attendance vs. total score; the regression line is fitted on all `n_total` completed enrolments, but `points` is capped to a random sample of `n_sampled` (both counts reported, never hidden) |
| GET | `/analytics/level-comparison` | any authenticated user | `{levels: [{level, n_students, average_gpa, average_cgpa, at_risk_low, at_risk_moderate, at_risk_high, at_risk_critical}]}` — GPA/CGPA averages and risk-tier distribution broken down by student level (100–500) |

These seven are **not** row-scoped by student — they're institution-wide
aggregates, computed live on every call (never a precomputed snapshot).

## Models

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/models` | any authenticated user | — | `ModelRegistryRead[]` (full registry: metrics, hyperparameters, fairness_report, feature_list) |
| GET | `/models/comparison` | any authenticated user | — | `{rows: [{task, algorithm, is_active, primary_metric_name, primary_metric_value, cv_std, train_test_gap, leakage_flag}]}` |
| GET | `/models/{version}/fairness` | any authenticated user | — | raw `fairness_report` JSON (`404` if not yet generated for that version) |
| POST | `/models/retrain` | admin | `{tasks: string[] \| null}` (null = all three) | `{status, message}` — **blocks for the full training duration** (minutes, not seconds); see below |
| POST | `/models/{version}/activate` | admin | — | `ModelRegistryRead` — demotes any other active model for that task |

`POST /models/retrain` has no background job queue: the HTTP request
doesn't return until `ml.train.train_task` finishes for every requested
task. That's a deliberate trade-off (Section C: no fabricated "in progress"
job status) documented in `model_service.retrain`'s docstring, not an
oversight — the frontend's Retrain button warns about this before firing.

## Interventions

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| GET | `/interventions` | any role, **scoped** | query: `student_id` | `InterventionRead[]`, newest first |
| POST | `/interventions` | admin or adviser | `{student_id, prediction_id?, action_type, notes?}` | `InterventionRead`, `201` |
| PUT | `/interventions/{id}` | admin, or the adviser managing that student | `{status?, notes?, outcome_note?}` | `InterventionRead` |

Setting `status` to `completed` or `cancelled` stamps `resolved_at`
automatically. `action_type` is one of `counselling, tutorial,
guardian_contact, workload_review, referral, other`; `status` is one of
`planned, in_progress, completed, cancelled`.

## Reports (PDF)

| Method | Path | Auth | Response |
|---|---|---|---|
| POST | `/reports/student/{id}` | any role, **scoped** | `application/pdf` — academic history + current enrolments |
| POST | `/reports/at-risk` | admin, lecturer, or adviser | `application/pdf` — high/critical risk-tier register, ranked by probability |

Both are generated live with reportlab on every call; nothing is cached
between requests.

## Error format

Every non-2xx response is `{"detail": "..."}`, or `{"detail": [{"msg":
"..."}, ...]}` for a Pydantic validation `422`. The frontend's API client
(`frontend/src/lib/api.ts`) normalises both shapes into a single
`ApiError(status, message)`.
