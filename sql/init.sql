-- ==============================================
-- 여주 센서 모니터링 시스템 데이터베이스 초기화
-- ==============================================
-- Database: sensor_yeoju
-- Encoding: UTF-8
-- Run: psql -U postgres -d sensor_yeoju -f sql/init.sql
-- Note: Existing tables are preserved (CREATE TABLE IF NOT EXISTS)


-- 1. heatpump
CREATE TABLE IF NOT EXISTS heatpump (
    id          BIGSERIAL PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    timestamp   TIMESTAMP    NOT NULL,
    input_temp  NUMERIC(5,1),
    output_temp NUMERIC(5,1),
    flow        INTEGER,
    energy      NUMERIC(12,2),
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  heatpump              IS 'Heatpump sensor data';
COMMENT ON COLUMN heatpump.device_id   IS 'Device ID (HP_1, HP_2, HP_3, HP_4)';
COMMENT ON COLUMN heatpump.timestamp   IS 'Measurement time';
COMMENT ON COLUMN heatpump.input_temp  IS 'Input temperature (Celsius, 1 decimal place)';
COMMENT ON COLUMN heatpump.output_temp IS 'Output temperature (Celsius, 1 decimal place)';
COMMENT ON COLUMN heatpump.flow        IS 'Flow rate (L, integer)';
COMMENT ON COLUMN heatpump.energy      IS 'Cumulative energy (kWh)';

CREATE INDEX IF NOT EXISTS idx_heatpump_device           ON heatpump(device_id);
CREATE INDEX IF NOT EXISTS idx_heatpump_timestamp        ON heatpump(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_heatpump_device_timestamp ON heatpump(device_id, timestamp DESC);


-- 2. groundpipe
CREATE TABLE IF NOT EXISTS groundpipe (
    id          BIGSERIAL PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    timestamp   TIMESTAMP    NOT NULL,
    input_temp  NUMERIC(5,1),
    output_temp NUMERIC(5,1),
    flow        INTEGER,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  groundpipe              IS 'Underground pipe sensor data';
COMMENT ON COLUMN groundpipe.device_id   IS 'Device ID (GP_1 ~ GP_10)';
COMMENT ON COLUMN groundpipe.timestamp   IS 'Measurement time';
COMMENT ON COLUMN groundpipe.input_temp  IS 'Input temperature (Celsius, 1 decimal place)';
COMMENT ON COLUMN groundpipe.output_temp IS 'Output temperature (Celsius, 1 decimal place)';
COMMENT ON COLUMN groundpipe.flow        IS 'Flow rate (L, integer)';

CREATE INDEX IF NOT EXISTS idx_groundpipe_device           ON groundpipe(device_id);
CREATE INDEX IF NOT EXISTS idx_groundpipe_timestamp        ON groundpipe(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_groundpipe_device_timestamp ON groundpipe(device_id, timestamp DESC);


-- 3. elec
CREATE TABLE IF NOT EXISTS elec (
    id           BIGSERIAL PRIMARY KEY,
    device_id    VARCHAR(50)  NOT NULL,
    timestamp    TIMESTAMP    NOT NULL,
    total_energy NUMERIC(12,2),
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  elec                IS 'Power meter data';
COMMENT ON COLUMN elec.device_id     IS 'Device ID (Total, Heater_1~6, HP_1~4)';
COMMENT ON COLUMN elec.timestamp     IS 'Measurement time';
COMMENT ON COLUMN elec.total_energy  IS 'Cumulative energy (kWh)';

CREATE INDEX IF NOT EXISTS idx_elec_device           ON elec(device_id);
CREATE INDEX IF NOT EXISTS idx_elec_timestamp        ON elec(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_elec_device_timestamp ON elec(device_id, timestamp DESC);


-- 4. remote_send_queue (Yeoju PC only)
CREATE TABLE IF NOT EXISTS remote_send_queue (
    id          BIGSERIAL PRIMARY KEY,
    table_name  VARCHAR(50)  NOT NULL,
    payload     JSONB        NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retry_count INT          NOT NULL DEFAULT 0,
    last_tried  TIMESTAMP
);

COMMENT ON TABLE remote_send_queue IS 'Remote DB retry queue (Yeoju PC only)';

CREATE INDEX IF NOT EXISTS idx_queue_created ON remote_send_queue(created_at ASC);
CREATE INDEX IF NOT EXISTS idx_queue_retry   ON remote_send_queue(retry_count ASC);


-- 5. result
SELECT
    'Table creation completed' AS message,
    COUNT(*) AS table_count
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('heatpump', 'groundpipe', 'elec', 'remote_send_queue');