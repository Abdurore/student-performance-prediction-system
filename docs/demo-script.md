# Demo Script

An 8-minute walkthrough for an examination panel, followed by the twelve
questions most likely to come up and grounded answers for each. Times are
cumulative and assume the system is already running (`make demo`, or
`make dev` after a prior `make seed`/`make train`) and the browser is on the
login page before you start the clock.

## Timed walkthrough (≈8 minutes)

**0:00 – 0:45 — What this is**
"This predicts three things for a student's *current* semester before it
ends: whether they're at risk of falling below the probation CGPA
threshold, what their GPA will actually be, and what score they'll get in
each course they're currently taking — all from a real trained model, never
a mocked number. It runs fully offline on one machine: FastAPI backend,
React frontend, SQLite by default."

**0:45 – 1:30 — Login and role model**
Point at the demo-credentials panel on the login page — every role's
account is visible on screen, nothing hidden. Log in as **admin**
(`admin@university.edu.ng` / `Demo@12345`, or click **Use**). Note the
sidebar: four roles see four different navigation sets, enforced both by
what's shown and by the server rejecting a role that hits a page it
shouldn't.

**1:30 – 2:30 — Admin dashboard**
Institution totals, the risk-tier donut, the GPA/CGPA trend by session, the
at-risk leaderboard. Say explicitly: "every number on this page is a live
query against the database and the active models right now — refresh it
and it's recomputed, not replayed."

**2:30 – 3:30 — A real prediction, staff view**
Students → open any student → **Run prediction**. Point at the risk tier,
the GPA forecast with its interval, the per-course score forecasts, and the
five ranked contributing factors rendered as sentences, not raw SHAP
numbers.

**3:30 – 4:15 — The ethical constraint, student view**
Log out, log in as the **student** demo account, land on their own
dashboard. Point at "Focus areas for next semester": every sentence is
forward-looking ("Improving your attendance to 80% would help going
forward") and every factor listed is something the student can act on —
no entry score, no prior CGPA, no bare "you are predicted to fail." Say:
"this filter runs on the server, inside the prediction service, not in the
page — a student calling the API directly gets the same filtered result,
because the unfiltered factors are never sent to them in the first place."

**4:15 – 5:00 — Batch prediction**
Back in as admin (or lecturer), open **Predict → Batch upload**, download
the template, upload a small filled CSV, show the validation preview
catching a duplicate or invalid row before anything is sent, then run it
and show the results table — including a row that legitimately errors
("No ongoing enrolment") rather than being silently dropped.

**5:00 – 5:45 — Analytics**
Feature-correlation heatmap, course-difficulty ranking, GPA distribution
histogram, attendance-vs-performance scatter with its fitted regression
line, and the level comparison chart (GPA/CGPA and risk-tier mix across
Levels 100–500). "Every chart here comes from a live endpoint — nothing in
this page is a static image."

**5:45 – 6:45 — Models: comparison, fairness, diagnostics**
Models page: point at the six-algorithm comparison table for one task,
**Activate** to explain how production model swaps work, **Fairness** to
expand a real demographic-parity/equal-opportunity report (note the flagged
attribute if one shows), **Diagnostics** to expand the confusion matrix and
ROC curve — "these are the exact numbers computed during training, not
redrawn for the demo."

**6:45 – 7:30 — Interventions**
Log one intervention against a student, then show the status transition to
"completed."

**7:30 – 8:00 — Close**
"Underneath all of this: a data-leakage guard that raises if any
target-semester outcome ever reaches the feature matrix, a fairness audit
across gender/entry-mode/accommodation, and roughly 165 automated tests —
124 backend, 35 frontend — covering the business logic and the ML pipeline
above 70% line coverage. Happy to take questions."

## Twelve likely examiner questions

**1. How do you know the model isn't just memorising outcomes it shouldn't see (leakage)?**
`ml/features.py`'s `assert_no_leakage(feature_df, task)` raises if any
target-semester outcome column (`exam_score`, `total_score`, `grade`,
`grade_point` for the semester/course being predicted) is present in the
feature matrix, and it's called inside the training pipeline itself, not
just as an external check. It's covered by a test that deliberately injects
a banned column and asserts the raise. Separately, `ml/train.py` halts and
prints a warning instead of reporting a score if any model exceeds 96%
accuracy or 0.95 R² — a suspiciously high score is treated as evidence of
leakage, not a result to be proud of.

**2. Why six algorithms instead of picking the best one up front?**
The brief asked for a defensible comparison, not a single black-box choice.
All six (logistic/linear regression, decision tree, random forest, XGBoost,
SVM, MLP) run through the identical preprocessing pipeline and identical
cross-validation folds, so the comparison table is genuinely apples-to-
apples. The simplest models (logistic/linear regression) are competitive
with the ensemble methods here, which itself is worth reporting — it says
the signal in the engineered features is close to linear, not that a
complex model was needed to find it.

**3. Why SHAP, and why one explainer path for every algorithm instead of the fast tree-specific one?**
`ml.explain` wraps each pipeline's own `predict`/`predict_proba` rather
than special-casing `TreeExplainer` for tree models. It costs more compute
per explanation, but it means switching the active model for a task never
silently loses explainability — an MLP, which has no fast tree-structure
shortcut, is explained through the exact same code path as random forest.

**4. How is class imbalance in the risk-classification task handled?**
SMOTE is applied, compared with and without, but strictly *inside* each
cross-validation fold — fitting it on the full dataset before splitting
would leak information about the test fold's minority-class examples into
training. `ml/train.py`'s pipeline construction enforces this ordering.

**5. What does the GPA prediction interval actually mean?**
It's the point forecast ± the active model's RMSE on its temporal holdout
(`prediction_service._active_model_rmse`), clipped to the valid GPA range.
It's a defensible, transparent width — not a formal confidence interval
with a stated coverage probability — and that's a deliberate simplicity
trade-off: computing a real prediction interval (e.g. quantile regression)
per algorithm would have meaningfully expanded scope for a figure that
still needs the same plain-language framing to be useful to a student.

**6. Why exclude gender, state of origin, and date of birth from the model but still store them?**
They're collected because the fairness audit needs a group variable to
measure disparity *against* — you can't check whether a model is unfair to
women if you never record gender. But `ml/config.py`'s
`USE_PROTECTED_ATTRIBUTES = False` keeps them out of the feature matrix
itself, so the model can't learn a shortcut through a protected
characteristic. The fairness audit then checks demographic parity, equal
opportunity, and predictive parity across those same groups on a temporal
holdout, and flags any gap above 10 percentage points.

**7. Why SQLite and no Docker — is this production-ready?**
It isn't claiming to be. The brief's hard constraint was "runs offline on a
mid-range laptop from one command" for a graded academic demo, not a
multi-tenant production deployment. SQLite is one file, zero setup, and the
only change needed to move to Postgres is one `DATABASE_URL` environment
variable — nothing in the application code assumes SQLite specifically.

**8. How is access control enforced — could a lecturer see another lecturer's students by editing the URL?**
Two independent layers. A FastAPI dependency on the route rejects a role
that shouldn't reach that endpoint at all (a student can't call `POST
/students`). Separately, `student_service.scope_student_ids` computes which
specific rows that user may see — a lecturer only students in courses they
teach, an adviser only their assigned advisees — and every service that
touches student data calls it. Editing the URL to another student's ID
returns `403` from the second layer even though the route itself is
allowed for that role; `tests/test_api_roles.py` asserts this for one
forbidden case per role.

