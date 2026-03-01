# Student Profile Wizard

## Overview

The **Student Profile Wizard** is a comprehensive feature designed to allow students to create and manage their profiles efficiently. This wizard supports both draft and final submission modes, ensuring flexibility and ease of use. The backend is built using **FastAPI**, **SQLAlchemy**, and **Pydantic**, ensuring robust validation and seamless integration with the database.

---

## Features

1. **Profile Creation and Updates**:
   - Create a new profile if one does not exist.
   - Update existing profiles with new data.
   - Supports both manual JSON input and AI-generated draft data.

2. **Draft Mode**:
   - Save progress without mandatory field validation.
   - Allows students to revisit and complete their profiles later.

3. **Validation**:
   - Mandatory fields are validated only during final submission.
   - Ensures data integrity and completeness.

4. **Profile Components**:
   - **Bio**: Includes date of birth, gender, and location.
   - **Education**: Add multiple education entries with details like degree, institution, and years.
   - **Skills**: Add skills with proficiency levels and years of experience.
   - **Projects**: Add projects with descriptions, tech stack, and links.

5. **Logging and Monitoring**:
   - Detailed logs for profile creation and updates.
   - Tracks draft and completion statuses.

---

## API Endpoints

### 1. Create or Update Profile (Wizard)

- **Endpoint**: `POST /api/v1/student/profile/wizard`
- **Description**: Unified endpoint for creating or updating student profiles.
- **Request Body**:
  ```json
  {
    "date_of_birth": "YYYY-MM-DD",
    "gender": "Male/Female/Other",
    "location": {
      "city": "City Name",
      "state": "State Name",
      "country": "Country Name",
      "pincode": "123456"
    },
    "education": [
      {
        "degree": "B.Tech",
        "institution": "University Name",
        "field_of_study": "Computer Science",
        "start_year": 2018,
        "end_year": 2022,
        "grade": "8.5 CGPA",
        "is_current": false
      }
    ],
    "skills": [
      {
        "name": "Python",
        "proficiency_level": "Advanced",
        "years_of_experience": 3
      }
    ],
    "projects": [
      {
        "title": "Portfolio Website",
        "short_description": "A personal portfolio website.",
        "tech_stack": ["HTML", "CSS", "JavaScript"],
        "links": {
          "github": "https://github.com/username/portfolio",
          "demo": "https://portfolio-demo.com"
        }
      }
    ],
    "is_draft": true
  }
  ```
- **Response**:
  ```json
  {
    "id": "UUID",
    "is_draft": true,
    "is_complete": false,
    "completion_percentage": 50
  }
  ```

### 2. Partial Profile Update

- **Endpoint**: `PATCH /api/v1/student/profile`
- **Description**: Update specific fields of an existing profile.
- **Request Body**:
  ```json
  {
    "bio": {
      "date_of_birth": "YYYY-MM-DD",
      "gender": "Male/Female/Other",
      "location": {
        "city": "City Name",
        "state": "State Name",
        "country": "Country Name",
        "pincode": "123456"
      }
    },
    "skills": [
      {
        "name": "Python",
        "proficiency_level": "Expert",
        "years_of_experience": 5
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "id": "UUID",
    "is_draft": false,
    "is_complete": true,
    "completion_percentage": 100
  }
  ```

---

## Database Schema

### StudentInfo Table

| Column               | Type       | Description                     |
|----------------------|------------|---------------------------------|
| `id`                 | UUID       | Primary key.                    |
| `user_id`            | UUID       | Foreign key to Users table.     |
| `date_of_birth`      | Date       | Student's date of birth.        |
| `gender`             | String     | Gender of the student.          |
| `location`           | JSON       | Location details.               |
| `education`          | JSON       | List of education entries.      |
| `skills`             | JSON       | List of skills.                 |
| `projects`           | JSON       | List of projects.               |
| `is_draft`           | Boolean    | Indicates if profile is a draft.|
| `is_complete`        | Boolean    | Indicates if profile is complete.|
| `completion_percentage` | Integer | Profile completion percentage.  |

---

## Development Notes

- **Validation**:
  - Use Pydantic schemas for strict validation.
  - Ensure all mandatory fields are provided during final submission.

- **Logging**:
  - Use `app.core.logging` for detailed logs.
  - Log both draft and final submissions.

- **Testing**:
  - Write unit tests for all endpoints.
  - Test edge cases like incomplete data, invalid fields, etc.

---

## Future Enhancements

- **AI Integration**:
  - Use AI to suggest skills and projects based on the student's education and interests.

- **Profile Analytics**:
  - Provide insights on profile completeness and suggestions for improvement.

- **Mobile Support**:
  - Optimize APIs for mobile applications.