from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.sqlite import (
    get_clone_quota, increment_used_slots, add_cloned_bot,
    get_cloned_bots_by_owner
)
from database.mongo import is_banned
import bot_manager
import config
import logging

logger = logging.getLogger(__name__)

router = Router()


class CloneStates(StatesGroup):
    waiting_for_token = State()


# ─── /start clone landing ────────────────────────────────────
@router.callback_query(F.data == "show_clone")
async def show_clone_info(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    quota = get_clone_quota(callback.from_user.id)
    remaining = quota["total_slots"] - quota["used_slots"]

    msg = (
        "🤖 <b>Clone Your Own Premium Group Bot!</b>\n\n"
        "Turn any Telegram group into a <b>premium membership</b> community.\n\n"
        "✨ <b>How it works:</b>\n"
        "1️⃣ Create a bot with <a href='https://t.me/BotFather'>@BotFather</a>\n"
        "2️⃣ Send us the token\n"
        "3️⃣ Add the bot to your group as admin\n"
        "4️⃣ Set subscription packages\n"
        "5️⃣ Start earning from group memberships!\n\n"
        "💰 <b>You earn 90%</b> of all USDT payments + 100% of Telegram Stars.\n\n"
        f"📊 <b>Your Slots:</b> {quota['used_slots']}/{quota['total_slots']} used ({remaining} remaining)\n"
    )

    buttons = [[InlineKeyboardButton(text="🤖 Create My Bot", callback_data="clone_create")]]
    if remaining <= 0:
        buttons.append([InlineKeyboardButton(text=f"🛒 Buy +5 Slots (⭐️ {config.CLONE_SLOT_STARS_PRICE} / 🪙 {config.CLONE_SLOT_USDT_PRICE} USDT)", callback_data="clone_buy_slots")])

    # Show existing bots
    my_bots = get_cloned_bots_by_owner(callback.from_user.id)
    if my_bots:
        msg += "\n<b>Your Bots:</b>\n"
        for b in my_bots:
            status_icon = "🟢" if b["clone_status"] == "active" else "🔴"
            msg += f"  {status_icon} @{b['bot_username']}\n"

    buttons.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(msg, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


# ─── Start clone creation ────────────────────────────────────
@router.callback_query(F.data == "clone_create")
async def clone_create(callback: CallbackQuery, state: FSMContext):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    quota = get_clone_quota(callback.from_user.id)
    remaining = quota["total_slots"] - quota["used_slots"]

    if remaining <= 0:
        await callback.answer("❌ No clone slots remaining! Buy more slots first.", show_alert=True)
        return

    await state.set_state(CloneStates.waiting_for_token)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="clone_cancel")]
    ])

    await callback.message.edit_text(
        "🔑 <b>Send Your Bot Token</b>\n\n"
        "Open <a href='https://t.me/BotFather'>@BotFather</a>, create a new bot, "
        "and send me the <b>API token</b> here.\n\n"
        "It looks like: <code>123456:ABCdefGHIjkl...</code>",
        reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == "clone_cancel")
async def clone_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Cancelled.")
    # Redirect back to clone info
    await show_clone_info(callback)


# ─── Receive and validate token ──────────────────────────────
@router.message(CloneStates.waiting_for_token)
async def receive_token(message: Message, state: FSMContext):
    token = message.text.strip()

    # Basic format check
    if ":" not in token or len(token) < 20:
        await message.answer(
            "❌ Invalid token format. Please send a valid BotFather token.\n\n"
            "It looks like: <code>123456:ABCdefGHIjkl...</code>",
            parse_mode="HTML"
        )
        return

    processing_msg = await message.answer("⏳ Validating your token...")

    try:
        # Validate by calling Telegram API
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        await test_bot.session.close()

        bot_id = bot_info.id
        bot_username = bot_info.username

        # Check if bot is already registered
        from database.sqlite import get_cloned_bot_by_id
        existing = get_cloned_bot_by_id(bot_id)
        if existing:
            await processing_msg.edit_text(
                f"❌ This bot (@{bot_username}) is already registered in our system.",
                parse_mode="HTML"
            )
            await state.clear()
            return

        # Re-check quota
        quota = get_clone_quota(message.from_user.id)
        if quota["used_slots"] >= quota["total_slots"]:
            await processing_msg.edit_text("❌ No clone slots remaining!")
            await state.clear()
            return

        # Save the clone
        add_cloned_bot(bot_id, message.from_user.id, bot_username, token)
        increment_used_slots(message.from_user.id)

        # Start the bot immediately
        await bot_manager.start_cloned_bot(token, bot_id)

        await state.clear()

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🤖 Open @{bot_username}", url=f"https://t.me/{bot_username}")],
            [InlineKeyboardButton(text="🔙 Back to Clone Menu", callback_data="show_clone")]
        ])

        await processing_msg.edit_text(
            f"✅ <b>Bot Created Successfully!</b>\n\n"
            f"🤖 Bot: @{bot_username}\n"
            f"🔑 ID: <code>{bot_id}</code>\n\n"
            f"Your bot is now <b>online</b>! Open it and start setting up your premium groups.\n\n"
            f"<i>Next step: Add the bot to your group as an administrator.</i>",
            reply_markup=markup, parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        await processing_msg.edit_text(
            "❌ <b>Invalid Token</b>\n\n"
            "The token could not be verified. Please make sure you copied the full token from @BotFather.",
            parse_mode="HTML"
        )
        # Don't clear state — let them try again


# ─── Buy more clone slots ────────────────────────────────────
@router.callback_query(F.data == "clone_buy_slots")
async def buy_clone_slots(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐️ Pay {config.CLONE_SLOT_STARS_PRICE} Stars", callback_data="paystars_cloneslots_5_" + str(config.CLONE_SLOT_STARS_PRICE))],
        [InlineKeyboardButton(text=f"🪙 Pay {config.CLONE_SLOT_USDT_PRICE} USDT", callback_data="paycrypto_cloneslots_5_" + str(config.CLONE_SLOT_STARS_PRICE))],
        [InlineKeyboardButton(text="🔙 Back", callback_data="show_clone")]
    ])

    await callback.message.edit_text(
        f"🛒 <b>Buy Clone Slots</b>\n\n"
        f"Get <b>+5 additional clone slots</b> to create more bots!\n\n"
        f"Price: ⭐️ {config.CLONE_SLOT_STARS_PRICE} Stars / 🪙 {config.CLONE_SLOT_USDT_PRICE} USDT",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()
