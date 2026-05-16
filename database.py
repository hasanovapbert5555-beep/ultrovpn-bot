import aiosqlite

async def init_db():
    async with aiosqlite.connect("ultrovpn.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at INTEGER DEFAULT (strftime('%s','now'))
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str):
    async with aiosqlite.connect("ultrovpn.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()

async def add_subscription_key(user_id: int, sub_key: str):
    async with aiosqlite.connect("ultrovpn.db") as db:
        await db.execute("UPDATE users SET sub_key = ? WHERE user_id = ?", (sub_key, user_id))
        await db.commit()

async def get_user_by_sub_key(sub_key: str):
    async with aiosqlite.connect("ultrovpn.db") as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE sub_key = ?", (sub_key,))
        row = await cur.fetchone()
        return dict(row) if row else None
