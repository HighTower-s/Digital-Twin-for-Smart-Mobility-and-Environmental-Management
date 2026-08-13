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

### Backend — Prototype (spawn-event, current)
- [x] `POST /api/ingest` — receives one spawn-event, validates, updates counters, `emit("spawn", event)`
- [x] `validateSpawnEvent()` — rejects invalid spawn-events with HTTP 400 + reason (15 unit tests, all passing)
- [x] `GET /api/stats` / `POST /api/stats/reset` — in-memory vehicle counters (by type × direction), 6 unit tests, all passing
- [x] `GET /health` — health check endpoint
- [x] No database — counters are in-memory only, reset on restart
- [x] Smoke tested: replayed `ai-worker/data/output_results/events.jsonl` (28 events) → `/api/stats` totals matched the file exactly; confirmed a Socket.io client receives `spawn` events (incl. `bus` type); confirmed invalid `type` → HTTP 400

### Backend — MVP (frame schema, deferred)
- [x] `POST /api/ingest` — receives payload from AI Worker or Mock Server (implemented 2026-06-13, code preserved in git history — deleted from working tree, restore when starting MVP)
- [x] Validation layer — rejects invalid payloads with HTTP 400
- [x] WebSocket — broadcasts valid payload via `emit("frame")`
- [x] TimescaleDB — async log insert (non-blocking) — ปิดด้วย ENABLE_DB_LOGGING (default false) ตามอาจารย์
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
| 2026-08-10 | **แก้ `docs/data-contract.md` → v1.1.0** (ผู้ใช้อนุมัติเอง — เจ้าของโปรเจกต์): เพิ่ม `"bus"` เข้า `type` enum, ทำ `speed`/`position.*` เป็น optional (ตรงกับ spawn event ของ prototype ที่ตัด lane/speed ออกไปแล้ว) **แก้แค่เอกสาร ยังไม่แก้โค้ด** — Backend validation (`validatePayload`) และ Unity `VehiclePool.cs` **ยังไม่รองรับ** กฎใหม่ (`_busPrefab` ยังไม่มี, ยังไม่มี logic รองรับรถที่ไม่มี position) เพิ่มคำเตือนไว้ในเอกสารและ Change Log ชัดเจนว่าห้ามส่ง payload แบบใหม่เข้า backend จริงจนกว่าจะ implement โค้ดรองรับ (**หมายเหตุภายหลัง 2026-08-12:** การตัดสินใจนี้ถูกแทนที่แล้ว — ดู entry 2026-08-12 ด้านล่าง เก็บ `speed`/`position.*` เป็น required บน Frame schema เหมือนเดิม แล้วแยก §2b spawn-event schema ต่างหากแทน) | implement โค้ด Backend+Unity ให้รองรับ schema v1.1.0 (หรือรอจนกว่าจะทำ Roadmap ขั้น 3 ของ ai-worker ที่จะเชื่อมจริง) |
| 2026-08-10 | เขียน `ai-worker/src/calibrate.py` — เครื่องมือคลิกหาพิกัด `polygon`/`line` จากเฟรมจริงของวิดีโอ (`python -m src.calibrate`) แทนการเดา/วัดพิกัดด้วยมือผ่าน VLC+IrfanView คลิกซ้าย=เพิ่มจุด, Enter=จบรูป (polygon→line→zone ถัดไป), u=undo, r=reset, q=เลิก จบแล้ว print YAML พร้อมวางใส่ `config.yaml` พิกัดที่ได้แปลงกลับเป็นขนาดเฟรมจริงเสมอแม้หน้าต่างที่เห็นถูกย่อแสดงผล (ทดสอบกับวิดีโอจริง `traffic-1.mp4` ขนาด 3840x2160 — ตรวจ round-trip พิกัดถูกต้อง) อัปเดต `CLAUDE.md` §3/§4/§8 และ `README.md` ให้ตรงกับเครื่องมือที่มีแล้ว **53 tests ยังผ่านหมด, ruff+black clean** | นับมือเทียบวัดความแม่นยำ (Roadmap ขั้น 4 ที่เหลือ) |
| 2026-08-09 | **ผู้ใช้ลบ `ai-worker/src/` และ `ai-worker/legacy/` ทิ้งเอง (ตั้งใจ, untracked ใน git กู้คืนไม่ได้) แล้วขอเขียน prototype ใหม่ทั้งหมด** พร้อมตัด `lane` และ `speed` ออก (ทั้งคู่วัดจากภาพจริงไม่ได้ในเวอร์ชันนี้ — ปัญหาเดียวกับ homography ที่ pivot ไปแล้ว 07-21) เขียนใหม่เป็นโครงลูกผสม: `data/{input_videos,output_results,weights}/` + `src/` เป็น package + `config.yaml` เป็นตัวตั้งค่าหลัก (แทน CLI args, เพิ่ม dep `pyyaml`) + รวม detect+track เป็น `detector.py` ไฟล์เดียว (ของเดิมแยก `tracker.py`). ไฟล์ที่เขียนใหม่: `constants.py`, `counter.py` (geometry+`VehicleCounter`, ไม่มี `lane_count`/`line_ratio` แล้ว), `config.py` (โหลด YAML แทน JSON calib), `emitter.py` (spawn event schema `0.2-draft` เหลือแค่ `trackId/type/direction/confidence` ตัด `lane`/`speed`/`speedSource` ออก), `detector.py`, `overlay.py`, `main.py`. **53 tests ผ่าน (18 counter + 17 config + 15 emitter + 3 detector), ruff + black clean**. ยืนยันแล้วว่า `counter/config/emitter/constants` ไม่ import cv2/torch/ultralytics จริง. เขียน `ai-worker/CLAUDE.md` ใหม่ทั้งฉบับ (ลบ RTSP/homography/capture.py ที่ไม่ตรงความจริงทิ้ง) แยก MVP Main (เป้าหมาย) กับ Prototype (ของจริงตอนนี้) ชัดเจน + เพิ่ม §5 อธิบายเหตุผลตัด lane/speed. **ผลตามมา**: `road.py`/`poster.py`/`replay.py`/`--backend` เดิมที่จำลองตำแหน่งจาก lane+speed ใช้ไม่ได้แล้ว ไม่ได้สร้างใหม่รอบนี้ — ต้องออกแบบสะพานไป backend ใหม่ตอนทำ lane/speed จริง (Roadmap ขั้น 2–3 ใน CLAUDE.md). อัปเดต `architecture.md` § Tech Decisions (เพิ่ม `pyyaml`, rule 2) | ทดสอบกับวิดีโอจริงคลิปแรก (ยังไม่มีในเครื่อง) → ดูผลนับ → ออกแบบ lane/speed แบบใหม่ (Roadmap ขั้น 2) |
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
| 2026-08-08 | เขียนสเปกฉบับแก้ไข `specs/2026-08-08-ai-worker-prototype-revision.md` (ตรวจพบว่าสเปก 08-07 อ้าง `src2/` และ `src/vehicle-twin/` ที่ไม่มีอยู่จริงแล้ว). **ทำขั้น 0–3 + 9 เสร็จ** (แกนที่ไม่ต้องใช้วิดีโอ): ย้าย `src/main.py` → `legacy/prototype-counting.py`; เขียน `constants.py`, `counter.py` (geometry + `VehicleCounter`: segment-intersection แทน `y > line_y`, โหวตชนิดล็อกตอนข้าม, ตรวจทิศ, กันนับซ้ำข้าม prune, anomaly 4 เหตุผล), `config.py` (validation 8 แบบ รวมทั้งเช็คว่าเส้นนับอยู่ใน polygon ตัวเอง), `emitter.py` (spawn event + `events.jsonl`, lane จากสัดส่วนบนเส้นนับแทน `LANE_X_BOUNDS`, `speedSource=assumed`). **63 tests ผ่าน, ruff + black clean**, ยืนยันว่า `counter/config/emitter` ไม่โหลด cv2/torch/numpy จริง. รองรับ 4 ชนิด (เดิม `classes=[2,7]` มองไม่เห็นมอเตอร์ไซค์/รถบัส). ยังไม่แตะ `data-contract.md` — `EMIT_BUS_AS="truck"` เป็นค่าเริ่มต้นจนกว่าทีมจะอนุมัติเพิ่ม `bus` | **[รอ path ฟุตเทจ KMITL]** แล้วทำขั้น 4 (`calibrate.py`) → 5 (`tracker.py`) → 6 (`overlay.py`) → 7 (`main.py`) → 8 (นับมือเทียบ + วัดความแม่นยำ) |
| 2026-08-08 | **ทำขั้น 5–7 ต่อจนรับคลิปได้จริง** (`tracker.py`, `overlay.py`, `main.py`). **เพิ่มจากสเปกเดิม: โหมดโซนอัตโนมัติ** — `config.auto_zones()` เดาโซนจากขนาดเฟรม ทำให้ `python main.py <วิดีโอ>` รันได้ทันทีโดยไม่ต้อง calibrate ก่อน (สเปกเดิมบังคับให้ calibrate ก่อนเสมอ ซึ่งเป็นกำแพงที่ไม่จำเป็นสำหรับการลองครั้งแรก) ผลลัพธ์เตือนชัดว่าเป็นโหมดเดา ตัวเลขยังอ้างอิงไม่ได้. `tracker.py`/`overlay.py` ใช้ lazy import จึงรัน pytest ชุดเต็มได้โดยไม่ต้องลง ultralytics/cv2. **99 tests ผ่าน, ruff + black clean**. **smoke test เจอบั๊ก**: `line_inset` 6% ของความกว้างสร้างช่องตาย 115 px ริมภาพ รถเลนนอกสุดข้าม polygon แต่ไม่ข้ามเส้น → ไม่ถูกนับและไม่ขึ้น anomaly ด้วย (หายเงียบ) ลดเหลือ 0.5% + เพิ่ม regression test 2 ตัว. เขียน `src/README.md` | **[รอ path ฟุตเทจ KMITL]** รันคลิปจริงดูผล → เขียน `calibrate.py` (ขั้น 4) → นับมือเทียบวัดความแม่นยำ (ขั้น 8) |
| 2026-08-08 | **ต่อ AI Worker เข้า backend สำเร็จ** เพิ่ม `road.py` (จำลองตำแหน่งรถ: spawn event → รถเสมือนวิ่งบนถนน → payload ตาม data-contract v1.0.0), `poster.py` (POST ด้วย urllib **ไม่เพิ่ม dependency** ตาม rule 2; backend ล่มไม่ทำให้การนับหยุด), `replay.py` (เล่นซ้ำ events.jsonl เข้า backend โดยไม่ต้องรัน YOLO ใหม่) + flag `--backend` ใน main.py. **ทดสอบกับ backend ตัวจริง (compile ด้วย tsc): ส่ง 108 payload ผ่านหมด 108/108 ไม่มี REJECTED**. ทดสอบด้านลบยืนยันว่า validation ทำงานจริง — `type:"bus"` / `position.y=0.5` / รถ 130 คัน ถูกปฏิเสธพร้อมเหตุผลครบ. **130 tests ผ่าน, ruff + black clean**. ⚠️ **ค่าพิกัดถนนยังไม่ได้ข้อสรุป**: `mock-server/normal.js` ใช้เลน ±9, z −60..240 แต่บันทึก 07-21 บอก LANES ±3.5, roadLen 200 — เลือกชุด mock-server ไว้ก่อน (เคยผ่าน M1 gate) **ต้องยืนยันกับซีน Unity ก่อนเดโม** | **[Unity]** ยืนยันค่า TrafficOrigin/gizmo ให้ตรงกับ `constants.py` → ทดสอบครบวงจร replay → backend → Unity. **[AI]** รันคลิปจริง → `calibrate.py` → วัดความแม่นยำ |
| 2026-08-12 | Redesigned backend docs into **Prototype** (spawn-event ingest, in-memory counters + `GET /api/stats`, no DB) vs **MVP** (frame schema, position/speed, TimescaleDB) phases, matching current AI Worker output (`ai-worker/data/output_results/events.jsonl`). Rewrote `backend/CLAUDE.md`; updated `docs/data-contract.md` to v1.1.0 (added §2b Prototype spawn-event schema, added `"bus"` to the `type` enum in both schemas). Backend `src/` code not yet implemented for this design — docs only. | Implement Prototype backend: `routes/ingest.ts` (spawn-event), `routes/stats.ts`, `validation/validateSpawnEvent.ts`, `counters/vehicleCounters.ts`. Also: AI Worker still maps `bus → truck` (`contract.py:27`) — needs updating to actually emit `bus`; Unity needs a `spawn` event handler + bus model |
| 2026-08-12 | Implemented Prototype backend (`server.ts`/`app.ts` split, `controllers/`, `routes/api.ts`, `sockets/unityHandler.ts`, `validation/validateSpawnEvent.ts`, `counters/vehicleCounters.ts` — no DB). Restored reusable config from git history (package.json, tsconfig, eslint, prettier), updated entry point references from `index.ts` → `server.ts`. tsc --noEmit + eslint clean. 21 unit tests pass (15 validator + 6 counters). Smoke tested end-to-end: replayed all 28 events from `events.jsonl` → `/api/stats` totals matched the file exactly (car 5in/13out, truck 0in/2out, motorcycle 7in/1out); confirmed a Socket.io client receives `emit("spawn", ...)` including a `bus`-type event; confirmed an invalid `type` is rejected with HTTP 400 + reason. Old MVP frame-schema files (`index.ts`, `routes/ingest.ts`, `validation/validatePayload.ts`, `db/logger.ts`, `public/index.html`) left deleted from working tree — still recoverable from git history for MVP. | Restore/adapt MVP frame-schema path on top of this structure when position/speed tracking is trustworthy again; fix AI Worker `bus → truck` map (`contract.py:27`); add Unity `spawn` event handler + bus model |
| 2026-08-12 | **Merged `feature/ai-worker` (spawn-event pipeline) + `feature/backend-websocket` (Prototype backend) → new `feature/connect-ai-worker-backend` branch**, resolving conflicts in `docs/data-contract.md` and `docs/project-status.md` (kept the required `speed`/`position.*` Frame schema + separate §2b spawn-event schema; the ai-worker branch's "make Frame fields optional" idea was superseded). Also found and staged an unrelated pre-existing issue: `mock-server/` and `infra/db/init.sql` were deleted from the working tree without `git rm` — confirmed intentional and staged the deletion. **Part B — connected AI Worker to backend**: added `ai-worker/src/poster.py` (`BackendPoster` — sync `httpx.Client`, POSTs to `{backend_url}/api/ingest`, catches all errors and returns `False` instead of raising so a backend outage never stops counting), wired into `main.py` right after `events.emit(event)` reuses the same payload dict — no duplication. Added `send_to_backend`/`backend_url` to `RunConfig`/`config.yaml` (both default off/local). Re-added `httpx>=0.27` to `requirements.txt`. 9 new tests for `poster.py` (via `httpx.MockTransport`, no real network) + 2 new tests for the config fields — 63/63 ai-worker tests pass, ruff + black clean. **Verified against the real backend** (not just mocks): posted a live `bus`-type spawn-event through `BackendPoster` to a running backend instance — `/api/stats` showed `bus.in: 1`; posted an invalid `type` — correctly rejected with HTTP 400 and not counted. Confirms the ai-worker spawn-event schema and the backend's `validateSpawnEvent()` need zero translation between them. Updated `ai-worker/CLAUDE.md` (Roadmap §4 step 3 marked done, §5, §6, §8, file listing, pipeline diagram). | Unity: add a `spawn` Socket.io event handler + `bus` prefab/model (still the only unconnected leg of the pipeline). Set `send_to_backend: true` and run a real video end-to-end. Commit/push `feature/connect-ai-worker-backend`. |
