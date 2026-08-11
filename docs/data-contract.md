# Data Contract — Smart Flow

> **⚠️ CRITICAL FILE — Do not modify without team agreement.**
> This schema is shared by AI Worker, Backend, and Unity.
> A breaking change here breaks all 3 modules simultaneously.

> Last reviewed: 2026-08-10
> Schema version: `1.1.0`

---

## 1. Overview

This file defines the **single JSON structure** used for all communication between:

- `AI Worker → Backend` (HTTP POST)
- `Mock Server → Backend` (HTTP POST)
- `Backend → Unity` (WebSocket emit)

All three use **identical payload format**. Backend must not transform the
payload before forwarding it to Unity.

---

## 2. Canonical Schema

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
| `speed` | `number` | ❌ (optional) | Speed in km/h. Range: `0.0` – `200.0` if present. Omit when not measured |
| `position.x` | `number` | ❌ (optional) | World space X coordinate (meters). Must be finite if present |
| `position.y` | `number` | ❌ (optional) | Always `0.0` for MVP (ground plane) if present |
| `position.z` | `number` | ❌ (optional) | World space Z coordinate (meters). Must be finite if present |

> ⚠️ **`position` เป็น optional ตั้งแต่ v1.1.0 แต่ยังไม่มีโค้ดรองรับ** — Unity ใช้ `position`
> วางตำแหน่งรถใน 3D ตรง ๆ ถ้า payload ไม่มี `position` ต้องตัดสินใจก่อนว่า Unity/Backend
> จะจัดการยังไง (ไม่วาด? วางที่ default?) — **ห้ามส่ง payload ที่ไม่มี `position` เข้า backend
> จริงจนกว่าจะออกแบบ+implement โค้ดรองรับเคสนี้เสร็จ** เอกสารนี้แก้ไว้ล่วงหน้าเพื่อเตรียม
> โครงร่างเท่านั้น (ดู `ai-worker/CLAUDE.md` §4 Roadmap ขั้น 3)

---

## 4. Validation Rules

Backend **must reject** (HTTP 400) any payload that violates these rules:

```
REJECT if: timestamp is missing or not a valid ISO 8601 string
REJECT if: cameraId is missing or empty string
REJECT if: vehicles is not an array
REJECT if: vehicle.position is present and (.x or .z) is NaN or Infinity
REJECT if: vehicle.position is present and .y is not 0.0
REJECT if: any vehicle.type is not one of ["car", "truck", "motorcycle", "bus"]
REJECT if: vehicle.speed is present and (< 0 or > 200)
REJECT if: vehicles.length > 120
```

Payload passes validation silently. Failed validation logs a warning with
the rejection reason and the raw payload (truncated to 500 chars).

---

## 5. Coordinate System

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

### Bus type, no speed/position (v1.1.0 — count-only payload)
```json
{
  "timestamp": "2026-08-10T09:15:55.000Z",
  "cameraId": "cam-chalongkrung-01",
  "frameCount": 1271,
  "vehicles": [
    { "trackId": "bus-0042", "type": "bus" }
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
| 1.1.0 | 2026-08-10 | ai-worker prototype | Added `"bus"` to `type` enum. Made `speed` and `position.*` optional (AI Worker's line-counting prototype has neither yet — see `ai-worker/CLAUDE.md` §5). **Docs-only change — Backend validation and Unity `VehiclePool.cs` do NOT yet implement these rules.** Do not send bus-typed or position-less payloads to a real backend until that code exists. |

> Before modifying this schema, confirm with all module owners.
> After modifying, bump the version, update the changelog above,
> and update affected module code before merging.