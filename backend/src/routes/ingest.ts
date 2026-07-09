import { Router, Request, Response } from 'express';
import { Server as SocketServer } from 'socket.io';
import { validatePayload, FramePayload } from '../validation/validatePayload';
import { insertFrame } from '../db/logger';
import { ENABLE_DB_LOGGING } from '../constants';

const LOG_TRUNCATE = 500;

export function createIngestRouter(io: SocketServer): Router {
  const router = Router();

  router.post('/api/ingest', (req: Request, res: Response) => {
    const result = validatePayload(req.body);

    if (!result.valid) {
      const raw = JSON.stringify(req.body).slice(0, LOG_TRUNCATE);
      console.warn(`[ingest] REJECTED — ${result.reason} | payload: ${raw}`);
      res.status(400).json({ error: result.reason });
      return;
    }

    const payload = req.body as FramePayload;

    io.emit('frame', payload);

    // Fire-and-forget — DB logging must never delay the broadcast.
    // Disabled by default for MVP (no TimescaleDB); enable via ENABLE_DB_LOGGING=true
    if (ENABLE_DB_LOGGING) {
      insertFrame(payload).catch((err: unknown) => {
        console.error('[ingest] DB insert failed:', err);
      });
    }

    res.status(200).json({ ok: true });
  });

  return router;
}
