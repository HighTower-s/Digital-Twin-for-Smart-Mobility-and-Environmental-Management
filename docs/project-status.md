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

### Backend
- [ ] `POST /api/ingest` — receives payload from AI Worker or Mock Server
- [ ] Validation layer — rejects invalid payloads with HTTP 400
- [ ] WebSocket — broadcasts valid payload via `emit("frame")`
- [ ] TimescaleDB — async log insert (non-blocking)
- [ ] `GET /health` — health check endpoint
- [ ] Unit test for `validatePayload()`

### Unity
- [ ] WebSocket client connects to Backend on startup
- [ ] Receives `frame` event and parses JSON
- [ ] Object Pool initialized (120 car models)
- [ ] Vehicle position updates via `Vector3.Lerp`
- [ ] Vehicles not in latest frame are hidden (not destroyed)
- [ ] WebGL build compiles and runs in Chrome

### Gate: M1 Complete When
- [ ] Mock Server (normal scenario) → Backend → Unity renders cars moving on screen
- [ ] Backend correctly rejects edge scenario payloads (HTTP 400)
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