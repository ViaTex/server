
## Overview

The **Disasetu Server** is a production-ready backend system built with **FastAPI**, **PostgreSQL**, **Redis**, **JWT**, and **OAuth**. It provides a robust authentication and authorization system with features like dual OTP verification, role-based access control (RBAC), OAuth integration, and session management.

---

## Table of Contents

1. **Authentication System**
   - User Registration
   - User Login
   - OTP Verification
   - OAuth Integration
   - Token Management
   - Password Reset
   - Logout
2. **Authorization System**
   - Role-Based Access Control (RBAC)
   - Predefined Roles
3. **API Endpoints**
   - Authentication APIs
   - OAuth APIs
   - Protected APIs
4. **Database Schema**
   - Users Table
   - OAuth Connections Table
   - Refresh Tokens Table
   - OTPs Table
5. **Rate Limiting**
6. **Security Features**
7. **Environment Configuration**
8. **Deployment and Testing**

---

## 1. Authentication System

### 1.1 User Registration

- **Flow**:
  1. User submits their email, phone number, password, role, and account type.
  2. Backend creates a user with `pending` status.
  3. OTPs are generated and sent to the user's email and phone for verification.

- **Key Features**:
  - Email and phone uniqueness are enforced.
  - Passwords are hashed using **bcrypt**.
  - OTPs are stored in the database with expiration and usage tracking.

- **Relevant Code**:
  - auth_service.py
  - otp_service.py

---

### 1.2 User Login

- **Flow**:
  1. User submits their email and password.
  2. Backend validates the credentials and checks the account status.
  3. If valid, an access token (15 minutes) and refresh token (30 days) are issued.

- **Key Features**:
  - Account lockout after multiple failed attempts.
  - Refresh token is stored in the database with device IP and user agent.

- **Relevant Code**:
  - auth_service.py
  - security.py
  - security.py

---

### 1.3 OTP Verification

- **Flow**:
  1. User submits the OTPs sent to their email and phone.
  2. Backend verifies the OTPs and activates the account.

- **Key Features**:
  - OTP expiration and maximum attempts are enforced.
  - OTPs are deleted after successful verification.

- **Relevant Code**:
  - auth_service.py
  - otp_service.py

---

### 1.4 OAuth Integration

- **Supported Providers**:
  - Google
  - LinkedIn

- **Flow**:
  1. User is redirected to the OAuth provider for authentication.
  2. Backend receives the user's profile data.
  3. If the user is new, they are prompted to verify their phone number and set their role.

- **Key Features**:
  - Email is auto-verified for OAuth users.
  - OAuth connections are stored in the database.

- **Relevant Code**:
  - oauth_service.py
  - oauth_service.py

---

### 1.5 Token Management

- **Access Token**:
  - Short-lived (15 minutes).
  - Used for accessing protected APIs.

- **Refresh Token**:
  - Long-lived (30 days).
  - Stored as an HttpOnly cookie.
  - Used to generate new access tokens.

- **Relevant Code**:
  - security.py
  - security.py
  - auth_service.py

---

### 1.6 Password Reset

- **Flow**:
  1. User requests a password reset by providing their email.
  2. Backend generates an OTP and sends it to the user's email.
  3. User submits the OTP and a new password.
  4. Backend verifies the OTP and updates the password.

- **Relevant Code**:
  - auth.py
  - auth.py

---

### 1.7 Logout

- **Flow**:
  1. User logs out by revoking their refresh token.
  2. Backend clears the refresh token from the database.

- **Relevant Code**:
  - auth_service.py

---

## 2. Authorization System

### 2.1 Role-Based Access Control (RBAC)

- **Roles**:
  - **Student**: Individual learners.
  - **Mentor**: Guides and advisors.
  - **TPO**: Training and Placement Officers.
  - **Corporate HR**: Company recruiters.

- **Implementation**:
  - Role-based access is enforced using the `RoleChecker` dependency.

- **Relevant Code**:
  - security.py

