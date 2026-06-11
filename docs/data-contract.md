# Data Contract — Smart Flow

> **⚠️ CRITICAL FILE — Do not modify without team agreement.**
> This schema is shared by AI Worker, Backend, and Unity.
> A breaking change here breaks all 3 modules simultaneously.

> Last reviewed: 2026-06-12
> Schema version: `1.0.0`

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
| `type` | `string` | ✅ | Enum: `"car"` \| `"truck"` \| `"motorcycle"` |
| `speed` | `number` | ✅ | Speed in km/h. Range: `0.0` – `200.0` |
| `position.x` | `number` | ✅ | World space X coordinate (meters). Must be finite |
| `position.y` | `number` | ✅ | Always `0.0` for MVP (ground plane) |
| `position.z` | `number` | ✅ | World space Z coordinate (meters). Must be finite |

---

## 4. Validation Rules

Backend **must reject** (HTTP 400) any payload that violates these rules:

```
REJECT if: timestamp is missing or not a valid ISO 8601 string
REJECT if: cameraId is missing or empty string
REJECT if: vehicles is not an array
REJECT if: any vehicle.position.x or .z is NaN or Infinity
REJECT if: any vehicle.position.y is not 0.0
REJECT if: any vehicle.type is not one of ["car", "truck", "motorcycle"]
REJECT if: any vehicle.speed < 0 or > 200
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

Current version: `1.0.0`

---

## 9. Change Log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-06-12 | initial | Initial schema based on project proposal |

> Before modifying this schema, confirm with all module owners.
> After modifying, bump the version, update the changelog above,
> and update affected module code before merging.