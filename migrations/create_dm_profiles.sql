-- Migration: Create DM profiles table
-- Stores preferred display names for DMs across all quests

CREATE TABLE IF NOT EXISTS dm_profiles (
    user_id BIGINT PRIMARY KEY,
    preferred_dm_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_dm_profiles_user_id ON dm_profiles(user_id);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_dm_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER dm_profile_updated
    BEFORE UPDATE ON dm_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_dm_profile_timestamp();
