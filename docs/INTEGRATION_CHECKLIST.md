# Dishasetu Auth System - Developer Integration Checklist

## ✅ Pre-Integration Tasks

### Backend Setup
- [ ] Copy `.env.example` to `.env` in server directory
- [ ] Install dependencies: `npm install`
- [ ] Generate Prisma client: `npx prisma generate`
- [ ] Create PostgreSQL database named `dishasetu`
- [ ] Run migrations: `npx prisma migrate dev --name init`
- [ ] Generate JWT secrets: `openssl rand -hex 32` (x2)
- [ ] Add secrets to `.env` file
- [ ] Test server startup: `npm run dev`
- [ ] Verify server runs at `http://localhost:5000`
- [ ] Check API docs at `http://localhost:5000/api/docs`

### Frontend Setup
- [ ] Install dependencies: `npm install`
- [ ] Create `.env.local` file
- [ ] Add `NEXT_PUBLIC_API_URL=http://localhost:5000/api`
- [ ] Check dependencies installed (zustand, axios, next-query)
- [ ] Test frontend startup: `npm run dev`
- [ ] Verify frontend runs at `http://localhost:3000`

### Dependency Verification
- [ ] Backend has `@prisma/client@^5.19.0`
- [ ] Backend has `bcryptjs@^2.4.3`
- [ ] Backend has `jsonwebtoken@^9.0.2`
- [ ] Frontend has `zustand@^5.0.8`
- [ ] Frontend has `axios@^1.13.1`

---

## 🔧 Code Integration Tasks

### 1. Update App Layout (Frontend)
**File:** `client/app/layout.tsx`

```tsx
// Add imports
import AuthProvider from '@/lib/auth.context';

// Wrap providers
export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

- [ ] Import AuthProvider
- [ ] Wrap children with AuthProvider
- [ ] Test app loads without errors

### 2. Create Login Page (Frontend)
**File:** `client/app/login/page.tsx`

```tsx
import { GuestRoute } from '@/components/auth/ProtectedRoute';
import { LoginForm } from '@/components/auth/LoginForm';

export default function LoginPage() {
  return (
    <GuestRoute>
      <div className="min-h-screen flex items-center justify-center">
        <div className="max-w-md w-full">
          <h1>Login</h1>
          <LoginForm />
        </div>
      </div>
    </GuestRoute>
  );
}
```

- [ ] Create login page
- [ ] Add LoginForm component
- [ ] Wrap with GuestRoute
- [ ] Test page loads and form works

### 3. Create Signup Page (Frontend)
**File:** `client/app/signup/page.tsx`

```tsx
import { GuestRoute } from '@/components/auth/ProtectedRoute';
import { SignupForm } from '@/components/auth/SignupForm';

export default function SignupPage() {
  return (
    <GuestRoute>
      <div className="min-h-screen flex items-center justify-center">
        <div className="max-w-2xl w-full">
          <h1>Create Account</h1>
          <SignupForm />
        </div>
      </div>
    </GuestRoute>
  );
}
```

- [ ] Create signup page
- [ ] Add SignupForm component
- [ ] Wrap with GuestRoute
- [ ] Test role selection works

### 4. Create Dashboard (Frontend)
**File:** `client/app/dashboard/page.tsx`

```tsx
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useAuth } from '@/lib/auth.context';

