/**
 * Authentication Controller
 * Handles HTTP requests for authentication operations
 */

import { Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import {
  signup,
  login as authLogin,
  logout,
  refreshAccessToken,
  generatePasswordResetToken,
  resetPassword,
  getUserById,
} from './auth.service';
import { AuthenticatedRequest } from '../../middlewares/auth.middleware';
import { SignupRequest, LoginRequest } from '../../types/auth.types';

// ============================================================================
// RESPONSE HELPERS
// ============================================================================

interface SuccessResponse<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface ErrorResponse {
  success: boolean;
  message: string;
  errors?: string[];
}

const sendSuccess = <T>(
  res: Response,
  data: T,
  message: string = 'Success',
  statusCode: number = 200
): Response => {
  return res.status(statusCode).json({
    success: true,
    message,
    data,
  } as SuccessResponse<T>);
};

const sendError = (
  res: Response,
  message: string,
  statusCode: number = 400,
  errors?: string[]
): Response => {
  return res.status(statusCode).json({
    success: false,
    message,
    errors,
  } as ErrorResponse);
};

// ============================================================================
// REQUEST VALIDATION HELPER
// ============================================================================

const validateRequest = (req: any): string[] | null => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return errors.array().map((err: any) => err.msg);
  }
  return null;
};

// ============================================================================
// AUTH CONTROLLERS
// ============================================================================

/**
 * POST /auth/signup
 * Register a new user
 */
export const signupController = async (
  req: any,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    // Validate request
    const validationErrors = validateRequest(req);
    if (validationErrors) {
      sendError(res, 'Validation failed', 422, validationErrors);
      return;
    }

    const signupData: SignupRequest = req.body;

    const result = await signup(signupData);

    // Set secure refresh token cookie
    res.cookie('refreshToken', result.refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    });

    sendSuccess(
      res,
      {
        user: result.user,
        accessToken: result.accessToken,
        expiresIn: result.expiresIn,
      },
      'User registered successfully',
      201
    );
  } catch (error: any) {
    console.error('Signup error:', error);
    sendError(res, error.message || 'Registration failed', 400);
  }
};

/**
 * POST /auth/login
 * Authenticate user with email and password
 */
export const loginController = async (
  req: any,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    // Validate request
    const validationErrors = validateRequest(req);
    if (validationErrors) {
      sendError(res, 'Validation failed', 422, validationErrors);
      return;
    }

    const loginData: LoginRequest = req.body;
    const ipAddress = req.ip || req.socket?.remoteAddress;
    const userAgent = req.headers['user-agent'];

    const result = await authLogin(loginData, ipAddress, userAgent);

    // Set secure refresh token cookie
    res.cookie('refreshToken', result.refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    });

    sendSuccess(
      res,
      {
        user: result.user,
        accessToken: result.accessToken,
        expiresIn: result.expiresIn,
      },
      'Login successful'
    );
  } catch (error: any) {
    console.error('Login error:', error);
    const statusCode = error.message?.includes('locked') ? 429 : 401;
    sendError(res, error.message || 'Authentication failed', statusCode);
  }
};

/**
 * POST /auth/refresh-token
 * Refresh access token using refresh token
 */
export const refreshTokenController = async (
  req: any,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    // Get refresh token from cookie or body
    const refreshToken = req.cookies.refreshToken || req.body.refreshToken;

    if (!refreshToken) {
      sendError(res, 'Refresh token is required', 401);
      return;
    }

    const ipAddress = req.ip || req.socket?.remoteAddress;
    const userAgent = req.headers['user-agent'];

    const result = await refreshAccessToken(refreshToken, ipAddress, userAgent);

    // Update refresh token cookie
    res.cookie('refreshToken', result.refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    });

    sendSuccess(
      res,
      {
        accessToken: result.accessToken,
        expiresIn: result.expiresIn,
      },
      'Token refreshed successfully'
    );
  } catch (error: any) {
    console.error('Token refresh error:', error);
    sendError(res, error.message || 'Token refresh failed', 401);
  }
};

/**
 * POST /auth/logout
 * Logout user by invalidating refresh tokens
 */
export const logoutController = async (
  req: AuthenticatedRequest,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    if (!req.user) {
      sendError(res, 'Not authenticated', 401);
      return;
    }

    await logout(req.user.id);

    // Clear refresh token cookie
    res.clearCookie('refreshToken');

    sendSuccess(res, null, 'Logout successful');
  } catch (error: any) {
    console.error('Logout error:', error);
    sendError(res, error.message || 'Logout failed', 500);
  }
};

/**
 * GET /auth/me
 * Get current authenticated user
 */
export const getMeController = async (
  req: AuthenticatedRequest,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    if (!req.user) {
      sendError(res, 'Not authenticated', 401);
      return;
    }

    const user = await getUserById(req.user.id);

    if (!user) {
      sendError(res, 'User not found', 404);
      return;
    }

    sendSuccess(
      res,
      {
        id: user.id,
        fullName: user.fullName,
        email: user.email,
        role: user.role,
        status: user.status,
        emailVerified: user.emailVerified,
        createdAt: user.createdAt.toISOString(),
      },
      'User retrieved successfully'
    );
  } catch (error: any) {
    console.error('Get me error:', error);
    sendError(res, error.message || 'Failed to get user', 500);
  }
};

/**
 * POST /auth/forgot-password
 * Request password reset token
 */
export const forgotPasswordController = async (
  req: any,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    // Validate request
    const validationErrors = validateRequest(req);
    if (validationErrors) {
      sendError(res, 'Validation failed', 422, validationErrors);
      return;
    }

    const { email } = req.body;

    const resetToken = await generatePasswordResetToken(email);

    // TODO: Send reset token via email
    console.log(`Password reset token for ${email}: ${resetToken}`);

    sendSuccess(
      res,
      { resetToken }, // In production, don't send token in response - send via email
      'If the email exists, you will receive a password reset link'
    );
  } catch (error: any) {
    console.error('Forgot password error:', error);
    sendError(res, error.message || 'Failed to process request', 400);
  }
};

/**
 * POST /auth/reset-password
 * Reset password with reset token
 */
export const resetPasswordController = async (
  req: any,
  res: Response,
  _next: NextFunction
): Promise<void> => {
  try {
    // Validate request
    const validationErrors = validateRequest(req);
    if (validationErrors) {
      sendError(res, 'Validation failed', 422, validationErrors);
      return;
    }

    const { token, newPassword, confirmPassword } = req.body;

    await resetPassword(token, newPassword, confirmPassword);

    sendSuccess(res, null, 'Password reset successfully');
  } catch (error: any) {
    console.error('Reset password error:', error);
    const statusCode = error.message?.includes('Invalid') ? 400 : 500;
    sendError(res, error.message || 'Failed to reset password', statusCode);
  }
};
