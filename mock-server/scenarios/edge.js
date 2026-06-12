const CAMERA_ID = "cam-chalongkrung-01";

// Each payload violates exactly one validation rule from data-contract.md.
// Backend must respond HTTP 400 for every one of these.
const EDGE_PAYLOADS = [
  {
    // Missing cameraId
    label: "missing cameraId",
    payload: {
      timestamp: null, // will be replaced at send time
      frameCount: null,
      vehicles: [
        { trackId: "car-01", type: "car", speed: 40.0, position: { x: 5.0, y: 0.0, z: 10.0 } },
      ],
    },
  },
  {
    // NaN coordinates
    label: "NaN position coordinates",
    payload: {
      timestamp: null,
      cameraId: CAMERA_ID,
      frameCount: null,
      vehicles: [
        { trackId: "car-01", type: "car", speed: 40.0, position: { x: NaN, y: 0.0, z: NaN } },
      ],
    },
  },
  {
    // Speed exceeds 200 km/h
    label: "speed > 200",
    payload: {
      timestamp: null,
      cameraId: CAMERA_ID,
      frameCount: null,
      vehicles: [
        { trackId: "car-01", type: "car", speed: 250.0, position: { x: 5.0, y: 0.0, z: 10.0 } },
      ],
    },
  },
  {
    // vehicles.length > 120
    label: "vehicles.length > 120",
    payload: {
      timestamp: null,
      cameraId: CAMERA_ID,
      frameCount: null,
      vehicles: Array.from({ length: 125 }, (_, i) => ({
        trackId: `car-${String(i + 1).padStart(3, "0")}`,
        type: "car",
        speed: 40.0,
        position: { x: 0.0, y: 0.0, z: 0.0 },
      })),
    },
  },
];

let edgeIndex = 0;

export function generateFrame(frameCount) {
  const entry = EDGE_PAYLOADS[edgeIndex % EDGE_PAYLOADS.length];
  edgeIndex++;

  // Clone so we don't mutate the template; inject live timestamp and frameCount
  const payload = JSON.parse(
    JSON.stringify(entry.payload, (_, v) => (typeof v === "number" && isNaN(v) ? "__NaN__" : v))
  );

  // Restore NaN values that JSON.stringify cannot represent
  function restoreNaN(obj) {
    for (const key of Object.keys(obj)) {
      if (obj[key] === "__NaN__") {
        obj[key] = NaN;
      } else if (typeof obj[key] === "object" && obj[key] !== null) {
        restoreNaN(obj[key]);
      }
    }
  }
  restoreNaN(payload);

  payload.timestamp = new Date().toISOString();
  payload.frameCount = frameCount;

  return { label: entry.label, payload };
}
