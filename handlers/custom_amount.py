import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.mongo import is_banned
import config

router = Router()

class CustomGems(StatesGroup):
    waiting_for_amount = State()

@router.callback_query(F.data == "custom_gems")
async def custom_gems_callback(callback: CallbackQuery, state: FSMContext):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    await callback.message.answer("Enter the number of Gems you want to buy (must be a positive number):")
    await state.set_state(CustomGems.waiting_for_amount)
    await callback.answer()

@router.message(CustomGems.waiting_for_amount)
async def process_custom_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Please enter a valid integer number of Gems.")
        return
        
    gems = int(message.text)
    if gems <= 0:
        await message.answer("The amount must be greater than 0.")
        return

    stars = math.ceil(gems / config.GEMS_PER_STAR)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Pay {stars} ⭐️ for {gems} 💎", callback_data=f"buy_gems_{gems}_{stars}")],
        [InlineKeyboardButton(text="Cancel", callback_data="cancel_payment")]
    ])
    
    await message.answer(f"You requested {gems} Gems.\nCost: {stars} Telegram Stars.", reply_markup=markup)
    await state.clear()

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Cancelled.")
