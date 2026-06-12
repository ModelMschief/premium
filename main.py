import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
from handlers import start, custom_amount, payments, groups, admin

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(custom_amount.router)
    dp.include_router(payments.router)
    dp.include_router(groups.router)
    dp.include_router(admin.router)

    logging.info("Starting Telegram Payment Bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
