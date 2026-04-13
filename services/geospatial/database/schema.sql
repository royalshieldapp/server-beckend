-- Royal Shield Risk Prediction Engine - Database Schema
-- PostGIS Extension for geospatial operations
-- Author: Royal Shield Development Team
-- Version: 1.0.0

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- For advanced indexing

-- Vector extension for embeddings (requires pgvector)
-- Install with: CREATE EXTENSION vector;
-- Note: Requires pgvector to be installed on PostgreSQL
-- CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- CUSTOM TYPES
-- =============================================================================

CREATE TYPE risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE event_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE data_source AS ENUM ('FBI', 'MIAMI_OPEN_DATA', 'NASA_FIRMS', 'NOAA', 'REDDIT', 'NEWS_API', 'TWITTER', 'USER_REPORT', 'OSM');
CREATE TYPE hotspot_type AS ENUM ('CRIME', 'ENVIRONMENTAL', 'COMPOSITE');
CREATE TYPE camera_protocol AS ENUM ('RTSP', 'ONVIF', 'HTTP', 'HTTPS');
CREATE TYPE activity_type AS ENUM ('MOTION', 'PERSON_DETECTED', 'VEHICLE_DETECTED', 'ANOMALY', 'ALERT');

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- -------------------------
-- Risk Zones (H3 Hexagonal Grid)
-- -------------------------
CREATE TABLE IF NOT EXISTS risk_zones (
    id SERIAL PRIMARY KEY,
    h3_index VARCHAR(15) UNIQUE NOT NULL,
    resolution INT NOT NULL CHECK (resolution BETWEEN 0 AND 15),
    geometry GEOGRAPHY(POLYGON, 4326) NOT NULL,
    
    -- Risk metrics
    risk_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 10),
    risk_level risk_level NOT NULL DEFAULT 'LOW',
    
    -- Density metrics
    crime_density NUMERIC(10,2) DEFAULT 0,
    poi_density NUMERIC(10,2) DEFAULT 0,
    population_estimate NUMERIC(10,0) DEFAULT 0,
    environmental_risk NUMERIC(5,2) DEFAULT 0,
    
    -- Metadata
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_h3_index CHECK (LENGTH(h3_index) = 15)
);

CREATE INDEX idx_risk_zones_h3 ON risk_zones (h3_index);
CREATE INDEX idx_risk_zones_geom ON risk_zones USING GIST (geometry);
CREATE INDEX idx_risk_zones_risk_score ON risk_zones (risk_score DESC);
CREATE INDEX idx_risk_zones_risk_level ON risk_zones (risk_level);
CREATE INDEX idx_risk_zones_resolution ON risk_zones (resolution);

COMMENT ON TABLE risk_zones IS 'Hexagonal risk zones using H3 spatial indexing';
COMMENT ON COLUMN risk_zones.h3_index IS 'Uber H3 hexagonal index (15 characters)';
COMMENT ON COLUMN risk_zones.risk_score IS 'Composite risk score from 0 (safe) to 10 (dangerous)';

-- -------------------------
-- Crime Events
-- -------------------------
CREATE TABLE IF NOT EXISTS crime_events (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE,
    source data_source NOT NULL,
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50),  -- VIOLENT, PROPERTY, DRUG, etc.
    severity event_severity NOT NULL DEFAULT 'MEDIUM',
    
    -- Location
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    h3_zone VARCHAR(15),
    address TEXT,
    
    -- Temporal
    occurred_at TIMESTAMP NOT NULL,
    reported_at TIMESTAMP,
    
    -- Details
    description TEXT,
    victim_count INT DEFAULT 0,
    raw_data JSONB,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE SET NULL
);

CREATE INDEX idx_crime_location ON crime_events USING GIST (location);
CREATE INDEX idx_crime_h3 ON crime_events (h3_zone);
CREATE INDEX idx_crime_occurred ON crime_events (occurred_at DESC);
CREATE INDEX idx_crime_type ON crime_events (event_type);
CREATE INDEX idx_crime_category ON crime_events (event_category);
CREATE INDEX idx_crime_severity ON crime_events (severity);
CREATE INDEX idx_crime_source ON crime_events (source);

COMMENT ON TABLE crime_events IS 'Crime incidents from FBI, Miami-Dade, and other sources';

-- -------------------------
-- Environmental Events
-- -------------------------
CREATE TABLE IF NOT EXISTS environmental_events (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE,
    source data_source NOT NULL,
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,  -- FIRE, HURRICANE, FLOOD, EARTHQUAKE
    event_category VARCHAR(50),
    severity event_severity NOT NULL DEFAULT 'MEDIUM',
    
    -- Location (can be point or polygon)
    location GEOGRAPHY(POINT, 4326),
    affected_area GEOGRAPHY(POLYGON, 4326),
    h3_zone VARCHAR(15),
    
    -- Temporal
    occurred_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    
    -- Details
    description TEXT,
    intensity NUMERIC(10,2),  -- Fire temperature, wind speed, etc.
    metadata JSONB,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE SET NULL
);

