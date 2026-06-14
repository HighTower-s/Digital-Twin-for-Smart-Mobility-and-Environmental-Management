// normal.js - 5 vehicles, one-way traffic, 3 lanes, 30-50 km/h
// All vehicles travel in +Z direction (away from camera)
// Lane centers: x = -9 (left), 0 (middle), +9 (right)

const CAMERA_ID = "cam-chalongkrung-01";

const ROAD_Z_MIN = -60;
const ROAD_Z_MAX = 240;
const DT = 1.0; // seconds per tick

const SPEED_MIN = 30;
const SPEED_MAX = 50;

const SPEED_LERP = 0.15;
const TARGET_CHANGE_PROB = 0.05;
const LANE_DRIFT_RATE = 0.4;
const LANE_JITTER = 0.15;
const LANE_HALF_WIDTH = 1.2;

// Persistent state - mutated in place every tick
const state = [
  { trackId: "car-01",  type: "car",        laneX: -9, x: -9.0, z: -40.0, speed: 38, targetSpeed: 40, resetting: false },
  { trackId: "car-02",  type: "car",        laneX:  0, x:  0.0, z:  30.0, speed: 44, targetSpeed: 45, resetting: false },
  { trackId: "car-03",  type: "car",        laneX:  9, x:  9.0, z: 100.0, speed: 36, targetSpeed: 38, resetting: false },
  { trackId: "moto-01", type: "motorcycle", laneX:  0, x:  0.2, z: 160.0, speed: 50, targetSpeed: 48, resetting: false },
  { trackId: "moto-02", type: "motorcycle", laneX: -9, x: -8.8, z: 210.0, speed: 42, targetSpeed: 44, resetting: false },
];

function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

function randFloat(min, max) {
  return Math.random() * (max - min) + min;
}

function toFixed2(n) {
  return parseFloat(n.toFixed(2));
}

function updateVehicle(v) {
  if (v.resetting) {
    v.resetting = false;
    return null; // Unity hides vehicle automatically when not in payload
  }

  if (Math.random() < TARGET_CHANGE_PROB) {
    v.targetSpeed = randFloat(SPEED_MIN, SPEED_MAX);
  }

  v.speed += (v.targetSpeed - v.speed) * SPEED_LERP;
  v.speed = clamp(v.speed, SPEED_MIN, SPEED_MAX);

  v.z += (v.speed / 3.6) * DT;

  if (v.z > ROAD_Z_MAX) {
    v.z = ROAD_Z_MIN;
    v.resetting = true;
    return null;
  }

  v.x += (v.laneX - v.x) * LANE_DRIFT_RATE;
  v.x += randFloat(-LANE_JITTER, LANE_JITTER);
  v.x = clamp(v.x, v.laneX - LANE_HALF_WIDTH, v.laneX + LANE_HALF_WIDTH);

  return {
    trackId: v.trackId,
    type: v.type,
    speed: toFixed2(v.speed),
    position: { x: toFixed2(v.x), y: 0.0, z: toFixed2(v.z) },
  };
}

export function generateFrame(frameCount) {
  return {
    timestamp: new Date().toISOString(),
    cameraId: CAMERA_ID,
    frameCount,
    vehicles: state.map(updateVehicle).filter(Boolean),
  };
}
