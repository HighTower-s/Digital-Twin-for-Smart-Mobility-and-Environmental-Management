import express, { Express } from 'express';

export function createApp(): Express {
  const app = express();
  app.use(express.json());
  return app;
}
