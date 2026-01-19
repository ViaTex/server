# DishaSetu Server

Backend API server for DishaSetu application built with Express, TypeScript, Prisma, and PostgreSQL.

## Tech Stack

- **Runtime**: Node.js
- **Framework**: Express.js
- **Language**: TypeScript
- **Database**: PostgreSQL
- **ORM**: Prisma
- **API Documentation**: Swagger UI

## Prerequisites

- Node.js (v18 or higher)
- PostgreSQL (v14 or higher)
- npm or yarn

## Setup

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env
```

Update the `.env` file with your database credentials:
```
DATABASE_URL="postgresql://username:password@localhost:5432/dishasetu?schema=public"
PORT=5000
NODE_ENV=development
JWT_SECRET=your-secret-key-change-in-production
JWT_EXPIRES_IN=7d
CORS_ORIGIN=*
```

3. Set up the database:
```bash
# Generate Prisma Client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# Seed the database (optional)
npm run prisma:seed
```

4. Start the development server:
```bash
npm run dev
```

The server will start on `http://localhost:5000`

## Available Scripts

- `npm run dev` - Start development server with nodemon
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint
- `npm run prisma:generate` - Generate Prisma Client
- `npm run prisma:migrate` - Run database migrations
- `npm run prisma:studio` - Open Prisma Studio
- `npm run prisma:seed` - Seed the database

## API Documentation

Once the server is running, visit `http://localhost:5000/api-docs` for Swagger UI documentation.

## Project Structure

```
src/
├── config/          # Configuration files
├── modules/         # Feature-based modules
│   ├── auth/       # Authentication module
│   └── user/       # User module
├── middlewares/     # Express middlewares
├── routes/          # Route definitions
├── utils/           # Utility functions
├── types/           # TypeScript type definitions
├── app.ts           # Express app setup
└── server.ts        # Server bootstrap
```

## License

ISC
