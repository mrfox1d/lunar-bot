from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.filters import CommandStart, Command
import aiosqlite
from typing import Optional, List, Dict
import time

DB_PATH = "data/moderation.db"

async def init_db():
    """Инициализация базы данных с иерархией ролей"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица групп с иерархией ролей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица для хранения членов группы и их рангов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                rank_priority INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (group_id),
                UNIQUE(group_id, user_id)
            )
        """)

        # Таблица разрешений по приоритетам (для каждой группы свои права по приоритетам)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rank_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                rank_priority INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                permission_value BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (group_id) REFERENCES groups (group_id),
                UNIQUE(group_id, rank_priority, permission_name)
            )
        """)

        # Таблица для склонений ролей по падежам (как в Iris Bot)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS role_cases_declension (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                rank_priority INTEGER NOT NULL,
                rank_name TEXT NOT NULL,
                nominative_singular TEXT NOT NULL,
                genitive_singular TEXT,
                dative_singular TEXT,
                accusative_singular TEXT,
                instrumental_singular TEXT,
                prepositional_singular TEXT,
                nominative_plural TEXT,
                genitive_plural TEXT,
                dative_plural TEXT,
                accusative_plural TEXT,
                instrumental_plural TEXT,
                prepositional_plural TEXT,
                color_hex TEXT DEFAULT '#808080',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (group_id),
                UNIQUE(group_id, rank_priority)
            )
        """)

        # Таблица логирования действий модерации
        await db.execute("""
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                target_user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                reason TEXT,
                duration INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (group_id)
            )
        """)

        # Создаем индексы для оптимизации запросов
        await db.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_rank_permissions ON rank_permissions(group_id, rank_priority)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_logs_group ON moderation_logs(group_id)")

        await db.commit()
        print("✅ База данных инициализирована успешно")


async def setup_default_ranks(group_id: int):
    """Создание рангов по умолчанию для новой группы"""
    async with aiosqlite.connect(DB_PATH) as db:
        default_ranks = [
            {
                "priority": 1,
                "name": "Участник",
                "color": "#808080",
                "cases": {
                    "nominative_singular": "Участник",
                    "genitive_singular": "Участника",
                    "dative_singular": "Участнику",
                    "accusative_singular": "Участника",
                    "instrumental_singular": "Участником",
                    "prepositional_singular": "Участнике",
                    "nominative_plural": "Участники",
                    "genitive_plural": "Участников",
                },
                "permissions": {"mute": False, "kick": False, "ban": False, "warn": False}
            },
            {
                "priority": 2,
                "name": "Модератор",
                "color": "#90EE90",
                "cases": {
                    "nominative_singular": "Модератор",
                    "genitive_singular": "Модератора",
                    "dative_singular": "Модератору",
                    "accusative_singular": "Модератора",
                    "instrumental_singular": "Модератором",
                    "prepositional_singular": "Модераторе",
                    "nominative_plural": "Модераторы",
                    "genitive_plural": "Модераторов",
                },
                "permissions": {"mute": True, "kick": False, "ban": False, "warn": True}
            },
            {
                "priority": 3,
                "name": "Младший админ",
                "color": "#FFA500",
                "cases": {
                    "nominative_singular": "Младший админ",
                    "genitive_singular": "Младшего админа",
                    "dative_singular": "Младшему админу",
                    "accusative_singular": "Младшего админа",
                    "instrumental_singular": "Младшим админом",
                    "prepositional_singular": "Младшем админе",
                    "nominative_plural": "Младшие админы",
                    "genitive_plural": "Младших админов",
                },
                "permissions": {"mute": True, "kick": True, "ban": False, "warn": True, "promote": False}
            },
            {
                "priority": 4,
                "name": "Старший админ",
                "color": "#FF6B6B",
                "cases": {
                    "nominative_singular": "Старший админ",
                    "genitive_singular": "Старшего админа",
                    "dative_singular": "Старшему админу",
                    "accusative_singular": "Старшего админа",
                    "instrumental_singular": "Старшим админом",
                    "prepositional_singular": "Старшем админе",
                    "nominative_plural": "Старшие админы",
                    "genitive_plural": "Старших админов",
                },
                "permissions": {"mute": True, "kick": True, "ban": True, "warn": True, "promote": True}
            },
            {
                "priority": 5,
                "name": "Создатель",
                "color": "#FF0000",
                "cases": {
                    "nominative_singular": "Создатель",
                    "genitive_singular": "Создателя",
                    "dative_singular": "Создателю",
                    "accusative_singular": "Создателя",
                    "instrumental_singular": "Создателем",
                    "prepositional_singular": "Создателе",
                    "nominative_plural": "Создатели",
                    "genitive_plural": "Создателей",
                },
                "permissions": {"mute": True, "kick": True, "ban": True, "warn": True, "promote": True, "delete_group": True}
            },
        ]

        for rank_data in default_ranks:
            # Вставляем склонения и информацию о ранге
            await db.execute(
                """
                INSERT INTO role_cases_declension 
                (group_id, rank_priority, rank_name, nominative_singular, genitive_singular, dative_singular,
                 accusative_singular, instrumental_singular, prepositional_singular,
                 nominative_plural, genitive_plural, color_hex)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    group_id, rank_data["priority"], rank_data["name"],
                    rank_data["cases"]["nominative_singular"],
                    rank_data["cases"]["genitive_singular"],
                    rank_data["cases"]["dative_singular"],
                    rank_data["cases"]["accusative_singular"],
                    rank_data["cases"]["instrumental_singular"],
                    rank_data["cases"]["prepositional_singular"],
                    rank_data["cases"]["nominative_plural"],
                    rank_data["cases"]["genitive_plural"],
                    rank_data["color"]
                )
            )

            # Вставляем разрешения для каждого приоритета
            for permission_name, permission_value in rank_data["permissions"].items():
                await db.execute(
                    """
                    INSERT INTO rank_permissions (group_id, rank_priority, permission_name, permission_value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (group_id, rank_data["priority"], permission_name, permission_value)
                )

        await db.commit()
        print(f"✅ Ранги по умолчанию созданы для группы {group_id}")


async def check_user_permission(group_id: int, user_id: int, permission_name: str) -> bool:
    """Проверить, есть ли у пользователя определенное право"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT rp.permission_value
            FROM group_members gm
            JOIN rank_permissions rp ON gm.rank_priority = rp.rank_priority AND gm.group_id = rp.group_id
            WHERE gm.group_id = ? AND gm.user_id = ? AND rp.permission_name = ?
            """,
            (group_id, user_id, permission_name)
        )
        row = await cursor.fetchone()
        return row[0] if row else False


