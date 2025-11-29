-- Migration: Normalize DM names
-- Creates dm_profiles for users who don't have one and syncs all quest_dms records

-- For each DM user, create a profile using their most recent username
INSERT INTO dm_profiles (user_id, preferred_dm_name)
SELECT DISTINCT ON (user_id)
    user_id,
    COALESCE(username, 'DM_' || user_id) as preferred_dm_name
FROM quest_dms
WHERE user_id NOT IN (SELECT user_id FROM dm_profiles)
  AND username IS NOT NULL
ORDER BY user_id, joined_at DESC
ON CONFLICT (user_id) DO NOTHING;

-- Update all quest_dms records to match their profile
UPDATE quest_dms qd
SET username = dmp.preferred_dm_name
FROM dm_profiles dmp
WHERE qd.user_id = dmp.user_id;

-- Show results
SELECT
    user_id,
    preferred_dm_name,
    (SELECT COUNT(*) FROM quest_dms WHERE user_id = dm_profiles.user_id) as quest_count
FROM dm_profiles
ORDER BY user_id;
