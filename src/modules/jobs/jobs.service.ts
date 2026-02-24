/**
 * Jobs service
 * List and get jobs for students (browse, recommendations placeholder)
 */

import prisma from '../../config/database';

export async function listJobs(opts?: { status?: string; limit?: number; offset?: number }) {
  const status = opts?.status ?? 'open';
  const limit = Math.min(opts?.limit ?? 50, 100);
  const offset = opts?.offset ?? 0;

  const [jobs, total] = await Promise.all([
    prisma.job.findMany({
      where: { status },
      include: { company: true },
      orderBy: { postedAt: 'desc' },
      take: limit,
      skip: offset,
    }),
    prisma.job.count({ where: { status } }),
  ]);

  return { jobs, total };
}

export async function getJobById(jobId: string) {
  return prisma.job.findUnique({
    where: { id: jobId },
    include: { company: true },
  });
}
