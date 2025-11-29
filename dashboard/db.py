"""
Database layer for XP Bot Web Dashboard
Handles async database queries for quest visualization
"""
import os
import asyncpg
from typing import List, Dict, Optional
from datetime import datetime


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize database connection pool"""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception("DATABASE_URL environment variable not set")

        self.pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    async def get_quest_stats(self) -> Dict:
        """Get overall quest statistics"""
        async with self.pool.acquire() as conn:
            stats = {}

            # Total quests
            stats['total_quests'] = await conn.fetchval(
                "SELECT COUNT(*) FROM quests"
            )

            # Active quests
            stats['active_quests'] = await conn.fetchval(
                "SELECT COUNT(*) FROM quests WHERE status = 'active'"
            )

            # Completed quests
            stats['completed_quests'] = await conn.fetchval(
                "SELECT COUNT(*) FROM quests WHERE status = 'completed'"
            )

            # Total participants
            stats['total_participants'] = await conn.fetchval(
                "SELECT COUNT(DISTINCT character_id) FROM quest_participants"
            )

            # Total DMs
            stats['total_dms'] = await conn.fetchval(
                "SELECT COUNT(DISTINCT user_id) FROM quest_dms"
            )

            # Average participants per quest
            avg_participants = await conn.fetchval("""
                SELECT AVG(participant_count)::numeric(10,1)
                FROM (
                    SELECT quest_id, COUNT(*) as participant_count
                    FROM quest_participants
                    GROUP BY quest_id
                ) subquery
            """)
            stats['avg_participants_per_quest'] = float(avg_participants) if avg_participants else 0

            return stats

    async def get_all_quests(self, status: Optional[str] = None,
                            level_bracket: Optional[str] = None,
                            limit: int = 100) -> List[Dict]:
        """Get all quests with optional filters"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT
                    q.*,
                    COUNT(DISTINCT qp.character_id) as participant_count,
                    ARRAY_AGG(DISTINCT COALESCE(dmp.preferred_dm_name, qd.username, 'User ' || qd.user_id))
                        FILTER (WHERE qd.user_id IS NOT NULL) as dm_usernames
                FROM quests q
                LEFT JOIN quest_participants qp ON q.id = qp.quest_id
                LEFT JOIN quest_dms qd ON q.id = qd.quest_id
                LEFT JOIN dm_profiles dmp ON qd.user_id = dmp.user_id
                WHERE 1=1
            """
            params = []
            param_idx = 1

            if status:
                query += f" AND q.status = ${param_idx}"
                params.append(status)
                param_idx += 1

            if level_bracket:
                query += f" AND q.level_bracket = ${param_idx}"
                params.append(level_bracket)
                param_idx += 1

            query += """
                GROUP BY q.id
                ORDER BY q.start_date DESC, q.created_at DESC
                LIMIT $""" + str(param_idx)
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_quest_by_id(self, quest_id: int) -> Optional[Dict]:
        """Get detailed quest information"""
        async with self.pool.acquire() as conn:
            quest = await conn.fetchrow(
                "SELECT * FROM quests WHERE id = $1",
                quest_id
            )

            if not quest:
                return None

            quest_dict = dict(quest)

            # Get participants
            participants = await conn.fetch("""
                SELECT qp.*, c.name as character_name, c.user_id
                FROM quest_participants qp
                JOIN characters c ON qp.character_id = c.id
                WHERE qp.quest_id = $1
                ORDER BY qp.joined_at
            """, quest_id)
            quest_dict['participants'] = [dict(p) for p in participants]

            # Get DMs with current profile names
            dms = await conn.fetch("""
                SELECT
                    qd.*,
                    qd.user_id as dm_user_id,
                    COALESCE(dmp.preferred_dm_name, qd.username, 'User ' || qd.user_id) as username
                FROM quest_dms qd
                LEFT JOIN dm_profiles dmp ON qd.user_id = dmp.user_id
                WHERE qd.quest_id = $1
                ORDER BY qd.is_primary DESC, qd.joined_at
            """, quest_id)
            quest_dict['dms'] = [dict(d) for d in dms]

            # Get monsters
            monsters = await conn.fetch("""
                SELECT * FROM quest_monsters
                WHERE quest_id = $1
                ORDER BY added_at
            """, quest_id)
            quest_dict['monsters'] = [dict(m) for m in monsters]

            return quest_dict

    async def get_level_brackets(self) -> List[str]:
        """Get all unique level brackets"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT level_bracket FROM quests ORDER BY level_bracket"
            )
            return [row['level_bracket'] for row in rows]

    async def get_quest_types(self) -> List[str]:
        """Get all unique quest types"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT quest_type FROM quests ORDER BY quest_type"
            )
            return [row['quest_type'] for row in rows]

    async def get_dm_stats(self) -> List[Dict]:
        """Get DM statistics (quest count per DM)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    user_id,
                    COUNT(DISTINCT quest_id) as quest_count,
                    SUM(CASE WHEN is_primary THEN 1 ELSE 0 END) as primary_dm_count
                FROM quest_dms
                GROUP BY user_id
                ORDER BY quest_count DESC
                LIMIT 20
            """)
            return [dict(row) for row in rows]

    async def get_character_quest_history(self, character_id: int) -> List[Dict]:
        """Get all quests a character has participated in"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT q.*, qp.starting_level, qp.starting_xp, qp.joined_at
                FROM quests q
                JOIN quest_participants qp ON q.id = qp.quest_id
                WHERE qp.character_id = $1
                ORDER BY q.start_date DESC
            """, character_id)
            return [dict(row) for row in rows]

    async def update_quest_dm_name(self, quest_id: int, user_id: int, new_name: str):
        """Update a DM's global profile name (updates all their quest assignments)"""
        async with self.pool.acquire() as conn:
            # Update or create the DM profile
            await conn.execute("""
                INSERT INTO dm_profiles (user_id, preferred_dm_name)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET preferred_dm_name = EXCLUDED.preferred_dm_name
            """, user_id, new_name)

            # Update all quest_dms records for this DM
            await conn.execute("""
                UPDATE quest_dms
                SET username = $1
                WHERE user_id = $2
            """, new_name, user_id)
