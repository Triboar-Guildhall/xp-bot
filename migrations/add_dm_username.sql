-- Migration: Add username to quest_dms table
-- Run this migration to store Discord usernames for DMs

-- Add username column to quest_dms
ALTER TABLE quest_dms
ADD COLUMN IF NOT EXISTS username VARCHAR(255);

-- Note: Existing DMs will have NULL usernames until the bot updates them
-- New DMs added via the bot will automatically include usernames
