import jwt from 'jsonwebtoken';
import { config } from '../config/env';

export interface TokenPayload {
  id: string;
  email: string;
}

export const generateToken = (payload: TokenPayload): string => {
  // @ts-ignore - JWT types issue
  return jwt.sign(payload, config.jwtSecret, {
    expiresIn: config.jwtAccessExpiresIn,
  });
};

export const verifyToken = (token: string): TokenPayload => {
  return jwt.verify(token, config.jwtSecret) as TokenPayload;
};
