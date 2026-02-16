import os
import aiosqlite
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv('DATABASE_URL', 'sqlite:///authchecker.db').replace('sqlite:///', '')
    
    async def init(self):
        """Initialize async database"""
        async with aiosqlite.connect(self.db_path) as db:
            # Verified users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS verified_users (
                    discord_id INTEGER PRIMARY KEY,
                    roblox_id INTEGER UNIQUE,
                    roblox_username TEXT,
                    verified_at TIMESTAMP,
                    guild_id INTEGER
                )
            ''')
            
            # Pending verifications
            await db.execute('''
                CREATE TABLE IF NOT EXISTS pending_verifications (
                    discord_id INTEGER PRIMARY KEY,
                    state_code TEXT UNIQUE,
                    guild_id INTEGER,
                    created_at TIMESTAMP
                )
            ''')
            
            # Guild settings (includes blacklisted groups)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    verify_channel_id INTEGER,
                    report_channel_id INTEGER,
                    unverified_role_id INTEGER,
                    verified_role_id INTEGER,
                    blacklisted_groups TEXT,  -- JSON array of group IDs
                    updated_at TIMESTAMP
                )
            ''')
            
            # Bot credentials (set via dashboard)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bot_credentials (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    discord_token TEXT,
                    roblox_client_id TEXT,
                    roblox_client_secret TEXT,
                    roblox_redirect_uri TEXT,
                    updated_at TIMESTAMP
                )
            ''')
            
            await db.commit()
    
    # Credentials (sync - for startup)
    def get_credentials(self) -> Dict[str, str]:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("SELECT * FROM bot_credentials WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return {
                    'discord_token': row[1],
                    'roblox_client_id': row[2],
                    'roblox_client_secret': row[3],
                    'roblox_redirect_uri': row[4]
                }
            return {}
    
    def save_credentials(self, discord_token: str, roblox_client_id: str = '', 
                        roblox_client_secret: str = '', roblox_redirect_uri: str = ''):
        with sqlite3.connect(self.db_path) as db:
            db.execute('''
                INSERT OR REPLACE INTO bot_credentials 
                (id, discord_token, roblox_client_id, roblox_client_secret, roblox_redirect_uri, updated_at)
                VALUES (1, ?, ?, ?, ?, ?)
            ''', (discord_token, roblox_client_id, roblox_client_secret, roblox_redirect_uri, datetime.utcnow()))
            db.commit()
    
    # Guild settings (sync)
    def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
            row = cursor.fetchone()
            if row:
                import json
                return {
                    'verify_channel_id': row[1],
                    'report_channel_id': row[2],
                    'unverified_role_id': row[3],
                    'verified_role_id': row[4],
                    'blacklisted_groups': json.loads(row[5]) if row[5] else []
                }
            return {}
    
    def save_guild_settings(self, guild_id: int, verify_channel_id: int = None,
                           report_channel_id: int = None, unverified_role_id: int = None,
                           verified_role_id: int = None, blacklisted_groups: list = None):
        with sqlite3.connect(self.db_path) as db:
            import json
            db.execute('''
                INSERT OR REPLACE INTO guild_settings 
                (guild_id, verify_channel_id, report_channel_id, unverified_role_id, verified_role_id, blacklisted_groups, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (guild_id, verify_channel_id, report_channel_id, unverified_role_id, 
                  verified_role_id, json.dumps(blacklisted_groups or []), datetime.utcnow()))
            db.commit()
    
    def get_blacklisted_groups(self) -> List[int]:
        """Get global blacklisted groups (from first guild or default)"""
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("SELECT blacklisted_groups FROM guild_settings LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                import json
                return json.loads(row[0])
            return []
    
    # Async methods for bot operations
    async def create_pending_verification(self, discord_id: int, state_code: str, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO pending_verifications (discord_id, state_code, guild_id, created_at) VALUES (?, ?, ?, ?)",
                (discord_id, state_code, guild_id, datetime.utcnow())
            )
            await db.commit()
    
    async def get_pending_verification(self, state_code: str) -> Optional[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT discord_id, guild_id FROM pending_verifications WHERE state_code = ?",
                (state_code,)
            ) as cursor:
                row = await cursor.fetchone()
                return row if row else None
    
    async def remove_pending_verification(self, discord_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM pending_verifications WHERE discord_id = ?", (discord_id,))
            await db.commit()
    
    async def verify_user(self, discord_id: int, roblox_id: int, roblox_username: str, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO verified_users 
                (discord_id, roblox_id, roblox_username, verified_at, guild_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (discord_id, roblox_id, roblox_username, datetime.utcnow(), guild_id))
            await db.commit()
    
    async def get_verified_user(self, discord_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT roblox_id, roblox_username FROM verified_users WHERE discord_id = ?",
                (discord_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return {"roblox_id": row[0], "roblox_username": row[1]} if row else None
    
    async def is_verified(self, discord_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM verified_users WHERE discord_id = ?",
                (discord_id,)
            ) as cursor:
                return await cursor.fetchone() is not None

# Global instance
db = Database()