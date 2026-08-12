import { Router } from 'express';
import { Server as SocketServer } from 'socket.io';
import { createIngestHandler } from '../controllers/ingestController';
import { getStatsHandler, resetStatsHandler } from '../controllers/statsController';
import healthRouter from './health';

export function createApiRouter(io: SocketServer): Router {
  const router = Router();

  router.use(healthRouter);
  router.post('/api/ingest', createIngestHandler(io));
  router.get('/api/stats', getStatsHandler);
  router.post('/api/stats/reset', resetStatsHandler);

  return router;
}
