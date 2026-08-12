# Data Contract — Smart Flow

> **⚠️ CRITICAL FILE — Do not modify without team agreement.**
> This schema is shared by AI Worker, Backend, and Unity.
> A breaking change here breaks all 3 modules simultaneously.

> Last reviewed: 2026-08-12
> Schema version: `1.1.0`

---

## 1. Overview

This file defines the JSON structures used for all communication between:

- `AI Worker → Backend` (HTTP POST)
- `Mock Server → Backend` (HTTP POST)
- `Backend → Unity` (WebSocket emit)

The project has **two schemas**, one per project phase — see `../backend/CLAUDE.md`
for the full phase breakdown:

- **§2 Frame schema (MVP)** — full payload with `vehicles[]`, `position`, `speed`.
  This was the original schema and remains canonical for MVP.
- **§2b Spawn-event schema (Prototype, current)** — one event per vehicle crossing
  the camera line, no position/speed. This is what AI Worker emits today (see
  `ai-worker/data/output_results/events.jsonl`).

All producers/consumers within a phase use **identical payload format**. Backend
must not transform the payload before forwarding it to Unity.

---

## 2. Canonical Schema (MVP — Frame)

```json
{
  "timestamp": "2026-06-12T08:15:55.000Z",
  "cameraId":  "cam-chalongkrung-01",
  "frameCount": 1450,
  "vehicles": [
    {
      "trackId":  "car-01",
      "type":     "car",
      "speed":    45.5,
      "position": {
        "x":  12.5,
        "y":  0.0,
        "z": -45.2
      }
    }
  ]
}
```

---

## 3. Field Reference

### Root fields

| Field | Type | Required | Description |
|---|---|---|---|
| `timestamp` | `string` (ISO 8601) | ✅ | UTC time when frame was captured |
| `cameraId` | `string` | ✅ | Unique camera identifier |
| `frameCount` | `integer` | ✅ | Monotonically increasing frame number (resets on restart) |
| `vehicles` | `array` | ✅ | List of detected vehicles. May be empty `[]` if no vehicles detected |

### Vehicle object

| Field | Type | Required | Constraints |
|---|---|---|---|
| `trackId` | `string` | ✅ | Stable across frames for the same vehicle. Format: `"car-01"`, `"truck-03"` |
| `type` | `string` | ✅ | Enum: `"car"` \| `"truck"` \| `"motorcycle"` \| `"bus"` |
| `speed` | `number` | ✅ | Speed in km/h. Range: `0.0` – `200.0` |
| `position.x` | `number` | ✅ | World space X coordinate (meters). Must be finite |
| `position.y` | `number` | ✅ | Always `0.0` for MVP (ground plane) |
| `position.z` | `number` | ✅ | World space Z coordinate (meters). Must be finite |

---

## 2b. Prototype Schema (Spawn-event) — Current

Used while position/speed tracking (homography) is unreliable — see
`docs/project-status.md` (2026-07-21 entry) for why the pipeline pivoted here.
One event per vehicle, fired when it crosses the camera's counting line.

### Example

