// demo.js — เดโมง่ายๆ: รถวิ่ง "เลนเดียว ไปข้างหน้า" ตามถนนใน Unity
// ไม่ต้องใช้วิดีโอ/YOLO — รันผ่าน mock-server ส่งเข้า backend -> Unity ได้เลย
//
// ▼▼▼ แก้ค่าตรงนี้ที่เดียวให้ตรงกับถนนในซีน Unity ▼▼▼
const CONFIG = {
  laneX: 0,          // ตำแหน่ง x ของเลน (อ่านจาก Unity: ลาก empty ไปวางกลางเลนแล้วดู Position.x)
  startZ: -60,       // จุดที่รถ "เข้ามา" (ต้นถนน) — Position.z ปลายใกล้กล้อง
  endZ: 240,         // จุดที่รถ "ออก" (ปลายถนน) — Position.z ปลายไกล
  direction: 1,      // ทิศวิ่ง: +1 = ไปทาง z มากขึ้น, -1 = ไปทาง z น้อยลง
  numCars: 6,        // จำนวนรถบนถนน
  speedKmh: 40,      // ความเร็ว (km/h)
  gapM: 45,          // ระยะห่างระหว่างรถ (เมตร)
  type: "car",       // ชนิดรถ: "car" | "truck" | "motorcycle"
};
// ▲▲▲ แก้แค่ข้างบนนี้พอ ที่เหลือไม่ต้องแตะ ▲▲▲

const CAMERA_ID = "cam-chalongkrung-01";
const DT = 1.0; // วินาทีต่อ 1 เฟรม (mock-server ยิงทุก 1 วินาที)

// สร้างรถเรียงกันในเลนเดียว ระยะห่างเท่าๆ กัน
const roadLength = Math.abs(CONFIG.endZ - CONFIG.startZ);
const cars = Array.from({ length: CONFIG.numCars }, (_, i) => ({
  trackId: `${CONFIG.type}-${String(i + 1).padStart(2, "0")}`,
  type: CONFIG.type,
  progress: (i * CONFIG.gapM) % roadLength, // ระยะที่วิ่งไปแล้วจากจุดเข้า (เมตร)
}));

function toFixed2(n) {
  return parseFloat(n.toFixed(2));
}

function generateFrame(frameCount) {
  const step = (CONFIG.speedKmh / 3.6) * DT; // เมตรต่อเฟรม

  const vehicles = cars.map((c) => {
    c.progress = (c.progress + step) % roadLength; // วิ่งไปเรื่อยๆ วนกลับต้นถนน
    const z = CONFIG.startZ + CONFIG.direction * c.progress;
    return {
      trackId: c.trackId,
      type: c.type,
      speed: toFixed2(CONFIG.speedKmh),
      position: { x: toFixed2(CONFIG.laneX), y: 0.0, z: toFixed2(z) },
    };
  });

  return {
    timestamp: new Date().toISOString(),
    cameraId: CAMERA_ID,
    frameCount,
    vehicles,
  };
}

export { generateFrame };
