# Smart Flow — Digital Twin for KMITL Smart Mobility

> Senior project — KMITL, Faculty of IT | Team: 2 developers | Phase: MVP (3 months)

Real-time Digital Twin that ingests CCTV footage, detects vehicles with YOLOv8,
and renders their positions in a Unity WebGL scene — second by second.

---

## Architecture (Quick View)

```
CCTV (RTSP)
    │
    ▼
┌─────────────┐   HTTP POST /api/ingest   ┌─────────────┐   WebSocket (emit "frame")   ┌──────────────┐
│  AI Worker  │ ────────────────────────▶ │   Backend   │ ──────────────────────────▶ │    Unity     │
│  (Python)   │                           │  (Node.js)  │                              │   (WebGL)    │
└─────────────┘                           └─────────────┘                              └──────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │ TimescaleDB │
                                          └─────────────┘
```

During development, **Mock Server** replaces AI Worker (same endpoint, same payload).

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | 20 LTS | Backend + Mock Server |
| Python | 3.11 | AI Worker |
| Docker Desktop | latest | TimescaleDB |
| Unity | 2022 LTS | WebGL build |

---

## Quick Start (Development with Mock Server)

### 1. Copy environment files

```bash
cp backend/.env.example backend/.env
cp ai-worker/.env.example ai-worker/.env
# fill in values before continuing
```

### 2. Start TimescaleDB

```bash
docker compose up -d
```

### 3. Start Backend

```bash
cd backend
npm install
npm run dev
# → Listening on http://localhost:3000
```

### 4. Start Mock Server

```bash
cd mock-server
npm install
node generator.js --scenario normal
# → POSTing to http://localhost:3000/api/ingest every 1s
```

### 5. Open Unity

Open the `unity/` folder in Unity 2022 LTS, press Play.
The scene connects to `ws://localhost:3000` and renders incoming vehicles.

---

## Module Overview

| Folder | Language | Role |
|---|---|---|
| `ai-worker/` | Python 3.11 | RTSP capture → YOLOv8 → Homography → POST |
| `backend/` | Node.js 20 | Validate → WebSocket broadcast → DB log |
| `unity/` | C# / Unity | WebSocket client → Object Pool → Lerp render |
| `mock-server/` | Node.js 20 | Simulates AI Worker for dev and demo |
| `docs/` | Markdown | Architecture, data contract, project status |

---

## API Reference

### `POST /api/ingest`
Accepts a JSON payload (see `docs/data-contract.md`).
- `200 OK` — payload accepted and broadcast
- `400 Bad Request` — validation failed (body contains reason)

### `GET /health`
Returns `{ "status": "ok" }`.

### WebSocket
Connect to `ws://localhost:3000`. Listen for event `"frame"` — payload is identical to the ingest body.

---

## Mock Server Scenarios

```bash
node generator.js --scenario normal      # 5 cars, 30–50 km/h
node generator.js --scenario congestion  # 15 cars, 2–15 km/h
node generator.js --scenario edge        # invalid payloads (validation testing)
```

---

## Database (TimescaleDB)

```
Host:     localhost
Port:     5432
Database: smartflow
User:     smartflow
Password: set in .env
```

`docker compose up -d` starts the DB. Schema is initialized automatically from `infra/db/init.sql`.

---

## Environment Variables

| File | Purpose |
|---|---|
| `backend/.env` | Port, DB connection |
| `ai-worker/.env` | RTSP URL, backend URL, model path |

**Never commit `.env` files.**

---

## Docs

| File | Purpose |
|---|---|
| `docs/architecture.md` | System design, tech decisions |
| `docs/data-contract.md` | JSON schema — source of truth for all modules |
| `docs/project-status.md` | Milestones, blockers, session log |
| `CLAUDE.md` | Rules and context for AI assistants |
