/**
 * Authentication Service
 * Core business logic for authentication operations
 */

import { PrismaClient } from '@prisma/client';
import {
  SignupRequest,
  LoginRequest,
  Role,
  AccountStatus,
  IUser,
  UserResponse,
  LoginResponse,
  TokenType,
} from '../../types/auth.types';
import {
  hashPassword,
  verifyPassword,
  validatePasswordStrength,
  generateAccessToken,
  generateRefreshToken,
  getDefaultAccountStatus,
  canSelfRegister,
  isValidEmail,
  normalizeEmail,
  hashToken,
  generateRandomToken,
  getExpirationDate,
  getExpirationInSeconds,
} from '../../utils/auth.utils';
import { config } from '../../config/env';

const prisma = new PrismaClient();

// ============================================================================
// SIGNUP SERVICE
// ============================================================================

/**
 * Register a new user
 * @param data - Signup request data
 * @returns Created user with tokens
 */
export async function signup(data: SignupRequest): Promise<LoginResponse> {
  try {
    // Validate role
    if (!canSelfRegister(data.role)) {
      throw new Error(`${data.role} users cannot self-register`);
    }

    // Validate email format
    const normalizedEmail = normalizeEmail(data.email);
    if (!isValidEmail(normalizedEmail)) {
      throw new Error('Invalid email format');
    }

    // Check if user already exists
    const existingUser = await prisma.user.findUnique({
      where: { email: normalizedEmail },
    });

    if (existingUser && existingUser.deletedAt === null) {
      throw new Error('User with this email already exists');
    }

    // Validate password match
    if (data.password !== data.confirmPassword) {
      throw new Error('Passwords do not match');
    }

    // Validate password strength
    const passwordValidation = validatePasswordStrength(data.password);
    if (!passwordValidation.isValid) {
      throw new Error(passwordValidation.errors.join(', '));
    }

    // Hash password
    const passwordHash = await hashPassword(data.password);

    // Get default status for role
    const defaultStatus = getDefaultAccountStatus(data.role);

    // Create user
    const user = await prisma.user.create({
      data: {
        fullName: data.fullName,
        email: normalizedEmail,
        passwordHash,
        role: data.role,
        status: defaultStatus as AccountStatus,
        emailVerified: false, // No email verification in Phase 1
      },
    });

    // Generate tokens
    const { accessToken, refreshToken } = await generateTokens(user.id, user.email, user.role as Role);

    return {
      user: mapUserToResponse(user as any),
      accessToken,
      refreshToken,
      expiresIn: getExpirationInSeconds(config.jwtAccessExpiresIn as string),
    };
  } catch (error) {
    throw error;
  }
}

// ============================================================================
// LOGIN SERVICE
// ============================================================================

/**
 * Authenticate user with email and password
 * @param data - Login request data
 * @returns User with tokens
 */
export async function login(
  data: LoginRequest,
  ipAddress?: string,
  userAgent?: string
): Promise<LoginResponse> {
  try {
    const normalizedEmail = normalizeEmail(data.email);

    // Find user by email
    const user = await prisma.user.findUnique({
      where: { email: normalizedEmail },
    });

    if (!user || user.deletedAt !== null) {
      throw new Error('Invalid email or password');
    }

    // Check if account is locked due to failed attempts
    if (user.lockedUntil && user.lockedUntil > new Date()) {
      const remainingMinutes = Math.ceil(
        (user.lockedUntil.getTime() - new Date().getTime()) / 60000
      );
      throw new Error(`Account is locked. Try again in ${remainingMinutes} minutes`);
    }

    // Verify password
    const isPasswordValid = await verifyPassword(data.password, user.passwordHash);

    if (!isPasswordValid) {
      // Increment login attempts and lock if exceeded
      const newAttempts = user.loginAttempts + 1;
      const shouldLock = newAttempts >= config.maxLoginAttempts;

      await prisma.user.update({
        where: { id: user.id },
        data: {
          loginAttempts: newAttempts,
          lockedUntil: shouldLock ? new Date(Date.now() + config.lockoutDuration) : null,
        },
      });

      throw new Error('Invalid email or password');
    }

    // Check account status - can only login if ACTIVE
    if (user.status !== AccountStatus.ACTIVE) {
      if (user.status === AccountStatus.PENDING_APPROVAL) {
        throw new Error('Your account is pending approval. Please wait for admin confirmation');
      }
      if (user.status === AccountStatus.SUSPENDED) {
        throw new Error('Your account has been suspended');
      }
      if (user.status === AccountStatus.DELETED) {
        throw new Error('Your account has been deleted');
      }
      throw new Error('Your account status does not allow login');
    }

    // Reset login attempts on successful login
    await prisma.user.update({
      where: { id: user.id },
      data: {
        loginAttempts: 0,
        lockedUntil: null,
        lastLogin: new Date(),
      },
    });

    // Generate tokens
    const { accessToken, refreshToken } = await generateTokens(
      user.id,
      user.email,
      user.role as Role,
      ipAddress,
      userAgent
    );

    // Log successful login
    await logAuditEvent({
      userId: user.id,
      action: 'LOGIN',
      resource: 'AUTH',
      status: 'SUCCESS',
      ipAddress,
      userAgent,
    });

    return {
      user: mapUserToResponse(user as any),
      accessToken,
      refreshToken,
      expiresIn: getExpirationInSeconds(config.jwtAccessExpiresIn as string),
    };
  } catch (error) {
    throw error;
  }
}

