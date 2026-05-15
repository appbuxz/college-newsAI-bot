import aiosqlite

DB_NAME = "students.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT,
            group_name TEXT,
            course INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT,
            formatted_text TEXT,
            type TEXT,
            event_date TEXT,
            priority TEXT,
            group_name TEXT,
            course INTEGER,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN course INTEGER")
        except:
            pass
        try:
            await db.execute("ALTER TABLE announcements ADD COLUMN course INTEGER")
        except:
            pass
        await db.commit()


async def add_user(user_id, full_name, group_name, course=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT OR IGNORE INTO users (user_id, full_name, group_name, course)
        VALUES (?, ?, ?, ?)
        """, (user_id, full_name, group_name, course))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        return await cursor.fetchall()

async def get_users_by_group(group_name):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE group_name = ?",
            (group_name,)
        )
        return await cursor.fetchall()

async def get_users_by_course(course):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE course = ?",
            (course,)
        )
        return await cursor.fetchall()

async def get_all_groups():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT DISTINCT group_name FROM users")
        return await cursor.fetchall()

async def get_users_in_group(group_name):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT full_name, user_id, course FROM users WHERE group_name = ?",
            (group_name,)
        )
        return await cursor.fetchall()

async def get_users_in_course(course):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT full_name, user_id, group_name FROM users WHERE course = ?",
            (course,)
        )
        return await cursor.fetchall()

async def delete_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

async def get_user_info(user_id):
    """Возвращает (full_name, group_name, course) или None если не зарегистрирован"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT full_name, group_name, course FROM users WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchone()


async def save_announcement(original_text, formatted_text, type_, event_date, priority, group_name=None, course=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO announcements (original_text, formatted_text, type, event_date, priority, group_name, course)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (original_text, formatted_text, type_, event_date, priority, group_name, course))
        await db.commit()

async def get_announcements(limit=10):
    """Последние рассылки — для истории в админке"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT type, event_date, priority, formatted_text, group_name, sent_at
        FROM announcements
        ORDER BY sent_at DESC
        LIMIT ?
        """, (limit,))
        return await cursor.fetchall()

async def get_announcements_for_student(group_name, course=None, limit=10):
    """Объявления для группы + для курса + общие (group_name IS NULL AND course IS NULL)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT type, event_date, priority, formatted_text, sent_at
        FROM announcements
        WHERE group_name = ? OR course = ? OR (group_name IS NULL AND course IS NULL)
        ORDER BY sent_at DESC
        LIMIT ?
        """, (group_name, course, limit))
        return await cursor.fetchall()