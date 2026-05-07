import asyncio
from aiogram import Bot, Dispatcher
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from config import BOT_TOKEN
from database import init_db

from handlers import start, admin

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await init_db()

    dp.include_router(start.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())