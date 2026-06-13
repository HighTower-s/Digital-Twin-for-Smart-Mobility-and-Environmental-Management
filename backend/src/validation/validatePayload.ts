import { GROUND_Y, MAX_SPEED, MAX_VEHICLES, MIN_SPEED, VEHICLE_TYPES } from '../constants';

export interface VehiclePayload {
  trackId: string;
  type: string;
  speed: number;
  position: {
    x: number;
    y: number;
    z: number;
  };
}

export interface FramePayload {
  timestamp: string;
  cameraId: string;
  frameCount: number;
  vehicles: VehiclePayload[];
}

type ValidationResult =
  | { valid: true }
  | { valid: false; reason: string };

function isValidIso8601(value: string): boolean {
  return !isNaN(Date.parse(value));
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && isFinite(value);
}

export function validatePayload(body: unknown): ValidationResult {
  if (typeof body !== 'object' || body === null) {
    return { valid: false, reason: 'Payload must be a JSON object' };
  }

  const payload = body as Record<string, unknown>;

  if (typeof payload['timestamp'] !== 'string' || !isValidIso8601(payload['timestamp'])) {
    return { valid: false, reason: 'timestamp is missing or not a valid ISO 8601 string' };
  }

  if (typeof payload['cameraId'] !== 'string' || payload['cameraId'].trim() === '') {
    return { valid: false, reason: 'cameraId is missing or empty string' };
  }

  if (!Array.isArray(payload['vehicles'])) {
    return { valid: false, reason: 'vehicles is not an array' };
  }

  const vehicles = payload['vehicles'] as unknown[];

  if (vehicles.length > MAX_VEHICLES) {
    return { valid: false, reason: `vehicles.length ${vehicles.length} exceeds maximum of ${MAX_VEHICLES}` };
  }

  for (let i = 0; i < vehicles.length; i++) {
    const v = vehicles[i] as Record<string, unknown>;
    const prefix = `vehicles[${i}]`;

    if (!VEHICLE_TYPES.includes(v['type'] as (typeof VEHICLE_TYPES)[number])) {
      return { valid: false, reason: `${prefix}.type "${String(v['type'])}" is not one of [${VEHICLE_TYPES.join(', ')}]` };
    }

    const speed = v['speed'];
    if (typeof speed !== 'number' || speed < MIN_SPEED || speed > MAX_SPEED) {
      return { valid: false, reason: `${prefix}.speed must be a number between ${MIN_SPEED} and ${MAX_SPEED}` };
    }

    const pos = v['position'] as Record<string, unknown> | undefined;
    if (typeof pos !== 'object' || pos === null) {
      return { valid: false, reason: `${prefix}.position is missing or not an object` };
    }

    if (!isFiniteNumber(pos['x'])) {
      return { valid: false, reason: `${prefix}.position.x must be a finite number` };
    }

    if (!isFiniteNumber(pos['z'])) {
      return { valid: false, reason: `${prefix}.position.z must be a finite number` };
    }

    if (pos['y'] !== GROUND_Y) {
      return { valid: false, reason: `${prefix}.position.y must be ${GROUND_Y}` };
    }
  }

  return { valid: true };
}
