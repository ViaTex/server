# Dishasetu Authentication System - Complete Implementation Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Backend Implementation](#backend-implementation)
5. [Frontend Implementation](#frontend-implementation)
6. [API Endpoints](#api-endpoints)
7. [Security Features](#security-features)
8. [Setup & Installation](#setup--installation)
9. [Testing](#testing)
10. [Future Enhancements](#future-enhancements)

---

## 🎯 Overview

A professional, scalable, role-based authentication system for the Dishasetu platform supporting 5 core user types:

- **STUDENT** - Can apply to jobs/internships
- **CORPORATE** - Can post jobs and manage hiring
- **UNIVERSITY** - TPO can manage university activities
- **MENTOR** - Can mentor students (requires approval)
- **ADMIN** - Full system access (created by admin only)

### Key Features

✅ Email-based signup/login  
✅ Secure password hashing (bcrypt)  
✅ JWT token management (access + refresh)  
✅ Role-based access control (RBAC)  
✅ Password reset functionality  
✅ Account status management  
✅ Login attempt limiting & account lockout  
✅ Audit logging  
✅ Secure token storage (hashed in DB)  
✅ Token refresh rotation  
✅ No email verification required (Phase 1)  

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- Node.js + Express.js
- TypeScript
- PostgreSQL + Prisma ORM
- JWT for authentication
- bcryptjs for password hashing

**Frontend:**
- Next.js 15
- React 19
- Zustand for state management
- Axios for API calls
- TailwindCSS for styling

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (React)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Login Form   │  │ Signup Form  │  │ Protected    │       │
│  │              │  │              │  │ Routes       │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                   │              │
│  ┌──────────────────────────────────────────────────┐        │
│  │       Auth Context + Zustand Store              │        │
│  │  (Token Management, User State, Refresh Logic)  │        │
│  └──────────────────────────────────────────────────┘        │
│         │                                                    │
└─────────│────────────────────────────────────────────────────┘
          │ API Calls (Axios)
          │
┌─────────▼────────────────────────────────────────────────────┐
│              Express.js Backend (Node.js)                    │
│  ┌──────────────────────────────────────────────────┐        │
│  │          Auth Routes & Controllers               │        │
│  │  /signup, /login, /refresh-token, /logout, etc  │        │
│  └──────────────────────────────────────────────────┘        │
│         │                                                    │
│  ┌──────────────────────────────────────────────────┐        │
│  │    Authentication Middleware & Guards            │        │
│  │  JWT Verification, Role-Based Access Control    │        │
│  └──────────────────────────────────────────────────┘        │
│         │                                                    │
│  ┌──────────────────────────────────────────────────┐        │
│  │      Auth Service Layer                          │        │
│  │  Signup, Login, Token Management, Validation    │        │
│  └──────────────────────────────────────────────────┘        │
│         │                                                    │
└─────────│────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│           PostgreSQL Database + Prisma ORM                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ users        │  │ auth_tokens  │  │ password_    │       │
│  │              │  │              │  │ resets       │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐                                            │
│  │ audit_logs   │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗃️ Database Schema

### Users Table

```prisma
model User {
  id                String        @id @default(uuid())
  fullName          String
  email             String        @unique
  passwordHash      String        (bcrypt)
  role              Role          (STUDENT|CORPORATE|UNIVERSITY|MENTOR|ADMIN)
  status            AccountStatus (ACTIVE|PENDING_APPROVAL|SUSPENDED|DELETED)
  emailVerified     Boolean       @default(false)
  lastLogin         DateTime?
  loginAttempts     Int           @default(0)
  lockedUntil       DateTime?     (for brute-force protection)
  createdAt         DateTime      @default(now())
  updatedAt         DateTime      @updatedAt
  deletedAt         DateTime?     (soft delete)
}
```

### Auth Tokens Table

```prisma
model AuthToken {
  id        String    @id @default(uuid())
  userId    String    @relation(User)
  token     String    (hashed JWT token)
  type      TokenType (ACCESS|REFRESH|RESET_PASSWORD|EMAIL_VERIFY)
  expiresAt DateTime
  used      Boolean   @default(false) (prevent replay attacks)
  usedAt    DateTime?
  ipAddress String?   (for security audit)
  userAgent String?   (for security audit)
}
```

### Password Reset Table

```prisma
model PasswordReset {
  id        String    @id @default(uuid())
  userId    String    @relation(User)
  token     String    (hashed)
  expiresAt DateTime  (1 hour from creation)
  usedAt    DateTime?
}
```

### Audit Logs Table

```prisma
model AuditLog {
  id        String   @id @default(uuid())
  userId    String?  @relation(User)
  action    String   (LOGIN|SIGNUP|PASSWORD_RESET|etc)
  resource  String   (AUTH|USER|etc)
  details   String?  (additional details)
  ipAddress String?
  userAgent String?
  status    String   (SUCCESS|FAILED)
  createdAt DateTime
}
```

---

## 🔧 Backend Implementation

### Key Files

```
server/src/
├── modules/auth/
│   ├── auth.service.ts       # Business logic (signup, login, etc)
│   ├── auth.controller.ts    # HTTP request handlers
│   ├── auth.routes.ts        # API endpoints
│   ├── auth.validation.ts    # Input validation rules
│   └── auth.types.ts         # TypeScript interfaces
├── middlewares/
│   ├── auth.middleware.ts    # JWT verification & RBAC
│   └── validate.middleware.ts
├── utils/
│   └── auth.utils.ts         # Password hashing, JWT, token utils
├── types/
│   └── auth.types.ts         # Central type definitions
└── config/
    ├── env.ts                # Environment variables
    └── database.ts           # Prisma client
```

### Auth Service Methods

```typescript
// Signup - Register new user
signup(data: SignupRequest): Promise<LoginResponse>

// Login - Authenticate user
login(data: LoginRequest, ipAddress?, userAgent?): Promise<LoginResponse>

// Refresh Token - Get new access token
refreshAccessToken(refreshToken: string): Promise<{accessToken, refreshToken}>

// Logout - Invalidate tokens
logout(userId: string): Promise<void>

// Password Reset
generatePasswordResetToken(email: string): Promise<string>
resetPassword(token, newPassword): Promise<void>

// Utilities
getUserById(userId): Promise<User>
getUserByEmail(email): Promise<User>
mapUserToResponse(user): UserResponse
logAuditEvent(data): Promise<void>
```

### Middleware Usage

```typescript
// Protect route with JWT verification
router.get('/protected', verifyToken, handler);

// Require specific role
router.delete('/admin/users/:id', verifyToken, requireRole(Role.ADMIN), handler);

// Optional authentication
router.get('/public', optionalAuth, handler);

// Require active account
router.post('/submit', verifyToken, requireActiveAccount, handler);
```

---

## 🎨 Frontend Implementation

### Key Files

```
client/
├── lib/
│   ├── auth.service.ts       # API calls to backend
│   ├── auth.context.tsx      # Auth context provider
├── store/
│   └── auth.store.ts         # Zustand state management
├── types/
│   └── auth.types.ts         # TypeScript types
├── components/auth/
│   ├── LoginForm.tsx         # Login form component
│   ├── SignupForm.tsx        # Signup form with role selection
│   └── ProtectedRoute.tsx    # Protected route components
└── app/
    ├── login/page.tsx        # Login page
    ├── signup/page.tsx       # Signup page
    ├── dashboard/page.tsx    # Protected dashboard
    └── providers.tsx         # App providers (AuthProvider)
```

### Auth Context Methods

```typescript
useAuth() → {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  signup: (data) => Promise<void>
  login: (data) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
  forgotPassword: (email) => Promise<void>
  resetPassword: (data) => Promise<void>
  
  hasRole: (role | roles[]) => boolean
  canAccess: (requiredRoles[]) => boolean
  clearError: () => void
}
```

### Protected Route Components

```typescript
// Wrap protected routes
<ProtectedRoute requiredRoles={[Role.ADMIN]}>
  <AdminDashboard />
</ProtectedRoute>

// Conditionally render based on role
<RoleGuard requiredRoles={Role.MENTOR}>
  <MentorFeatures />
</RoleGuard>

// Admin-only shorthand
<AdminOnly>
  <UserManagement />
</AdminOnly>
```

---

## 📡 API Endpoints

### Authentication Endpoints

```
POST   /api/auth/signup
       - Register new user
       - Body: { fullName, email, password, confirmPassword, role }
       - Response: { user, accessToken, expiresIn }

POST   /api/auth/login
       - Authenticate user
       - Body: { email, password }
       - Response: { user, accessToken, expiresIn }

POST   /api/auth/refresh-token
       - Refresh access token
       - Body: { refreshToken }
       - Response: { accessToken, expiresIn }

POST   /api/auth/logout
       - Logout user (requires auth)
       - Response: { success: true }

GET    /api/auth/me
       - Get current user (requires auth)
       - Response: { user }

POST   /api/auth/forgot-password
       - Request password reset token
       - Body: { email }
       - Response: { message: "Reset link sent" }

POST   /api/auth/reset-password
       - Reset password with token
       - Body: { token, newPassword, confirmPassword }
       - Response: { message: "Password reset successfully" }
```

### Response Format

**Success:**
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "user": { ... },
    "accessToken": "eyJ...",
    "expiresIn": 900
  }
}
```

**Error:**
```json
{
  "success": false,
  "message": "Error description",
  "errors": ["Field error 1", "Field error 2"]
}
```

---

## 🔐 Security Features

### 1. Password Security

- ✅ bcrypt hashing (12 rounds)
- ✅ Strong password requirements:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number
  - At least one special character

### 2. Token Security

- ✅ JWT with HS256 algorithm
- ✅ Short-lived access tokens (15 minutes)
- ✅ Longer-lived refresh tokens (7 days)
- ✅ Refresh token rotation (each refresh generates new token)
- ✅ Tokens are hashed before storage in database
- ✅ Replay attack prevention (mark used tokens)

### 3. Account Security

- ✅ Login attempt limiting (5 failed attempts)
- ✅ Account lockout (15 minutes)
- ✅ Soft delete support (never truly delete user data)
- ✅ Account status management (ACTIVE, PENDING_APPROVAL, SUSPENDED)
- ✅ Last login tracking

### 4. HTTP Security

- ✅ Secure cookies (httpOnly, sameSite, secure flags)
- ✅ CORS protection
- ✅ Helmet.js headers
- ✅ Rate limiting ready (implement with express-rate-limit)

### 5. Audit & Monitoring

- ✅ Audit logs for all auth events
- ✅ IP address and user-agent tracking
- ✅ Failed login tracking
- ✅ Status change tracking

### 6. Data Protection

- ✅ Email normalization (lowercase)
- ✅ Input validation and sanitization
- ✅ RBAC at middleware level
- ✅ Protected routes require valid JWT
- ✅ Role hierarchy enforcement

---

## 🚀 Setup & Installation

### Prerequisites

- Node.js 18+
- PostgreSQL 14+
- npm or yarn

### Backend Setup

```bash
# 1. Install dependencies
cd server
npm install

# 2. Setup environment variables
cp .env.example .env
# Edit .env and set DATABASE_URL, JWT_SECRET, etc.

# 3. Setup database
npx prisma generate
npx prisma migrate dev --name init

# 4. (Optional) Seed database
npx prisma db seed

# 5. Start development server
npm run dev
```

### Frontend Setup

```bash
# 1. Install dependencies
cd client
npm install

# 2. Setup environment variables
cp .env.example .env.local
# Edit .env.local and set NEXT_PUBLIC_API_URL

# 3. Start development server
npm run dev
```

### Environment Variables

See `.env.example` for all available variables. Key ones:

**Backend:**
```
DATABASE_URL=postgresql://user:pass@localhost/dishasetu
JWT_SECRET=<generate with: openssl rand -hex 32>
JWT_REFRESH_SECRET=<generate with: openssl rand -hex 32>
JWT_ACCESS_EXPIRES_IN=15m
JWT_REFRESH_EXPIRES_IN=7d
```

**Frontend:**
```
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

---

## 🧪 Testing

### Test Signup/Login Flow

1. **Signup as Student:**
```bash
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "fullName": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass@123",
    "confirmPassword": "SecurePass@123",
    "role": "STUDENT"
  }'
```

2. **Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass@123"
  }'
```

3. **Access Protected Route:**
```bash
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Test Role-Based Access

```bash
# As STUDENT - Should succeed
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <student_token>"

# As different role trying to access ADMIN route - Should fail
curl -X DELETE http://localhost:5000/api/admin/users/123 \
  -H "Authorization: Bearer <student_token>"
# Response: 403 Forbidden
```

### Test Token Refresh

```bash
curl -X POST http://localhost:5000/api/auth/refresh-token \
  -H "Content-Type: application/json" \
  -d '{"refreshToken": "<refresh_token>"}'
```

### Test Locked Account

```bash
# Make 5 failed login attempts
for i in {1..5}; do
  curl -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "email": "john@example.com",
      "password": "WrongPassword"
    }'
done

# 6th attempt should return: "Account is locked"
```

---

## 📈 Future Enhancements

### Phase 2 - Email Verification
- [ ] Email verification on signup
- [ ] Resend verification email
- [ ] Email verification deadline

### Phase 3 - OAuth
- [ ] Google OAuth integration
- [ ] LinkedIn OAuth integration
- [ ] GitHub OAuth integration

### Phase 4 - 2FA & Advanced Security
- [ ] Two-factor authentication (2FA)
- [ ] SMS verification
- [ ] Device management
- [ ] Session management

### Phase 5 - Profile & Preferences
- [ ] User profile management
- [ ] Notification preferences
- [ ] Theme preferences
- [ ] Privacy settings

### Phase 6 - Admin Features
- [ ] User management dashboard
- [ ] Role management
- [ ] Permission management
- [ ] Audit log viewer
- [ ] Bulk user operations

### Phase 7 - Sub-Roles
- [ ] Corporate: HR, Hiring Manager, Recruiter
- [ ] University: TPO, Coordinator
- [ ] Student: Active, Alumni, Graduate

### Phase 8 - Analytics
- [ ] Login analytics
- [ ] Signup funnel analysis
- [ ] User retention metrics
- [ ] Activity dashboards

---

## 📚 File Structure Overview

### Backend File Structure
```
server/
├── prisma/
│   ├── schema.prisma          # Database schema with User, AuthToken, etc.
│   ├── migrations/            # Database migrations
│   └── seed.ts                # Database seeding
├── src/
│   ├── modules/auth/
│   │   ├── auth.service.ts    # signup, login, logout, token refresh
│   │   ├── auth.controller.ts # HTTP handlers with error handling
│   │   ├── auth.routes.ts     # Express routes with Swagger docs
│   │   ├── auth.validation.ts # Input validation rules
│   │   └── auth.types.ts      # Re-exports from central types
│   ├── middlewares/
│   │   ├── auth.middleware.ts # verifyToken, requireRole, requireActiveAccount
│   │   ├── error.middleware.ts
│   │   ├── notFound.ts
│   │   └── validate.middleware.ts
│   ├── utils/
│   │   └── auth.utils.ts      # hashPassword, generateJWT, validatePassword, etc.
│   ├── types/
│   │   └── auth.types.ts      # Central type definitions for entire backend
│   ├── config/
│   │   ├── env.ts             # Environment variables
│   │   ├── database.ts        # Prisma client
│   │   └── swagger.ts         # Swagger documentation
│   ├── app.ts                 # Express app setup
│   └── server.ts              # Server startup
└── package.json
```

### Frontend File Structure
```
client/
├── types/
│   └── auth.types.ts          # Mirror of backend auth types + UI types
├── lib/
│   ├── auth.service.ts        # API client for auth endpoints
│   ├── auth.context.tsx       # AuthProvider context with useAuth hook
│   ├── axios.ts               # Axios instance with interceptors
│   └── constants.ts
├── store/
│   ├── auth.store.ts          # Zustand store for auth state
│   └── index.ts
├── components/auth/
│   ├── LoginForm.tsx          # Unified login form
│   ├── SignupForm.tsx         # Role-based signup form
│   ├── ProtectedRoute.tsx     # Protected, RoleGuard, GuestRoute components
│   ├── ForgotPasswordForm.tsx # Password reset forms
│   └── LogoutButton.tsx
├── app/
│   ├── login/page.tsx         # Login page using GuestRoute
│   ├── signup/page.tsx        # Signup page using GuestRoute
│   ├── dashboard/page.tsx     # Protected dashboard
│   ├── layout.tsx             # Root layout with AuthProvider
│   ├── providers.tsx          # App providers setup
│   └── api/
│       ├── auth/[...route].ts # API routes (if needed)
│       └── middleware.ts
├── public/
└── package.json
```

---

## ✨ Best Practices Implemented

1. **Security First**
   - Passwords never logged
   - Tokens hashed in database
   - Secure HTTP headers
   - Rate limiting ready

2. **Clean Code**
   - Separation of concerns (service/controller/routes)
   - Comprehensive error handling
   - TypeScript strict mode
   - Well-documented code with JSDoc comments

3. **Scalability**
   - Modular architecture
   - Environment-based configuration
   - Database migrations
   - Ready for horizontal scaling

4. **User Experience**
   - Clear error messages
   - Loading states
   - Success notifications
   - Form validation feedback

5. **Developer Experience**
   - Comprehensive documentation
   - Example environment file
   - API documentation with Swagger
   - Easy-to-use hooks and components

---

## 🤝 Support & Troubleshooting

### Common Issues

**1. "Cannot find module '@prisma/client'"**
```bash
cd server
npm install
npx prisma generate
```

**2. "Database connection refused"**
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Check database exists

**3. "JWT secret not found"**
- Ensure JWT_SECRET is set in .env
- Generate one: `openssl rand -hex 32`

**4. "CORS error in frontend"**
- Check CORS_ORIGIN matches frontend URL
- Verify API URL in NEXT_PUBLIC_API_URL

---

## 📞 Questions?

Refer to the inline code documentation and comments for detailed implementation details.

---

**Version:** 1.0.0  
**Last Updated:** January 2026  
**Status:** Production Ready
