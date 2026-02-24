# SHEMS / Student Schema – MVP-First Design

**Principle:** Two tables only for student + applications. No extra join tables, minimal confusion.

---

## 1. Single master table: `students`

Holds **all** student-related data. Some fields are JSON (fine for MVP).

| Section | Field | Type | Notes |
|--------|--------|------|--------|
| **Identity** | `id` | PK (uuid) | |
| | `full_name` | string | |
| | `email` | string, unique | |
| | `phone` | string | |
| | `password_hash` | string | |
| | `account_status` | enum | PENDING_EMAIL_VERIFICATION, PENDING_APPROVAL, ACTIVE, SUSPENDED, DELETED |
| | `created_at` | timestamp | |
| | `updated_at` | timestamp | |
| **Profile** | `profile_photo` | string (URL) | |
| | `college_name` | string | |
| | `degree` | string | |
| | `branch` | string | |
| | `graduation_year` | int | |
| | `current_city` | string | |
| | `about_me` | text | |
| | `linkedin_url` | string | |
| | `github_url` | string | |
| | `portfolio_url` | string | |
| **Resume** | `resume_file_url` | string | |
| | `resume_ats_score` | int | |
| **Skills** | `skills_json` | JSON | `[{ "name": "Java", "level": 4, "verified": true }, ...]` |
| **Projects** | `projects_json` | JSON | `[{ "title": "E-commerce App", "tech": ["React","Node"], "verified": true }, ...]` |
| **DES** | `technical_score` | int | |
| | `communication_score` | int | |
| | `aptitude_score` | int | |
| | `project_score` | int | |
| | `overall_des` | int | |
| **Job prefs** | `job_preferences_json` | JSON | `{ "roles": [], "locations": [], "job_type": "", "expected_salary": 0 }` |
| **Privacy** | `show_phone` | boolean | |
| | `show_email` | boolean | |
| | `show_resume` | boolean | |
| | `show_des` | boolean | |
| **Interview** | `mock_interview_score` | int/float | |
| | `mentor_feedback` | text | |

---

## 2. Second table: `student_applications`

Only other table (many-to-many: students ↔ jobs).

| Field | Type | Notes |
|--------|------|--------|
| `id` | PK (uuid) | |
| `student_id` | FK → students.id | |
| `job_id` | FK → jobs.id | |
| `application_status` | string | e.g. applied, shortlisted, rejected |
| `applied_at` | timestamp | |
| `last_updated` | timestamp | |

---

## JSON shapes (reference)

**skills_json**
```json
[
  { "name": "Java", "level": 4, "verified": true },
  { "name": "React", "level": 3, "verified": false }
]
```

**projects_json**
```json
[
  { "title": "E-commerce App", "tech": ["React", "Node"], "verified": true }
]
```

**job_preferences_json**
```json
{
  "roles": ["Backend Developer"],
  "locations": ["Bangalore", "Pune"],
  "job_type": "Full-time",
  "expected_salary": 600000
}
```

---

## Summary

- **students** = one row per student, all profile/DES/prefs in one place (with JSON where needed).
- **student_applications** = one row per (student, job) application.
- No separate tables for skills, projects, resumes, or DES breakdown for MVP.
