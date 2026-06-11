# Mock Server — CLAUDE.md

> Read `../CLAUDE.md` and `../docs/architecture.md` before this file.
> This file covers only Mock Server-specific context.

---

## What This Module Does

Simulates AI Worker output so Backend and Unity can be developed without a live CCTV feed.
Produces **identical JSON payloads** to the real AI Worker and POSTs them to
`POST /api/ingest` every 1 second. Backend cannot distinguish it from the real AI Worker.

---

## Planned Folder Layout

```
mock-server/
├── CLAUDE.md
├── package.json
├── generator.js         ← main runner: picks scenario, posts every 1s
└── scenarios/
    ├── normal.js        ← 5 cars, 30–50 km/h
    ├── congestion.js    ← 15 cars, 2–15 km/h
    └── edge.js          ← invalid payloads for validation testing
```

---

## Usage

```bash
node generator.js --scenario normal       # default
node generator.js --scenario congestion
node generator.js --scenario edge
```

---

## Scenario Rules

### `normal.js`
- 5 vehicles (`car`, `motorcycle`)
- Speed: 30–50 km/h
- Positions bounce within road boundary (named constants — no inline literals)
- `trackId` stable per vehicle across frames

### `congestion.js`
- 15 vehicles (`car`, `truck`)
- Speed: 2–15 km/h, positions cluster

### `edge.js`
- Sends a mix of intentionally invalid payloads
- Covers: missing `cameraId`, NaN coordinates, speed > 200, `vehicles.length > 120`
- Every POST must return HTTP 400 — do not fix these payloads

---

## Key Rules

- `frameCount` must increment monotonically on every POST; resets to 0 on restart
- `timestamp` must be current UTC: `new Date().toISOString()`
- Road boundary coordinates are named constants — never hardcode inline
- No persistent state between runs

---

## Standards

- Node.js 20 LTS, no TypeScript needed (dev-only tool)
- No external npm dependencies — Node.js built-ins only
