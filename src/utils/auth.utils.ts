/**
 * Authentication Utilities
 * Password hashing, JWT generation, token validation, etc.
 */

import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { config } from '../config/env';
import { AccessTokenPayload, RefreshTokenPayload, PasswordValidation, Role } from '../types/auth.types';

// ============================================================================
// PASSWORD UTILITIES
// ============================================================================

/**
 * Hash a plain text password using bcrypt
 * @param password - Plain text password
 * @returns Hashed password
 */
export async function hashPassword(password: string): Promise<string> {
  try {
    const salt = await bcrypt.genSalt(config.bcryptRounds);
    return await bcrypt.hash(password, salt);
  } catch (error) {
    throw new Error('Failed to hash password');
  }
}

/**
 * Compare plain text password with hashed password
 * @param password - Plain text password
 * @param passwordHash - Hashed password from database
 * @returns True if passwords match
 */
export async function verifyPassword(password: string, passwordHash: string): Promise<boolean> {
  try {
    return await bcrypt.compare(password, passwordHash);
  } catch (error) {
    return false;
  }
}

/**
 * Validate password strength
 * Requirements:
 * - Minimum 8 characters
 * - At least one uppercase letter
 * - At least one lowercase letter
 * - At least one number
 * - At least one special character
 * @param password - Password to validate
 * @returns Validation result with errors
 */
export function validatePasswordStrength(password: string): PasswordValidation {
  const errors: string[] = [];

  if (!password) {
    errors.push('Password is required');
    return { isValid: false, errors };
  }

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// ============================================================================
// JWT TOKEN UTILITIES
// ============================================================================

/**
 * Generate JWT access token
 * @param payload - Token payload
 * @param expiresIn - Expiration time (default from config)
 * @returns Signed JWT token
 */
export function generateAccessToken(
  payload: Omit<AccessTokenPayload, 'iat' | 'exp'>,
  expiresIn: string = config.jwtAccessExpiresIn as string
): string {
  // @ts-ignore - JWT types issue
  return jwt.sign(payload, config.jwtSecret as string, {
    expiresIn,
    algorithm: 'HS256',
  });
}

/**
 * Generate JWT refresh token
 * @param payload - Token payload
 * @param expiresIn - Expiration time (default from config)
 * @returns Signed JWT token
 */
export function generateRefreshToken(
  payload: Omit<RefreshTokenPayload, 'iat' | 'exp'>,
  expiresIn: string = config.jwtRefreshExpiresIn as string
): string {
  // @ts-ignore - JWT types issue
  return jwt.sign(payload, config.jwtRefreshSecret as string, {
    expiresIn,
    algorithm: 'HS256',
  });
}

/**
 * Verify and decode JWT access token
 * @param token - JWT token to verify
 * @returns Decoded token payload
 * @throws Error if token is invalid or expired
 */
export function verifyAccessToken(token: string): AccessTokenPayload {
  try {
    const decoded = jwt.verify(token, config.jwtSecret, {
      algorithms: ['HS256'],
    }) as AccessTokenPayload;
    return decoded;
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      throw new Error('Access token has expired');
    }
    if (error instanceof jwt.JsonWebTokenError) {
      throw new Error('Invalid access token');
    }
    throw error;
  }
}

/**
 * Verify and decode JWT refresh token
 * @param token - JWT token to verify
 * @returns Decoded token payload
 * @throws Error if token is invalid or expired
 */
export function verifyRefreshToken(token: string): RefreshTokenPayload {
  try {
    const decoded = jwt.verify(token, config.jwtRefreshSecret, {
      algorithms: ['HS256'],
    }) as RefreshTokenPayload;
    return decoded;
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      throw new Error('Refresh token has expired');
    }
    if (error instanceof jwt.JsonWebTokenError) {
      throw new Error('Invalid refresh token');
    }
    throw error;
  }
}

/**
 * Get expiration timestamp from token expiry time
 * @param expiresIn - Expiration time string (e.g., "15m", "7d")
 * @returns Expiration timestamp as Date
 */