**9. Where exactly is the "don't scare the student" rule enforced — could someone bypass it from the browser console?**
No — it's server-side, in `prediction_service.contributors_for_role`. A
student caller gets `filter_to_modifiable_contributors` applied *before*
the top-5 truncation (not after, which would risk truncating away
modifiable factors ranked 6th–10th), then `render_student_sentences` for
forward-looking language. The unfiltered factors are never included in the
HTTP response to a student in the first place, so there's nothing in the
browser to bypass.

**10. Why does clicking "Retrain" block the whole request instead of returning immediately with a job ID?**
Because a fake "in progress" status with no real job behind it would
violate the same "never fabricate a value" principle the rest of the
system holds to. There's no background job queue in this system, so
`model_service.retrain` genuinely blocks for the training duration
(minutes) and returns only once it's actually done; the frontend warns
about this before the confirm dialog fires.

**11. What happens with a real institution's data instead of the synthetic set?**
`app/db/csv_import.py` loads student records against the same schema with
row-level validation, producing a report of inserted rows, duplicate
matric numbers skipped, and per-row field errors — no code change is
required to point it at a real CSV. The synthetic generator exists
specifically so the system has a full, causally-coherent demo dataset (not
an empty one) on first run, per the brief's "never demo against an empty
application" constraint.

**12. What's the biggest known limitation?**
Documented rather than hidden: `docs/known-issues.md` tracks the frontend's
missing ESLint config as the current open item, plus a running record of
what's already been fixed. Earlier in the build, the batch-prediction
endpoint computed risk classification but not GPA, and the analytics page
had no histogram/scatter/level-comparison charts because the locked API
contract had no endpoints to back them — both were flagged rather than
faked with plausible-looking numbers at the time, and both were closed out
in a later finalization pass once the missing backend aggregation endpoints
were added.
