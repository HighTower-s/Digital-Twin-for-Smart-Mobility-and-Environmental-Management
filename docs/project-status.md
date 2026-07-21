# Project Status — Smart Flow

> Update this file at the end of every work session.
> Commit message: `docs: update project-status — <what changed>`

---

## Current Phase
**Month 1 — Foundation**
Focus: Prove that the pipeline works end-to-end with mock data before touching real CCTV.

---

## Milestone Overview

| # | Milestone | Target | Status |
|---|---|---|---|
| M1 | Foundation — mock pipeline running end-to-end | End of Month 1 | 🔲 Not started |
| M2 | Integration — real CV pipeline replaces mock | End of Month 2 | 🔲 Not started |
| M3 | Polish & Demo — optimized, stable, demo-ready | End of Month 3 | 🔲 Not started |

---

## M1 — Foundation Checklist

### Documentation
- [x] `CLAUDE.md` created
- [x] `docs/architecture.md` created
- [x] `docs/data-contract.md` created
- [x] `docs/project-status.md` created
- [x] `README.md` with setup instructions
- [x] Module-level `CLAUDE.md` for each module

### Project Setup
- [x] Folder structure created (`ai-worker`, `backend`, `unity`, `mock-server`, `infra`)
- [x] `docker-compose.yml` for TimescaleDB
- [ ] Git repo initialized with `.gitignore`
- [x] `README.md` with quick start commands

### Mock Server
- [x] `scenarios/normal.js` — 5 cars, 30–50 km/h
- [x] `scenarios/congestion.js` — 15 cars, 2–15 km/h
- [x] `scenarios/edge.js` — invalid payloads for validation testing
- [x] `generator.js` — main runner, posts to `/api/ingest` every 1s
- [x] Vehicles move continuously (bounce within road boundary)
- [x] Realistic speed/position ranges — physics-based movement with lanes, smooth speed, stop-and-go (BUG-004 resolved 2026-06-14)

### Backend
- [x] `POST /api/ingest` — receives payload from AI Worker or Mock Server
- [x] Validation layer — rejects invalid payloads with HTTP 400
- [x] WebSocket — broadcasts valid payload via `emit("frame")`
- [x] TimescaleDB — async log insert (non-blocking) — ปิดด้วย ENABLE_DB_LOGGING (default false) ตามอาจารย์
- [x] `GET /health` — health check endpoint
- [x] Unit test for `validatePayload()` — 22 tests, all passing

### Unity
- [x] WebSocket client connects to Backend on startup (SocketIOUnity)
- [x] Receives `frame` event and parses JSON (JsonUtility via raw JSON extraction)
- [x] Object Pool initialized (120 vehicle models, type-keyed)
- [x] Vehicle position updates via `Vector3.Lerp` (fixed-start linear interpolation)
- [x] Vehicles not in latest frame are hidden (not destroyed)
- [ ] WebGL build compiles and runs in Chrome

### Gate: M1 Complete When
- [x] Mock Server (normal scenario) → Backend → Unity renders cars moving on screen (Play mode, โปรเจกต์ Smartflow — 2026-07-09)
- [x] Backend correctly rejects edge scenario payloads (HTTP 400)
- [ ] End-to-end latency measured and documented below

---

## M2 — Integration Checklist

### AI Worker
- [ ] RTSP capture from CCTV camera (1 viewpoint)
- [ ] YOLOv8 vehicle detection with confidence threshold 0.5
- [ ] ByteTrack tracking — stable `trackId` across frames
- [ ] Homography matrix computed from calibration waypoints
- [ ] Coordinate validation before POST (no NaN/Infinity)
- [ ] POSTs to Backend at ~1 frame/second

### Homography Calibration
- [ ] Physical ground truth waypoints placed on Chalong Krung Road
- [ ] GPS coordinates recorded for each waypoint
- [ ] Homography matrix computed and stored
- [ ] Accuracy validated: reprojection error < threshold (to be defined)
- [ ] Accuracy documented in this file

### Integration
- [ ] AI Worker replaces Mock Server in pipeline
- [ ] Real cars visible in Unity from live CCTV stream
- [ ] On-premise server deployment (KMITL)

---

## M3 — Polish & Demo Checklist

### Performance
- [ ] End-to-end latency < 500ms (CCTV → Unity visible update)
- [ ] Unity WebGL loads in < 15 seconds on standard Chrome
- [ ] Backend handles dropped frames gracefully

### Demo Preparation
- [ ] 2D fallback dashboard (live vehicle count + dot map) for backup
- [ ] Mock Server "congestion" scenario ready as demo mode
- [ ] Demo script written (what to show, in what order)
- [ ] Pre-loaded Unity session for fast demo startup

### Documentation
- [ ] `README.md` complete with full setup guide
- [ ] Architecture diagram finalized
- [ ] Known limitations documented

---

## Metrics Log

Record measurements here as the project progresses.

| Date | Metric | Value | Notes |
|---|---|---|---|
| — | End-to-end latency (mock) | — | Not yet measured |
| — | End-to-end latency (real) | — | Not yet measured |
| — | Homography reprojection error | — | Not yet measured |
| — | Unity WebGL initial load time | — | Not yet measured |
| — | Max vehicles before frame drop | — | Not yet tested |

---

## Blockers & Risks

| Risk | Impact | Mitigation | Status |
|---|---|---|---|
| Homography accuracy too low | High — entire pipeline invalid | Validate with ground truth waypoints before building backend | 🔲 Not yet tested |
| RTSP stream unstable from CCTV | High — AI Worker cannot run | Pre-record video as fallback for development and demo | 🔲 Not mitigated |
| Unity WebGL load time too slow for demo | Medium — bad first impression | Pre-load session, have 2D fallback ready | 🔲 Not mitigated |
| TimescaleDB insert falls behind real-time | Low — logging only, non-blocking | Async insert already planned | ✅ Designed |

