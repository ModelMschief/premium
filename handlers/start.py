from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned
import config

router = Router()

def get_gems_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.GEMS_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"💎 {pkg['name']} - {pkg['stars']} ⭐️", callback_data=f"buy_gems_{pkg['gems']}_{pkg['stars']}")])
    buttons.append([InlineKeyboardButton(text="✍️ Custom Amount", callback_data="custom_gems")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.PREMIUM_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"👑 {pkg['name']} - {pkg['stars']} ⭐️", callback_data=f"buy_premium_{pkg['duration_days']}_{pkg['stars']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Buy Gems", callback_data="show_gems")],
        [InlineKeyboardButton(text="👑 Buy Premium", callback_data="show_premium")]
    ])

def get_welcome_text() -> str:
    return (
        "👋 *Welcome to the Official Payment Bot!*\n\n"
        "This bot is your central hub for purchasing Gems and Premium plans using Telegram Stars. "
        "All purchases are securely processed and can be used across our network of bots.\n\n"
        "🔹 *Gems:* Use gems for special in-bot actions.\n"
        "🔹 *Premium:* Unlock exclusive features and remove restrictions.\n\n"
        "Select an option below to browse our packages:"
    )

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    if await is_banned(message.from_user.id):
        await message.answer("You are banned from using this bot.")
        return

    args = command.args
    if args == "buygems":
        await message.answer("Select a Gems package to purchase:", reply_markup=get_gems_keyboard())
    elif args == "buypremium":
        await message.answer("Select a Premium plan to purchase:", reply_markup=get_premium_keyboard())
    else:
        await message.answer(get_welcome_text(), reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "show_gems")
async def process_show_gems(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    await callback.message.edit_text("Select a Gems package to purchase:", reply_markup=get_gems_keyboard())

@router.callback_query(F.data == "show_premium")
async def process_show_premium(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    await callback.message.edit_text("Select a Premium plan to purchase:", reply_markup=get_premium_keyboard())

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    await callback.message.edit_text(get_welcome_text(), reply_markup=get_main_keyboard(), parse_mode="Markdown")
