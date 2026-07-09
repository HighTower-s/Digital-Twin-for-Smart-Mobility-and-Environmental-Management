export const PORT = process.env['PORT'] ? parseInt(process.env['PORT'], 10) : 3000;

export const MAX_VEHICLES = 120;
export const MAX_SPEED = 200;
export const MIN_SPEED = 0;
export const GROUND_Y = 0.0;

export const VEHICLE_TYPES = ['car', 'truck', 'motorcycle'] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];

// TimescaleDB ปิดเป็นค่าเริ่มต้นสำหรับ MVP (ตามที่อาจารย์ระบุว่ายังไม่ต้องมี DB)
// เปิดเมื่อพร้อมเก็บ log: ตั้ง ENABLE_DB_LOGGING=true ใน .env
export const ENABLE_DB_LOGGING = process.env['ENABLE_DB_LOGGING'] === 'true';