---

## 3. API Endpoints

### 3.1 Authentication APIs

| Method | Endpoint                        | Description                     |
|--------|---------------------------------|---------------------------------|
| POST   | `/api/v1/auth/register`         | Register a new user.           |
| POST   | `/api/v1/auth/verify-otp`       | Verify email and phone OTPs.   |
| POST   | `/api/v1/auth/resend-otp`       | Resend OTPs.                   |
| POST   | `/api/v1/auth/login`            | Login with email and password. |
| POST   | `/api/v1/auth/logout`           | Logout and revoke tokens.      |
| POST   | `/api/v1/auth/refresh`          | Refresh access token.          |
| POST   | `/api/v1/auth/password-reset/request` | Request password reset. |
| POST   | `/api/v1/auth/password-reset/confirm` | Confirm password reset. |

---

### 3.2 OAuth APIs

| Method | Endpoint                        | Description                     |
|--------|---------------------------------|---------------------------------|
| GET    | `/api/v1/auth/oauth/google/login` | Redirect to Google login.    |
| GET    | `/api/v1/auth/oauth/google/callback` | Handle Google callback.    |
| POST   | `/api/v1/auth/oauth/complete-registration` | Complete OAuth registration. |
| POST   | `/api/v1/auth/oauth/verify-phone` | Verify phone for OAuth users. |

---

### 3.3 Protected APIs

| Method | Endpoint                        | Description                     |
|--------|---------------------------------|---------------------------------|
| GET    | `/api/v1/auth/me`               | Get current user info.         |
| GET    | `/jobs/list`                    | List all job postings.         |
| POST   | `/jobs/create`                  | Create a new job posting.      |

---

## 4. Database Schema

### 4.1 Users Table

| Column             | Type       | Description                     |
|--------------------|------------|---------------------------------|
| `id`               | UUID       | Primary key.                    |
| `email`            | String     | User's email.                   |
| `phone_number`     | String     | User's phone number.            |
| `password_hash`    | String     | Hashed password.                |
| `account_status`   | String     | `pending`, `active`, `suspended`. |

---

### 4.2 OAuth Connections Table

| Column             | Type       | Description                     |
|--------------------|------------|---------------------------------|
| `id`               | UUID       | Primary key.                    |
| `provider`         | String     | OAuth provider (e.g., Google).  |
| `provider_id`      | String     | Provider's unique user ID.      |

---

### 4.3 Refresh Tokens Table

| Column             | Type       | Description                     |
|--------------------|------------|---------------------------------|
| `id`               | UUID       | Primary key.                    |
| `token`            | String     | Refresh token.                  |
| `expires_at`       | DateTime   | Expiration time.                |

---

### 4.4 OTPs Table

| Column             | Type       | Description                     |
|--------------------|------------|---------------------------------|
| `id`               | UUID       | Primary key.                    |
| `otp_code`         | String     | OTP code.                       |
| `expires_at`       | DateTime   | Expiration time.                |

---

## 5. Rate Limiting

- **API Endpoints**: 10 requests/second.
- **Login Endpoints**: 5 requests/minute.
- **OTP Endpoints**: 3 requests/5 minutes.

---

## 6. Security Features

- **Password Hashing**: Bcrypt.
- **JWT Tokens**: Short-lived access tokens and long-lived refresh tokens.
- **Account Lockout**: After 5 failed login attempts.
- **Rate Limiting**: Enforced via Redis.

---

## 7. Environment Configuration

- **File**: .env
- **Key Variables**:
  - `DATABASE_URL`: PostgreSQL connection string.
  - `REDIS_URL`: Redis connection string.
  - `JWT_SECRET_KEY`: Secret key for JWT.
  - `SMS_API_KEY`: SMS provider API key.

---

## 8. Deployment and Testing

- **Development**:
  ```bash
  uvicorn app.main:app --reload
  ```

- **Production**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```

- **Testing**:
  ```bash
  pytest tests/
  ```

--- 

