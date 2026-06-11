# Backend — CLAUDE.md

> Read `../CLAUDE.md` and `../docs/architecture.md` before this file.
> This file covers only Backend-specific context.

---

## What This Module Does

1. Exposes `POST /api/ingest` — receives payload from AI Worker or Mock Server
2. Validates payload against data contract — rejects invalid with HTTP 400
3. Broadcasts valid payload to all Unity clients via Socket.io `emit("frame")`
4. Asynchronously logs each frame to TimescaleDB (non-blocking — never delays broadcast)
5. Exposes `GET /health` for uptime monitoring

---

## Planned Folder Layout

```
backend/
├── CLAUDE.md
├── package.json
├── tsconfig.json
├── .env.example
└── src/
    ├── index.ts                  ← Express + Socket.io setup, server start
    ├── routes/
    │   ├── ingest.ts             ← POST /api/ingest handler
    │   └── health.ts             ← GET /health handler
    ├── validation/
    │   └── validatePayload.ts    ← schema validation (must have unit tests)
    ├── db/
    │   └── logger.ts             ← async TimescaleDB insert
    └── constants.ts              ← named constants
```

---

## Business Rules (from data-contract.md)

```
REJECT if: timestamp missing or not valid ISO 8601
REJECT if: cameraId missing or empty string
REJECT if: vehicles is not an array
REJECT if: any position.x or .z is NaN or Infinity
REJECT if: any position.y is not 0.0
REJECT if: any vehicle.type not in ["car", "truck", "motorcycle"]
REJECT if: any vehicle.speed < 0 or > 200
REJECT if: vehicles.length > 120
```

On rejection: HTTP 400 + reason string. Log warning with reason + raw payload (truncated to 500 chars).

**Never transform the payload** before forwarding to Unity — emit exactly what was received.

---

## Environment Variables (`.env`)

```
PORT=3000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smartflow
DB_USER=smartflow
DB_PASSWORD=...
```

---

## Standards

- TypeScript strict mode — `tsc --noEmit` must pass before committing
- Format: Prettier
- Lint: ESLint — `npm run lint`
- Unit test required for `validatePayload()` — most critical function in this module
