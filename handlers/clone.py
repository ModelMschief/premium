from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.sqlite import (
    get_clone_quota, increment_used_slots, add_cloned_bot,
    get_cloned_bots_by_owner, get_user_lang
)
from locales import t
from database.mongo import is_banned
import bot_manager
import config
import logging

logger = logging.getLogger(__name__)

router = Router()


class CloneStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_new_token = State()


# ─── /start clone landing ────────────────────────────────────
@router.callback_query(F.data == "show_clone")
async def show_clone_info(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    lang = get_user_lang(callback.from_user.id) or "en"
    quota = get_clone_quota(callback.from_user.id)
    remaining = quota["total_slots"] - quota["used_slots"]

    msg = (
        f"<h3>{t('CLONE_MAIN_TITLE', lang)}</h3>\n"
        f"{t('CLONE_MAIN_BODY', lang).format(used=quota['used_slots'], total=quota['total_slots'], remaining=remaining)}"
    )

    buttons = [[InlineKeyboardButton(text=t("BTN_CREATE_BOT", lang), callback_data="clone_create")]]
    if remaining <= 0:
        buttons.append([InlineKeyboardButton(text=t("BTN_BUY_SLOTS", lang).format(stars=config.CLONE_SLOT_STARS_PRICE, usdt=config.CLONE_SLOT_USDT_PRICE), callback_data="clone_buy_slots")])

    # Show existing bots
    my_bots = get_cloned_bots_by_owner(callback.from_user.id)
    if my_bots:
        msg += "\n<b>Your Bots:</b> Click below to manage your bots or replace revoked tokens.\n"
        for b in my_bots:
            status_icon = "🟢" if b["clone_status"] == "active" else "🔴"
            manage_text = t("BTN_MANAGE_BOT", lang).format(icon=status_icon, username=b['bot_username'])
            buttons.append([InlineKeyboardButton(text=manage_text, callback_data=f"manageclone_{b['bot_id']}")])

    buttons.append([InlineKeyboardButton(text=t("BTN_BACK_MAIN", lang), callback_data="main_menu")])
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
    lang = get_user_lang(callback.from_user.id) or "en"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("BTN_BACK", lang), callback_data="clone_cancel")]
    ])

    await callback.message.edit_text(
        f"<h3>{t('CLONE_SEND_TOKEN_TITLE', lang)}</h3>\n"
        f"<p>{t('CLONE_SEND_TOKEN_BODY', lang)}</p>",
        reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == "clone_cancel")
async def clone_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Cancelled.")
    # Redirect back to clone info
    await show_clone_info(callback)


# ─── Manage individual bot ───────────────────────────────────
@router.callback_query(F.data.startswith("manageclone_"))
async def manage_clone_bot(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    bot_id = int(callback.data.split("_")[1])
    from database.sqlite import get_cloned_bot_by_id
    b = get_cloned_bot_by_id(bot_id)
    
    if not b or b["owner_user_id"] != callback.from_user.id:
        await callback.answer("Bot not found or unauthorized.", show_alert=True)
        return

    status = "🟢 Active" if b["clone_status"] == "active" else "🔴 Inactive"
    
    msg = (
        f"🤖 <b>Manage Bot: @{b['bot_username']}</b>\n\n"
        f"<b>ID:</b> <code>{b['bot_id']}</code>\n"
        f"<b>Status:</b> {status}\n\n"
        f"<i>Has your bot token been revoked by @BotFather? You can replace the bot token to seamlessly migrate all your groups and balances to a new bot!</i>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Change Bot Token", callback_data=f"changetoken_{bot_id}")],
        [InlineKeyboardButton(text="🔙 Back to Clone Menu", callback_data="show_clone")]
    ])

    await callback.message.edit_text(msg, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


# ─── Change token flow ───────────────────────────────────────
@router.callback_query(F.data.startswith("changetoken_"))
async def prompt_change_token(callback: CallbackQuery, state: FSMContext):
    bot_id = int(callback.data.split("_")[1])
    await state.set_state(CloneStates.waiting_for_new_token)
    await state.update_data(change_target_bot_id=bot_id)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="show_clone")]
    ])

    await callback.message.edit_text(
        "🔄 <b>Change Bot Token</b>\n\n"
        "Send me the new <b>API token</b> from @BotFather. This will replace your old token.\n\n"
        "⚠️ <b>Note:</b> If you just revoked the token for the <i>same</i> bot, everything will instantly resume working once you send the new token. "
        "However, if you send a token for a <i>completely different</i> bot, you will need to manually re-add that new bot to your groups as an Admin!\n\n"
        "Send the new token now (e.g. <code>123456:ABCdef...</code>):",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


@router.message(CloneStates.waiting_for_new_token)
async def receive_new_token(message: Message, state: FSMContext):
    token = message.text.strip()
    data = await state.get_data()
    old_bot_id = data.get("change_target_bot_id")

    if ":" not in token or len(token) < 20:
        await message.answer("❌ Invalid token format. Please send a valid BotFather token.", parse_mode="HTML")
        return

    processing_msg = await message.answer("⏳ Validating new token and migrating data...")

    try:
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        await test_bot.session.close()

        new_bot_id = bot_info.id
        new_bot_username = bot_info.username

        from database.sqlite import get_cloned_bot_by_id, update_cloned_bot_token
        existing = get_cloned_bot_by_id(new_bot_id)
        if existing and new_bot_id != old_bot_id:
            await processing_msg.edit_text("❌ This new bot is already registered in our system.", parse_mode="HTML")
            await state.clear()
            return

        # Stop old bot if it happens to be running
        await bot_manager.stop_cloned_bot(old_bot_id)

        # Migrate DB
        success = update_cloned_bot_token(old_bot_id, token, new_bot_id, new_bot_username)
        if not success:
            await processing_msg.edit_text("❌ Failed to migrate database records. Please try again or contact support.")
            await state.clear()
            return

        # Start new bot
        await bot_manager.start_cloned_bot(token, new_bot_id)

        await state.clear()

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🤖 Open @{new_bot_username}", url=f"https://t.me/{new_bot_username}")],
            [InlineKeyboardButton(text="🔙 Back to Clone Menu", callback_data="show_clone")]
        ])

        if new_bot_id == old_bot_id:
            msg_text = (
                f"✅ <b>Bot Token Successfully Updated!</b>\n\n"
                f"🤖 Bot: @{new_bot_username}\n\n"
                f"Since you just revoked and updated the token for your existing bot, everything will instantly resume working! "
                f"You do <b>NOT</b> need to re-add the bot to your groups."
            )
        else:
            msg_text = (
                f"✅ <b>Bot Successfully Replaced!</b>\n\n"
                f"🤖 New Bot: @{new_bot_username}\n"
                f"🔑 New ID: <code>{new_bot_id}</code>\n\n"
                f"⚠️ <b>ACTION REQUIRED:</b> Because this is a brand new bot, you MUST manually re-add @{new_bot_username} to your connected groups as an Administrator immediately so it can resume managing your memberships!"
            )

        await processing_msg.edit_text(msg_text, reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Change token validation failed: {e}")
        await processing_msg.edit_text(
            "❌ <b>Invalid Token</b>\n\n"
            "The token could not be verified. Please make sure you copied the full token from @BotFather."
        )


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