async def set_rank_permission(group_id: int, rank_priority: int, permission_name: str, value: bool) -> bool:
    """Установить/изменить разрешение для приоритета в группе"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO rank_permissions (group_id, rank_priority, permission_name, permission_value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(group_id, rank_priority, permission_name) DO UPDATE SET permission_value = ?
                """,
                (group_id, rank_priority, permission_name, value, value)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Ошибка при установке разрешения: {e}")
        return False


async def get_rank_permissions(group_id: int, rank_priority: int) -> Dict[str, bool]:
    """Получить все разрешения для приоритета в группе"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT permission_name, permission_value
            FROM rank_permissions
            WHERE group_id = ? AND rank_priority = ?
            """,
            (group_id, rank_priority)
        )
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}


async def get_user_rank_info(group_id: int, user_id: int) -> Optional[Dict]:
    """Получить информацию о ранге пользователя в группе"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT gm.rank_priority, rcd.rank_name, rcd.color_hex, rcd.nominative_singular
            FROM group_members gm
            JOIN role_cases_declension rcd ON gm.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            WHERE gm.group_id = ? AND gm.user_id = ?
            """,
            (group_id, user_id)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "rank_priority": row[0],
                "rank_name": row[1],
                "color_hex": row[2],
                "display_name": row[3]
            }
        return None


async def add_member_to_group(group_id: int, user_id: int, rank_priority: int) -> bool:
    """Добавить участника в группу с определенным рангом"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO group_members (group_id, user_id, rank_priority)
                VALUES (?, ?, ?)
                """,
                (group_id, user_id, rank_priority)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Ошибка при добавлении участника: {e}")
        return False


async def change_user_rank(group_id: int, user_id: int, new_rank_priority: int) -> bool:
    """Изменить ранг пользователя в группе"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                UPDATE group_members
                SET rank_priority = ?
                WHERE group_id = ? AND user_id = ?
                """,
                (new_rank_priority, group_id, user_id)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Ошибка при изменении ранга: {e}")
        return False


async def get_group_hierarchy(group_id: int) -> List[Dict]:
    """Получить иерархию рангов в группе (отсортировано по приоритету)"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT rcd.rank_priority, rcd.rank_name, rcd.color_hex, 
                   COUNT(gm.user_id) as member_count
            FROM role_cases_declension rcd
            LEFT JOIN group_members gm ON rcd.rank_priority = gm.rank_priority AND rcd.group_id = gm.group_id
            WHERE rcd.group_id = ?
            GROUP BY rcd.rank_priority
            ORDER BY rcd.rank_priority ASC
            """,
            (group_id,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "rank_priority": row[0],
                "rank_name": row[1],
                "color_hex": row[2],
                "member_count": row[3]
            }
            for row in rows
        ]


async def get_user_groups_with_permission(user_id: int, permission_name: str) -> List[Dict]:
    """Получить все группы пользователя, в которых у него есть определенное право"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT g.group_id, g.title, rcd.rank_name, gm.rank_priority
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            JOIN rank_permissions rp ON g.group_id = rp.group_id AND gm.rank_priority = rp.rank_priority
            JOIN role_cases_declension rcd ON g.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            WHERE gm.user_id = ? AND rp.permission_name = ? AND rp.permission_value = TRUE
            ORDER BY gm.rank_priority ASC
            """,
            (user_id, permission_name)
        )
        rows = await cursor.fetchall()
        return [
            {
                "group_id": row[0],
                "group_title": row[1],
                "rank_name": row[2],
                "rank_priority": row[3]
            }
            for row in rows
        ]


