-- TimescaleDB initialization for Smart Flow
-- Runs once on first container start via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS frames (
    time        TIMESTAMPTZ     NOT NULL,
    camera_id   TEXT            NOT NULL,
    frame_count INTEGER         NOT NULL,
    payload     JSONB           NOT NULL
);

SELECT create_hypertable('frames', 'time', if_not_exists => TRUE);
