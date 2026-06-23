import asyncio
import logging
import datetime
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database.sqlite import (
    get_connected_group, get_clone_subscription, get_cloned_bot_by_id,
    add_connected_group, get_group_lang, get_user_lang,
    add_to_whitelist, remove_from_whitelist, is_whitelisted
)
import config
from locales import t

logger = logging.getLogger(__name__)

router = Router()

# Telegram's official Anonymous Admin user ID
ANONYMOUS_ADMIN_ID = 1087968824


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


async def _auto_delete(msg: Message, delay: int = 300):
    """Delete a message after `delay` seconds (default 5 min)."""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


# ─── /connect command ────────────────────────────────────────

@router.message(Command("connect"))
async def connect_group_command(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    bot_info = await message.bot.get_me()
    bot_id = bot_info.id
    clone_data = get_cloned_bot_by_id(bot_id)

    if not clone_data:
        return

    # Only the bot owner can connect a group
    if message.from_user.id != clone_data["owner_user_id"]:
        await message.reply("❌ Only the bot owner can connect this group.")
        return

    # Bot must be admin in the group
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

    add_connected_group(group_id, group_title, bot_id, owner_user_id)

    await message.reply(
        f"✅ <b>Group Connected Successfully!</b>\n\n"
        f"This group is now managed by the bot. You can configure subscription packages in your private dashboard.",
        parse_mode="HTML"
    )


# ─── /white command ─────────────────────────────────────────

@router.message(Command("white"))
async def whitelist_add_command(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    bot_info = await message.bot.get_me()
    bot_id = bot_info.id
    clone_data = get_cloned_bot_by_id(bot_id)

    if not clone_data or message.from_user.id != clone_data["owner_user_id"]:
        # Silently ignore non-owners
        return

    group_id = message.chat.id
    target_id, target_name = await _resolve_target(message)

    if target_id is None:
        reply = await message.reply(
            "⚠️ <b>Usage:</b>\n"
            "1. Reply to the bot's warning message with <code>/white</code>\n"
            "2. Send <code>/white 123456789</code> (User ID)\n"
            "3. Send <code>/white @username</code>\n"
            "4. Reply to a user's message with <code>/white</code>",
            parse_mode="HTML"
        )
        asyncio.create_task(_auto_delete(reply))
        return

    add_to_whitelist(group_id, target_id, bot_id)

    reply = await message.reply(
        f"✅ <a href='tg://user?id={target_id}'>{target_name}</a> has been <b>whitelisted</b>. "
        f"They can now chat freely without a subscription.",
        parse_mode="HTML"
    )
    asyncio.create_task(_auto_delete(reply))
    # Also delete the command message itself after 5 min
    asyncio.create_task(_auto_delete(message))


# ─── /black command ─────────────────────────────────────────

@router.message(Command("black"))
async def whitelist_remove_command(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    bot_info = await message.bot.get_me()
    bot_id = bot_info.id
    clone_data = get_cloned_bot_by_id(bot_id)

    if not clone_data or message.from_user.id != clone_data["owner_user_id"]:
        return

    group_id = message.chat.id
    target_id, target_name = await _resolve_target(message)

    if target_id is None:
        reply = await message.reply(
            "⚠️ <b>Usage:</b>\n"
            "1. Reply to a user's message with <code>/black</code>\n"
            "2. Send <code>/black 123456789</code> (User ID)\n"
            "3. Send <code>/black @username</code>",
            parse_mode="HTML"
        )
        asyncio.create_task(_auto_delete(reply))
        return

    remove_from_whitelist(group_id, target_id)

    reply = await message.reply(
        f"🚫 <a href='tg://user?id={target_id}'>{target_name}</a> has been <b>removed from the whitelist</b>. "
        f"They now need an active subscription to chat.",
        parse_mode="HTML"
    )
    asyncio.create_task(_auto_delete(reply))
    asyncio.create_task(_auto_delete(message))


# ─── Target resolution helper ────────────────────────────────

async def _resolve_target(message: Message):
    """
    Helper to resolve target user from command message.
    Returns (user_id, first_name) or (None, None).
    """
    # 1. Check if owner replied to a message
    if message.reply_to_message:
        replied = message.reply_to_message
        
        # Case A: Replied to an actual user's message (e.g. for /black)
        if replied.from_user and replied.from_user.id != message.bot.id:
            u = replied.from_user
            return u.id, u.first_name
            
        # Case B: Replied to the bot's own warning message!
        # The bot's GROUP_KICK_MSG contains <a href='tg://user?id=123456'>Name</a>
        if replied.from_user and replied.from_user.id == message.bot.id:
            if replied.entities:
                for entity in replied.entities:
                    if entity.type == "text_link" and entity.url and entity.url.startswith("tg://user?id="):
                        try:
                            user_id = int(entity.url.split("=")[1])
                            # Extract the name from the text based on offset/length
                            name = "User"
                            if replied.text:
                                # Encode to utf-16-le to match telegram's entity offsets
                                text_utf16 = replied.text.encode("utf-16-le")
                                name_utf16 = text_utf16[entity.offset * 2 : (entity.offset + entity.length) * 2]
                                name = name_utf16.decode("utf-16-le")
                            return user_id, name
                        except Exception:
                            pass
                    # If it was a text_mention instead (some clients)
                    if entity.type == "text_mention" and entity.user:
                        u = entity.user
                        return u.id, u.first_name

    # 2. Check entities in the command itself
    if message.entities:
        for entity in message.entities:
            if entity.type == "text_mention" and entity.user:
                u = entity.user
                return u.id, u.first_name

    # 3. Check text arguments (e.g., /white 123456789 or /white @username)
    parts = message.text.split()
    if len(parts) > 1:
        target_str = parts[1]
        
        # If they passed an ID directly
        if target_str.isdigit() or (target_str.startswith("-") and target_str[1:].isdigit()):
            user_id = int(target_str)
            try:
                chat = await message.bot.get_chat(user_id)
                return chat.id, chat.first_name or str(user_id)
            except Exception:
                return user_id, str(user_id)
                
        # If they passed @username
        if target_str.startswith("@"):
            username = target_str.lstrip("@")
            try:
                chat = await message.bot.get_chat(f"@{username}")
                return chat.id, chat.first_name or username
            except Exception:
                # Telegram often blocks this for regular users. We return None so the command handles it.
                pass

    return None, None


# ─── Group message filter ────────────────────────────────────

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def clone_group_message_filter(message: Message):
    """
    Group protection: Delete messages from unsubscribed users in connected groups.
    Admins, the owner, anonymous admins, and whitelisted users are always allowed.
    """
    if not message.from_user:
        return

    bot_info = await message.bot.get_me()

    # Allow bot's own messages
    if message.from_user.id == bot_info.id:
        return

    group_id = message.chat.id
    user_id = message.from_user.id

    # Check if this group is managed by this bot
    group_data = get_connected_group(group_id)
    if not group_data:
        return
    if group_data["bot_id"] != bot_info.id:
        return

    # ── Allow: Bot owner ────────────────────────────────────
    clone_data = get_cloned_bot_by_id(bot_info.id)
    if clone_data and user_id == clone_data["owner_user_id"]:
        return

    # ── Allow: Anonymous admin (official Telegram ID) ───────
    if user_id == ANONYMOUS_ADMIN_ID:
        return

    # ── Allow: Group admins and creator ─────────────────────
    try:
        member = await message.chat.get_member(user_id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        pass  # If we can't check, fall through to subscription check

    # ── Allow: Whitelisted users ─────────────────────────────
    if is_whitelisted(group_id, user_id):
        return

    # ── Check subscription ───────────────────────────────────
    sub_expiry = get_clone_subscription(user_id, group_id)
    if sub_expiry:
        expiry_dt = datetime.datetime.fromisoformat(sub_expiry)
        now = datetime.datetime.now(datetime.timezone.utc)
        if expiry_dt > now:
            return  # Active subscription — allow

    # ── No access: Delete + Warn ─────────────────────────────
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message in {group_id}: {e}")
        return

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
        asyncio.create_task(_auto_delete(warning_msg))
    except Exception as e:
        logger.warning(f"Failed to send warning in {group_id}: {e}")