async def get_rank_declension(group_id: int, rank_priority: int, case: str = "nominative_singular") -> Optional[str]:
    """Получить склонение ранга по падежу"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"SELECT {case} FROM role_cases_declension WHERE group_id = ? AND rank_priority = ?",
            (group_id, rank_priority)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def log_moderation_action(group_id: int, moderator_id: int, target_user_id: int, 
                                 action_type: str, reason: str = None, duration: int = None) -> bool:
    """Логировать действие модерации"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO moderation_logs (group_id, moderator_id, target_user_id, action_type, reason, duration)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, moderator_id, target_user_id, action_type, reason, duration)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Ошибка при логировании действия: {e}")
        return False

async def get_user_groups_by_exact_rank(user_id: int, rank_priority: int) -> List[Dict]:
    """Получить все группы пользователя, в которых у него ИМЕННО ЭТОТ приоритет"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT g.group_id, g.title, rcd.rank_name, gm.rank_priority, rcd.color_hex
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            JOIN role_cases_declension rcd ON g.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            WHERE gm.user_id = ? AND gm.rank_priority = ?
            ORDER BY g.title ASC
            """,
            (user_id, rank_priority)
        )
        rows = await cursor.fetchall()
        return [
            {
                "group_id": row[0],
                "group_title": row[1],
                "rank_name": row[2],
                "rank_priority": row[3],
                "color_hex": row[4]
            }
            for row in rows
        ]


async def get_user_groups_by_min_rank(user_id: int, min_rank_priority: int) -> List[Dict]:
    """Получить все группы пользователя, в которых у него КАК МИНИМУМ этот приоритет (или выше)"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT g.group_id, g.title, rcd.rank_name, gm.rank_priority, rcd.color_hex
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            JOIN role_cases_declension rcd ON g.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            WHERE gm.user_id = ? AND gm.rank_priority >= ?
            ORDER BY gm.rank_priority DESC, g.title ASC
            """,
            (user_id, min_rank_priority)
        )
        rows = await cursor.fetchall()
        return [
            {
                "group_id": row[0],
                "group_title": row[1],
                "rank_name": row[2],
                "rank_priority": row[3],
                "color_hex": row[4]
            }
            for row in rows
        ]


