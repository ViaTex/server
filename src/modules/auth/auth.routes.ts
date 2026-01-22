/**
 * Authentication Routes
 * All auth-related endpoints
 */

import { Router } from 'express';
import {
  signupController,
  loginController,
  logoutController,
  refreshTokenController,
  getMeController,
  forgotPasswordController,
  resetPasswordController,
} from './auth.controller';
import {
  signupValidation,
  loginValidation,
  forgotPasswordValidation,
  resetPasswordValidation,
  refreshTokenValidation,
} from './auth.validation';
import { validationResult } from 'express-validator';
import { verifyToken } from '../../middlewares/auth.middleware';

const router = Router();

// Validation middleware wrapper
const validate = (req: any, res: any, next: any) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(422).json({
      success: false,
      message: 'Validation failed',
      errors: errors.array().map((e: any) => e.msg),
    });
  }
  next();
};

// ============================================================================
// PUBLIC ROUTES (No authentication required)
// ============================================================================

/**
 * @swagger
 * /api/auth/signup:
 *   post:
 *     summary: Register a new user
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - fullName
 *               - email
 *               - password
 *               - confirmPassword
 *               - role
 *             properties:
 *               fullName:
 *                 type: string
 *                 example: "John Doe"
 *               email:
 *                 type: string
 *                 format: email
 *                 example: "john@example.com"
 *               password:
 *                 type: string
 *                 format: password
 *                 minLength: 8
 *                 example: "SecurePass@123"
 *               confirmPassword:
 *                 type: string
 *                 format: password
 *                 example: "SecurePass@123"
 *               role:
 *                 type: string
 *                 enum: [STUDENT, CORPORATE, UNIVERSITY, MENTOR]
 *                 example: "STUDENT"
 *     responses:
 *       201:
 *         description: User registered successfully
 *       400:
 *         description: Validation error or user already exists
 *       422:
 *         description: Validation failed
 */
router.post('/signup', signupValidation, validate, signupController);

/**
 * @swagger
 * /api/auth/login:
 *   post:
 *     summary: Login user
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - email
 *               - password
 *             properties:
 *               email:
 *                 type: string
 *                 format: email
 *                 example: "john@example.com"
 *               password:
 *                 type: string
 *                 format: password
 *                 example: "SecurePass@123"
 *     responses:
 *       200:
 *         description: Login successful
 *       401:
 *         description: Invalid credentials
 *       422:
 *         description: Validation failed
 */
router.post('/login', loginValidation, validate, loginController);

/**
 * @swagger
 * /api/auth/refresh-token:
 *   post:
 *     summary: Refresh access token
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               refreshToken:
 *                 type: string
 *     responses:
 *       200:
 *         description: Token refreshed successfully
 *       401:
 *         description: Invalid or expired refresh token
 */
router.post('/refresh-token', refreshTokenValidation, validate, refreshTokenController);

/**
 * @swagger
 * /api/auth/forgot-password:
 *   post:
 *     summary: Request password reset token
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - email
 *             properties:
 *               email:
 *                 type: string
 *                 format: email
 *     responses:
 *       200:
 *         description: If email exists, reset token will be sent
 *       422:
 *         description: Validation failed
 */
router.post('/forgot-password', forgotPasswordValidation, validate, forgotPasswordController);

/**
 * @swagger
 * /api/auth/reset-password:
 *   post:
 *     summary: Reset password with reset token
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - token
 *               - newPassword
 *               - confirmPassword
 *             properties:
 *               token:
 *                 type: string
 *               newPassword:
 *                 type: string
 *                 format: password
 *               confirmPassword:
 *                 type: string
 *                 format: password
 *     responses:
 *       200:
 *         description: Password reset successfully
 *       400:
 *         description: Invalid or expired token
 *       422:
 *         description: Validation failed
 */
router.post('/reset-password', resetPasswordValidation, validate, resetPasswordController);

// ============================================================================
// PROTECTED ROUTES (Requires authentication)
// ============================================================================

/**
 * @swagger
 * /api/auth/me:
 *   get:
 *     summary: Get current authenticated user
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: User data retrieved successfully
 *       401:
 *         description: Not authenticated or token expired
 */
router.get('/me', verifyToken, getMeController);

/**
 * @swagger
 * /api/auth/logout:
 *   post:
 *     summary: Logout user
 *     tags: [Authentication]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Logout successful
 *       401:
 *         description: Not authenticated
 */
router.post('/logout', verifyToken, logoutController);

export default router;
