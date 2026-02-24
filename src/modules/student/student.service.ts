/**
 * Student service
 * Profile (onboarding), applications, and DES-related updates
 */

import prisma from '../../config/database';
import { AccountStatus } from '@prisma/client';
import type { SkillItem, ProjectItem, JobPreferences } from './student.types';

// ============================================================================
// PROFILE
// ============================================================================

export async function getStudentByUserId(userId: string) {
  return prisma.student.findUnique({
    where: { userId },
    include: {
      applications: {
        include: { job: { include: { company: true } } },
        orderBy: { appliedAt: 'desc' },
      },
    },
  });
}

export async function getStudentById(studentId: string) {
  return prisma.student.findUnique({
    where: { id: studentId },
    include: {
      applications: {
        include: { job: { include: { company: true } } },
        orderBy: { appliedAt: 'desc' },
      },
    },
  });
}

export type StudentProfileUpdate = {
  fullName?: string;
  phone?: string;
  profilePhoto?: string;
  collegeName?: string;
  degree?: string;
  branch?: string;
  graduationYear?: number;
  currentCity?: string;
  aboutMe?: string;
  linkedinUrl?: string;
  githubUrl?: string;
  portfolioUrl?: string;
  resumeFileUrl?: string;
  resumeAtsScore?: number;
  skillsJson?: SkillItem[];
  projectsJson?: ProjectItem[];
  technicalScore?: number;
  communicationScore?: number;
  aptitudeScore?: number;
  projectScore?: number;
  overallDes?: number;
  jobPreferencesJson?: JobPreferences;
  showPhone?: boolean;
  showEmail?: boolean;
  showResume?: boolean;
  showDes?: boolean;
  mockInterviewScore?: number;
  mentorFeedback?: string;
};

export async function updateStudentProfile(studentId: string, data: StudentProfileUpdate) {
  return prisma.student.update({
    where: { id: studentId },
    data: {
      ...(data.fullName != null && { fullName: data.fullName }),
      ...(data.phone !== undefined && { phone: data.phone }),
      ...(data.profilePhoto !== undefined && { profilePhoto: data.profilePhoto }),
      ...(data.collegeName !== undefined && { collegeName: data.collegeName }),
      ...(data.degree !== undefined && { degree: data.degree }),
      ...(data.branch !== undefined && { branch: data.branch }),
      ...(data.graduationYear !== undefined && { graduationYear: data.graduationYear }),
      ...(data.currentCity !== undefined && { currentCity: data.currentCity }),
      ...(data.aboutMe !== undefined && { aboutMe: data.aboutMe }),
      ...(data.linkedinUrl !== undefined && { linkedinUrl: data.linkedinUrl }),
      ...(data.githubUrl !== undefined && { githubUrl: data.githubUrl }),
      ...(data.portfolioUrl !== undefined && { portfolioUrl: data.portfolioUrl }),
      ...(data.resumeFileUrl !== undefined && { resumeFileUrl: data.resumeFileUrl }),
      ...(data.resumeAtsScore !== undefined && { resumeAtsScore: data.resumeAtsScore }),
      ...(data.skillsJson !== undefined && { skillsJson: data.skillsJson as any }),
      ...(data.projectsJson !== undefined && { projectsJson: data.projectsJson as any }),
      ...(data.technicalScore !== undefined && { technicalScore: data.technicalScore }),
      ...(data.communicationScore !== undefined && { communicationScore: data.communicationScore }),
      ...(data.aptitudeScore !== undefined && { aptitudeScore: data.aptitudeScore }),
      ...(data.projectScore !== undefined && { projectScore: data.projectScore }),
      ...(data.overallDes !== undefined && { overallDes: data.overallDes }),
      ...(data.jobPreferencesJson !== undefined && { jobPreferencesJson: data.jobPreferencesJson as any }),
      ...(data.showPhone !== undefined && { showPhone: data.showPhone }),
      ...(data.showEmail !== undefined && { showEmail: data.showEmail }),
      ...(data.showResume !== undefined && { showResume: data.showResume }),
      ...(data.showDes !== undefined && { showDes: data.showDes }),
      ...(data.mockInterviewScore !== undefined && { mockInterviewScore: data.mockInterviewScore }),
      ...(data.mentorFeedback !== undefined && { mentorFeedback: data.mentorFeedback }),
    },
  });
}

export async function activateStudentAccount(studentId: string) {
  return prisma.student.update({
    where: { id: studentId },
    data: { accountStatus: AccountStatus.ACTIVE },
  });
}

// ============================================================================
// APPLICATIONS
// ============================================================================

export async function getStudentApplications(studentId: string) {
  return prisma.studentApplication.findMany({
    where: { studentId },
    include: {
      job: { include: { company: true } },
    },
    orderBy: { appliedAt: 'desc' },
  });
}

export async function applyToJob(studentId: string, jobId: string) {
  const job = await prisma.job.findUnique({
    where: { id: jobId },
  });
  if (!job) throw new Error('Job not found');
  if (job.status !== 'open') throw new Error('Job is no longer accepting applications');

  const existing = await prisma.studentApplication.findUnique({
    where: {
      studentId_jobId: { studentId, jobId },
    },
  });
  if (existing) throw new Error('Already applied to this job');

  return prisma.studentApplication.create({
    data: {
      studentId,
      jobId,
      applicationStatus: 'applied',
    },
    include: {
      job: { include: { company: true } },
    },
  });
}

export async function updateApplicationStatus(
  studentId: string,
  applicationId: string,
  status: string
) {
  const app = await prisma.studentApplication.findFirst({
    where: { id: applicationId, studentId },
  });
  if (!app) throw new Error('Application not found');

  // Student can only accept or decline when status is 'offered'
  if (status === 'accepted' || status === 'declined') {
    if (app.applicationStatus !== 'offered') {
      throw new Error('You can only accept or decline an offer');
    }
  } else {
    throw new Error('Students can only set status to accepted or declined for offers');
  }

  return prisma.studentApplication.update({
    where: { id: applicationId },
    data: { applicationStatus: status },
    include: {
      job: { include: { company: true } },
    },
  });
}