async def get_user_all_groups(user_id: int) -> List[Dict]:
    """Получить все группы пользователя со всеми их рангами"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT g.group_id, g.title, rcd.rank_name, gm.rank_priority, rcd.color_hex, g.owner_id
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            JOIN role_cases_declension rcd ON g.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            WHERE gm.user_id = ?
            ORDER BY gm.rank_priority DESC, g.title ASC
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "group_id": row[0],
                "group_title": row[1],
                "rank_name": row[2],
                "rank_priority": row[3],
                "color_hex": row[4],
                "is_owner": row[5] == user_id
            }
            for row in rows
        ]

async def get_user_groups_with_permissions(user_id: int, permissions: List[str]) -> List[Dict]:
    """Получить все группы пользователя, в которых у него есть ВСЕ указанные права"""
    async with aiosqlite.connect(DB_PATH) as db:
        placeholders = ','.join('?' * len(permissions))
        cursor = await db.execute(
            f"""
            SELECT DISTINCT g.group_id, g.title, rcd.rank_name, gm.rank_priority, rcd.color_hex
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            JOIN role_cases_declension rcd ON g.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            WHERE gm.user_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM (
                    SELECT ? as permission
                ) AS needed_perms
                WHERE needed_perms.permission NOT IN (
                    SELECT rp.permission_name
                    FROM rank_permissions rp
                    WHERE rp.group_id = g.group_id 
                    AND rp.rank_priority = gm.rank_priority 
                    AND rp.permission_value = TRUE
                )
            )
            ORDER BY gm.rank_priority DESC, g.title ASC
            """,
            [user_id] + permissions
        )
        rows = await cursor.fetchall()
        return [
            {
                "group_id": row[0],
                "group_title": row[1],
                "rank_name": row[2],
                "rank_priority": row[3],
                "color_hex": row[4]
            }
            for row in rows
        ]


async def get_user_groups_with_any_permission(user_id: int, permissions: List[str]) -> List[Dict]:
    """Получить все группы пользователя, в которых у него есть ХОТЯ БЫ ОДНО из указанных прав"""
    async with aiosqlite.connect(DB_PATH) as db:
        placeholders = ','.join('?' * len(permissions))
        cursor = await db.execute(
            f"""
            SELECT DISTINCT g.group_id, g.title, rcd.rank_name, gm.rank_priority, rcd.color_hex
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            JOIN role_cases_declension rcd ON g.group_id = rcd.group_id AND gm.rank_priority = rcd.rank_priority
            JOIN rank_permissions rp ON g.group_id = rp.group_id AND gm.rank_priority = rp.rank_priority
            WHERE gm.user_id = ? AND rp.permission_name IN ({placeholders}) AND rp.permission_value = TRUE
            ORDER BY gm.rank_priority DESC, g.title ASC
            """,
            [user_id] + permissions
        )
        rows = await cursor.fetchall()
        return [
            {
                "group_id": row[0],
                "group_title": row[1],
                "rank_name": row[2],
                "rank_priority": row[3],
                "color_hex": row[4]
            }
            for row in rows
        ]


router = Router()

def parse_time_to_seconds(time_str: str) -> int:
    """Парсит время в формате '1h', '30m', '1d' в секунды"""
    if not time_str:
        return 0  # Навсегда
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
        'с': 1,
        'м': 60,
        'ч': 3600,
        'д': 86400,
        'н': 604800
    }
    
    try:
        value = int(time_str[:-1])
        unit = time_str[-1].lower()
        return value * multipliers.get(unit, 0)
    except (ValueError, IndexError):
        return 0


from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.filters import Command, CommandObject
import re

# Функция для парсинга текстовых команд
def parse_text_command(text: str, command_name: str) -> tuple[bool, list]:
    """Парсит текстовую команду вида *ban @user 1h причина"""
    pattern = rf'^\*{command_name}\s+(.*)'
    match = re.match(pattern, text, re.IGNORECASE)
    if match:
        args = match.group(1).split(maxsplit=3)
        return True, args
    return False, []


# Обновляем все команды, добавляя текстовые триггеры

@router.message(Command("ban", "бан"))
@router.message(F.text.regex(r'^\*ban\s+') | F.text.regex(r'^\*бан\s+'))
async def ban(message: Message):
    """Забанить пользователя: /ban @user 1h причина или *ban @user 1h причина"""
    
    # Парсим команду
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split(maxsplit=3)
    else:
        is_text, parameters = parse_text_command(message.text, r'(ban|бан)')
    
    if len(parameters) < 2:
        await message.reply("❌ Использование: /ban @user [время] [причина]\n\n"
                           "Примеры:\n"
                           "/ban @user - забан навсегда\n"
                           "/ban @user 1h - забан на 1 час\n"
                           "/ban @user 1d спам - забан на 1 день")
        return
    
    target = parameters[0] if is_text else parameters[1]
    time_str = parameters[1] if is_text and len(parameters) > 1 else (parameters[2] if len(parameters) > 2 else "")
    reason = parameters[2] if is_text and len(parameters) > 2 else (parameters[3] if len(parameters) > 3 else "Нет причины")
    
    if message.chat.type == "private":
        groups = await get_user_groups_with_permissions(
            user_id=message.from_user.id,
            permissions=["ban"]
        )
        
        if not groups:
            await message.reply("❌ У вас нет прав на бан ни в одной группе")
            return
        
        kb = []
        for group in groups:
            kb.append([InlineKeyboardButton(
                text=f"{group['group_title']} ({group['rank_name']})",
                callback_data=f"select_group_for_ban:{group['group_id']}:{target}:{time_str}:{reason}"
            )])
        
        mk = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.reply(
            "❌ Эта команда работает только в группах.\n\n"
            "Выберите группу, в которой хотите забанить пользователя:",
            reply_markup=mk
        )
        return
    
    elif message.chat.type in ["group", "supergroup"]:
        has_permission = await check_user_permission(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            permission_name="ban"
        )
        
        if not has_permission:
            await message.reply("❌ У вас нет прав для использования этой команды")
            return
        
        target_user_id = None
        
        try:
            if target.startswith("@"):
                target_user_id = int(target[1:]) if target[1:].isdigit() else None
            elif target.isdigit():
                target_user_id = int(target)
        except (ValueError, IndexError):
            pass
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        
        if not target_user_id:
            await message.reply("❌ Не удалось получить ID пользователя")
            return
        
        try:
            ban_time_seconds = parse_time_to_seconds(time_str)
            
            await message.bot.ban_chat_member(
                chat_id=message.chat.id,
                user_id=target_user_id,
                until_date=ban_time_seconds if ban_time_seconds > 0 else 0
            )
            
            await log_moderation_action(
                group_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_user_id=target_user_id,
                action_type="ban",
                reason=reason,
                duration=ban_time_seconds
            )
            
            time_text = f"на {time_str}" if time_str else "навсегда"
            await message.reply(
                f"✅ Пользователь {target_user_id} забанен {time_text}\n"
                f"📝 Причина: {reason}"
            )
        except Exception as e:
            await message.reply(f"❌ Ошибка при бане: {e}")


@router.message(Command("unban", "разбан"))
@router.message(F.text.regex(r'^\*unban\s+') | F.text.regex(r'^\*разбан\s+'))
async def unban(message: Message):
    """Разбанить пользователя: /unban user_id или *unban user_id"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(unban|разбан)')
    
    if len(parameters) < 2 and not is_text:
        await message.reply("❌ Использование: /unban <user_id>")
        return
    
    if is_text and len(parameters) < 1:
        await message.reply("❌ Использование: *unban <user_id>")
        return
    
    try:
        target_user_id = int(parameters[0] if is_text else parameters[1])
    except (ValueError, IndexError):
        await message.reply("❌ ID должен быть числом")
        return
    
    if message.chat.type == "private":
        groups = await get_user_groups_with_permissions(
            user_id=message.from_user.id,
            permissions=["ban"]
        )
        
        if not groups:
            await message.reply("❌ У вас нет прав на разбан ни в одной группе")
            return
        
        kb = []
        for group in groups:
            kb.append([InlineKeyboardButton(
                text=group["group_title"],
                callback_data=f"select_group_for_unban:{group['group_id']}:{target_user_id}"
            )])
        
        mk = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.reply("Выберите группу:", reply_markup=mk)
        return
    
    elif message.chat.type in ["group", "supergroup"]:
        has_permission = await check_user_permission(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            permission_name="ban"
        )
        
        if not has_permission:
            await message.reply("❌ У вас нет прав для использования этой команды")
            return
        
        try:
            await message.bot.unban_chat_member(
                chat_id=message.chat.id,
                user_id=target_user_id
            )
            
            await log_moderation_action(
                group_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_user_id=target_user_id,
                action_type="unban"
            )
            
            await message.reply(f"✅ Пользователь {target_user_id} разбанен")
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("mute", "мьют"))
@router.message(F.text.regex(r'^\*mute\s+') | F.text.regex(r'^\*мьют\s+'))
async def mute(message: Message):
    """Замьютить пользователя: /mute @user 1h причина или *mute @user 1h причина"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split(maxsplit=3)
    else:
        is_text, parameters = parse_text_command(message.text, r'(mute|мьют)')
    
    if len(parameters) < 2 and not is_text:
        await message.reply("❌ Использование: /mute @user [время] [причина]")
        return
    
    if is_text and len(parameters) < 1:
        await message.reply("❌ Использование: *mute @user [время] [причина]")
        return
    
    target = parameters[0] if is_text else parameters[1]
    time_str = parameters[1] if is_text and len(parameters) > 1 else (parameters[2] if len(parameters) > 2 else "")
    reason = parameters[2] if is_text and len(parameters) > 2 else (parameters[3] if len(parameters) > 3 else "Нет причины")
    
    if message.chat.type == "private":
        groups = await get_user_groups_with_permissions(
            user_id=message.from_user.id,
            permissions=["mute"]
        )
        
        if not groups:
            await message.reply("❌ У вас нет прав на мьют ни в одной группе")
            return
        
        kb = []
        for group in groups:
            kb.append([InlineKeyboardButton(
                text=f"{group['group_title']} ({group['rank_name']})",
                callback_data=f"select_group_for_mute:{group['group_id']}:{target}:{time_str}:{reason}"
            )])
        
        mk = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.reply("Выберите группу:", reply_markup=mk)
        return
    
    elif message.chat.type in ["group", "supergroup"]:
        has_permission = await check_user_permission(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            permission_name="mute"
        )
        
        if not has_permission:
            await message.reply("❌ У вас нет прав для использования этой команды")
            return
        
        target_user_id = None
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            try:
                if target.startswith("@"):
                    target_user_id = int(target[1:]) if target[1:].isdigit() else None
                elif target.isdigit():
                    target_user_id = int(target)
            except (ValueError, IndexError):
                pass
        
        if not target_user_id:
            await message.reply("❌ Не удалось получить ID пользователя")
            return
        
        try:
            mute_time_seconds = parse_time_to_seconds(time_str)
            
            if not mute_time_seconds:
                mute_time_seconds = 3600
            
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=int(datetime.now().timestamp()) + mute_time_seconds
            )
            
            await log_moderation_action(
                group_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_user_id=target_user_id,
                action_type="mute",
                reason=reason,
                duration=mute_time_seconds
            )
            
            time_text = f"на {time_str}" if time_str else "на 1 час"
            await message.reply(
                f"✅ Пользователь {target_user_id} замьючен {time_text}\n"
                f"📝 Причина: {reason}"
            )
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("unmute", "размьют"))
@router.message(F.text.regex(r'^\*unmute\s+') | F.text.regex(r'^\*размьют\s+'))
async def unmute(message: Message):
    """Размьютить пользователя: /unmute user_id или *unmute user_id"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(unmute|размьют)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /unmute <user_id>")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *unmute <user_id>")
        return
    
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        try:
            target_user_id = int(parameters[0] if is_text else parameters[1])
        except (ValueError, IndexError):
            await message.reply("❌ ID должен быть числом")
            return
    
    if message.chat.type == "private":
        groups = await get_user_groups_with_permissions(
            user_id=message.from_user.id,
            permissions=["mute"]
        )
        
        if not groups:
            await message.reply("❌ У вас нет прав")
            return
        
        kb = []
        for group in groups:
            kb.append([InlineKeyboardButton(
                text=group["group_title"],
                callback_data=f"select_group_for_unmute:{group['group_id']}:{target_user_id}"
            )])
        
        mk = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.reply("Выберите группу:", reply_markup=mk)
        return
    
    elif message.chat.type in ["group", "supergroup"]:
        has_permission = await check_user_permission(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            permission_name="mute"
        )
        
        if not has_permission:
            await message.reply("❌ У вас нет прав")
            return
        
        try:
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_user_id,
                permissions=types.ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            
            await log_moderation_action(
                group_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_user_id=target_user_id,
                action_type="unmute"
            )
            
            await message.reply(f"✅ Пользователь {target_user_id} размьючен")
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("kick", "кик"))
@router.message(F.text.regex(r'^\*kick\s+') | F.text.regex(r'^\*кик\s+'))
async def kick(message: Message):
    """Выгнать пользователя: /kick @user [причина] или *kick @user [причина]"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split(maxsplit=2)
    else:
        is_text, parameters = parse_text_command(message.text, r'(kick|кик)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /kick @user [причина]")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *kick @user [причина]")
        return
    
    target = parameters[0] if is_text else (parameters[1] if len(parameters) > 1 else "")
    reason = parameters[1] if is_text and len(parameters) > 1 else (parameters[2] if len(parameters) > 2 else "Нет причины")
    
    if message.chat.type == "private":
        groups = await get_user_groups_with_permissions(
            user_id=message.from_user.id,
            permissions=["kick"]
        )
        
        if not groups:
            await message.reply("❌ У вас нет прав на кик ни в одной группе")
            return
        
        kb = []
        for group in groups:
            kb.append([InlineKeyboardButton(
                text=f"{group['group_title']} ({group['rank_name']})",
                callback_data=f"select_group_for_kick:{group['group_id']}:{target}:{reason}"
            )])
        
        mk = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.reply("Выберите группу:", reply_markup=mk)
        return
    
    elif message.chat.type in ["group", "supergroup"]:
        has_permission = await check_user_permission(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            permission_name="kick"
        )
        
        if not has_permission:
            await message.reply("❌ У вас нет прав для использования этой команды")
            return
        
        target_user_id = None
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            try:
                if target.startswith("@"):
                    target_user_id = int(target[1:]) if target[1:].isdigit() else None
                elif target.isdigit():
                    target_user_id = int(target)
            except (ValueError, IndexError):
                pass
        
        if not target_user_id:
            await message.reply("❌ Не удалось получить ID пользователя")
            return
        
        try:
            await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user_id)
            await message.bot.unban_chat_member(chat_id=message.chat.id, user_id=target_user_id)
            
            await log_moderation_action(
                group_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_user_id=target_user_id,
                action_type="kick",
                reason=reason
            )
            
            await message.reply(
                f"✅ Пользователь {target_user_id} выгнан из группы\n"
                f"📝 Причина: {reason}"
            )
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("warn", "варн"))
@router.message(F.text.regex(r'^\*warn\s+') | F.text.regex(r'^\*варн\s+'))
async def warn(message: Message):
    """Выдать варн: /warn @user [причина] или *warn @user [причина]"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split(maxsplit=2)
    else:
        is_text, parameters = parse_text_command(message.text, r'(warn|варн)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /warn @user [причина]")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *warn @user [причина]")
        return
    
    target = parameters[0] if is_text else (parameters[1] if len(parameters) > 1 else "")
    reason = parameters[1] if is_text and len(parameters) > 1 else (parameters[2] if len(parameters) > 2 else "Нет причины")
    
    if message.chat.type == "private":
        groups = await get_user_groups_with_permissions(
            user_id=message.from_user.id,
            permissions=["warn"]
        )
        
        if not groups:
            await message.reply("❌ У вас нет прав на варн ни в одной группе")
            return
        
        kb = []
        for group in groups:
            kb.append([InlineKeyboardButton(
                text=f"{group['group_title']} ({group['rank_name']})",
                callback_data=f"select_group_for_warn:{group['group_id']}:{target}:{reason}"
            )])
        
        mk = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.reply("Выберите группу:", reply_markup=mk)
        return
    
    elif message.chat.type in ["group", "supergroup"]:
        has_permission = await check_user_permission(
            group_id=message.chat.id,
            user_id=message.from_user.id,
            permission_name="warn"
        )
        
        if not has_permission:
            await message.reply("❌ У вас нет прав для использования этой команды")
            return
        
        target_user_id = None
        
        if message.reply_to_message:
            target_user_id = message.reply_to_message.from_user.id
        else:
            try:
                if target.startswith("@"):
                    target_user_id = int(target[1:]) if target[1:].isdigit() else None
                elif target.isdigit():
                    target_user_id = int(target)
            except (ValueError, IndexError):
                pass
        
        if not target_user_id:
            await message.reply("❌ Не удалось получить ID пользователя")
            return
        
        try:
            warn_count = await get_user_warn_count(message.chat.id, target_user_id)
            warn_count += 1
            
            await log_moderation_action(
                group_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_user_id=target_user_id,
                action_type="warn",
                reason=reason
            )
            
            await message.reply(
                f"⚠️ Пользователь {target_user_id} получил варн\n"
                f"📊 Всего варнов: {warn_count}/3\n"
                f"📝 Причина: {reason}"
            )
            
            if warn_count >= 3:
                await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user_id)
                await clear_user_warns(message.chat.id, target_user_id)
                await message.reply(f"🚫 Пользователь {target_user_id} забанен (3 варна)")
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("warns", "варны"))
@router.message(F.text.regex(r'^\*warns\s+') | F.text.regex(r'^\*варны\s+'))
async def check_warns(message: Message):
    """Проверить варны: /warns @user или *warns @user"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(warns|варны)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /warns @user")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *warns @user")
        return
    
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        try:
            target = parameters[0] if is_text else parameters[1]
            if target.startswith("@"):
                target_user_id = int(target[1:]) if target[1:].isdigit() else None
            elif target.isdigit():
                target_user_id = int(target)
        except (ValueError, IndexError):
            pass
    
    if not target_user_id:
        await message.reply("❌ Не удалось получить ID пользователя")
        return
    
    if message.chat.type in ["group", "supergroup"]:
        warn_count = await get_user_warn_count(message.chat.id, target_user_id)
        await message.reply(f"⚠️ Пользователь {target_user_id}: {warn_count}/3 варнов")


@router.message(Command("clearwarns", "варн-клир"))
@router.message(F.text.regex(r'^\*clearwarns\s+') | F.text.regex(r'^\*варн-клир\s+'))
async def clear_warns(message: Message):
    """Очистить варны: /clearwarns @user или *clearwarns @user"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(clearwarns|очиститьварны)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /clearwarns @user")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *clearwarns @user")
        return
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    has_permission = await check_user_permission(
        group_id=message.chat.id,
        user_id=message.from_user.id,
        permission_name="warn"
    )
    
    if not has_permission:
        await message.reply("❌ У вас нет прав для использования этой команды")
        return
    
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        try:
            target = parameters[0] if is_text else parameters[1]
            if target.startswith("@"):
                target_user_id = int(target[1:]) if target[1:].isdigit() else None
            elif target.isdigit():
                target_user_id = int(target)
        except (ValueError, IndexError):
            pass
    
    if not target_user_id:
        await message.reply("❌ Не удалось получить ID пользователя")
        return
    
    await clear_user_warns(message.chat.id, target_user_id)
    await message.reply(f"✅ Варны пользователя {target_user_id} очищены")


