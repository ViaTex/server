# Dishasetu Auth System - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Backend Setup (Server)

```bash
# Navigate to server directory
cd server

# Install dependencies
npm install

# Generate Prisma client
npx prisma generate

# Create .env file
cp ../.env.example .env

# Edit .env with your PostgreSQL credentials
# DATABASE_URL=postgresql://user:password@localhost:5432/dishasetu
# Generate JWT secrets: openssl rand -hex 32

# Run database migrations
npx prisma migrate dev --name init

# Start server
npm run dev
# Server runs at http://localhost:5000
```

### Step 2: Frontend Setup (Client)

```bash
# Navigate to client directory
cd client

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:5000/api" > .env.local

# Start frontend
npm run dev
# Frontend runs at http://localhost:3000
```

### Step 3: Test Authentication

1. **Visit http://localhost:3000**
2. **Go to Sign Up**
   - Fill in form with role: STUDENT
   - Use password: `SecurePass@123`
3. **Login with credentials**
4. **Access dashboard** - you're authenticated!

---

## 📋 What Was Implemented

### Backend ✅
- [x] Prisma schema with User, AuthToken, PasswordReset, AuditLog models
- [x] Role-based enums (STUDENT, CORPORATE, UNIVERSITY, MENTOR, ADMIN)
- [x] Account status management
- [x] Auth service: signup, login, logout, token refresh, password reset
- [x] JWT utilities: generation, verification, hashing
- [x] Password utilities: hashing (bcrypt), validation, strength checking
- [x] Auth middleware: JWT verification, role guards, active account checks
- [x] Comprehensive input validation
- [x] Error handling and audit logging
- [x] 6 main API endpoints

### Frontend ✅
- [x] TypeScript auth types (mirrors backend)
- [x] Zustand auth store with token management
- [x] Auth context provider with useAuth hook
- [x] API service with axios + interceptors
- [x] Login form component
- [x] Signup form with role selection
- [x] Protected route components (ProtectedRoute, RoleGuard, etc.)
- [x] Role-specific component guards

---

## 🔧 Environment Variables

Create `.env` in server directory:
```env
NODE_ENV=development
PORT=5000
DATABASE_URL=postgresql://postgres:password@localhost:5432/dishasetu
JWT_SECRET=<run: openssl rand -hex 32>
JWT_REFRESH_SECRET=<run: openssl rand -hex 32>
CORS_ORIGIN=http://localhost:3000
```

Create `.env.local` in client directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

---

## 🎯 Key Features Ready to Use

### Authentication Flows
- ✅ Signup with role selection
- ✅ Login with email/password
- ✅ Token refresh (15m access, 7d refresh)
- ✅ Logout with token invalidation
- ✅ Password reset
- ✅ Account status handling

### Security
- ✅ bcrypt password hashing (12 rounds)
- ✅ JWT token management
- ✅ Login attempt limiting (5 failed attempts)
- ✅ Account lockout (15 minutes)
- ✅ Secure token storage (hashed)
- ✅ Replay attack prevention
- ✅ Role-based access control

### User Management
- ✅ Role-based signup (STUDENT, CORPORATE, UNIVERSITY, MENTOR)
- ✅ ADMIN created by backend only
- ✅ Account status tracking
- ✅ Last login tracking
- ✅ Audit logging

---

## 📱 Usage Examples

### Backend API Calls

**Signup:**
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

**Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass@123"
  }'
```

**Protected Route:**
```bash
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

### Frontend Hook Usage

```tsx
import { useAuth } from '@/lib/auth.context';

function MyComponent() {
  const { user, login, logout, hasRole, isLoading, error } = useAuth();

  // Check user authentication
  if (!user) return <div>Please login</div>;

  // Check role
  if (hasRole('ADMIN')) {
    return <AdminDashboard />;
  }

  // Use auth methods
  const handleLogout = async () => {
    await logout();
  };

  return (
    <div>
      <p>Welcome, {user.fullName}!</p>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}
```

