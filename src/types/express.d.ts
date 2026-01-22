import { Role, AccountStatus } from './auth.types';

declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        email: string;
        role: Role;
        status: AccountStatus;
      };
      token?: string;
      ipAddress?: string;
    }
  }
}