@router.message(Command("modlog", "модлог"))
@router.message(F.text.regex(r'^\*modlog\s*') | F.text.regex(r'^\*модлог\s*'))
async def moderation_log(message: Message):
    """Показать логи модерации: /modlog или *modlog"""
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    has_permission = await check_user_permission(
        group_id=message.chat.id,
        user_id=message.from_user.id,
        permission_name="kick"
    )
    
    if not has_permission:
        await message.reply("❌ У вас нет прав для просмотра логов")
        return
    
    logs = await get_moderation_logs(message.chat.id, limit=10)
    
    if not logs:
        await message.reply("📋 Логов модерации не найдено")
        return
    
    text = "📋 **Последние действия модерации:**\n\n"
    for log in logs:
        text += (f"🔹 {log['action_type'].upper()}\n"
                f"   Модератор: {log['moderator_id']}\n"
                f"   Пользователь: {log['target_user_id']}\n"
                f"   Причина: {log['reason']}\n"
                f"   Время: {log['timestamp']}\n\n")
    
    await message.reply(text)


@router.message(Command("userlog", "юзерлог"))
@router.message(F.text.regex(r'^\*userlog\s+') | F.text.regex(r'^\*юзерлог\s+'))
async def user_moderation_log(message: Message):
    """Показать логи пользователя: /userlog @user или *userlog @user"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(userlog|логпользователя)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /userlog @user")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *userlog @user")
        return
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        try:
            target = parameters[0] if is_text else parameters[1]
            if target.startswith("@"):
                target_user_id = int(target[1:]) if target[1:].isdigit() else None
            elif target.isdigit():
                target_user_id = int(target)
        except (ValueError, IndexError):
            pass
    
    if not target_user_id:
        await message.reply("❌ Не удалось получить ID пользователя")
        return
    
    logs = await get_user_moderation_logs(message.chat.id, target_user_id, limit=10)
    
    if not logs:
        await message.reply(f"📋 Логов для пользователя {target_user_id} не найдено")
        return
    
    text = f"📋 **Логи пользователя {target_user_id}:**\n\n"
    for log in logs:
        text += (f"🔹 {log['action_type'].upper()}\n"
                f"   Причина: {log['reason']}\n"
                f"   Модератор: {log['moderator_id']}\n"
                f"   Время: {log['timestamp']}\n\n")
    
    await message.reply(text)


@router.message(Command("myrank", "мой-ранг"))
@router.message(F.text.regex(r'^\*myrank\s*') | F.text.regex(r'^\*мой-ранг\s*'))
async def my_rank(message: Message):
    """Показать свой ранг: /myrank или *myrank"""
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    rank_info = await get_user_rank_info(message.chat.id, message.from_user.id)
    
    if not rank_info:
        await message.reply("❌ Вы не участник этой группы")
        return
    
    await message.reply(
        f"👤 **Ваш ранг в этой группе:**\n\n"
        f"Название: {rank_info['rank_name']}\n"
        f"Приоритет: {rank_info['rank_priority']}/5\n"
        f"🎨 Цвет: {rank_info['color_hex']}"
    )


@router.message(Command("members", "участники"))
@router.message(F.text.regex(r'^\*members\s*') | F.text.regex(r'^\*участники\s*'))
async def list_members(message: Message):
    """Показать участников: /members или *members"""
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    members = await get_group_members(message.chat.id)
    
    if not members:
        await message.reply("❌ Участники не найдены")
        return
    
    by_rank = {}
    for member in members:
        rank = member['rank_name']
        if rank not in by_rank:
            by_rank[rank] = []
        by_rank[rank].append(member)
    
    text = "👥 **Участники группы:**\n\n"
    for rank_name in sorted(by_rank.keys(), reverse=True):
        text += f"**{rank_name}** ({len(by_rank[rank_name])})\n"
        for member in by_rank[rank_name][:10]:
            text += f"  • {member['user_id']}\n"
        if len(by_rank[rank_name]) > 10:
            text += f"  ... и ещё {len(by_rank[rank_name]) - 10}\n"
        text += "\n"
    
    await message.reply(text)


@router.message(Command("promote", "повысить"))
@router.message(F.text.regex(r'^\*promote\s+') | F.text.regex(r'^\*повысить\s+'))
async def promote_user(message: Message):
    """Повысить пользователя: /promote @user или *promote @user"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(promote|повысить)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /promote @user")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *promote @user")
        return
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    has_permission = await check_user_permission(
        group_id=message.chat.id,
        user_id=message.from_user.id,
        permission_name="promote"
    )
    
    if not has_permission:
        await message.reply("❌ У вас нет прав для использования этой команды")
        return
    
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        try:
            target = parameters[0] if is_text else parameters[1]
            if target.startswith("@"):
                target_user_id = int(target[1:]) if target[1:].isdigit() else None
            elif target.isdigit():
                target_user_id = int(target)
        except (ValueError, IndexError):
            pass
    
    if not target_user_id:
        await message.reply("❌ Не удалось получить ID пользователя")
        return
    
    rank_info = await get_user_rank_info(message.chat.id, target_user_id)
    
    if not rank_info:
        await message.reply(f"❌ Пользователь {target_user_id} не в группе")
        return
    
    if rank_info['rank_priority'] >= 5:
        await message.reply("❌ Пользователь уже максимального ранга")
        return
    
    new_rank = rank_info['rank_priority'] + 1
    
    success = await change_user_rank(message.chat.id, target_user_id, new_rank)
    
    if success:
        await message.reply(f"✅ Пользователь {target_user_id} повышен на ранг {new_rank}")
    else:
        await message.reply("❌ Ошибка при повышении ранга")


