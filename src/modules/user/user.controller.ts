import { Request, Response, NextFunction } from 'express';
import prisma from '../../config/database';
import { sendSuccess, sendError } from '../../utils/response';

export const userController = {
  async getProfile(
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> {
    try {
      const { id } = req.params;

      const user = await prisma.user.findUnique({
        where: { id },
        select: {
          id: true,
          email: true,
          name: true,
          createdAt: true,
          updatedAt: true,
        },
      });

      if (!user) {
        sendError(res, 'User not found', 404);
        return;
      }

      sendSuccess(res, user, 'User profile retrieved successfully');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to get user profile', 500);
    }
  },

  async updateProfile(
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> {
    try {
      const { id } = req.params;
      const { name } = req.body;

      const user = await prisma.user.update({
        where: { id },
        data: { name },
        select: {
          id: true,
          email: true,
          name: true,
          createdAt: true,
          updatedAt: true,
        },
      });

      sendSuccess(res, user, 'Profile updated successfully');
    } catch (error: any) {
      sendError(res, error.message || 'Failed to update profile', 500);
    }
  },
};
