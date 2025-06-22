import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import config

class DatabaseManager:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        self._lock = asyncio.Lock()
    
    async def init_database(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    position INTEGER NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    UNIQUE(event_id, user_id)
                )
            """)
            
            await db.commit()
    
    async def create_event(self, date: str, message_id: int) -> int:
        """Создание нового события"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "INSERT OR REPLACE INTO events (date, message_id) VALUES (?, ?)",
                    (date, message_id)
                )
                await db.commit()
                return cursor.lastrowid
    
    async def get_event_by_date(self, date: str) -> Optional[Tuple]:
        """Получение события по дате"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, date, message_id FROM events WHERE date = ?",
                (date,)
            )
            return await cursor.fetchone()
    
    async def add_participant(self, event_id: int, user_id: int, username: str, 
                            first_name: str, last_name: str) -> Tuple[bool, int]:
        """
        Добавление участника к событию
        Возвращает (успех, позиция)
        """
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем, не записан ли уже пользователь
                cursor = await db.execute(
                    "SELECT position FROM participants WHERE event_id = ? AND user_id = ?",
                    (event_id, user_id)
                )
                existing = await cursor.fetchone()
                
                if existing:
                    return False, existing[0]
                
                # Проверяем количество участников
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM participants WHERE event_id = ?",
                    (event_id,)
                )
                count = (await cursor.fetchone())[0]
                
                if count >= config.MAX_PARTICIPANTS:
                    return False, -1
                
                # Добавляем участника
                position = count + 1
                await db.execute(
                    """INSERT INTO participants 
                       (event_id, user_id, username, first_name, last_name, position) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (event_id, user_id, username, first_name, last_name, position)
                )
                await db.commit()
                return True, position
    
    async def remove_participant(self, event_id: int, user_id: int) -> bool:
        """Удаление участника из события"""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT position FROM participants WHERE event_id = ? AND user_id = ?",
                    (event_id, user_id)
                )
                participant = await cursor.fetchone()
                
                if not participant:
                    return False
                
                removed_position = participant[0]
                
                # Удаляем участника
                await db.execute(
                    "DELETE FROM participants WHERE event_id = ? AND user_id = ?",
                    (event_id, user_id)
                )
                
                # Обновляем позиции остальных участников
                await db.execute(
                    "UPDATE participants SET position = position - 1 WHERE event_id = ? AND position > ?",
                    (event_id, removed_position)
                )
                
                await db.commit()
                return True
    
    async def get_participants(self, event_id: int) -> List[Tuple]:
        """Получение списка участников события"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT user_id, username, first_name, last_name, position 
                   FROM participants WHERE event_id = ? ORDER BY position""",
                (event_id,)
            )
            return await cursor.fetchall()
    
    async def get_participant_count(self, event_id: int) -> int:
        """Получение количества участников"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM participants WHERE event_id = ?",
                (event_id,)
            )
            return (await cursor.fetchone())[0] 