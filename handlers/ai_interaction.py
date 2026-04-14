import aiosqlite
import asyncio
import os
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/ai_chats.db"

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT
            )
        """)
        await db.commit()

async def save_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()

async def get_history(user_id: int, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"role": r, "content": c} for r, c in rows[::-1]]

router = Router()

OPENROUTER_API_KEY = os.getenv("OPENAI_TOKEN")
MODEL_NAME = "deepseek/deepseek-chat"

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = (
    "Ты — Люнар, харизматичный и ироничный ассистент в Telegram-боте. "
    "В боте есть игры, ивенты и модерация, поэтому ты ведешь себя как 'хозяин положения'. "
    "Твой стиль: легкий юмор, капля сарказма, никакой занудной вежливости. "
    "Отвечай не слишком коротко, но и не катай простыни текста."
)

def is_reply_to_lunar(message: types.Message):
    return message.reply_to_message and message.reply_to_message.from_user.id == message.bot.id

@router.message(F.text.lower().startswith(("лун", "люн", "lun", "moon", "lunar", "люнар", "лунар", "@lunargmbot")))
async def lunar_chat_handler(message: types.Message):
    bot: Bot = message.bot
    user_id = message.from_user.id
    is_private = message.chat.type == "private"

    can_request = await db.increment_ai_request(user_id)
    
    if not can_request:
        limit_text = "⚠ Твои лимиты на сегодня исчерпаны, смертный. Приходи завтра или приобрети Premium."
        if not is_private:
            return await message.reply(limit_text)
        return await message.answer(limit_text)

    try:
        await bot.send_chat_action(message.chat.id, "typing")

        await save_message(user_id, "user", message.text)
        
        history = await get_history(user_id, limit=20)
        messages_to_ai = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_to_ai,
            extra_headers={
                "HTTP-Referer": "https://t.me/lunargmbot",
                "X-Title": "Lunar | Group Manager",
            }
        )
        
        answer = response.choices[0].message.content

        await save_message(user_id, "assistant", answer)

        if not is_private:
            await message.reply(answer, parse_mode="Markdown")
        else:
            await message.answer(answer, parse_mode="Markdown")

    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        if "402" in str(e):
            await message.answer("У меня закончилось топливо (кредиты). Покорми создателя.")
        else:
            await message.answer("Мои нейронные цепи слегка закоротило. Попробуй позже.")


    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        if "402" in str(e):
            await message.answer("У меня закончилось топливо (кредиты). Покорми создателя, чтобы я снова заговорил.")
        else:
            await message.answer("Мои нейронные цепи слегка закоротило. Попробуй позже.")

@router.message(is_reply_to_lunar)
async def reply_to_lunar_handler(message: types.Message):
    await lunar_chat_handler(message)

@router.message(Command("hclear") or F.text.lower().startswith(("*hclear", "*кэшклир")))
async def history_clear(message: types.Message):
    user_id = message.from_user.id
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await db.commit()
        await message.answer("🧹 История чата очищена!")
    except Exception as e:
        print(f"Ошибка очистки истории: {e}")
        await message.answer("❌ Не удалось очистить историю.")