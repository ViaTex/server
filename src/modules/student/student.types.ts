/**
 * Student module types
 * Aligned with students table and student_applications (see shems_design.md)
 */

// JSON shapes (reference for API)
export interface SkillItem {
  name: string;
  level: number;
  verified: boolean;
}

export interface ProjectItem {
  title: string;
  tech: string[];
  verified: boolean;
}

export interface JobPreferences {
  roles?: string[];
  locations?: string[];
  job_type?: string;
  expected_salary?: number;
}

// Application status values (workflow: applied → shortlisted → interviewed → offered → accepted | declined)
export const APPLICATION_STATUS = {
  APPLIED: 'applied',
  SHORTLISTED: 'shortlisted',
  INTERVIEW_SCHEDULED: 'interview_scheduled',
  INTERVIEWED: 'interviewed',
  OFFERED: 'offered',
  ACCEPTED: 'accepted',
  DECLINED: 'declined',
  REJECTED: 'rejected',
} as const;

export type ApplicationStatusType = (typeof APPLICATION_STATUS)[keyof typeof APPLICATION_STATUS];
