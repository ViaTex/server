/**
 * Authentication & Authorization Middleware
 * Verifies JWT tokens and enforces role-based access control
 */

import { Request, Response, NextFunction } from 'express';
import { AccessTokenPayload, Role, AccountStatus } from '../types/auth.types';
import { verifyAccessToken, extractTokenFromHeader } from '../utils/auth.utils';
import { getUserById } from '../modules/auth/auth.service';

// ============================================================================
// EXTENDED REQUEST INTERFACE
// ============================================================================

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    role: Role;
    status: AccountStatus;
  };
  token?: string;
  ipAddress?: string;
}

// ============================================================================
// JWT VERIFICATION MIDDLEWARE
// ============================================================================

/**
 * Middleware to verify JWT token
 * Extracts token from Authorization header and verifies it
 */
export const verifyToken = (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
  try {
    const token = extractTokenFromHeader(req.headers.authorization);

    if (!token) {
      res.status(401).json({
        success: false,
        message: 'No authentication token provided',
      });
      return;
    }

    const decoded = verifyAccessToken(token) as AccessTokenPayload;

    req.user = {
      id: decoded.userId,
      email: decoded.email,
      role: decoded.role,
      status: AccountStatus.ACTIVE, // Will be validated in role middleware if needed
    };

    req.token = token;
    req.ipAddress = req.ip || req.socket.remoteAddress || undefined;

    next();
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Token verification failed';
    res.status(401).json({
      success: false,
      message,
    });
  }
};

// ============================================================================
// ROLE-BASED ACCESS CONTROL MIDDLEWARE
// ============================================================================

/**
 * Create middleware that checks if user has required role
 * @param requiredRoles - Array of roles that are allowed
 * @returns Express middleware function
 */
export const requireRole = (...requiredRoles: Role[]) => {
  return async (req: AuthenticatedRequest, res: Response, next: NextFunction): Promise<void> => {
    try {
      if (!req.user) {
        res.status(401).json({
          success: false,
          message: 'Authentication required',
        });
        return;
      }

      if (!requiredRoles.includes(req.user.role)) {
        res.status(403).json({
          success: false,
          message: `Access denied. Required roles: ${requiredRoles.join(', ')}`,
        });
        return;
      }

      // Verify user still exists and is active
      const user = await getUserById(req.user.id);
      if (!user || user.status !== AccountStatus.ACTIVE) {
        res.status(401).json({
          success: false,
          message: 'User account is not active',
        });
        return;
      }

      next();
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Authorization check failed',
      });
    }
  };
};

// ============================================================================
// OPTIONAL AUTHENTICATION MIDDLEWARE
// ============================================================================

/**
 * Optional authentication - doesn't fail if no token, just sets user if valid token
 */
export const optionalAuth = (req: AuthenticatedRequest, _res: Response, next: NextFunction): void => {
  try {
    const token = extractTokenFromHeader(req.headers.authorization);

    if (token) {
      const decoded = verifyAccessToken(token) as AccessTokenPayload;

      req.user = {
        id: decoded.userId,
        email: decoded.email,
        role: decoded.role,
        status: AccountStatus.ACTIVE,
      };

      req.token = token;
    }
  } catch (error) {
    // Silently continue if token is invalid
    console.debug('Optional auth token validation failed', error);
  }

  req.ipAddress = req.ip || req.socket.remoteAddress || undefined;
  next();
};

// ============================================================================
// ADMIN-ONLY MIDDLEWARE
// ============================================================================

/**
 * Middleware that requires ADMIN role
 */
export const requireAdmin = requireRole(Role.ADMIN);

/**
 * Alias for verifyToken for backward compatibility
 */
export const authMiddleware = verifyToken;

// ============================================================================
// ACTIVE ACCOUNT MIDDLEWARE
// ============================================================================

/**
 * Verify that user account is active
 */
export const requireActiveAccount = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        message: 'Authentication required',
      });
      return;
    }

    const user = await getUserById(req.user.id);

    if (!user) {
      res.status(401).json({
        success: false,
        message: 'User not found',
      });
      return;
    }

    if (user.status !== AccountStatus.ACTIVE) {
      const statusMessage = {
        [AccountStatus.PENDING_EMAIL_VERIFICATION]: 'Please verify your email',
        [AccountStatus.PENDING_APPROVAL]: 'Your account is pending approval',
        [AccountStatus.SUSPENDED]: 'Your account has been suspended',
        [AccountStatus.DELETED]: 'Your account has been deleted',
      };

      res.status(403).json({
        success: false,
        message: statusMessage[user.status] || 'Your account is not active',
      });
      return;
    }

    // Update user in request with current status
    req.user.status = user.status;
    next();
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Account verification failed',
    });
  }
};
