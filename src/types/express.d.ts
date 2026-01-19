import { AuthRequest } from '../middlewares/auth.middleware';

declare global {
  namespace Express {
    interface Request extends AuthRequest {}
  }
}