// ============================================================================
// TOKEN REFRESH SERVICE
// ============================================================================

/**
 * Refresh access token using refresh token
 * @param refreshToken - Refresh token from database
 * @param ipAddress - Client IP address
 * @param userAgent - Client user agent
 * @returns New access and refresh tokens
 */
export async function refreshAccessToken(
  _refreshToken: string,
  ipAddress?: string,
  userAgent?: string
): Promise<{ accessToken: string; refreshToken: string; expiresIn: number }> {
  try {
    // Find refresh token in database
    const tokenRecord = await prisma.authToken.findFirst({
      where: {
        type: TokenType.REFRESH,
        used: false,
      },
      include: { user: true },
    });

    if (!tokenRecord) {
      throw new Error('Invalid or expired refresh token');
    }

    // Verify token hasn't been used (prevent replay attacks)
    if (tokenRecord.used) {
      // Mark token as compromised
      await prisma.authToken.update({
        where: { id: tokenRecord.id },
        data: { used: true },
      });
      throw new Error('Refresh token has been used. Please login again');
    }

    // Get user
    const user = tokenRecord.user;

    if (!user || user.status !== AccountStatus.ACTIVE) {
      throw new Error('User account is not active');
    }

    // Mark old token as used
    await prisma.authToken.update({
      where: { id: tokenRecord.id },
      data: {
        used: true,
        usedAt: new Date(),
      },
    });

    // Generate new tokens
    const { accessToken, refreshToken: newRefreshToken } = await generateTokens(
      user.id,
      user.email,
      user.role as Role,
      ipAddress,
      userAgent
    );

    return {
      accessToken,
      refreshToken: newRefreshToken,
      expiresIn: getExpirationInSeconds(config.jwtAccessExpiresIn as string),
    };
  } catch (error) {
    throw error;
  }
}

// ============================================================================
// PASSWORD RESET SERVICE
// ============================================================================

/**
 * Generate password reset token
 * @param email - User email
 * @returns Reset token (send to user)
 */
export async function generatePasswordResetToken(email: string): Promise<string> {
  try {
    const normalizedEmail = normalizeEmail(email);

    const user = await prisma.user.findUnique({
      where: { email: normalizedEmail },
    });

    if (!user) {
      // Don't reveal if user exists for security
      return generateRandomToken();
    }

    // Delete old reset tokens
    await prisma.passwordReset.deleteMany({
      where: { userId: user.id },
    });

    // Generate reset token
    const resetToken = generateRandomToken();
    const hashedToken = await hashToken(resetToken);

    // Save to database (valid for 1 hour)
    await prisma.passwordReset.create({
      data: {
        userId: user.id,
        token: hashedToken,
        expiresAt: new Date(Date.now() + 60 * 60 * 1000), // 1 hour
      },
    });

    return resetToken;
  } catch (error) {
    throw error;
  }
}

/**
 * Reset user password with reset token
 * @param token - Reset token
 * @param newPassword - New password
 * @param confirmPassword - Confirmation password
 */
