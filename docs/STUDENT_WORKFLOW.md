# Student Workflow – API Mapping

This document maps the **Student Journey** sequence diagrams to backend APIs and data flow.

---

## 1. Registration & Onboarding

| Step | Diagram | API / Backend | Notes |
|------|---------|----------------|-------|
| Register (email / mobile) | Student → SYSTEM | `POST /api/auth/signup` with `role: "STUDENT"` | Creates **User** + **Student** (linked by `userId`). |
| Validate email/OTP | SYSTEM | (MVP: skip or `POST /api/students/verify-email` stub) | In MVP, students get ACTIVE on signup. |
| Account activated, Login enabled | SYSTEM → Student | `POST /api/auth/login` | Same as existing auth; JWT carries `userId` + `role: STUDENT`. |
| Start onboarding | Student → SYSTEM | `GET /api/students/me`, `PATCH /api/students/me` | Profile-building: profile fields, `skills_json`, `projects_json`, `job_preferences_json`. |
| Profile-building guidance | SYSTEM | Step-by-step hints can be driven by completeness of `students` fields (e.g. missing `collegeName`, `skills_json`). | |
| Create / update resume | Student → SYSTEM | `PATCH /api/students/me` with `resumeFileUrl`, optional `resumeAtsScore` | Resume URL from upload flow; ATS score from external/service later. |

**Relevant schema:** `students` (all profile, resume, skills, projects, job_preferences_json, privacy flags).

---

## 2. Skill Verification & DES

| Step | Diagram | API / Backend | Notes |
|------|---------|----------------|-------|
| Request skill verification (skill + project) | Student → SYSTEM | Stub: `POST /api/students/me/skill-verification-request` (or in MVP, just track intent in `skills_json` / future table) | Full flow: mentor assign, slots, viva, evaluation. |
| Assign mentor & propose slots | SYSTEM → Mentor | Backend service / future APIs | Not in MVP. |
| Confirm slot, notify student | SYSTEM | Notifications / calendar (future) | |
| Conduct viva, submit evaluation | Mentor → SYSTEM | Future: mentor submits score + feedback → system updates DES. | |
| Auto-generate / update DES | SYSTEM | `PATCH /api/students/me` with `technical_score`, `communication_score`, `aptitude_score`, `project_score`, `overall_des` (or internal/service only) | DES fields on `students` table. |
| Sync verified skills + DES to search | SYSTEM | Same student record; search/matching can read `students.skills_json`, `overall_des`. | |
| Alert admin if anomaly | SYSTEM → Admin | Future: anomaly detection + admin decision API. | |

**Relevant schema:** `students.skills_json` (per-skill `verified`), `students.*_score`, `overall_des`, `mentor_feedback`, `mock_interview_score`.

---

## 3. Job Search, Application, Screening, Interview & Decision

| Step | Diagram | API / Backend | Notes |
|------|---------|----------------|-------|
| Make student searchable | SYSTEM | Student is searchable when profile is complete and `account_status = ACTIVE`. | Employer search (future): DES + skills + filters. |
| Browse jobs & recommendations | Student → SYSTEM | `GET /api/jobs`, `GET /api/jobs?…` | List open jobs; recommendations can filter by `job_preferences_json` later. |
| Apply to job | Student → SYSTEM | `POST /api/students/me/applications` body: `{ "jobId": "..." }` | Creates row in `student_applications` with `application_status: "applied"`. |
| Application submitted | SYSTEM | `student_applications` record; employer sees new application (future employer APIs). | |
| Auto-sync application status to TPO | SYSTEM | Future: TPO dashboard reads `student_applications` / events. | |
| Update application status | Employer / SYSTEM | Status flow: applied → shortlisted → interview_scheduled → interviewed → offered → accepted/declined. | Student can only set **accepted** or **declined** when status is **offered** (see Offer flow). |
| Application & interview tracking | Student | `GET /api/students/me/applications` | Returns list with `application_status`, job, company. |
| Schedule interview, notify student | SYSTEM | Future: calendar + notifications; status → `interview_scheduled`. | |
| Record interview decision (Select/Reject/On-hold) | Employer | Future: PATCH application status. | |
| Hiring outcome sync to TPO | SYSTEM | Future. | |

**Relevant schema:** `jobs`, `student_applications` (`application_status`).

---

## 4. Offer, Acceptance & Placement

| Step | Diagram | API / Backend | Notes |
|------|---------|----------------|-------|
| Release offer letter | Employer → Student | Employer sets `application_status` to **offered** (future employer API). | |
| Accept / decline offer | Student → SYSTEM | `PATCH /api/students/me/applications/:id` body: `{ "applicationStatus": "accepted" \| "declined" }` | Allowed only when current status is **offered**. |
| Update placement status | SYSTEM → Student | Same application record updated; student sees via `GET /api/students/me/applications`. | |
| Placement outcomes on dashboard | Student | Dashboard uses `GET /api/students/me` (includes applications). | |
| Approve offer (HR) | Employer Admin → SYSTEM | Future: policy/compliance step. | |
| Placement records to TPO | SYSTEM → TPO | Future: TPO dashboard / reports. | |
| Refresh institution dashboards | TPO → Platform Admin | Future: DES + performance visibility. | |

**Relevant schema:** `student_applications.application_status` (`offered` → `accepted` | `declined`).

---

## Quick API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/signup` | No | Register (use `role: "STUDENT"` for student). |
| POST | `/api/auth/login` | No | Login (returns JWT). |
| GET | `/api/students/me` | Bearer (STUDENT) | Get my profile + applications. |
| PATCH | `/api/students/me` | Bearer (STUDENT) | Update profile, resume, skills, prefs, privacy. |
| GET | `/api/students/me/applications` | Bearer (STUDENT) | List my applications. |
| POST | `/api/students/me/applications` | Bearer (STUDENT) | Apply to job (`jobId`). |
| PATCH | `/api/students/me/applications/:id` | Bearer (STUDENT) | Accept/decline offer (`applicationStatus`). |
| GET | `/api/jobs` | No | List jobs. |
| GET | `/api/jobs/:id` | No | Get job by id. |

See **Swagger** at `/api-docs` for request/response schemas.
