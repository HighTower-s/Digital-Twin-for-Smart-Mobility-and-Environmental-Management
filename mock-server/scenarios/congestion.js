const CAMERA_ID = "cam-chalongkrung-01";

const ROAD_X_MIN = -15;
const ROAD_X_MAX = 15;
// Tighter Z band to simulate vehicles clustered in a jam
const ROAD_Z_MIN = -20;
const ROAD_Z_MAX = 20;
// บีบขนาดถนน
const SPEED_MIN = 2;
const SPEED_MAX = 15;
// ลดความเร็ว

const VEHICLES = [
  { trackId: "car-01",   type: "car" },
  { trackId: "car-02",   type: "car" },
  { trackId: "car-03",   type: "car" },
  { trackId: "car-04",   type: "car" },
  { trackId: "car-05",   type: "car" },
  { trackId: "car-06",   type: "car" },
  { trackId: "car-07",   type: "car" },
  { trackId: "car-08",   type: "car" },
  { trackId: "car-09",   type: "car" },
  { trackId: "car-10",   type: "car" },
  { trackId: "truck-01", type: "truck" },
  { trackId: "truck-02", type: "truck" },
  { trackId: "truck-03", type: "truck" },
  { trackId: "truck-04", type: "truck" },
  { trackId: "truck-05", type: "truck" },
];

function randFloat(min, max) {
  return parseFloat((Math.random() * (max - min) + min).toFixed(2));
}

export function generateFrame(frameCount) {
  return {
    timestamp: new Date().toISOString(),
    cameraId: CAMERA_ID,
    frameCount,
    vehicles: VEHICLES.map((v) => ({
      trackId: v.trackId,
      type: v.type,
      speed: randFloat(SPEED_MIN, SPEED_MAX),
      position: {
        x: randFloat(ROAD_X_MIN, ROAD_X_MAX),
        y: 0.0,
        z: randFloat(ROAD_Z_MIN, ROAD_Z_MAX),
      },
    })),
  };
}
