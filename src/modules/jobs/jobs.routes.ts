/**
 * Jobs routes
 * Public (or optional auth) for browsing jobs
 */

import { Router } from 'express';
import { jobsController } from './jobs.controller';

const router = Router();

/**
 * @swagger
 * /api/jobs:
 *   get:
 *     summary: List jobs (open by default)
 *     tags: [Jobs]
 *     parameters:
 *       - in: query
 *         name: status
 *         schema: { type: string, default: open }
 *       - in: query
 *         name: limit
 *         schema: { type: integer, default: 50 }
 *       - in: query
 *         name: offset
 *         schema: { type: integer, default: 0 }
 *     responses:
 *       200:
 *         description: { jobs, total }
 */
router.get('/', jobsController.list);

/**
 * @swagger
 * /api/jobs/{id}:
 *   get:
 *     summary: Get job by id
 *     tags: [Jobs]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema: { type: string }
 *     responses:
 *       200:
 *         description: Job with company
 *       404:
 *         description: Job not found
 */
router.get('/:id', jobsController.getById);

export default router;
