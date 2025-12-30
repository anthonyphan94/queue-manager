"""
Database Module - SQLite persistence for Salon Turn Manager.

Provides async SQLite database operations for storing technician data
persistently. Used when running in production with GCS FUSE volume.
"""

import os
import json
import aiosqlite
from typing import List, Optional
from datetime import datetime

# Database path - uses DATA_DIR env var for Cloud Run GCS mount
DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.path.join(DATA_DIR, "salon.db")


async def init_db():
    """Initialize the database and create tables if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS technicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'AVAILABLE',
                queue_position INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                break_start_time TEXT
            )
        """)
        await db.commit()
        print(f"📦 Database initialized at: {DB_PATH}")


async def load_technicians() -> List[dict]:
    """Load all technicians from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM technicians ORDER BY queue_position") as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "status": row["status"],
                    "queue_position": row["queue_position"],
                    "is_active": bool(row["is_active"]),
                    "break_start_time": row["break_start_time"]
                }
                for row in rows
            ]


async def save_technician(tech: dict) -> int:
    """Save or update a technician in the database. Returns the technician ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        if tech.get("id"):
            # Update existing
            await db.execute("""
                UPDATE technicians 
                SET name=?, status=?, queue_position=?, is_active=?, break_start_time=?
                WHERE id=?
            """, (
                tech["name"],
                tech["status"],
                tech["queue_position"],
                1 if tech["is_active"] else 0,
                tech.get("break_start_time"),
                tech["id"]
            ))
            await db.commit()
            return tech["id"]
        else:
            # Insert new
            cursor = await db.execute("""
                INSERT INTO technicians (name, status, queue_position, is_active, break_start_time)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tech["name"],
                tech["status"],
                tech["queue_position"],
                1 if tech["is_active"] else 0,
                tech.get("break_start_time")
            ))
            await db.commit()
            return cursor.lastrowid


async def delete_technician(tech_id: int):
    """Delete a technician from the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM technicians WHERE id=?", (tech_id,))
        await db.commit()


async def save_all_technicians(technicians: List[dict]):
    """Save all technicians to the database (batch update)."""
    async with aiosqlite.connect(DB_PATH) as db:
        for tech in technicians:
            if tech.get("id"):
                await db.execute("""
                    UPDATE technicians 
                    SET name=?, status=?, queue_position=?, is_active=?, break_start_time=?
                    WHERE id=?
                """, (
                    tech["name"],
                    tech["status"],
                    tech["queue_position"],
                    1 if tech["is_active"] else 0,
                    tech.get("break_start_time"),
                    tech["id"]
                ))
        await db.commit()
