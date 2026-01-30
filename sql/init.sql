-- ==============================================
-- 여주 센서 모니터링 시스템 데이터베이스 초기화
-- ==============================================
-- 데이터베이스: sensor_yeoju
-- 인코딩: UTF-8
-- 실행: psql -U postgres -d sensor_yeoju -f sql/init.sql

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 1. 기존 테이블 삭제 (주의: 데이터 손실!)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DROP TABLE IF EXISTS heatpump CASCADE;
DROP TABLE IF EXISTS groundpipe CASCADE;
DROP TABLE IF EXISTS elec CASCADE;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 2. 히트펌프 데이터 테이블
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE heatpump (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    input_temp NUMERIC(5,2),
    output_temp NUMERIC(5,2),
    flow NUMERIC(8,2),
    energy NUMERIC(12,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE heatpump IS 'Heatpump sensor data';
COMMENT ON COLUMN heatpump.device_id IS 'Device ID (HP_1, HP_2, HP_3, HP_4)';
COMMENT ON COLUMN heatpump.timestamp IS 'Measurement time';
COMMENT ON COLUMN heatpump.input_temp IS 'Input temperature (Celsius)';
COMMENT ON COLUMN heatpump.output_temp IS 'Output temperature (Celsius)';
COMMENT ON COLUMN heatpump.flow IS 'Flow rate (L/min)';
COMMENT ON COLUMN heatpump.energy IS 'Cumulative energy (kWh)';

CREATE INDEX idx_heatpump_device ON heatpump(device_id);
CREATE INDEX idx_heatpump_timestamp ON heatpump(timestamp DESC);
CREATE INDEX idx_heatpump_device_timestamp ON heatpump(device_id, timestamp DESC);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 3. 지중배관 데이터 테이블
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE groundpipe (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    input_temp NUMERIC(5,2),
    output_temp NUMERIC(5,2),
    flow NUMERIC(8,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE groundpipe IS 'Underground pipe sensor data';
COMMENT ON COLUMN groundpipe.device_id IS 'Device ID (UP_1 ~ UP_10)';
COMMENT ON COLUMN groundpipe.timestamp IS 'Measurement time';
COMMENT ON COLUMN groundpipe.input_temp IS 'Input temperature (Celsius)';
COMMENT ON COLUMN groundpipe.output_temp IS 'Output temperature (Celsius)';
COMMENT ON COLUMN groundpipe.flow IS 'Flow rate (L/min)';

CREATE INDEX idx_groundpipe_device ON groundpipe(device_id);
CREATE INDEX idx_groundpipe_timestamp ON groundpipe(timestamp DESC);
CREATE INDEX idx_groundpipe_device_timestamp ON groundpipe(device_id, timestamp DESC);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 4. 전력량계 데이터 테이블
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE TABLE elec (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    total_energy NUMERIC(12,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE elec IS 'Power meter data';
COMMENT ON COLUMN elec.device_id IS 'Device ID (Total, Heater_1~6, HP_1~4)';
COMMENT ON COLUMN elec.timestamp IS 'Measurement time';
COMMENT ON COLUMN elec.total_energy IS 'Cumulative energy (kWh)';

CREATE INDEX idx_elec_device ON elec(device_id);
CREATE INDEX idx_elec_timestamp ON elec(timestamp DESC);
CREATE INDEX idx_elec_device_timestamp ON elec(device_id, timestamp DESC);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- 5. 완료 메시지
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELECT 
    'Table creation completed' AS message,
    COUNT(*) AS table_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('heatpump', 'groundpipe', 'elec');
