-- SQL script to create the cancer_image_analyses table
-- Run this directly in your PostgreSQL database if migrations fail

CREATE TABLE IF NOT EXISTS cancer_image_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    image VARCHAR(100) NOT NULL,
    image_type VARCHAR(20) NOT NULL DEFAULT 'other',
    original_filename VARCHAR(255) NOT NULL,
    tumor_detected BOOLEAN NOT NULL DEFAULT FALSE,
    tumor_type VARCHAR(100),
    tumor_stage VARCHAR(50),
    tumor_size_mm DOUBLE PRECISION,
    tumor_location VARCHAR(200),
    genetic_profile JSONB DEFAULT '{}',
    comorbidities JSONB DEFAULT '[]',
    analysis_data JSONB DEFAULT '{}',
    detection_confidence DOUBLE PRECISION DEFAULT 0.0,
    stage_confidence DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    CONSTRAINT cancer_image_analyses_user_id_fkey FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS cancer_image_analyses_user_id_idx ON cancer_image_analyses(user_id);
CREATE INDEX IF NOT EXISTS cancer_image_analyses_created_at_idx ON cancer_image_analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS cancer_image_analyses_tumor_detected_idx ON cancer_image_analyses(tumor_detected);

COMMENT ON TABLE cancer_image_analyses IS 'Stores uploaded cancer images and their OpenCV-based analysis results';

