/**
 * Authentication and Authorization Types
 * Comprehensive type definitions for the auth system
 */

// ============================================================================
// ENUMS
// ============================================================================

export enum Role {
  STUDENT = 'STUDENT',
  CORPORATE = 'CORPORATE',
  UNIVERSITY = 'UNIVERSITY',
  MENTOR = 'MENTOR',
  ADMIN = 'ADMIN',
}

export enum AccountStatus {
  PENDING_EMAIL_VERIFICATION = 'PENDING_EMAIL_VERIFICATION',
  PENDING_APPROVAL = 'PENDING_APPROVAL',
  ACTIVE = 'ACTIVE',
  SUSPENDED = 'SUSPENDED',
  DELETED = 'DELETED',
}

export enum TokenType {
  ACCESS = 'ACCESS',
  REFRESH = 'REFRESH',
  RESET_PASSWORD = 'RESET_PASSWORD',
  EMAIL_VERIFY = 'EMAIL_VERIFY',
}

// ============================================================================
// REQUEST/RESPONSE DTOs
// ============================================================================

/**
 * User signup request body
 * Common to all roles
 */
export interface SignupRequest {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  role: Role;
}

/**
 * User login request body
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Password reset request
 */
export interface ForgotPasswordRequest {
  email: string;
}

/**
 * Password reset confirmation
 */
export interface ResetPasswordRequest {
  token: string;
  newPassword: string;
  confirmPassword: string;
}

/**
 * Token refresh request
 */
export interface RefreshTokenRequest {
  refreshToken: string;
}

/**
 * Authentication response with tokens
 */
export interface AuthResponse {
  success: boolean;
  message: string;
  data?: {
    user: UserResponse;
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

/**
 * User response data (safe to send to client)
 */
export interface UserResponse {
  id: string;
  fullName: string;
  email: string;
  role: Role;
  status: AccountStatus;
  emailVerified: boolean;
  createdAt: string;
}

/**
 * Token refresh response
 */
export interface TokenResponse {
  accessToken: string;
  refreshToken?: string;
  expiresIn: number;
}

// ============================================================================
// JWT PAYLOADS
// ============================================================================

/**
 * JWT Access Token Payload
 */
export interface AccessTokenPayload {
  userId: string;
  email: string;
  role: Role;
  iat?: number;
  exp?: number;
}

/**
 * JWT Refresh Token Payload
 */
export interface RefreshTokenPayload {
  userId: string;
  tokenId: string;
  iat?: number;
  exp?: number;
}

// ============================================================================
// DATABASE ENTITIES
// ============================================================================

/**
 * User entity as stored in database
 */
export interface IUser {
  id: string;
  fullName: string;
  email: string;
  passwordHash: string;
  role: Role;
  status: AccountStatus;
  emailVerified: boolean;
  lastLogin: Date | null;
  loginAttempts: number;
  lockedUntil: Date | null;
  createdAt: Date;
  updatedAt: Date;
  deletedAt: Date | null;
}

/**
 * Auth token entity
 */
export interface IAuthToken {
  id: string;
  userId: string;
  token: string;
  type: TokenType;
  expiresAt: Date;
  used: boolean;
  usedAt: Date | null;
  ipAddress?: string;
  userAgent?: string;
  createdAt: Date;
}

/**
 * Password reset token entity
 */
export interface IPasswordReset {
  id: string;
  userId: string;
  token: string;
  expiresAt: Date;
  usedAt: Date | null;
  createdAt: Date;
}

/**
 * Audit log entity
 */
export interface IAuditLog {
  id: string;
  userId?: string;
  action: string;
  resource: string;
  details?: string;
  ipAddress?: string;
  userAgent?: string;
  status: string;
  createdAt: Date;
}

// ============================================================================
// CONTEXT & MIDDLEWARE
// ============================================================================

/**
 * Authenticated request context
 * Extended Express Request with auth data
 */
export interface AuthenticatedRequest {
  user?: {
    id: string;
    email: string;
    role: Role;
    status: AccountStatus;
  };
  token?: string;
  ipAddress?: string;
  userAgent?: string;
}

/**
 * Role-based access requirements
 */
export interface RoleRequirement {
  requiredRoles: Role[];
  allowedStatuses?: AccountStatus[];
}

// ============================================================================
// HELPER TYPES
// ============================================================================

/**
 * Password validation result
 */
export interface PasswordValidation {
  isValid: boolean;
  errors: string[];
}

/**
 * Signup validation result for each role
 */
export interface SignupValidation {
  isValid: boolean;
  errors: string[];
  defaultStatus: AccountStatus;
}

/**
 * Login response with session details
 */
export interface LoginResponse {
  user: UserResponse;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

/**
 * User creation payload (internal use)
 */
export interface CreateUserPayload {
  fullName: string;
  email: string;
  passwordHash: string;
  role: Role;
  status: AccountStatus;
  emailVerified: boolean;
}
