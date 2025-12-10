-- Migration: Add map dimensions for triangulation accuracy
-- Date: 2025-12-10

-- Add width_meters and height_meters columns to maps table
ALTER TABLE maps ADD COLUMN width_meters REAL DEFAULT 20.0;
ALTER TABLE maps ADD COLUMN height_meters REAL DEFAULT 20.0;

-- Update existing maps to have default 20m x 20m dimensions
UPDATE maps SET width_meters = 20.0, height_meters = 20.0 WHERE width_meters IS NULL;
