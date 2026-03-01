# Disasetu Server - FastAPI Authentication System

A production-ready authentication and authorization system built with FastAPI, PostgreSQL, Redis, JWT, and OAuth.

## 🚀 Features

- **Modern Tech Stack**: FastAPI, PostgreSQL (NeonDB), Redis, SQLAlchemy 2.0 (async), Alembic
- **Authentication**: 
  - Email/Password with JWT tokens
  - Dual verification (Email + Phone OTP)
  - OAuth integration (Google, LinkedIn)
  - 30-day session persistence with refresh tokens
- **Authorization**: Role-Based Access Control (RBAC) with 4 roles (Student, Mentor, TPO, Corporate HR)
- **Security**: 
  - Password hashing with Bcrypt
  - Account lockout after failed attempts
  - Rate limiting (API, Login, OTP endpoints)
  - Security headers via Nginx
- **Infrastructure**: 
  - Nginx reverse proxy with load balancing
  - Redis caching and session storage
  - Structured JSON logging with Structlog
  - Database migrations with Alembic

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL (or NeonDB account)
- Redis
- Nginx (optional, for production)

## 🛠️ Installation

### 1. Clone and Setup Environment

```bash
cd server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
# Required settings:
# - DATABASE_URL (NeonDB PostgreSQL connection string)
# - REDIS_URL
# - SECRET_KEY and JWT_SECRET_KEY (generate secure random strings)
# - OAuth credentials (Google, LinkedIn)
# - Email settings (ZeptoMail)
# - SMS provider settings
```

### 3. Database Migration

```bash
# Run Alembic migrations to create database tables
alembic upgrade head
```

### 4. Run the Server

```bash
# Development mode (with auto-reload)
python app/main.py

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (with multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📚 API Endpoints

### Authentication

#### Standard Registration & Login
```
POST /api/v1/auth/register
POST /api/v1/auth/verify-otp
POST /api/v1/auth/resend-otp
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
```

#### OAuth (Google/LinkedIn)
```
GET  /api/v1/auth/oauth/google/login
GET  /api/v1/auth/oauth/google/callback
POST /api/v1/auth/oauth/complete-registration
POST /api/v1/auth/oauth/verify-phone

GET  /api/v1/auth/oauth/linkedin/login
GET  /api/v1/auth/oauth/linkedin/callback
```

#### Password Reset
```
POST /api/v1/auth/password-reset/request
POST /api/v1/auth/password-reset/confirm
```

#### User Info
```
GET  /api/v1/auth/me
```

## 🔐 Authentication Flow

### Standard Sign-Up
1. User submits email, phone, password, role, and account type
2. Backend creates user with `pending` status
3. Sends OTP to both email and phone
4. User verifies both OTPs
5. Account status changes to `active`

### Standard Sign-In
1. User submits email and password
2. Backend validates credentials and account status
3. Issues 15-minute access token and 30-day refresh token
4. Refresh token stored as HttpOnly cookie

### OAuth Flow (Google/LinkedIn)
1. User redirects to OAuth provider
2. Backend receives profile data
3. Email auto-verified (trusted provider)
4. New users prompted for phone number and role
5. Phone OTP verification required
6. Account activated after phone verification

### Token Refresh
1. Access token expires after 15 minutes
2. Client receives 401 Unauthorized
3. Client calls `/refresh` endpoint with refresh token cookie
4. Backend issues new access token

## 🛡️ Authorization (RBAC)

### Available Roles
- **Student**: Individual learners
- **Mentor**: Guides and advisors
- **TPO**: Training and Placement Officers
- **Corporate HR**: Company recruiters

### Using Role Checkers

```python
from fastapi import APIRouter, Depends
from app.core.security import get_current_active_user, RoleChecker

router = APIRouter()

# Single role
allow_hr = RoleChecker(["Corporate HR"])

@router.post("/jobs/create", dependencies=[Depends(allow_hr)])
async def create_job(
    current_user = Depends(get_current_active_user)
):
    return {"message": "Job created"}

# Multiple roles
allow_staff = RoleChecker(["TPO", "Corporate HR", "Mentor"])

@router.get("/applications", dependencies=[Depends(allow_staff)])
async def view_applications(
    current_user = Depends(get_current_active_user)
):
    return {"applications": []}
```

## 📊 Database Schema

### Users Table
- Authentication (email, phone, password_hash)
- Verification status (email_verified, phone_verified)
- Account info (account_type, role, account_status)
- Security (failed_login_attempts, locked_until)

### OAuth Connections Table
- Links OAuth providers to user accounts
- Stores provider ID and metadata

### Refresh Tokens Table
- 30-day session tokens
- Device tracking (IP, user agent)
- Revocation support

### OTPs Table
- Email and phone verification codes
- Password reset codes
- Expiration and attempt tracking

## 🚀 Deployment

### Using Nginx

1. Copy nginx.conf to your Nginx configuration directory:
```bash
sudo cp nginx.conf /etc/nginx/sites-available/disasetu
sudo ln -s /etc/nginx/sites-available/disasetu /etc/nginx/sites-enabled/
```

2. Update the configuration:
   - Replace `your-domain.com` with your domain
   - Configure SSL certificates for HTTPS
   - Adjust upstream servers for load balancing

3. Test and reload Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Using Docker (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 🔧 Configuration

### Rate Limiting
- API endpoints: 10 requests/second
- Login endpoints: 5 requests/minute
- OTP endpoints: 3 requests/5 minutes

### Security Settings
- Max login attempts: 5
- Account lockout: 30 minutes
- OTP expiration: 10 minutes
- Access token: 15 minutes
- Refresh token: 30 days

## 📝 Example Usage

### Registration
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "phone_number": "+1234567890",
    "password": "SecurePass123",
    "account_type": "Individual",
    "role": "Student"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "SecurePass123"
  }'
```

### Protected Endpoint
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <your_access_token>"
```

## 🧪 Testing

```bash
# Install testing dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## 📖 Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🔍 Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL in .env
- Check PostgreSQL/NeonDB is running
- Ensure database exists and is accessible

### Redis Connection Issues
- Verify REDIS_URL in .env
- Check Redis server is running: `redis-cli ping`

### OAuth Issues
- Verify OAuth credentials in .env
- Check redirect URIs match provider settings
- Ensure callback URLs are whitelisted

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check documentation at /docs
- Review logs for error details
