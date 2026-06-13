import { Pool } from 'pg';
import { FramePayload } from '../validation/validatePayload';

const pool = new Pool({
  host: process.env['DB_HOST'] ?? 'localhost',
  port: process.env['DB_PORT'] ? parseInt(process.env['DB_PORT'], 10) : 5432,
  database: process.env['DB_NAME'] ?? 'smartflow',
  user: process.env['DB_USER'] ?? 'smartflow',
  password: process.env['DB_PASSWORD'] ?? '',
});

export async function insertFrame(payload: FramePayload): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    for (const vehicle of payload.vehicles) {
      await client.query(
        `INSERT INTO vehicle_positions (time, camera_id, frame_count, track_id, vehicle_type, speed, pos_x, pos_y, pos_z)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          payload.timestamp,
          payload.cameraId,
          payload.frameCount,
          vehicle.trackId,
          vehicle.type,
          vehicle.speed,
          vehicle.position.x,
          vehicle.position.y,
          vehicle.position.z,
        ]
      );
    }
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