CREATE INDEX idx_env_location ON environmental_events USING GIST (location);
CREATE INDEX idx_env_area ON environmental_events USING GIST (affected_area);
CREATE INDEX idx_env_h3 ON environmental_events (h3_zone);
CREATE INDEX idx_env_occurred ON environmental_events (occurred_at DESC);
CREATE INDEX idx_env_type ON environmental_events (event_type);
CREATE INDEX idx_env_severity ON environmental_events (severity);

COMMENT ON TABLE environmental_events IS 'Environmental hazards from NASA FIRMS, NOAA, USGS';

-- -------------------------
-- Points of Interest (POI)
-- -------------------------
CREATE TABLE IF NOT EXISTS poi_data (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    
    -- POI classification
    category VARCHAR(100) NOT NULL,  -- SCHOOL, HOSPITAL, BAR, ATM, POLICE, etc.
    subcategory VARCHAR(100),
    name VARCHAR(255),
    
    -- Location
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    h3_zone VARCHAR(15),
    address TEXT,
    
    -- Risk factor (based on POI type)
    risk_factor NUMERIC(3,2) DEFAULT 1.0 CHECK (risk_factor >= 0 AND risk_factor <= 5),
    
    -- OSM tags
    tags JSONB,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE SET NULL
);

CREATE INDEX idx_poi_location ON poi_data USING GIST (location);
CREATE INDEX idx_poi_h3 ON poi_data (h3_zone);
CREATE INDEX idx_poi_category ON poi_data (category);
CREATE INDEX idx_poi_risk_factor ON poi_data (risk_factor DESC);

COMMENT ON TABLE poi_data IS 'Points of Interest from OpenStreetMap';
COMMENT ON COLUMN poi_data.risk_factor IS 'Risk weight (high crime areas near bars get higher factor)';

-- -------------------------
-- User Community Reports
-- -------------------------
CREATE TABLE IF NOT EXISTS user_reports (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,  -- Firebase UID
    
    -- Report details
    report_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    severity event_severity DEFAULT 'LOW',
    
    -- Location
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    h3_zone VARCHAR(15),
    
    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(255),
    verified_at TIMESTAMP,
    
    -- Temporal
    reported_at TIMESTAMP NOT NULL DEFAULT NOW(),
    incident_occurred_at TIMESTAMP,
    
    -- Attachments (metadata only, files stored separately)
    media_urls TEXT[],
    
    -- Vector embedding for semantic search (384 dimensions for all-MiniLM-L6-v2)
    -- embedding_vector VECTOR(384),
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE SET NULL
);

CREATE INDEX idx_reports_location ON user_reports USING GIST (location);
CREATE INDEX idx_reports_h3 ON user_reports (h3_zone);
CREATE INDEX idx_reports_user ON user_reports (user_id);
CREATE INDEX idx_reports_verified ON user_reports (verified);
CREATE INDEX idx_reports_reported_at ON user_reports (reported_at DESC);
CREATE INDEX idx_reports_description_trgm ON user_reports USING GIN (description gin_trgm_ops);

-- Vector index (enable when pgvector is installed)
-- CREATE INDEX idx_reports_embedding ON user_reports USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE user_reports IS 'Community-submitted incident reports';

-- =============================================================================
-- ML/AI TABLES
-- =============================================================================

