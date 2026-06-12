from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from database.sqlite import extend_group_subscription, log_local_payment
import config

router = Router()

class AdminGiveSub(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_duration = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message, bot: Bot):
    if message.from_user.id != config.ADMIN_ID:
        return # Ignore silently for non-admins

    buttons = []
    for chat_id in config.SUPPORTED_GROUPS:
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title
        except Exception:
            title = f"Group {chat_id}"
        
        buttons.append([InlineKeyboardButton(text=f"🎁 Give Sub: {title}", callback_data=f"admin_give_sub_{chat_id}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🛠 <b>Admin Menu</b>\nSelect a group to grant a manual subscription:", reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_give_sub_"))
async def process_admin_give_sub(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Unauthorized.", show_alert=True)
        return

    chat_id = int(callback.data.split("_")[3])
    
    await state.update_data(chat_id=chat_id)
    await state.set_state(AdminGiveSub.waiting_for_user_id)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="admin_cancel")]])
    await callback.message.edit_text(f"Please enter the <b>User ID</b> to grant the subscription to for group <code>{chat_id}</code>:", reply_markup=markup, parse_mode="HTML")

@router.message(AdminGiveSub.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != config.ADMIN_ID:
        return
        
    if not message.text.isdigit():
        await message.answer("Please enter a valid numeric User ID.")
        return
        
    user_id = int(message.text)
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check if user is in the group
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ['left', 'kicked', 'banned']:
            await message.answer(f"❌ User <code>{user_id}</code> is currently <b>{member.status}</b> from the group. Operation cancelled.", parse_mode="HTML")
            await state.clear()
            return
    except TelegramBadRequest:
        await message.answer(f"❌ User <code>{user_id}</code> is not in the group or the bot cannot access them. Operation cancelled.", parse_mode="HTML")
        await state.clear()
        return
    except Exception as e:
        await message.answer(f"❌ An error occurred while checking group membership: {e}. Operation cancelled.")
        await state.clear()
        return

    await state.update_data(user_id=user_id)
    await state.set_state(AdminGiveSub.waiting_for_duration)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Cancel", callback_data="admin_cancel")]])
    await message.answer(f"User is in the group! ✅\n\nHow many <b>days</b> should this subscription last?", reply_markup=markup, parse_mode="HTML")

@router.message(AdminGiveSub.waiting_for_duration)
async def process_duration(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != config.ADMIN_ID:
        return
        
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Please enter a valid positive number of days.")
        return
        
    duration = int(message.text)
    data = await state.get_data()
    chat_id = data['chat_id']
    user_id = data['user_id']
    
    extend_group_subscription(user_id, chat_id, duration)
    package_name = f"Manual Group Access {duration} Days"
    log_local_payment(user_id, "MANUAL_ADMIN", package_name)
    
    await message.answer(f"✅ Successfully granted <b>{duration} days</b> of subscription to User <code>{user_id}</code> for Group <code>{chat_id}</code>.", parse_mode="HTML")
    await state.clear()
    
    # Try to notify the user
    notification_text = f"🎉 <b>Subscription Granted!</b>\n\nYou have been manually granted <b>{duration} days</b> of access to the group by an Admin. Enjoy!"
    
    try:
        await bot.send_message(user_id, notification_text, parse_mode="HTML")
    except TelegramForbiddenError:
        # Fallback to group mention
        try:
            chat = await bot.get_chat(chat_id)
            group_title = chat.title
        except Exception:
            group_title = f"Group {chat_id}"
            
        fallback_text = f"<a href='tg://user?id={user_id}'>Hello</a>! 🎉\n\nYou have been manually granted <b>{duration} days</b> of access to <b>{group_title}</b> by an Admin."
        try:
            await bot.send_message(chat_id, fallback_text, parse_mode="HTML")
        except Exception as e:
            await message.answer(f"⚠️ Could not send fallback notification to the group: {e}")
    except Exception as e:
         await message.answer(f"⚠️ Could not send private notification to the user: {e}")

@router.callback_query(F.data == "admin_cancel")
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.ADMIN_ID:
        return
    await state.clear()
    await callback.message.edit_text("Admin action cancelled.")
    await callback.answer()