@router.message(Command("demote", "понизить"))
@router.message(F.text.regex(r'^\*demote\s+') | F.text.regex(r'^\*понизить\s+'))
async def demote_user(message: Message):
    """Понизить пользователя: /demote @user или *demote @user"""
    
    is_text, parameters = False, []
    
    if message.text.startswith('/'):
        parameters = message.text.split()
    else:
        is_text, parameters = parse_text_command(message.text, r'(demote|понизить)')
    
    if len(parameters) < 2 and not is_text and not message.reply_to_message:
        await message.reply("❌ Использование: /demote @user")
        return
    
    if is_text and len(parameters) < 1 and not message.reply_to_message:
        await message.reply("❌ Использование: *demote @user")
        return
    
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Эта команда работает только в группах")
        return
    
    has_permission = await check_user_permission(
        group_id=message.chat.id,
        user_id=message.from_user.id,
        permission_name="promote"
    )
    
    if not has_permission:
        await message.reply("❌ У вас нет прав для использования этой команды")
        return
    
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        try:
            target = parameters[0] if is_text else parameters[1]
            if target.startswith("@"):
                target_user_id = int(target[1:]) if target[1:].isdigit() else None
            elif target.isdigit():
                target_user_id = int(target)
        except (ValueError, IndexError):
            pass
    
    if not target_user_id:
        await message.reply("❌ Не удалось получить ID пользователя")
        return
    
    rank_info = await get_user_rank_info(message.chat.id, target_user_id)
    
    if not rank_info:
        await message.reply(f"❌ Пользователь {target_user_id} не в группе")
        return
    
    if rank_info['rank_priority'] <= 1:
        await message.reply("❌ Пользователь уже минимального ранга")
        return
    
    new_rank = rank_info['rank_priority'] - 1
    
    success = await change_user_rank(message.chat.id, target_user_id, new_rank)
    
    if success:
        await message.reply(f"✅ Пользователь {target_user_id} понижен на ранг {new_rank}")
    else:
        await message.reply("❌ Ошибка при понижении ранга")