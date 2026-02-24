/**
 * Student controller
 * Profile (onboarding), applications, offer accept/decline
 */

import { Response, NextFunction } from 'express';
import { StudentAuthenticatedRequest } from '../../middlewares/auth.middleware';
import {
  getStudentByUserId,
  updateStudentProfile,
  getStudentApplications,
  applyToJob,
  updateApplicationStatus,
  type StudentProfileUpdate,
} from './student.service';
import { sendSuccess, sendError } from '../../utils/response';

export const studentController = {
  /** GET /api/students/me – full profile + applications (for dashboard) */
  async getMe(req: StudentAuthenticatedRequest, res: Response, _next: NextFunction): Promise<void> {
    try {
      if (!req.user?.id) {
        sendError(res, 'Not authenticated', 401);
        return;
      }
      const student = await getStudentByUserId(req.user.id);
      if (!student) {
        sendError(res, 'Student profile not found', 404);
        return;
      }
      sendSuccess(res, student, 'Student profile retrieved');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to get profile', 500);
    }
  },

  /** PATCH /api/students/me – update profile (onboarding, resume, skills, prefs, privacy) */
  async updateMe(req: StudentAuthenticatedRequest, res: Response, _next: NextFunction): Promise<void> {
    try {
      if (!req.studentId) {
        sendError(res, 'Student context required', 403);
        return;
      }
      const data = req.body as StudentProfileUpdate;
      const updated = await updateStudentProfile(req.studentId, data);
      sendSuccess(res, updated, 'Profile updated');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to update profile', 500);
    }
  },

  /** GET /api/students/me/applications */
  async getMyApplications(
    req: StudentAuthenticatedRequest,
    res: Response,
    _next: NextFunction
  ): Promise<void> {
    try {
      if (!req.studentId) {
        sendError(res, 'Student context required', 403);
        return;
      }
      const applications = await getStudentApplications(req.studentId);
      sendSuccess(res, applications, 'Applications retrieved');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to get applications', 500);
    }
  },

  /** POST /api/students/me/applications – apply to job */
  async apply(req: StudentAuthenticatedRequest, res: Response, _next: NextFunction): Promise<void> {
    try {
      if (!req.studentId) {
        sendError(res, 'Student context required', 403);
        return;
      }
      const { jobId } = req.body;
      if (!jobId) {
        sendError(res, 'jobId is required', 400);
        return;
      }
      const application = await applyToJob(req.studentId, jobId);
      sendSuccess(res, application, 'Application submitted', 201);
    } catch (error: any) {
      const code = error.message === 'Job not found' ? 404 : error.message === 'Already applied to this job' ? 409 : 400;
      sendError(res, error.message || 'Failed to apply', code);
    }
  },

  /** PATCH /api/students/me/applications/:id – accept or decline offer */
  async updateApplication(
    req: StudentAuthenticatedRequest,
    res: Response,
    _next: NextFunction
  ): Promise<void> {
    try {
      if (!req.studentId) {
        sendError(res, 'Student context required', 403);
        return;
      }
      const { id } = req.params;
      const { applicationStatus } = req.body;
      if (!id || !applicationStatus) {
        sendError(res, 'id and applicationStatus required', 400);
        return;
      }
      if (applicationStatus !== 'accepted' && applicationStatus !== 'declined') {
        sendError(res, 'Only accepted or declined allowed for offers', 400);
        return;
      }
      const application = await updateApplicationStatus(req.studentId, id, applicationStatus);
      sendSuccess(res, application, 'Application updated');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to update application', 400);
    }
  },
};