---

## Session Log

Record what was done each session. Newest at top.

| Date | What was done | Next task |
|---|---|---|
| 2026-06-12 | Created CLAUDE.md, architecture.md, data-contract.md, project-status.md | Create README.md and folder structure |
| 2026-06-12 | Created README.md, folder structure, all module CLAUDE.md files, docker-compose.yml, infra/db/init.sql | Add .gitignore, then implement Mock Server |
| 2026-06-12 | Implemented Mock Server: generator.js + 3 scenarios (normal, congestion, edge). All smoke tests pass. | Implement Backend (`POST /api/ingest`, validation, WebSocket, TimescaleDB) |
| 2026-06-13 | Implemented Backend: Express + Socket.io, POST /api/ingest, GET /health, validatePayload (22 unit tests), async TimescaleDB logger. tsc --noEmit passes clean. | Connect Mock Server → Backend → Unity (M1 gate) |
| 2026-06-13 | Implemented Unity scripts (FrameData, VehiclePool, VehicleController, WebSocketClient). Fixed 5 code-review bugs + 2 integration bugs (SocketIOUnity threading, System.Text.Json field deserialization). Vehicles now spawn and move in Editor Play mode. Mock-server data quality deferred (BUG-004). | WebGL build + M1 gate test |
| 2026-06-14 | Rewrote normal.js + congestion.js: physics-based movement (lane assignment, smooth speed lerp, wrap-around), congestion adds stop-and-go. Road layout matches real Chalong Krung divided highway (3 lanes/side). BUG-004 resolved. | WebGL build + M1 gate test |
| 2026-07-09 | AI Worker (FastAPI vehicle-twin): เพิ่ม contract.py แปลง output ให้ตรง data-contract (map type, y=0, cap 120) + endpoint /stream สตรีมผล YOLOv8+homography เข้า backend/api/ingest แบบ real-time (~2 Hz, httpx) + ปุ่ม "ส่งเข้า Digital Twin" ใน UI. Backend: เพิ่ม ENABLE_DB_LOGGING flag (ปิด TimescaleDB เป็นค่าเริ่มต้นตามอาจารย์). อัปเดต architecture.md (dep + DB optional). ยืนยันเรื่องกล้อง: SICA CCTV มีแต่ยังไม่ได้สิทธิ์ → ใช้วิดีโออัปโหลดแทน RTSP ไปก่อน | WebGL build + ทดสอบครบวงจร upload→detect→backend→Unity |
| 2026-07-09 | Unity หายไป → สร้างโปรเจกต์ใหม่ Smartflow, ใส่สคริปต์ 4 ตัว (FrameData/VehicleController/VehiclePool/WebSocketClient) + FreeCameraController (Input System ใหม่). ผ่าน M1 gate: mock → backend → Unity เห็นรถวิ่งใน Play mode | ทดสอบ ai-worker (วิดีโอจริง) → Unity, วัด latency, init git |
| 2026-07-09 | เพิ่ม Plan 1 (คร่าวๆ): count_detector.py — ตีเส้น 2 เส้น นับรถ (counted-set กันซ้ำ) + วัดความเร็ว (d/เวลาข้าม A→B) + PopulationManager จำลองตำแหน่งลงถนน (เลน −9/0/9, z −60..240 ตรงกับ mock/Unity). เพิ่ม endpoint /process_count + toggle โหมด twin/count ใน UI. Unit test ผ่าน: population layout, cap 120, สูตรความเร็ว, contract ผ่าน validatePayload. ตอนนี้ 1 เว็บทำได้ทั้ง 2 Plan สลับด้วยปุ่ม | WebGL build + ทดสอบครบวงจรด้วยวิดีโอจริง (ทั้ง 2 โหมด) |
| 2026-07-21 | ทดสอบ twin (homography) กับวิดีโอจริง (per1–per4) → พบว่ามั่ว: พิกัดเพี้ยน, ความเร็วพุ่ง 200–290 km/h, ByteTrack สลับ ID เร็ว (>100 ใน 18วิ), มอไซค์หลุด. **ตัดสินใจ pivot**: เลิกใช้ homography-twin สำหรับเดโม เปลี่ยนเป็น **count-event** — ตรวจตอนรถข้ามเส้น A → ยิง spawn event {ชนิด(โหวต), เลน(จาก x), ความเร็ว(ตามชนิด SPEED_BY_TYPE)} → PopulationManager ขับไป +Z. rewrite count_detector.py (event-driven, ล็อกชนิด, lane_index_from_x, ความเร็วกำหนดตามชนิด). ไม่แตะ data-contract/backend/Unity logic. เพิ่ม test_count_sim.py (8 tests ผ่านหมด). อัปเดต .env.example (SPEED_BY_TYPE, LANE_X_BOUNDS, ROAD เป็น local frame). **พบบั๊ก Unity**: `_originAnchor` = null ในซีน + ไม่มี TrafficOrigin ในซีน + LANES/roadLen ไม่ตรงกัน 3 ที่ → เป็นเหตุรถสปอนมั่ว. รวมค่าเป็น single source of truth แล้ว (env ↔ gizmo default = LANES −3.5/0/3.5, halfWidth 1.6, roadLen 200) | **[Unity editor]** วาง TrafficOrigin ทับถนนโมเดล (หมุน +Z ตามถนน) + assign เข้า `_originAnchor` ของ VehiclePool → set gizmo.lanes/roadLen ให้ตรง .env → ทดสอบครบวงจร per4 (upload→count→backend→Unity) + วัด latency |