-- -------------------------
-- Hotspots (Clustering Results)
-- -------------------------
CREATE TABLE IF NOT EXISTS hotspots (
    id SERIAL PRIMARY KEY,
    cluster_id INT NOT NULL,
    
    -- Location
    center_location GEOGRAPHY(POINT, 4326) NOT NULL,
    boundary GEOGRAPHY(POLYGON, 4326),
    h3_zones TEXT[],  -- Array of H3 indexes in this hotspot
    
    -- Classification
    hotspot_type hotspot_type NOT NULL DEFAULT 'CRIME',
    severity event_severity NOT NULL DEFAULT 'MEDIUM',
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Statistics
    event_count INT NOT NULL DEFAULT 0,
    avg_severity NUMERIC(3,2),
    
    -- Temporal validity
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Model metadata
    model_version VARCHAR(50),
    model_params JSONB,
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hotspots_location ON hotspots USING GIST (center_location);
CREATE INDEX idx_hotspots_boundary ON hotspots USING GIST (boundary);
CREATE INDEX idx_hotspots_detected ON hotspots (detected_at DESC);
CREATE INDEX idx_hotspots_type ON hotspots (hotspot_type);
CREATE INDEX idx_hotspots_active ON hotspots (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_hotspots_h3_zones ON hotspots USING GIN (h3_zones);

COMMENT ON TABLE hotspots IS 'ML-detected crime and environmental hotspots using DBSCAN/K-means';

-- -------------------------
-- Risk Predictions
-- -------------------------
CREATE TABLE IF NOT EXISTS risk_predictions (
    id SERIAL PRIMARY KEY,
    h3_zone VARCHAR(15) NOT NULL,
    
    -- Prediction
    prediction_date DATE NOT NULL,
    predicted_risk_score NUMERIC(5,2) NOT NULL CHECK (predicted_risk_score >= 0 AND predicted_risk_score <= 10),
    predicted_risk_level risk_level NOT NULL,
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Feature contributions (for explainability)
    contributing_factors JSONB,
    
    -- Model info
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,  -- XGBOOST, LIGHTGBM, etc.
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE (h3_zone, prediction_date),
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE CASCADE
);

CREATE INDEX idx_predictions_zone_date ON risk_predictions (h3_zone, prediction_date);
CREATE INDEX idx_predictions_date ON risk_predictions (prediction_date);
CREATE INDEX idx_predictions_score ON risk_predictions (predicted_risk_score DESC);

COMMENT ON TABLE risk_predictions IS 'Future risk predictions from XGBoost/LightGBM models';

-- -------------------------
-- Zone Embeddings (for semantic search)
-- -------------------------
CREATE TABLE IF NOT EXISTS zone_embeddings (
    id SERIAL PRIMARY KEY,
    h3_zone VARCHAR(15) UNIQUE NOT NULL,
    
    -- Vector embedding (384 dimensions for all-MiniLM-L6-v2)
    -- embedding_vector VECTOR(384) NOT NULL,
    
    -- Feature summary used for embedding
    features JSONB,
    
    -- Timestamps
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE CASCADE
);

-- Vector index (enable when pgvector is installed)
-- CREATE INDEX idx_zone_embeddings ON zone_embeddings USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_zone_embeddings_h3 ON zone_embeddings (h3_zone);

COMMENT ON TABLE zone_embeddings IS 'Vector embeddings for semantic zone search';

-- =============================================================================
-- CAMERA INTEGRATION TABLES
-- =============================================================================

-- -------------------------
-- Camera Configurations
-- -------------------------
CREATE TABLE IF NOT EXISTS camera_configs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    
    -- Camera info
    camera_name VARCHAR(255) NOT NULL,
    camera_model VARCHAR(100),
    protocol camera_protocol NOT NULL DEFAULT 'RTSP',
    
    -- Location
    location GEOGRAPHY(POINT, 4326),
    h3_zone VARCHAR(15),
    coverage_radius INT DEFAULT 100,  -- meters
    
    -- Connection (encrypted at application level)
    rtsp_url TEXT NOT NULL,
    username TEXT,
    password_encrypted TEXT,
    
    -- Settings
    enabled BOOLEAN DEFAULT TRUE,
    recording_enabled BOOLEAN DEFAULT FALSE,  -- Privacy: disabled by default
    detection_sensitivity NUMERIC(3,2) DEFAULT 0.7,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_online TIMESTAMP,
    
    FOREIGN KEY (h3_zone) REFERENCES risk_zones(h3_index) ON DELETE SET NULL
);

CREATE INDEX idx_cameras_user ON camera_configs (user_id);
CREATE INDEX idx_cameras_location ON camera_configs USING GIST (location);
CREATE INDEX idx_cameras_enabled ON camera_configs (enabled) WHERE enabled = TRUE;

COMMENT ON TABLE camera_configs IS 'User-configured IP cameras (RTSP/ONVIF)';
COMMENT ON COLUMN camera_configs.password_encrypted IS 'Encrypted camera password, never store plaintext';

-- -------------------------
-- Camera Activity Logs
-- -------------------------
CREATE TABLE IF NOT EXISTS camera_activity (
    id SERIAL PRIMARY KEY,
    camera_id INT NOT NULL,
    
    -- Activity details
    activity_type activity_type NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    confidence NUMERIC(5,4),
    
    -- Detection metadata (NO video/image data stored)
    object_count INT DEFAULT 0,
    bounding_boxes JSONB,  -- Coordinates only
    metadata JSONB,
    
    -- Alert
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_sent_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (camera_id) REFERENCES camera_configs(id) ON DELETE CASCADE
);

CREATE INDEX idx_activity_camera ON camera_activity (camera_id, detected_at DESC);
CREATE INDEX idx_activity_detected ON camera_activity (detected_at DESC);
CREATE INDEX idx_activity_type ON camera_activity (activity_type);
CREATE INDEX idx_activity_alert ON camera_activity (alert_sent) WHERE alert_sent = FALSE;

COMMENT ON TABLE camera_activity IS 'Camera activity logs (metadata only, NO raw video)';
COMMENT ON LINE camera_activity.bounding_boxes IS 'Object bounding boxes for person/vehicle detection (privacy-compliant)';

-- =============================================================================
-- HELPER TABLES
-- =============================================================================

-- -------------------------
-- Data Collection Logs
-- -------------------------
CREATE TABLE IF NOT EXISTS data_collection_logs (
    id SERIAL PRIMARY KEY,
    source data_source NOT NULL,
    collection_type VARCHAR(50) NOT NULL,  -- SCHEDULED, MANUAL, BACKFILL
    
    -- Statistics
    records_fetched INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    
    -- Status
    status VARCHAR(20) NOT NULL,  -- SUCCESS, PARTIAL, FAILED
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INT,
    
    -- Metadata
    params JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_collection_logs_source ON data_collection_logs (source, started_at DESC);
CREATE INDEX idx_collection_logs_status ON data_collection_logs (status);

COMMENT ON TABLE data_collection_logs IS 'Audit log for data collection jobs';

-- -------------------------
-- Model Training History
-- -------------------------
CREATE TABLE IF NOT EXISTS model_training_history (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    
    -- Training data
    training_start_date DATE NOT NULL,
    training_end_date DATE NOT NULL,
    sample_count INT NOT NULL,
    
    -- Metrics
    metrics JSONB,  -- Accuracy, precision, recall, MAE, etc.
    
    -- Model artifacts
    model_path TEXT,
    hyperparameters JSONB,
    
    -- Status
    status VARCHAR(20) NOT NULL,  -- TRAINING, COMPLETED, FAILED, DEPLOYED
    
    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INT,
    
    -- Metadata
    created_by VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_logs_model ON model_training_history (model_name, model_version);
CREATE INDEX idx_training_logs_status ON model_training_history (status);
CREATE INDEX idx_training_logs_started ON model_training_history (started_at DESC);

COMMENT ON TABLE model_training_history IS 'ML model training history and performance metrics';

-- =============================================================================
-- MATERIALIZED VIEWS (for performance)
-- =============================================================================

-- Current risk summary by zone (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_zone_risk_summary AS
SELECT 
    rz.h3_index,
    rz.risk_score,
    rz.risk_level,
    COUNT(DISTINCT ce.id) AS crime_count_30d,
    COUNT(DISTINCT ee.id) AS env_event_count_30d,
    COUNT(DISTINCT ur.id) AS user_report_count_30d,
    MAX(ce.occurred_at) AS last_crime_date,
    MAX(ee.occurred_at) AS last_env_event_date
FROM risk_zones rz
LEFT JOIN crime_events ce ON ce.h3_zone = rz.h3_index AND ce.occurred_at > NOW() - INTERVAL '30 days'
LEFT JOIN environmental_events ee ON ee.h3_zone = rz.h3_index AND ee.occurred_at > NOW() - INTERVAL '30 days'
LEFT JOIN user_reports ur ON ur.h3_zone = rz.h3_index AND ur.reported_at > NOW() - INTERVAL '30 days'
GROUP BY rz.h3_index, rz.risk_score, rz.risk_level;

CREATE UNIQUE INDEX idx_mv_zone_risk_h3 ON mv_zone_risk_summary (h3_index);

COMMENT ON MATERIALIZED VIEW mv_zone_risk_summary IS 'Pre-aggregated risk metrics for faster API queries';

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_risk_zones_updated_at BEFORE UPDATE ON risk_zones FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_crime_events_updated_at BEFORE UPDATE ON crime_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_environmental_events_updated_at BEFORE UPDATE ON environmental_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_poi_data_updated_at BEFORE UPDATE ON poi_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_reports_updated_at BEFORE UPDATE ON user_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_hotspots_updated_at BEFORE UPDATE ON hotspots FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_zone_embeddings_updated_at BEFORE UPDATE ON zone_embeddings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_camera_configs_updated_at BEFORE UPDATE ON camera_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON FUNCTION update_updated_at_column IS 'Automatically update updated_at timestamp on row modification';

-- =============================================================================
-- PERMISSIONS (adjust based on your needs)
-- =============================================================================

-- Create application user (run separately with appropriate credentials)
-- CREATE USER royal_shield_app WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE royal_shield_risk_db TO royal_shield_app;
-- GRANT USAGE ON SCHEMA public TO royal_shield_app;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO royal_shield_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO royal_shield_app;

-- =============================================================================
-- INITIAL DATA (Miami-Dade H3 grid seeding would go here)
-- =============================================================================

-- Note: Initial H3 grid population should be done via Python script
-- using the h3-py library to generate hexagons for the Miami-Dade bbox

COMMENT ON DATABASE royal_shield_risk_db IS 'Royal Shield Risk Prediction Engine - Geospatial database with PostGIS';
