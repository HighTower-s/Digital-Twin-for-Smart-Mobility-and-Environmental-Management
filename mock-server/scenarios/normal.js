const CAMERA_ID = "cam-chalongkrung-01";
//รหัสกล้อง 

const ROAD_X_MIN = -15;
const ROAD_X_MAX = 15;
const ROAD_Z_MIN = -60;
const ROAD_Z_MAX = 60;
//ขอบเขตพื้นที่ถนน

const SPEED_MIN = 30;
const SPEED_MAX = 50;
//ความเร็ว

const VEHICLES = [
  { trackId: "car-01",  type: "car" },
  { trackId: "car-02",  type: "car" },
  { trackId: "car-03",  type: "car" },
  { trackId: "moto-01", type: "motorcycle" },
  { trackId: "moto-02", type: "motorcycle" },
];

function randFloat(min, max) {
  return parseFloat((Math.random() * (max - min) + min).toFixed(2));
}
//สุ่มค่า

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