```json
{
  "schema": "spawn-event/0.2-draft",
  "timestamp": "2026-08-10T15:42:47.671Z",
  "cameraId": "cam-chalongkrung-01",
  "videoTimeSec": 2.398891,
  "frameCount": 72,
  "trackId": "car-0025",
  "type": "car",
  "direction": "out",
  "confidence": 0.757
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `schema` | `string` | ✅ | Schema tag, e.g. `"spawn-event/0.2-draft"` |
| `timestamp` | `string` (ISO 8601) | ✅ | UTC time the event was emitted |
| `cameraId` | `string` | ✅ | Unique camera identifier |
| `videoTimeSec` | `number` | — | Seconds into the source video (upload-based detection) |
| `frameCount` | `integer` | — | Video frame index at detection time |
| `trackId` | `string` | ✅ | Tracker ID of the vehicle, e.g. `"car-0025"` |
| `type` | `string` | ✅ | Enum: `"car"` \| `"truck"` \| `"motorcycle"` \| `"bus"` |
| `direction` | `string` | ✅ | Enum: `"in"` \| `"out"` — direction of travel relative to camera |
| `confidence` | `number` | ✅ | Detection confidence, range `0.0` – `1.0` |

No `position` or `speed` fields exist in this schema — Prototype only counts
vehicles by `type` and `direction`.

---

## 4. Validation Rules

### Frame schema (MVP)

Backend **must reject** (HTTP 400) any payload that violates these rules:

```
REJECT if: timestamp is missing or not a valid ISO 8601 string
REJECT if: cameraId is missing or empty string
REJECT if: vehicles is not an array
REJECT if: any vehicle.position.x or .z is NaN or Infinity
REJECT if: any vehicle.position.y is not 0.0
REJECT if: any vehicle.type is not one of ["car", "truck", "motorcycle", "bus"]
REJECT if: any vehicle.speed < 0 or > 200
REJECT if: vehicles.length > 120
```

### Spawn-event schema (Prototype)

Backend **must reject** (HTTP 400) any payload that violates these rules:

```
REJECT if: timestamp is missing or not a valid ISO 8601 string
REJECT if: cameraId is missing or empty string
REJECT if: trackId is missing or empty string
REJECT if: type is not one of ["car", "truck", "motorcycle", "bus"]
REJECT if: direction is not one of ["in", "out"]
REJECT if: confidence is not a number in range [0.0, 1.0]
REJECT if: videoTimeSec or frameCount is present but negative or not finite
```

Payload passes validation silently. Failed validation logs a warning with
the rejection reason and the raw payload (truncated to 500 chars).

---

## 5. Coordinate System (MVP — Frame schema only)

```
       Z+
       │
       │    (road ahead)
       │
───────┼──────── X+
       │
       │
    Camera
```

- Origin `(0, 0, 0)` = calibration reference point on Chalong Krung Road
- **X axis**: horizontal across the road (positive = right)
- **Y axis**: vertical (always 0.0 for ground-level vehicles in MVP)
- **Z axis**: along the road (positive = away from camera)
- Units: **meters**

---

## 6. Known `cameraId` Values

| cameraId | Location | Status |
|---|---|---|
| `cam-chalongkrung-01` | Chalong Krung Rd — railway crossing viewpoint | Active (MVP) |

---

## 7. Example Payloads

### Normal traffic (3 vehicles)
```json
{
  "timestamp": "2026-06-12T08:15:55.000Z",
  "cameraId": "cam-chalongkrung-01",
  "frameCount": 1450,
  "vehicles": [
    { "trackId": "car-01", "type": "car",        "speed": 45.5, "position": { "x":  12.5, "y": 0.0, "z": -45.2 } },
    { "trackId": "car-02", "type": "car",        "speed": 38.0, "position": { "x":  -3.2, "y": 0.0, "z":  12.8 } },
    { "trackId": "car-03", "type": "motorcycle", "speed": 52.1, "position": { "x":   8.0, "y": 0.0, "z":  30.0 } }
  ]
}
```

### Bus type (v1.1.0)
```json
{
  "timestamp": "2026-08-10T09:15:55.000Z",
  "cameraId": "cam-chalongkrung-01",
  "frameCount": 1271,
  "vehicles": [
    { "trackId": "bus-0042", "type": "bus", "speed": 34.2, "position": { "x": 5.1, "y": 0.0, "z": 60.4 } }
  ]
}
```

### Empty frame (no vehicles detected)
```json
{
  "timestamp": "2026-06-12T08:16:01.000Z",
  "cameraId": "cam-chalongkrung-01",
  "frameCount": 1451,
  "vehicles": []
}
```

### Invalid payload (backend will reject with HTTP 400)
```json
{
  "timestamp": "2026-06-12T08:16:02.000Z",
  "cameraId": "cam-chalongkrung-01",
  "frameCount": 1452,
  "vehicles": [
    { "trackId": "car-01", "type": "car", "speed": 40.0, "position": { "x": null, "y": 0.0, "z": NaN } }
  ]
}
```

---

## 8. Versioning Policy

- This schema uses **Semantic Versioning**: `MAJOR.MINOR.PATCH`
- **MAJOR** bump = breaking change (field removed, type changed, rename) → requires update in all 3 modules
- **MINOR** bump = new optional field added → backwards compatible
- **PATCH** bump = description / comment clarification only

Current version: `1.1.0`

---

## 9. Change Log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-06-12 | initial | Initial schema based on project proposal |
| 1.1.0 | 2026-08-12 | backend redesign | Added §2b Prototype spawn-event schema; added `"bus"` to the `type` enum in both schemas |

> Before modifying this schema, confirm with all module owners.
> After modifying, bump the version, update the changelog above,
> and update affected module code before merging.