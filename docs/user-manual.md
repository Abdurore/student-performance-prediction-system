# User Manual

This walks through every screen a signed-in user can reach, organised by
what each of the four roles can actually do. For "how do I install and
start this" see `docs/installation.md`; for API details see `docs/api.md`.

## Signing in

Open `http://localhost:5173`. The login page shows the demo credentials for
all four roles directly on the page — a shared password
(`Demo@12345`) and a role-specific email — with a **Use** button next to
each that fills the form for you. This is not incidental UI polish: it's an
explicit requirement (Section I) so an examiner can try every role without
being told a password out of band.

Once signed in, the left sidebar shows only the pages your role can reach —
a student never sees Analytics or Models in the nav even though the
sidebar itself is the same component for everyone. Direct-URL navigation to
a page your role can't use redirects you back to the dashboard rather than
erroring (`frontend/src/components/auth/ProtectedRoute.tsx`).

## Every role: Dashboard, Students, Interventions, Profile

- **Dashboard** (`/`) — content is entirely different per role (see below),
  but the shell is shared.
- **Students** (`/students`) — a searchable, filterable, paginated list.
  Filters are search text (name or matric number), department, level, and
  risk tier; results and their risk badges reflect only what your role is
  scoped to see (a student sees a one-row list containing just themself).
  Clicking a name opens `/students/:id`.
- **Student detail** (`/students/:id`) — profile header, a **Run
  prediction** button that calls the live models and shows the risk tier,
  GPA forecast, per-course score forecasts, and the ranked contributing
  factors as plain-language sentences; full academic history and enrolment
  tables; a **Download report** button producing a real PDF; an
  interventions panel (see below); and, for admin/adviser, a form to log a
  new intervention against this student.
- **Interventions** (`/interventions`) — every intervention within your
  scope, filterable by status. Admin and adviser get an inline status
  dropdown (`planned → in_progress → completed/cancelled`) on each row;
  everyone else sees status as a read-only badge.
- **Profile** (`/profile`) — your name, email, and role. Read-only: account
  changes go through your institution's administrator, not self-service,
  since there is no `PUT /auth/me` endpoint to back one.

## Admin dashboard

Institution-wide totals (active students, average CGPA, students at
critical risk, open interventions), a risk-tier donut, a GPA/CGPA trend
line across sessions, an at-risk leaderboard (top 8 by probability), and a
recent-interventions list. Every number here is a live query — refresh the
page and it's recomputed, not replayed from a cache.

## Lecturer dashboard

Your own course list (from `Course.lecturer_id`) with level/semester/units,
and a class-risk table for students across those courses, capped to the 10
most at-risk with a "showing N of total" note so a lecturer teaching a
large service course doesn't get a page-breaking table.

## Adviser dashboard

Your assigned advisees grouped into four sections — Critical (act now),
High (schedule this week), Moderate (monitor), Low (stable) — so the most
urgent cases are the first thing you see, not buried in a flat list sorted
by name.

## Student dashboard

Your own GPA/CGPA trend, a predicted GPA/CGPA for the current semester, a
current-outlook risk badge, and a "Focus areas for next semester" list.
That list is the one place Section I's ethical constraint is directly
visible: it never says "you are predicted to fail," and it only lists
factors you can actually change (attendance, study hours, assignment
submission, tutorial attendance) — a fixed attribute like prior CGPA or
entry score never appears here, because the server itself filters it out
before the response is sent (`docs/architecture.md` §5), not just the UI.

## Staff-only: Predict (`/predict`)

Visible to admin, lecturer, and adviser (not student — a student already
has their own outlook on the dashboard, and the batch-prediction endpoint
this page drives is staff-only server-side too).

- **Single student** tab: search by name or matric number, pick a result,
  and the same prediction panel used on the student detail page appears.
- **Batch upload** tab: download a one-column CSV template
  (`student_id`), upload a filled-in copy, and a validation preview shows
  how many rows parsed as valid IDs versus duplicates versus unreadable
  rows *before* anything is sent to the server. **Run batch prediction**
  then calls every valid ID through the real risk model and shows a
  results table — including per-row errors like "No ongoing enrolment,"
  rather than silently skipping a row.
- From the **Students** list, selecting rows via the checkbox column and
  clicking **Predict selected** jumps straight to the batch tab with those
  IDs already loaded, skipping the CSV step entirely.

## Staff-only: Analytics (`/analytics`)

Visible to admin, lecturer, and adviser. A session-by-session GPA/CGPA
trend, a feature-correlation heatmap (every numeric engineered feature
against every other, Pearson correlation, navy-to-amber diverging scale),
and a course-difficulty view (bar chart plus table) ranked by failure rate.
A **Download at-risk register (PDF)** button is also here for convenience.

## Admin-only: Models (`/models`)

The model comparison table lists all six algorithms across all three
tasks, with each row's primary metric, leakage-check status, and active/
inactive state. Per row:

- **Activate** promotes that algorithm to production for its task
  (demoting whichever was previously active) — gated behind a confirm
  dialog, since it changes what every subsequent prediction call actually
  returns.
- **Fairness** expands the demographic-parity/equal-opportunity/predictive-
  parity report for that model, per protected-attribute group, with a
  Flagged/Within-threshold badge per attribute.
- **Diagnostics** expands a confusion matrix + ROC curve + calibration
  curve for a classification model, or a predicted-vs-actual + residuals
  scatter for a regression model — all from the same metrics already
  computed and persisted during training, never recomputed or invented for
  display.

A **Retrain** section lets you pick specific tasks (or leave all
unchecked to retrain everything) and re-run the full `GridSearchCV`
pipeline. This is a real, synchronous, multi-minute operation — the confirm
dialog says so before you commit to it, because there is no background job
queue faking a progress bar in the meantime (Section C).

## What every async view does while loading or on failure

Every page that fetches data has three states, not just a happy path
(Section I): a skeleton placeholder while loading, an empty state with
plain guidance on what would make the section populate (not a bare "No
data"), and an error state with a **Retry** button rather than a silent
blank screen. This applies uniformly across dashboards, lists, and detail
pages — it's implemented once as shared `Skeleton`, `EmptyState`, and
`ErrorState` components rather than reimplemented per page.

## Testing accounts recap

| Role | Email | Password |
|---|---|---|
| Admin | `admin@university.edu.ng` | `Demo@12345` |
| Lecturer | `lecturer01@university.edu.ng` | `Demo@12345` |
| Adviser | `adviser01@university.edu.ng` | `Demo@12345` |
| Student | `eco.24.00002@university.edu.ng` | `Demo@12345` |

Every seeded account shares the same password. Student accounts otherwise
follow `<matric-no, lowercased, "/" → ".">@university.edu.ng`.