### Protected Routes

```tsx
import { ProtectedRoute, RoleGuard, AdminOnly } from '@/components/auth/ProtectedRoute';
import { Role } from '@/types/auth.types';

// Full protection
<ProtectedRoute requiredRoles={[Role.ADMIN]}>
  <AdminDashboard />
</ProtectedRoute>

// Conditional rendering
<RoleGuard requiredRoles={Role.MENTOR}>
  <MentorPanel />
</RoleGuard>

// Shorthand
<AdminOnly>
  <UserManagement />
</AdminOnly>
```

---

## 🧪 Testing Roles

Use these test accounts after signup:

```
Role: STUDENT
- Status: ACTIVE (can login immediately)
- Access: Student features

Role: CORPORATE
- Status: ACTIVE (can login immediately)
- Access: Job posting, hiring management

Role: UNIVERSITY
- Status: ACTIVE (can login immediately)
- Access: TPO activities

Role: MENTOR
- Status: PENDING_APPROVAL (cannot login)
- Access: None (requires admin approval)
- Note: Admin must update status to ACTIVE

Role: ADMIN
- Status: N/A (created via database)
- Access: Full system access
- Creation: Manual DB entry
```

---

## 🔐 Security Checklist

- [x] Passwords hashed with bcrypt (12 rounds)
- [x] JWT tokens secure and time-limited
- [x] Refresh token rotation implemented
- [x] Login attempt limiting (5 attempts)
- [x] Account lockout (15 minutes)
- [x] Secure cookies (httpOnly, sameSite)
- [x] CORS configured
- [x] Input validation
- [x] Role-based access control
- [x] Audit logging
- [x] Soft delete support
- [x] Token hashing in database

---

## 📚 File Reference

### Key Backend Files
- `server/prisma/schema.prisma` - Database schema
- `server/src/modules/auth/auth.service.ts` - Core auth logic
- `server/src/modules/auth/auth.controller.ts` - HTTP handlers
- `server/src/modules/auth/auth.routes.ts` - API endpoints
- `server/src/middlewares/auth.middleware.ts` - Security middleware
- `server/src/utils/auth.utils.ts` - Auth utilities
- `server/src/types/auth.types.ts` - Type definitions
- `server/src/config/env.ts` - Configuration

### Key Frontend Files
- `client/types/auth.types.ts` - Auth type definitions
- `client/lib/auth.service.ts` - API client
- `client/lib/auth.context.tsx` - Auth provider
- `client/store/auth.store.ts` - Zustand store
- `client/components/auth/LoginForm.tsx` - Login form
- `client/components/auth/SignupForm.tsx` - Signup form
- `client/components/auth/ProtectedRoute.tsx` - Route guards

---

## 🐛 Troubleshooting

### "Cannot connect to database"
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Run: `npx prisma db push`

### "JWT_SECRET not found"
- Add to .env: `JWT_SECRET=<run: openssl rand -hex 32>`
- Restart server

### "CORS error in frontend"
- Check CORS_ORIGIN in server .env matches frontend URL
- Verify NEXT_PUBLIC_API_URL is correct

### "Token verification failed"
- Check JWT_SECRET matches between .env and code
- Ensure token hasn't expired

---

## 📞 Next Steps

1. **Database Seeding** - Create test users
   ```bash
   cd server
   npx prisma db seed
   ```

2. **Email Configuration** - Set up password reset emails
   - Update SMTP settings in .env
   - Implement email service

3. **2FA** - Add two-factor authentication
   - Use libraries like `speakeasy` for TOTP

4. **OAuth** - Add Google/LinkedIn login
   - Use `passport.js` strategies

5. **Admin Panel** - Create user management dashboard

---

## ✅ Done!

Your complete authentication system is ready! 🎉

- Sign up at: http://localhost:3000/signup
- Log in at: http://localhost:3000/login
- API docs at: http://localhost:5000/api/docs

For detailed documentation, see `AUTH_SYSTEM_DOCUMENTATION.md`
