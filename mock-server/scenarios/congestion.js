// congestion.js - 15 vehicles, one-way traffic, 3 lanes, 2-15 km/h, stop-and-go
// All vehicles travel in +Z direction (away from camera)
// Lane centers: x = -9 (left), 0 (middle), +9 (right)

const CAMERA_ID = "cam-chalongkrung-01";

const ROAD_Z_MIN = -30;
const ROAD_Z_MAX = 240;
const DT = 1.0;

const SPEED_MIN = 0;
const SPEED_MAX = 15;

const SPEED_LERP = 0.12;
const TARGET_CHANGE_PROB = 0.08;
const STOP_PROB = 0.06;
const GO_PROB = 0.10;
const LANE_DRIFT_RATE = 0.35;
const LANE_JITTER = 0.1;
const LANE_HALF_WIDTH = 1.0;

// Persistent state - mutated in place every tick
const state = [
  // Left lane (x = -9)
  { trackId: "car-01",   type: "car",   laneX: -9, x: -9.0, z: -25.0, speed: 5,  targetSpeed: 8,  stopped: false, resetting: false },
  { trackId: "car-02",   type: "car",   laneX: -9, x: -9.0, z: -10.0, speed: 3,  targetSpeed: 5,  stopped: false, resetting: false },
  { trackId: "car-03",   type: "car",   laneX: -9, x: -9.0, z:   2.0, speed: 0,  targetSpeed: 0,  stopped: true,  resetting: false },
  { trackId: "car-04",   type: "car",   laneX: -9, x: -9.0, z:  14.0, speed: 8,  targetSpeed: 10, stopped: false, resetting: false },
  { trackId: "car-05",   type: "car",   laneX: -9, x: -9.0, z:  24.0, speed: 4,  targetSpeed: 6,  stopped: false, resetting: false },
  // Middle lane (x = 0)
  { trackId: "car-06",   type: "car",   laneX:  0, x:  0.0, z: -28.0, speed: 0,  targetSpeed: 0,  stopped: true,  resetting: false },
  { trackId: "car-07",   type: "car",   laneX:  0, x:  0.1, z: -14.0, speed: 6,  targetSpeed: 8,  stopped: false, resetting: false },
  { trackId: "car-08",   type: "car",   laneX:  0, x: -0.1, z:  -2.0, speed: 0,  targetSpeed: 0,  stopped: true,  resetting: false },
  { trackId: "car-09",   type: "car",   laneX:  0, x:  0.0, z:  10.0, speed: 5,  targetSpeed: 7,  stopped: false, resetting: false },
  { trackId: "car-10",   type: "car",   laneX:  0, x:  0.0, z:  22.0, speed: 3,  targetSpeed: 5,  stopped: false, resetting: false },
  // Right lane (x = +9)
  { trackId: "truck-01", type: "truck", laneX:  9, x:  9.0, z: -26.0, speed: 7,  targetSpeed: 10, stopped: false, resetting: false },
  { trackId: "truck-02", type: "truck", laneX:  9, x:  9.0, z: -12.0, speed: 0,  targetSpeed: 0,  stopped: true,  resetting: false },
  { trackId: "truck-03", type: "truck", laneX:  9, x:  9.0, z:   0.0, speed: 5,  targetSpeed: 8,  stopped: false, resetting: false },
  { trackId: "truck-04", type: "truck", laneX:  9, x:  9.0, z:  12.0, speed: 0,  targetSpeed: 0,  stopped: true,  resetting: false },
  { trackId: "truck-05", type: "truck", laneX:  9, x:  9.0, z:  24.0, speed: 4,  targetSpeed: 6,  stopped: false, resetting: false },
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
    return null;
  }

  if (v.stopped) {
    if (Math.random() < GO_PROB) {
      v.stopped = false;
      v.targetSpeed = randFloat(5, SPEED_MAX);
    } else {
      v.targetSpeed = 0;
    }
  } else {
    if (Math.random() < STOP_PROB) {
      v.stopped = true;
      v.targetSpeed = 0;
    } else if (Math.random() < TARGET_CHANGE_PROB) {
      v.targetSpeed = randFloat(2, SPEED_MAX);
    }
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