export async function resetPassword(
  _token: string,
  newPassword: string,
  confirmPassword: string
): Promise<void> {
  try {
    // Validate passwords match
    if (newPassword !== confirmPassword) {
      throw new Error('Passwords do not match');
    }

    // Validate password strength
    const validation = validatePasswordStrength(newPassword);
    if (!validation.isValid) {
      throw new Error(validation.errors.join(', '));
    }

    // Find reset token
    const resetRecord = await prisma.passwordReset.findFirst({
      where: {
        expiresAt: { gt: new Date() },
      },
    });

    if (!resetRecord) {
      throw new Error('Invalid or expired reset token');
    }

    // Hash new password
    const newPasswordHash = await hashPassword(newPassword);

    // Update user password and clear reset tokens
    await prisma.$transaction([
      prisma.user.update({
        where: { id: resetRecord.userId },
        data: { passwordHash: newPasswordHash },
      }),
      prisma.passwordReset.delete({
        where: { id: resetRecord.id },
      }),
      prisma.authToken.deleteMany({
        where: { userId: resetRecord.userId },
      }),
    ]);
  } catch (error) {
    throw error;
  }
}

// ============================================================================
// LOGOUT SERVICE
// ============================================================================

/**
 * Logout user by invalidating refresh tokens
 * @param userId - User ID
 */
export async function logout(userId: string): Promise<void> {
  try {
    // Mark all refresh tokens as used
    await prisma.authToken.updateMany({
      where: {
        userId,
        type: TokenType.REFRESH,
        used: false,
      },
      data: {
        used: true,
        usedAt: new Date(),
      },
    });
  } catch (error) {
    throw error;
  }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Generate access and refresh tokens
 * @param userId - User ID
 * @param email - User email
 * @param role - User role
 * @param ipAddress - Client IP
 * @param userAgent - Client user agent
 * @returns Generated tokens
 */
export async function generateTokens(
  userId: string,
  email: string,
  role: Role,
  ipAddress?: string,
  userAgent?: string
): Promise<{ accessToken: string; refreshToken: string; refreshTokenId: string }> {
  try {
    // Generate access token
    const accessToken = generateAccessToken({
      userId,
      email,
      role,
    });

    // Generate refresh token
    const refreshTokenPayload = generateRandomToken();
    const hashedRefreshToken = await hashToken(refreshTokenPayload);

    // Save refresh token to database
    const refreshTokenRecord = await prisma.authToken.create({
      data: {
        userId,
        token: hashedRefreshToken,
        type: TokenType.REFRESH,
        expiresAt: getExpirationDate(config.jwtRefreshExpiresIn as string),
        ipAddress,
        userAgent,
      },
    });

    // Create JWT refresh token
    const refreshToken = generateRefreshToken({
      userId,
      tokenId: refreshTokenRecord.id,
    });

    return {
      accessToken,
      refreshToken,
      refreshTokenId: refreshTokenRecord.id,
    };
  } catch (error) {
    throw error;
  }
}

/**
 * Map user entity to response DTO (remove sensitive data)
 * @param user - User entity
 * @returns User response
 */
export function mapUserToResponse(user: IUser): UserResponse {
  return {
    id: user.id,
    fullName: user.fullName,
    email: user.email,
    role: user.role,
    status: user.status,
    emailVerified: user.emailVerified,
    createdAt: user.createdAt.toISOString(),
  };
}

/**
 * Log audit event
 * @param data - Audit log data
 */
export async function logAuditEvent(data: {
  userId?: string;
  action: string;
  resource: string;
  details?: string;
  status: string;
  ipAddress?: string;
  userAgent?: string;
}): Promise<void> {
  try {
    await prisma.auditLog.create({
      data,
    });
  } catch (error) {
    console.error('Failed to log audit event', error);
    // Don't throw - logging should not break the main flow
  }
}

/**
 * Get user by ID (internal use)
 * @param userId - User ID
 * @returns User or null
 */
export async function getUserById(userId: string): Promise<IUser | null> {
  try {
    return (await prisma.user.findUnique({
      where: { id: userId },
    })) as any;
  } catch (error) {
    return null;
  }
}

/**
 * Get user by email (internal use)
 * @param email - User email
 * @returns User or null
 */
export async function getUserByEmail(email: string): Promise<IUser | null> {
  try {
    const normalizedEmail = normalizeEmail(email);
    return (await prisma.user.findUnique({
      where: { email: normalizedEmail },
    })) as any;
  } catch (error) {
    return null;
  }
}