function DashboardContent() {
  const { user, logout } = useAuth();
  
  return (
    <div>
      <h1>Welcome, {user?.fullName}!</h1>
      <p>Role: {user?.role}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
```

- [ ] Create dashboard page
- [ ] Use ProtectedRoute wrapper
- [ ] Display user information
- [ ] Add logout button
- [ ] Test protected access

### 5. Connect Existing Routes
**Update existing user routes to use auth:**

```tsx
// Example: User profile route
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <UserProfile />
    </ProtectedRoute>
  );
}
```

- [ ] Wrap student routes with `<ProtectedRoute requiredRoles={[Role.STUDENT]}>`
- [ ] Wrap corporate routes with `<ProtectedRoute requiredRoles={[Role.CORPORATE]}>`
- [ ] Wrap university routes with `<ProtectedRoute requiredRoles={[Role.UNIVERSITY]}>`
- [ ] Wrap admin routes with `<ProtectedRoute requiredRoles={[Role.ADMIN]}>`

---

## 🧪 Testing Tasks

### Authentication Flow Tests
- [ ] **Signup Flow**
  - [ ] Fill signup form with STUDENT role
  - [ ] Submit and verify success message
  - [ ] Check tokens in localStorage
  - [ ] Verify user redirects to dashboard

- [ ] **Login Flow**
  - [ ] Go to login page
  - [ ] Enter correct credentials
  - [ ] Verify login success
  - [ ] Check tokens saved
  - [ ] Verify dashboard access

- [ ] **Failed Login**
  - [ ] Try wrong password 5 times
  - [ ] Verify account lockout message
  - [ ] Wait 15 minutes (or check code)
  - [ ] Verify account unlock

- [ ] **Logout Flow**
  - [ ] Login successfully
  - [ ] Click logout button
  - [ ] Verify tokens cleared
  - [ ] Verify redirect to login

### Role-Based Access Tests
- [ ] **STUDENT Role**
  - [ ] Can access student dashboard
  - [ ] Cannot access corporate routes
  - [ ] Cannot access admin routes

- [ ] **CORPORATE Role**
  - [ ] Can access corporate dashboard
  - [ ] Cannot access student routes
  - [ ] Cannot access admin routes

- [ ] **MENTOR Role**
  - [ ] Cannot login before approval
  - [ ] After admin approval, can login
  - [ ] Can access mentor dashboard

- [ ] **ADMIN Role** (Manual creation)
  - [ ] Can access admin dashboard
  - [ ] Can access all routes
  - [ ] Can manage users

### Token Tests
- [ ] **Token Refresh**
  - [ ] Wait for access token to expire (or mock)
  - [ ] Verify automatic token refresh
  - [ ] Verify new token used in requests

- [ ] **Token Expiry**
  - [ ] Clear localStorage tokens
  - [ ] Try to access protected route
  - [ ] Verify redirect to login

### Form Validation Tests
- [ ] **Signup Form**
  - [ ] Empty fields show errors
  - [ ] Invalid email shows error
  - [ ] Password too short shows error
  - [ ] Password without uppercase shows error
  - [ ] Passwords don't match show error

- [ ] **Login Form**
  - [ ] Empty email shows error
  - [ ] Empty password shows error
  - [ ] Invalid email shows error

### API Tests
```bash
# Test signup
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "fullName": "Test User",
    "email": "test@example.com",
    "password": "SecurePass@123",
    "confirmPassword": "SecurePass@123",
    "role": "STUDENT"
  }'

# Test login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass@123"
  }'

# Test protected route
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

- [ ] Signup returns tokens
- [ ] Login returns tokens
- [ ] Protected route accessible with token
- [ ] Protected route returns 401 without token
- [ ] Logout invalidates tokens

---

## 📋 Database Verification

### Table Verification
- [ ] `users` table exists
  - [ ] All columns present (id, fullName, email, passwordHash, role, status, etc.)
  - [ ] Indexes on email and role
  - [ ] UUID primary key

- [ ] `auth_tokens` table exists
  - [ ] Columns: id, userId, token, type, expiresAt, used, etc.
  - [ ] Foreign key to users
  - [ ] Index on expiresAt

- [ ] `password_resets` table exists
  - [ ] Columns: id, userId, token, expiresAt, usedAt
  - [ ] Foreign key to users

- [ ] `audit_logs` table exists
  - [ ] Columns: id, userId, action, resource, status, etc.
  - [ ] Index on createdAt

### Data Verification
- [ ] Can insert test user
- [ ] Email is unique
- [ ] Soft delete works (deletedAt nullable)
- [ ] Enums created correctly (Role, AccountStatus, TokenType)

