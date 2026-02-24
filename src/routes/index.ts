import { Router } from 'express';
import authRoutes from '../modules/auth/auth.routes';
import userRoutes from '../modules/user/user.routes';
import studentRoutes from '../modules/student/student.routes';
import jobsRoutes from '../modules/jobs/jobs.routes';

const router = Router();

router.use('/auth', authRoutes);
router.use('/users', userRoutes);
router.use('/students', studentRoutes);
router.use('/jobs', jobsRoutes);

export default router;
