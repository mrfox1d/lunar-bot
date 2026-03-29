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

async def main():
    print("▶️ Bot is running...")
    await db.init_db()
    dp.include_routers(*get_all_routers("handlers"))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())