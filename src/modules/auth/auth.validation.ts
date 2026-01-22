/**
 * Authentication Request Validation Rules
 * Using express-validator for comprehensive input validation
 */

import { body } from 'express-validator';

// ============================================================================
// SIGNUP VALIDATION
// ============================================================================

export const signupValidation = [
  body('fullName')
    .trim()
    .notEmpty()
    .withMessage('Full name is required')
    .isLength({ min: 2, max: 100 })
    .withMessage('Full name must be between 2 and 100 characters'),

  body('email')
    .trim()
    .toLowerCase()
    .isEmail()
    .withMessage('Valid email address is required')
    .isLength({ max: 255 })
    .withMessage('Email must not exceed 255 characters'),

  body('password')
    .isLength({ min: 8 })
    .withMessage('Password must be at least 8 characters')
    .matches(/[A-Z]/)
    .withMessage('Password must contain at least one uppercase letter')
    .matches(/[a-z]/)
    .withMessage('Password must contain at least one lowercase letter')
    .matches(/[0-9]/)
    .withMessage('Password must contain at least one number')
    .matches(/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/)
    .withMessage('Password must contain at least one special character'),

  body('confirmPassword')
    .custom((value, { req }) => {
      if (value !== req.body.password) {
        throw new Error('Passwords do not match');
      }
      return true;
    }),

  body('role')
    .isIn(['STUDENT', 'CORPORATE', 'UNIVERSITY', 'MENTOR', 'ADMIN'])
    .withMessage('Invalid role. Allowed: STUDENT, CORPORATE, UNIVERSITY, MENTOR, ADMIN'),
];

// ============================================================================
// LOGIN VALIDATION
// ============================================================================

export const loginValidation = [
  body('email')
    .trim()
    .toLowerCase()
    .isEmail()
    .withMessage('Valid email address is required'),

  body('password')
    .notEmpty()
    .withMessage('Password is required'),
];

// ============================================================================
// PASSWORD RESET VALIDATION
// ============================================================================

export const forgotPasswordValidation = [
  body('email')
    .trim()
    .toLowerCase()
    .isEmail()
    .withMessage('Valid email address is required'),
];

export const resetPasswordValidation = [
  body('token')
    .trim()
    .notEmpty()
    .withMessage('Reset token is required')
    .isLength({ min: 32 })
    .withMessage('Invalid reset token'),

  body('newPassword')
    .isLength({ min: 8 })
    .withMessage('Password must be at least 8 characters')
    .matches(/[A-Z]/)
    .withMessage('Password must contain at least one uppercase letter')
    .matches(/[a-z]/)
    .withMessage('Password must contain at least one lowercase letter')
    .matches(/[0-9]/)
    .withMessage('Password must contain at least one number')
    .matches(/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/)
    .withMessage('Password must contain at least one special character'),

  body('confirmPassword')
    .custom((value, { req }) => {
      if (value !== req.body.newPassword) {
        throw new Error('Passwords do not match');
      }
      return true;
    }),
];

// ============================================================================
// REFRESH TOKEN VALIDATION
// ============================================================================

export const refreshTokenValidation = [
  body('refreshToken')
    .trim()
    .notEmpty()
    .withMessage('Refresh token is required'),
];
