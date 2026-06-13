import { validatePayload } from './validatePayload';

const validPayload = {
  timestamp: '2026-06-12T08:15:55.000Z',
  cameraId: 'cam-chalongkrung-01',
  frameCount: 1450,
  vehicles: [
    { trackId: 'car-01', type: 'car', speed: 45.5, position: { x: 12.5, y: 0.0, z: -45.2 } },
  ],
};

function withOverride(overrides: Record<string, unknown>) {
  return { ...validPayload, ...overrides };
}

describe('validatePayload', () => {
  describe('valid payloads', () => {
    it('accepts a well-formed payload', () => {
      expect(validatePayload(validPayload)).toEqual({ valid: true });
    });

    it('accepts an empty vehicles array', () => {
      expect(validatePayload(withOverride({ vehicles: [] }))).toEqual({ valid: true });
    });

    it('accepts all vehicle types', () => {
      for (const type of ['car', 'truck', 'motorcycle']) {
        const payload = withOverride({
          vehicles: [{ trackId: 'v-01', type, speed: 30, position: { x: 0, y: 0.0, z: 0 } }],
        });
        expect(validatePayload(payload)).toEqual({ valid: true });
      }
    });

    it('accepts speed at boundary values (0 and 200)', () => {
      for (const speed of [0, 200]) {
        const payload = withOverride({
          vehicles: [{ trackId: 'v-01', type: 'car', speed, position: { x: 0, y: 0.0, z: 0 } }],
        });
        expect(validatePayload(payload)).toEqual({ valid: true });
      }
    });

    it('accepts exactly 120 vehicles', () => {
      const vehicles = Array.from({ length: 120 }, (_, i) => ({
        trackId: `car-${i}`, type: 'car', speed: 30, position: { x: 0, y: 0.0, z: 0 },
      }));
      expect(validatePayload(withOverride({ vehicles }))).toEqual({ valid: true });
    });
  });

  describe('timestamp validation', () => {
    it('rejects missing timestamp', () => {
      const { timestamp: _t, ...payload } = validPayload;
      const result = validatePayload(payload);
      expect(result.valid).toBe(false);
    });

    it('rejects non-ISO timestamp', () => {
      const result = validatePayload(withOverride({ timestamp: 'not-a-date' }));
      expect(result.valid).toBe(false);
    });
  });

  describe('cameraId validation', () => {
    it('rejects missing cameraId', () => {
      const { cameraId: _c, ...payload } = validPayload;
      expect(validatePayload(payload).valid).toBe(false);
    });

    it('rejects empty cameraId', () => {
      expect(validatePayload(withOverride({ cameraId: '' })).valid).toBe(false);
    });

    it('rejects whitespace-only cameraId', () => {
      expect(validatePayload(withOverride({ cameraId: '   ' })).valid).toBe(false);
    });
  });

  describe('vehicles array validation', () => {
    it('rejects non-array vehicles', () => {
      expect(validatePayload(withOverride({ vehicles: null })).valid).toBe(false);
      expect(validatePayload(withOverride({ vehicles: 'bad' })).valid).toBe(false);
    });

    it('rejects more than 120 vehicles', () => {
      const vehicles = Array.from({ length: 121 }, (_, i) => ({
        trackId: `car-${i}`, type: 'car', speed: 30, position: { x: 0, y: 0.0, z: 0 },
      }));
      expect(validatePayload(withOverride({ vehicles })).valid).toBe(false);
    });
  });

  describe('vehicle field validation', () => {
    function vehicle(overrides: Record<string, unknown>) {
      return withOverride({
        vehicles: [{ trackId: 'v-01', type: 'car', speed: 30, position: { x: 0, y: 0.0, z: 0 }, ...overrides }],
      });
    }

    it('rejects unknown vehicle type', () => {
      expect(validatePayload(vehicle({ type: 'bus' })).valid).toBe(false);
    });

    it('rejects negative speed', () => {
      expect(validatePayload(vehicle({ speed: -1 })).valid).toBe(false);
    });

    it('rejects speed above 200', () => {
      expect(validatePayload(vehicle({ speed: 201 })).valid).toBe(false);
    });

    it('rejects position.x as NaN', () => {
      expect(validatePayload(vehicle({ position: { x: NaN, y: 0.0, z: 0 } })).valid).toBe(false);
    });

    it('rejects position.x as Infinity', () => {
      expect(validatePayload(vehicle({ position: { x: Infinity, y: 0.0, z: 0 } })).valid).toBe(false);
    });

    it('rejects position.z as NaN', () => {
      expect(validatePayload(vehicle({ position: { x: 0, y: 0.0, z: NaN } })).valid).toBe(false);
    });

    it('rejects position.y !== 0.0', () => {
      expect(validatePayload(vehicle({ position: { x: 0, y: 1.0, z: 0 } })).valid).toBe(false);
    });
  });

  describe('non-object input', () => {
    it('rejects null', () => expect(validatePayload(null).valid).toBe(false));
    it('rejects a string', () => expect(validatePayload('hello').valid).toBe(false));
    it('rejects a number', () => expect(validatePayload(42).valid).toBe(false));
  });
});
