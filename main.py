import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import config
from handlers import start, custom_amount, payments, groups, admin, clone
import bot_manager
import tasks

logging.basicConfig(level=logging.DEBUG)

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Get main bot username for viral buttons
    bot_info = await bot.get_me()
    config.MAIN_BOT_USERNAME = bot_info.username

    # Register main bot routers
    dp.include_router(start.router)
    dp.include_router(clone.router)
    dp.include_router(custom_amount.router)
    dp.include_router(payments.router)
    dp.include_router(groups.router)
    dp.include_router(admin.router)

    logging.info("Starting Telegram Payment Bot...")
    await bot.delete_webhook(drop_pending_updates=True)

    # Start all cloned bots and main bot concurrently
    await asyncio.gather(
        dp.start_polling(bot),
        bot_manager.start_all_cloned_bots(),
        asyncio.create_task(tasks.cleanup_stale_invoices_loop())
    )

if __name__ == "__main__":
    asyncio.run(main())
