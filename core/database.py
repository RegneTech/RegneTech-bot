import sqlite3
import aiosqlite
from typing import List, Tuple

DATABASE_PATH = "bot_data.db"

# Inicializar base de datos
async def init_database():
    """Inicializa la base de datos y crea las tablas necesarias"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bumps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, guild_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bump_counts (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.commit()

async def add_bump(user_id: int, guild_id: int) -> int:
    """Agrega un bump y retorna el total de bumps del usuario"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Insertar o actualizar contador
        await db.execute("""
            INSERT INTO bump_counts (user_id, guild_id, count) 
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, guild_id) 
            DO UPDATE SET count = count + 1
        """, (user_id, guild_id))
        
        # Registrar el bump individual
        await db.execute("""
            INSERT INTO bumps (user_id, guild_id) 
            VALUES (?, ?)
        """, (user_id, guild_id))
        
        # Obtener el total actual
        cursor = await db.execute("""
            SELECT count FROM bump_counts 
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        
        result = await cursor.fetchone()
        await db.commit()
        
        return result[0] if result else 1

async def get_bumps(user_id: int, guild_id: int) -> int:
    """Obtiene el número total de bumps de un usuario en un servidor"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT count FROM bump_counts 
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        
        result = await cursor.fetchone()
        return result[0] if result else 0

async def get_all_bumps(guild_id: int) -> List[Tuple[int, int]]:
    """Obtiene el ranking de todos los usuarios por bumps en un servidor"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT user_id, count FROM bump_counts 
            WHERE guild_id = ? 
            ORDER BY count DESC
        """, (guild_id,))
        
        results = await cursor.fetchall()
        return results