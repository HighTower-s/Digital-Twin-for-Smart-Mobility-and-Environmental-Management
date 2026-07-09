# Smartflow (Unity) — วิธีติดตั้งโปรเจกต์ใหม่

สคริปต์ 4 ตัวอยู่ที่ `Assets/Scripts/` แล้ว (FrameData, VehicleController, VehiclePool, WebSocketClient)
ทำตามขั้นตอนนี้ให้รถวิ่งใน Unity จากข้อมูล backend

---

## 1. ติดตั้งไลบรารี SocketIOUnity (จำเป็น — WebSocketClient ใช้)

Unity → **Window ▸ Package Manager** → กด **+** ▸ **Add package from git URL...** วาง:

```
https://github.com/itisnajim/SocketIOUnity.git
```

รอจนติดตั้งเสร็จ (จะได้ namespace `SocketIOClient` + คลาส `SocketIOUnity`)
ถ้า error เรื่อง dependency ให้เพิ่ม Newtonsoft Json ด้วย: Add package by name → `com.unity.nuget.newtonsoft-json`

> คอมไพล์ผ่านแล้ว namespace `SmartFlow.Network` / `SmartFlow.Vehicles` จะใช้ได้

---

## 2. สร้าง Prefab รถ 3 ชนิด (car / truck / motorcycle)

ชั่วคราวใช้กล่องสีก่อนก็ได้ (เปลี่ยนเป็นโมเดลสวยทีหลัง):

1. Hierarchy → คลิกขวา ▸ **3D Object ▸ Cube** ตั้งชื่อ `Car`
2. ปรับ Scale ~ `(2, 1, 4)` (กxสูงxยาว เมตร) ใส่สี (สร้าง Material สีน้ำเงิน)
3. ลาก `Car` จาก Hierarchy ลงโฟลเดอร์ `Assets/Prefabs/` → เกิด **Car.prefab**
4. ลบ Car ออกจาก Hierarchy (เก็บแต่ prefab)
5. ทำซ้ำ: **Truck** scale ~`(2.5, 2, 7)` สีแดง · **Motorcycle** scale ~`(0.8, 1, 2)` สีเหลือง

> ไม่ต้องใส่สคริปต์ VehicleController ที่ prefab — Pool จะ `AddComponent` ให้อัตโนมัติ

---

## 3. สร้าง Manager (ตัวคุมหลัก)

1. Hierarchy → คลิกขวา ▸ **Create Empty** ตั้งชื่อ `Manager`
2. เลือก Manager → Inspector ▸ **Add Component** ▸ พิมพ์ `VehiclePool` → เพิ่ม
3. Add Component ▸ `WebSocketClient` → เพิ่ม
4. ตั้งค่าใน Inspector:
   - **VehiclePool**: ลาก Car.prefab / Truck.prefab / Motorcycle.prefab ลงช่อง Car/Truck/Motorcycle Prefab
   - **WebSocketClient**: `Server Url` = `http://localhost:3000` · ลาก **Manager** ตัวเอง (ที่มี VehiclePool) ลงช่อง `Vehicle Pool`

---

## 4. ตั้งกล้องให้เห็นถนน

ถนนอยู่ในช่วง `x = -9..9`, `z = -60..240` (y=0) ตั้ง Main Camera ประมาณ:

- Position: `(0, 60, -70)`
- Rotation: `(35, 0, 0)`  (ก้มมองไปตามแนว +Z)

(ปรับให้เห็นรถวิ่งเข้ามาได้ตามชอบ) จะเพิ่ม Plane เป็นพื้นถนนที่ scale ~`(2, 1, 30)` วางที่ y=0 ก็ได้เพื่อให้เห็นถนน

---

## 5. บันทึก Scene

**File ▸ Save As** → `Assets/Scenes/DigitalTwin.unity`

---

## 6. รันทดสอบ (Play mode)

เปิด 2 อย่างนี้ก่อน แล้วค่อยกด **Play** ใน Unity:

```bash
# 1) backend
cd backend && npm install && npm run dev

# 2) แหล่งข้อมูล — เลือกอย่างใดอย่างหนึ่ง
cd mock-server && node generator.js --scenario normal      # ทดสอบเร็วสุด ไม่ต้องมีวิดีโอ
# หรือ เปิดเว็บ ai-worker (:8000) อัปโหลดวิดีโอ → กด "ส่งเข้า Digital Twin"
```

**ผ่านเมื่อ:** Console Unity ขึ้น `[WebSocketClient] Connected` และเห็นรถวิ่งใน Game view

---

## หมายเหตุ WebGL

`SocketIOUnity` ใช้ได้ใน **Editor Play mode** และ build **Desktop** ปกติ
แต่ **WebGL** เบราว์เซอร์ไม่รองรับ native WebSocket ของ .NET — ถ้าจะ build WebGL จริง
ต้องเปลี่ยน transport เป็น websocket ฝั่งเบราว์เซอร์ (เช่น native-websocket) ภายหลัง
สำหรับเดโมตอนนี้ใช้ **Play mode** พอ

---

## Troubleshooting

- **คอมไพล์ error หา SocketIOClient ไม่เจอ** → ยังไม่ได้ติดตั้ง package ขั้นที่ 1
- **Connected แต่รถไม่ขึ้น** → prefab ไม่ได้ลากใส่ VehiclePool หรือ type ไม่ตรง (car/truck/motorcycle)
- **รถกองมุมเดียว/นอกจอ** → ปรับกล้อง หรือเช็กว่าใช้ข้อมูลจากถนน z -60..240 (mock ใช้ค่านี้อยู่แล้ว)
- **ไม่ Connected** → backend ยังไม่รัน หรือ Server Url ผิด
