from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import asyncio
import os
from handlers import get_all_routers
from handlers.databases import Database

load_dotenv()

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

async def on_startup():
    print("✅ Бот успешно запущен и слушает серверы Telegram!")

async def main():
    await db.init_db()
    print("✅ Основная БД инициализирована.")

    dp.include_routers(*get_all_routers("handlers"))

    dp.startup.register(on_startup)

    print("▶️ Попытка подключения...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())