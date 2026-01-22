import express, { Request, Response } from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import cors from 'cors';
import { config } from './config/env';
import { swaggerSpec, swaggerUi } from './config/swagger';
import routes from './routes';
import { errorHandler } from './middlewares/error.middleware';
import { notFound } from './middlewares/notFound';

const app = express();

// CORS configuration
app.use(
  cors({
    origin: config.corsOrigin === '*' ? '*' : config.corsOrigin,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);

// Security middleware
app.use(
  helmet({
    contentSecurityPolicy: false,
    crossOriginEmbedderPolicy: false,
  })
);

// Body parser middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Compression middleware
app.use(compression());

// Logging middleware
if (config.nodeEnv === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// Health check route
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({
    success: true,
    message: 'Server is running',
    timestamp: new Date().toISOString(),
  });
});

// Swagger documentation
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
  customCss: '.swagger-ui .topbar { display: none }',
  customSiteTitle: 'DishaSetu API Documentation',
}));

// API routes
app.use('/api', routes);

// 404 handler (must be before error handler)
app.use(notFound);

// Error handler (must be last)
app.use(errorHandler);

export default app;
