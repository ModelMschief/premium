import asyncio
import logging
import datetime
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database.sqlite import get_connected_group, get_clone_subscription, get_cloned_bot_by_id, add_connected_group, get_group_lang, get_user_lang
import config
from locales import t

logger = logging.getLogger(__name__)

router = Router()


def get_viral_button() -> list:
    main_bot = config.MAIN_BOT_USERNAME
    if main_bot:
        return [InlineKeyboardButton(text="🤖Get Your Own Bot FREE!", url=f"https://t.me/{main_bot}?start=clone")]
    return []


def _resolve_lang(user_id: int, group_id: int = None) -> str:
    """Group lang overrides user lang overrides English."""
    if group_id:
        gl = get_group_lang(group_id)
        if gl and gl != "en":
            return gl
    ul = get_user_lang(user_id)
    return ul if ul else "en"


@router.message(Command("connect"))
async def connect_group_command(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    bot_info = await message.bot.get_me()
    bot_id = bot_info.id
    clone_data = get_cloned_bot_by_id(bot_id)

    if not clone_data:
        return

    # Check if the sender is the owner of the bot
    if message.from_user.id != clone_data["owner_user_id"]:
        await message.reply("❌ Only the bot owner can connect this group.")
        return

    # Check if the bot is actually an admin in the group
    try:
        bot_member = await message.chat.get_member(bot_id)
        if bot_member.status != "administrator":
            await message.reply("❌ I must be an administrator in this group before you can connect it!")
            return
    except Exception as e:
        logger.error(f"Could not get bot member status: {e}")
        return

    group_id = message.chat.id
    group_title = message.chat.title or f"Group {group_id}"
    owner_user_id = clone_data["owner_user_id"]

    # Register the group
    add_connected_group(group_id, group_title, bot_id, owner_user_id)

    await message.reply(
        f"✅ <b>Group Connected Successfully!</b>\n\n"
        f"This group is now managed by the bot. You can configure subscription packages in your private dashboard.",
        parse_mode="HTML"
    )


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def clone_group_message_filter(message: Message):
    """
    Group protection: Delete messages from unsubscribed users in connected groups.
    """
    if not message.from_user:
        return

    # Ignore bot's own messages
    bot_info = await message.bot.get_me()
    if message.from_user.id == bot_info.id:
        return

    group_id = message.chat.id
    user_id = message.from_user.id

    # Check if this group is connected to this bot
    group_data = get_connected_group(group_id)
    if not group_data:
        return  # Not a managed group, ignore

    # Check if bot_id matches
    if group_data["bot_id"] != bot_info.id:
        return

    # Skip the group owner — they always have access
    clone_data = get_cloned_bot_by_id(bot_info.id)
    if clone_data and user_id == clone_data["owner_user_id"]:
        return

    # Check subscription
    sub_expiry = get_clone_subscription(user_id, group_id)

    if sub_expiry:
        expiry_dt = datetime.datetime.fromisoformat(sub_expiry)
        now = datetime.datetime.now(datetime.timezone.utc)
        if expiry_dt > now:
            return  # Active subscription — allow message

    # ─── No active subscription: Delete + Warn ───────────
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message in {group_id}: {e}")
        return

    # Send warning with subscribe button — in the group's language
    bot_username = bot_info.username
    subscribe_url = f"https://t.me/{bot_username}?start=sub_{group_id}"
    lang = _resolve_lang(user_id, group_id)

    buttons = [
        [InlineKeyboardButton(text=t("GROUP_KICK_BTN", lang), url=subscribe_url, style="primary")]
    ]
    viral = get_viral_button()
    if viral:
        buttons.append(viral)

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        warning_msg = await message.answer(
            t("GROUP_KICK_MSG", lang).format(user_id=user_id, name=message.from_user.first_name),
            reply_markup=markup,
            parse_mode="HTML"
        )

        # Auto-delete warning after 5 minutes
        async def delete_warning():
            await asyncio.sleep(300)  # 5 minutes
            try:
                await warning_msg.delete()
            except Exception:
                pass

        asyncio.create_task(delete_warning())

    except Exception as e:
        logger.warning(f"Failed to send warning in {group_id}: {e}")
