import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, List


class Database:
    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_premium BOOLEAN DEFAULT 0,
                    daily_ai_requests INTEGER DEFAULT 0,
                    request_limit INTEGER DEFAULT 10,
                    currency INTEGER DEFAULT 0,
                    last_request_date TEXT,
                    registration_date TEXT,
                    total_requests INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS premium_subscriptions (
                    user_id INTEGER PRIMARY KEY,
                    start_date TEXT,
                    end_date TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    total_days INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            await db.commit()

    async def add_user(self, user_id: int, username: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            today = datetime.now().strftime("%Y-%m-%d")
            await db.execute("""
                INSERT OR IGNORE INTO users 
                (user_id, username, last_request_date, registration_date) 
                VALUES (?, ?, ?, ?)
            """, (user_id, username, today, today))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_username(self, user_id: int, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (username, user_id)
            )
            await db.commit()

    async def set_premium(self, user_id: int, is_premium: bool):
        await self._check_and_update_premium_status(user_id)
        
        limit = 20 if is_premium else 10
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_premium = ?, request_limit = ? WHERE user_id = ?",
                (is_premium, limit, user_id)
            )
            await db.commit()

    async def add_currency(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET currency = currency + ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def remove_currency(self, user_id: int, amount: int) -> bool:
        user = await self.get_user(user_id)
        if user and user['currency'] >= amount:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET currency = currency - ? WHERE user_id = ?",
                    (amount, user_id)
                )
                await db.commit()
            return True
        return False

    async def increment_ai_request(self, user_id: int) -> bool:
        await self._reset_daily_requests_if_needed(user_id)
        
        user = await self.get_user(user_id)
        if user and user['daily_ai_requests'] < user['request_limit']:
            async with aiosqlite.connect(self.db_path) as db:
                today = datetime.now().strftime("%Y-%m-%d")
                await db.execute("""
                    UPDATE users 
                    SET daily_ai_requests = daily_ai_requests + 1,
                        total_requests = total_requests + 1,
                        last_request_date = ?
                    WHERE user_id = ?
                """, (today, user_id))
                await db.commit()
            return True
        return False

    async def get_remaining_requests(self, user_id: int) -> int:
        await self._reset_daily_requests_if_needed(user_id)
        user = await self.get_user(user_id)
        if user:
            return user['request_limit'] - user['daily_ai_requests']
        return 0

    async def _reset_daily_requests_if_needed(self, user_id: int):
        user = await self.get_user(user_id)
        if user:
            today = datetime.now().strftime("%Y-%m-%d")
            if user['last_request_date'] != today:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "UPDATE users SET daily_ai_requests = 0, last_request_date = ? WHERE user_id = ?",
                        (today, user_id)
                    )
                    await db.commit()

    async def get_all_users(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_premium_users(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE is_premium = 1"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0]

    async def get_top_users_by_currency(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users ORDER BY currency DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def set_custom_limit(self, user_id: int, limit: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET request_limit = ? WHERE user_id = ?",
                (limit, user_id)
            )
            await db.commit()

    async def add_premium_subscription(self, user_id: int, days: int):
        await self._check_and_update_premium_status(user_id)
        
        subscription = await self.get_premium_subscription(user_id)
        now = datetime.now()
        
        if subscription and subscription['is_active']:
            current_end = datetime.fromisoformat(subscription['end_date'])
            new_end = current_end + timedelta(days=days)
            total_days = subscription['total_days'] + days
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE premium_subscriptions 
                    SET end_date = ?, total_days = ?
                    WHERE user_id = ?
                """, (new_end.isoformat(), total_days, user_id))
                await db.commit()
        else:
            start = now
            end = now + timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO premium_subscriptions 
                    (user_id, start_date, end_date, is_active, total_days) 
                    VALUES (?, ?, ?, 1, ?)
                """, (user_id, start.isoformat(), end.isoformat(), days))
                await db.commit()
        
        await self.set_premium(user_id, True)

    async def get_premium_subscription(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM premium_subscriptions WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def check_premium_expired(self, user_id: int) -> bool:
        subscription = await self.get_premium_subscription(user_id)
        if not subscription or not subscription['is_active']:
            return True
        
        end_date = datetime.fromisoformat(subscription['end_date'])
        return datetime.now() > end_date

    async def _check_and_update_premium_status(self, user_id: int):
        subscription = await self.get_premium_subscription(user_id)
        if subscription and subscription['is_active']:
            end_date = datetime.fromisoformat(subscription['end_date'])
            
            if datetime.now() > end_date:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "UPDATE premium_subscriptions SET is_active = 0 WHERE user_id = ?",
                        (user_id,)
                    )
                    await db.commit()
                await self.set_premium(user_id, False)

    async def get_premium_time_left(self, user_id: int) -> Optional[timedelta]:
        subscription = await self.get_premium_subscription(user_id)
        if not subscription or not subscription['is_active']:
            return None
        
        end_date = datetime.fromisoformat(subscription['end_date'])
        time_left = end_date - datetime.now()
        
        return time_left if time_left.total_seconds() > 0 else None

    async def cancel_premium_subscription(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE premium_subscriptions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
        await self.set_premium(user_id, False)

    async def get_all_active_subscriptions(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM premium_subscriptions WHERE is_active = 1"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_expiring_subscriptions(self, days: int = 3) -> List[Dict]:
        threshold = (datetime.now() + timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM premium_subscriptions WHERE is_active = 1 AND end_date <= ?",
                (threshold,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]