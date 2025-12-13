-- Manual migration for new device features
-- Run this if you have existing data, otherwise Flask will create the new schema

-- Add authorized column to devices table
ALTER TABLE devices ADD COLUMN authorized BOOLEAN DEFAULT 0;

-- Add unauthorized_notified_at column to devices table
ALTER TABLE devices ADD COLUMN unauthorized_notified_at DATETIME;

-- Add last_rssi column to devices table
ALTER TABLE devices ADD COLUMN last_rssi INTEGER;

-- Note: SQLite doesn't support adding NOT NULL columns to existing tables easily
-- The new columns will be nullable initially and get populated as devices are observed