---

## 🔐 Security Verification

- [ ] Passwords are hashed (not plain text in database)
- [ ] JWT secrets are NOT in code (only in .env)
- [ ] Tokens are hashed before storage
- [ ] No sensitive data in error messages
- [ ] CORS origin is configured
- [ ] Cookies are secure (httpOnly, sameSite)
- [ ] Rate limiting can be added to routes
- [ ] Audit logs capture all auth events

---

## 📦 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] No console errors
- [ ] No TypeScript errors
- [ ] Environment variables set correctly
- [ ] Database migrations run
- [ ] CORS configured for production domain
- [ ] JWT secrets are strong (use `openssl rand -hex 32`)

### Deployment Steps
```bash
# Backend
cd server
npm run build
npm start

# Frontend
cd client
npm run build
npm start
```

- [ ] Backend builds successfully
- [ ] Frontend builds successfully
- [ ] No console errors on load
- [ ] Authentication works on production domain
- [ ] HTTPS enabled
- [ ] Environment variables loaded from secrets

---

## 🚨 Troubleshooting

### Issue: "Cannot find module '@prisma/client'"
**Solution:**
```bash
cd server
npm install
npx prisma generate
```

### Issue: "Database connection refused"
**Solution:**
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Check database name matches
- Run: `psql -U postgres -c "CREATE DATABASE dishasetu;"`

### Issue: "JWT_SECRET not found"
**Solution:**
```bash
# Generate secrets
openssl rand -hex 32
openssl rand -hex 32

# Add to .env
JWT_SECRET=<generated_secret>
JWT_REFRESH_SECRET=<generated_secret>
```

### Issue: "CORS error in frontend"
**Solution:**
- Update CORS_ORIGIN in backend .env
- Verify NEXT_PUBLIC_API_URL in frontend .env
- Check API calls target correct URL

### Issue: "Token verification failed"
**Solution:**
- Clear localStorage
- Restart both servers
- Check JWT_SECRET matches between .env and production

### Issue: "Form validation not working"
**Solution:**
- Check express-validator is installed
- Verify validation rules match schema
- Check middleware order in routes

---

## 📞 Quick Reference

### Key API Endpoints
```
POST   /api/auth/signup           - Create account
POST   /api/auth/login            - Login
POST   /api/auth/refresh-token    - Refresh token
POST   /api/auth/logout           - Logout
GET    /api/auth/me               - Get user
POST   /api/auth/forgot-password  - Password reset request
POST   /api/auth/reset-password   - Password reset
```

### Key Frontend Hooks
```tsx
useAuth() → {
  user, isAuthenticated, isLoading, error,
  signup, login, logout, refreshToken,
  hasRole, canAccess
}
```

### Key Components
```tsx
<ProtectedRoute />        // Require auth + roles
<RoleGuard />             // Conditional render by role
<GuestRoute />            // Only for non-authenticated
<AdminOnly />             // Shorthand for admin
<StudentOnly />           // Shorthand for students
```

### Environment Variables
```
# Server
DATABASE_URL
JWT_SECRET
JWT_REFRESH_SECRET
CORS_ORIGIN

# Frontend
NEXT_PUBLIC_API_URL
```

---

## ✅ Final Sign-Off

Once all checkboxes are complete:

- [ ] **Development Complete** - All code integrated
- [ ] **Testing Complete** - All tests passing
- [ ] **Security Review** - No vulnerabilities
- [ ] **Documentation** - Team trained
- [ ] **Ready for Production** - Can deploy

---

## 📚 Reference Documentation

- **Complete Guide:** `AUTH_SYSTEM_DOCUMENTATION.md`
- **Quick Start:** `QUICK_START.md`
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY.md`
- **Environment Template:** `.env.example`

---

**Created:** January 2026  
**System:** Dishasetu Authentication  
**Status:** Ready for Integration  
**Next Step:** Begin checklist tasks
