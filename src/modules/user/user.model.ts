// This file is for documentation purposes
// The actual model is defined in Prisma schema

export interface User {
  id: string;
  email: string;
  password: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
}
