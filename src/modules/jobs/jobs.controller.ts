/**
 * Jobs controller
 * Browse jobs, get job detail (for students)
 */

import { Request, Response, NextFunction } from 'express';
import { listJobs, getJobById } from './jobs.service';
import { sendSuccess, sendError } from '../../utils/response';

export const jobsController = {
  /** GET /api/jobs – list open jobs */
  async list(req: Request, res: Response, _next: NextFunction): Promise<void> {
    try {
      const status = (req.query.status as string) || 'open';
      const limit = req.query.limit ? parseInt(String(req.query.limit), 10) : 50;
      const offset = req.query.offset ? parseInt(String(req.query.offset), 10) : 0;
      const result = await listJobs({ status, limit, offset });
      sendSuccess(res, result, 'Jobs retrieved');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to list jobs', 500);
    }
  },

  /** GET /api/jobs/:id – get job detail */
  async getById(req: Request, res: Response, _next: NextFunction): Promise<void> {
    try {
      const job = await getJobById(req.params.id);
      if (!job) {
        sendError(res, 'Job not found', 404);
        return;
      }
      sendSuccess(res, job, 'Job retrieved');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to get job', 500);
    }
  },
};
