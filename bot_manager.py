import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database.sqlite import get_all_active_cloned_bots

logger = logging.getLogger(__name__)

# Registry of running cloned bots: {bot_id: (Bot, Dispatcher, asyncio.Task)}
active_bots = {}


async def start_cloned_bot(bot_token: str, bot_id: int):
    """Start a single cloned bot instance with its own Dispatcher."""
    import importlib
    from handlers import clone_start, clone_payments, clone_groups, owner_dashboard

    if bot_id in active_bots:
        logger.warning(f"Bot {bot_id} is already running, skipping.")
        return

    try:
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())

        # Reload the modules to get fresh Router instances for this dispatcher
        # This prevents the 'Router is already attached to Dispatcher' error in Aiogram 3
        importlib.reload(owner_dashboard)
        importlib.reload(clone_start)
        importlib.reload(clone_payments)
        importlib.reload(clone_groups)

        # Register cloned-bot-specific routers
        dp.include_router(owner_dashboard.router)
        dp.include_router(clone_start.router)
        dp.include_router(clone_payments.router)
        dp.include_router(clone_groups.router)

        await bot.delete_webhook(drop_pending_updates=True)

        task = asyncio.create_task(dp.start_polling(bot))
        active_bots[bot_id] = (bot, dp, task)

        bot_info = await bot.get_me()
        logger.info(f"✅ Cloned bot @{bot_info.username} (ID: {bot_id}) started successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to start cloned bot {bot_id}: {e}")


async def stop_cloned_bot(bot_id: int):
    """Stop a running cloned bot instance."""
    if bot_id not in active_bots:
        logger.warning(f"Bot {bot_id} is not running.")
        return

    bot, dp, task = active_bots[bot_id]
    try:
        await dp.stop_polling()
        task.cancel()
        await bot.session.close()
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id}: {e}")
    finally:
        del active_bots[bot_id]
        logger.info(f"🛑 Cloned bot {bot_id} stopped.")


async def start_all_cloned_bots():
    """Load all active cloned bots from the database and start them."""
    clones = get_all_active_cloned_bots()
    if not clones:
        logger.info("No active cloned bots to start.")
        return

    logger.info(f"Starting {len(clones)} cloned bot(s)...")
    for clone in clones:
        await start_cloned_bot(clone["bot_token"], clone["bot_id"])


def get_active_bot(bot_id: int):
    """Get a running Bot instance by its bot_id."""
    entry = active_bots.get(bot_id)
    if entry:
        return entry[0]  # Return the Bot object
    return None
