export const VEHICLE_TYPES = ['car', 'truck', 'motorcycle', 'bus'] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];

export const DIRECTIONS = ['in', 'out'] as const;
export type Direction = (typeof DIRECTIONS)[number];

export const LOG_TRUNCATE = 500;
