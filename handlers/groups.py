import datetime
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import config
from database.sqlite import get_group_subscription, get_last_warning, set_last_warning

router = Router()

# Only handle messages in supported groups
@router.message(F.chat.id.in_(config.SUPPORTED_GROUPS))
async def group_message_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    chat_id = message.chat.id

    print("HELLOOOOOOOOOOO")
    
    # Get chat member to check privileges
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception as e:
        # If the bot can't get member info, it's safer to just delete the message if not subscribed
        logging.error(f"Failed to get chat member {user_id} in {chat_id}: {e}")
        member = None
        
    # Check if user is exempt (creator, administrator, or anonymous)
    if member:
        status = getattr(member.status, "value", member.status) # Handle both string and Enum
        if status in ['creator', 'administrator']:
            return # Exempt, allow message
    
    # Additional check for Group Anonymous Bot or channel posts
    if message.sender_chat:
        return # Likely an anonymous admin or channel linking to the group

    # Check subscription
    try:
        expiry_iso = get_group_subscription(user_id, chat_id)
    except Exception as e:
        logging.error(f"Database error checking subscription: {e}")
        expiry_iso = None
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    is_subscribed = False
    if expiry_iso:
        try:
            expiry_date = datetime.datetime.fromisoformat(expiry_iso)
            if expiry_date > now:
                is_subscribed = True
        except ValueError:
            pass
            
    if not is_subscribed:
        # Delete user's message
        try:
            await message.delete()
        except Exception as e:
            logging.error(f"Failed to delete message in {chat_id}: {e}")
            # Do not return here, we still want to send the warning!
            
        # Try to delete previous warning message
        try:
            last_warning_id = get_last_warning(chat_id)
            if last_warning_id:
                try:
                    await bot.delete_message(chat_id, last_warning_id)
                except Exception:
                    pass # Message might be already deleted or too old
        except Exception as e:
            logging.error(f"Database error fetching last warning: {e}")
                
        # Send new warning message
        try:
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            
            deep_link = f"https://t.me/{bot_username}?start=subs_{chat_id}"
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Subscribe Now", url=deep_link,style="primary")]
            ])
            
            warning_text = (
                f"⚠️ <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>! Become the only few privileged users with access to Message here, by subscribing.✨\n\n"
                f"\n\n<i>🥇Subscribe And Become Unstoppable here🥇</i> \n\n"
                f"<blockquote>Or Use @anoni67_bot to send messages in this group</blockquote>"
                f"\n\n<b>Please purchase a subscription via the bot</b>.✨"
            )
            
            warning_msg = await bot.send_message(chat_id, warning_text, reply_markup=markup, parse_mode="HTML")
            set_last_warning(chat_id, warning_msg.message_id)
        except Exception as e:
            logging.error(f"Failed to send warning or save it: {e}")
