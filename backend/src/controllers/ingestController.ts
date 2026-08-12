import { Request, Response } from 'express';
import { Server as SocketServer } from 'socket.io';
import { Direction, LOG_TRUNCATE, VehicleType } from '../constants';
import { vehicleCounters } from '../counters/vehicleCounters';
import { SpawnEvent, validateSpawnEvent } from '../validation/validateSpawnEvent';

export function createIngestHandler(io: SocketServer) {
  return (req: Request, res: Response): void => {
    const result = validateSpawnEvent(req.body);

    if (!result.valid) {
      const raw = JSON.stringify(req.body).slice(0, LOG_TRUNCATE);
      console.warn(`[ingest] REJECTED — ${result.reason} | payload: ${raw}`);
      res.status(400).json({ error: result.reason });
      return;
    }

    const event = req.body as SpawnEvent;
    vehicleCounters.record(event.type as VehicleType, event.direction as Direction, event.cameraId);

    io.emit('spawn', event);

    res.status(200).json({ ok: true });
  };
}