export function getExpirationDate(expiresIn: string): Date {
  const now = new Date();
  const match = expiresIn.match(/^(\d+)([smhd])$/);

  if (!match) {
    throw new Error('Invalid expiration format');
  }

  const [, value, unit] = match;
  const num = parseInt(value);

  switch (unit) {
    case 's':
      now.setSeconds(now.getSeconds() + num);
      break;
    case 'm':
      now.setMinutes(now.getMinutes() + num);
      break;
    case 'h':
      now.setHours(now.getHours() + num);
      break;
    case 'd':
      now.setDate(now.getDate() + num);
      break;
  }

  return now;
}

// ============================================================================
// EMAIL UTILITIES
// ============================================================================

/**
 * Validate email format
 * @param email - Email to validate
 * @returns True if valid email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Normalize email (lowercase)
 * @param email - Email to normalize
 * @returns Normalized email
 */
export function normalizeEmail(email: string): string {
  return email.toLowerCase().trim();
}

// ============================================================================
// ROLE & STATUS UTILITIES
// ============================================================================

/**
 * Get default account status based on role
 * - STUDENT: ACTIVE
 * - CORPORATE: ACTIVE
 * - UNIVERSITY: ACTIVE
 * - MENTOR: PENDING_APPROVAL
 * - ADMIN: ACTIVE (but only created by admin)
 * @param role - User role
 * @returns Default account status
 */
export function getDefaultAccountStatus(role: Role): 'ACTIVE' | 'PENDING_APPROVAL' {
  if (role === Role.MENTOR) {
    return 'PENDING_APPROVAL';
  }
  return 'ACTIVE';
}

/**
 * Check if a role can self-register
 * @param role - User role
 * @returns True if role can self-register
 */
export function canSelfRegister(role: Role): boolean {
  return role !== Role.ADMIN;
}

/**
 * Get role hierarchy for authorization checks
 * @param role - User role
 * @returns Numeric hierarchy level (higher = more permissions)
 */
export function getRoleHierarchy(role: Role): number {
  const hierarchy: Record<Role, number> = {
    [Role.STUDENT]: 1,
    [Role.CORPORATE]: 2,
    [Role.UNIVERSITY]: 2,
    [Role.MENTOR]: 3,
    [Role.ADMIN]: 100,
  };
  return hierarchy[role];
}

// ============================================================================
// TOKEN HASHING FOR STORAGE
// ============================================================================

/**
 * Hash a token for secure storage in database
 * @param token - Token to hash
 * @returns Hashed token
 */
export async function hashToken(token: string): Promise<string> {
  try {
    const salt = await bcrypt.genSalt(10);
    return await bcrypt.hash(token, salt);
  } catch (error) {
    throw new Error('Failed to hash token');
  }
}

/**
 * Verify token against hashed version in database
 * @param token - Plain token
 * @param hashedToken - Hashed token from database
 * @returns True if tokens match
 */
export async function verifyToken(token: string, hashedToken: string): Promise<boolean> {
  try {
    return await bcrypt.compare(token, hashedToken);
  } catch (error) {
    return false;
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Generate a random secure token
 * @param length - Token length in bytes
 * @returns Random token as hex string
 */
export function generateRandomToken(length: number = 32): string {
  return require('crypto').randomBytes(length).toString('hex');
}

/**
 * Extract token from Authorization header
 * @param authHeader - Authorization header value
 * @returns Token or null if not found
 */
export function extractTokenFromHeader(authHeader: string | undefined): string | null {
  if (!authHeader) return null;

  const parts = authHeader.split(' ');
  if (parts.length !== 2 || parts[0] !== 'Bearer') {
    return null;
  }

  return parts[1];
}

/**
 * Get token expiration time in seconds
 * @param expiresIn - Expiration time string (e.g., "15m", "7d")
 * @returns Expiration time in seconds
 */
export function getExpirationInSeconds(expiresIn: string): number {
  const match = expiresIn.match(/^(\d+)([smhd])$/);

  if (!match) {
    throw new Error('Invalid expiration format');
  }

  const [, value, unit] = match;
  const num = parseInt(value);

  switch (unit) {
    case 's':
      return num;
    case 'm':
      return num * 60;
    case 'h':
      return num * 60 * 60;
    case 'd':
      return num * 24 * 60 * 60;
    default:
      throw new Error('Invalid time unit');
  }
}
