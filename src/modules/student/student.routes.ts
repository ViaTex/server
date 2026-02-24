/**
 * Student routes
 * Registration & Onboarding → Profile; Job search → Applications; Offer accept/decline
 */

import { Router } from 'express';
import { verifyToken } from '../../middlewares/auth.middleware';
import { requireStudent } from '../../middlewares/auth.middleware';
import { studentController } from './student.controller';

const router = Router();

// All student routes require auth + STUDENT role + loaded student
const studentAuth = [verifyToken, requireStudent()];

/**
 * @swagger
 * /api/students/me:
 *   get:
 *     summary: Get current student profile (dashboard)
 *     tags: [Students]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Student profile with applications
 *       403:
 *         description: Not a student or student profile not found
 */
router.get('/me', studentAuth, studentController.getMe);

/**
 * @swagger
 * /api/students/me:
 *   patch:
 *     summary: Update student profile (onboarding, resume, skills, job prefs, privacy)
 *     tags: [Students]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               fullName: { type: string }
 *               phone: { type: string }
 *               collegeName: { type: string }
 *               degree: { type: string }
 *               branch: { type: string }
 *               graduationYear: { type: number }
 *               currentCity: { type: string }
 *               aboutMe: { type: string }
 *               linkedinUrl: { type: string }
 *               githubUrl: { type: string }
 *               portfolioUrl: { type: string }
 *               resumeFileUrl: { type: string }
 *               resumeAtsScore: { type: number }
 *               skillsJson: { type: array, items: { type: object } }
 *               projectsJson: { type: array, items: { type: object } }
 *               jobPreferencesJson: { type: object }
 *               showPhone: { type: boolean }
 *               showEmail: { type: boolean }
 *               showResume: { type: boolean }
 *               showDes: { type: boolean }
 *     responses:
 *       200:
 *         description: Profile updated
 *       403:
 *         description: Student context required
 */
router.patch('/me', studentAuth, studentController.updateMe);

/**
 * @swagger
 * /api/students/me/applications:
 *   get:
 *     summary: List my applications
 *     tags: [Students]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: List of applications with job and company
 */
router.get('/me/applications', studentAuth, studentController.getMyApplications);

/**
 * @swagger
 * /api/students/me/applications:
 *   post:
 *     summary: Apply to a job
 *     tags: [Students]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [jobId]
 *             properties:
 *               jobId: { type: string }
 *     responses:
 *       201:
 *         description: Application submitted
 *       409:
 *         description: Already applied
 */
router.post('/me/applications', studentAuth, studentController.apply);

/**
 * @swagger
 * /api/students/me/applications/{id}:
 *   patch:
 *     summary: Accept or decline offer (only when status is offered)
 *     tags: [Students]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema: { type: string }
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [applicationStatus]
 *             properties:
 *               applicationStatus: { type: string, enum: [accepted, declined] }
 *     responses:
 *       200:
 *         description: Application updated
 */
router.patch('/me/applications/:id', studentAuth, studentController.updateApplication);

/**
 * @swagger
 * /api/students/me/skill-verification-request:
 *   post:
 *     summary: "Request skill verification (MVP stub – full flow: mentor assign, viva, DES update later)"
 *     tags: [Students]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               skillName: { type: string }
 *               projectTitle: { type: string }
 *     responses:
 *       202:
 *         description: Request received (stub)
 */
import { Request, Response } from 'express';

router.post('/me/skill-verification-request', studentAuth, (_req: Request, res: Response) => {
  res.status(202).json({
    success: true,
    message: 'Skill verification request received. Mentor assignment and viva scheduling will be available in a future release.',
  });
});

export default router;
