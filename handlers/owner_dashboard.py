from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, ADMINISTRATOR
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.sqlite import (
    get_cloned_bot_by_id, get_connected_groups, add_connected_group,
    remove_connected_group, get_group_packages, add_group_package,
    delete_group_package, get_group_package_by_id, update_group_package,
    get_creator_balance, set_withdrawal_address, debit_creator_balance,
    create_withdrawal, complete_withdrawal, fail_withdrawal,
    set_group_lang, get_user_lang
)
import config
import aiohttp
import shortuuid
import logging
from locales import t, LANG_NAMES
from handlers.language import build_lang_picker_markup
from rich_utils import safe_edit_rich_message

logger = logging.getLogger(__name__)

router = Router()


class OwnerStates(StatesGroup):
    waiting_for_package = State()
    waiting_for_edit_package = State()
    waiting_for_wallet_address = State()


# ─── Helper: Check if user is owner ─────────────────────────
async def is_owner(callback: CallbackQuery) -> bool:
    bot_info = await callback.bot.get_me()
    clone_data = get_cloned_bot_by_id(bot_info.id)
    if not clone_data:
        return False
    return callback.from_user.id == clone_data["owner_user_id"]


# ═══════════════════════════════════════════════════════════════
# CONNECT NEW GROUP
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "owner_connect_group")
async def owner_connect_group(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Dashboard", callback_data="clone_main_menu", style="primary")]
    ])

    await callback.message.edit_text(
        "➕ <b>Connect a New Group</b>\n\n"
        "To connect a group, follow these steps:\n\n"
        f"1️⃣ Open your group settings\n"
        f"2️⃣ Go to <b>Administrators</b>\n"
        f"3️⃣ Add @{bot_info.username} as an administrator\n"
        f"4️⃣ Grant these permissions:\n"
        "   • <i>Delete messages</i>\n"
        "   • <i>Send messages</i>\n"
        f"5️⃣ Send the command <code>/connect</code> inside the group!\n\n"
        "✅ The bot will verify you are the owner and connect the group.",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()



# Auto-unregister when bot is removed
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> IS_NOT_MEMBER))
async def bot_removed_from_group(event: ChatMemberUpdated):
    bot_info = await event.bot.get_me()
    clone_data = get_cloned_bot_by_id(bot_info.id)
    if not clone_data:
        return

    remove_connected_group(event.chat.id)
    logger.info(f"Group {event.chat.id} removed for bot {bot_info.id}")

    try:
        await event.bot.send_message(
            clone_data["owner_user_id"],
            f"🔴 <b>Group Disconnected</b>\n\n"
            f"The bot was removed from <b>{event.chat.title}</b>.",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# MANAGE GROUPS
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "owner_manage_groups")
async def owner_manage_groups(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    groups = get_connected_groups(bot_info.id)

    if not groups:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Connect New Group", callback_data="owner_connect_group", style="primary")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="clone_main_menu", style="primary")]
        ])
        await callback.message.edit_text(
            "📋 <b>No Groups Connected</b>\n\n"
            "Add the bot to a group as admin to get started.",
            reply_markup=markup, parse_mode="HTML"
        )
        await callback.answer()
        return

    buttons = []
    for g in groups:
        pkg_count = len(get_group_packages(g["group_id"]))
        buttons.append([InlineKeyboardButton(
            text=f"📢 {g['group_title']} ({pkg_count} packages)",
            callback_data=f"owner_group_{g['group_id']}",
            style="primary"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="clone_main_menu", style="primary")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        "📋 <b>Manage Groups</b>\n\nSelect a group to manage its subscription packages:",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


# ─── View group packages ─────────────────────────────────────
@router.callback_query(F.data.startswith("owner_group_"))
async def owner_group_detail(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    group_id = int(callback.data.split("_")[2])
    packages = get_group_packages(group_id)

    msg = f"📢 <b>Group Packages</b>\n🆔 <code>{group_id}</code>\n\n"

    if packages:
        for pkg in packages:
            msg += f"  📦 <b>{pkg['duration_days']} Days</b> — ⭐️ {pkg['stars_price']} / 🪙 {pkg['usdt_price']} USDT\n"
    else:
        msg += "<i>No packages configured yet.</i>\n"

    buttons = [
        [InlineKeyboardButton(text="➕ Add Package", callback_data=f"owner_addpkg_{group_id}", style="primary")],
        [InlineKeyboardButton(text=t("BTN_SET_GROUP_LANG", "en"), callback_data=f"owner_setlang_{group_id}", style="primary")],
    ]
    if packages:
        for pkg in packages:
            buttons.append([
                InlineKeyboardButton(text=f"✏️ Edit {pkg['duration_days']}d", callback_data=f"owner_editpkg_{pkg['package_id']}", style="primary"),
                InlineKeyboardButton(text=f"🗑 Del {pkg['duration_days']}d", callback_data=f"owner_delpkg_{pkg['package_id']}_{group_id}", style="primary")
            ])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="owner_manage_groups", style="primary")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(msg, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


# ─── Add package ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("owner_addpkg_"))
async def owner_add_package(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    group_id = int(callback.data.split("_")[2])
    await state.update_data(group_id=group_id)
    await state.set_state(OwnerStates.waiting_for_package)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data=f"owner_group_{group_id}", style="primary")]
    ])

    await callback.message.edit_text(
        "➕ <b>Add Package</b>\n\n"
        "Send the package details in this format:\n"
        "<code>days,stars,usdt</code>\n\n"
        "Example: <code>30,100,5</code>\n"
        "<i>(30 days, 100 Stars, $5 USDT)</i>",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


@router.message(OwnerStates.waiting_for_package)
async def receive_package(message: Message, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("group_id")

    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data=f"owner_group_{group_id}", style="primary")]
    ])

    try:
        parts = message.text.strip().split(",")
        duration_days = int(parts[0].strip())
        stars_price = int(parts[1].strip())
        usdt_price = float(parts[2].strip())

        if duration_days <= 0 or stars_price <= 0 or usdt_price <= 0:
            raise ValueError("All values must be positive")

        add_group_package(group_id, duration_days, stars_price, usdt_price)
        await state.clear()
        
        lang = get_user_lang(message.from_user.id) or "en"
        success_msg = t("OWNER_PKG_ADDED", lang).format(
            days=duration_days,
            stars=stars_price,
            usdt=usdt_price
        )
        
        success_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("BTN_ADD_MORE_PKG", lang), callback_data=f"owner_addpkg_{group_id}", style="primary")],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"owner_group_{group_id}", style="primary")]
        ])

        await message.answer(
            success_msg,
            reply_markup=success_markup,
            parse_mode="HTML"
        )
    except (ValueError, IndexError):
        await message.answer(
            "❌ Invalid format. Please send: <code>days,stars,usdt</code>\n"
            "Example: <code>30,100,5</code>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )


# ─── Delete package ───────────────────────────────────────────
@router.callback_query(F.data.startswith("owner_delpkg_"))
async def owner_delete_package(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    parts = callback.data.split("_")
    package_id = int(parts[2])
    group_id = int(parts[3])

    delete_group_package(package_id)
    await callback.answer("Package deleted!", show_alert=True)

    # Refresh the group detail view
    callback.data = f"owner_group_{group_id}"
    await owner_group_detail(callback)


# ─── Edit package ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("owner_editpkg_"))
async def owner_edit_package(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    package_id = int(callback.data.split("_")[2])
    pkg = get_group_package_by_id(package_id)
    if not pkg:
        await callback.answer("Package not found.", show_alert=True)
        return

    await state.update_data(edit_package_id=package_id, group_id=pkg["group_id"])
    await state.set_state(OwnerStates.waiting_for_edit_package)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data=f"owner_group_{pkg['group_id']}", style="primary")]
    ])

    await callback.message.edit_text(
        f"✏️ <b>Edit Package</b>\n\n"
        f"Current: <b>{pkg['duration_days']} Days</b> | ⭐️ {pkg['stars_price']} | 🪙 {pkg['usdt_price']} USDT\n\n"
        f"Send the new values: <code>days,stars,usdt</code>",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


@router.message(OwnerStates.waiting_for_edit_package)
async def receive_edit_package(message: Message, state: FSMContext):
    data = await state.get_data()
    edit_package_id = data.get("edit_package_id")
    group_id = data.get("group_id")

    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data=f"owner_group_{group_id}", style="primary")]
    ])

    try:
        parts = message.text.strip().split(",")
        duration_days = int(parts[0].strip())
        stars_price = int(parts[1].strip())
        usdt_price = float(parts[2].strip())

        if duration_days <= 0 or stars_price <= 0 or usdt_price <= 0:
            raise ValueError("All values must be positive")

        update_group_package(edit_package_id, duration_days, stars_price, usdt_price)
        await state.clear()

        await message.answer(
            f"✅ <b>Package Updated!</b>\n\n"
            f"📦 {duration_days} Days | ⭐️ {stars_price} Stars | 🪙 {usdt_price} USDT",
            parse_mode="HTML"
        )
    except (ValueError, IndexError):
        await message.answer(
            "❌ Invalid format. Please send: <code>days,stars,usdt</code>\n"
            "Example: <code>30,100,5</code>",
            reply_markup=cancel_markup,
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════════════════════════
# WALLET & WITHDRAWALS
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "owner_wallet")
async def owner_wallet(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    balance = get_creator_balance(callback.from_user.id)

    wallet_display = balance["withdrawal_address"] or "<i>Not set</i>"

    buttons = [
        [InlineKeyboardButton(text="💳 Set/Change Wallet", callback_data="owner_set_wallet", style="primary")],
    ]
    if balance["balance_usdt"] > 0 and balance["withdrawal_address"]:
        buttons.append([InlineKeyboardButton(text=f"💸 Withdraw ${balance['balance_usdt']:.2f}", callback_data="owner_withdraw_confirm", style="primary")])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="clone_main_menu", style="primary")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        f"💰 <b>Wallet & Earnings</b>\n\n"
        f"💵 Available Balance: <b>${balance['balance_usdt']:.2f} USDT</b>\n"
        f"📊 Total Earned: <b>${balance['total_earned_usdt']:.2f} USDT</b>\n\n"
        f"💳 Withdrawal Wallet:\n<code>{wallet_display}</code>\n\n"
        f"<i>You earn {int(config.CREATOR_REVENUE_SHARE * 100)}% of all USDT payments.</i>",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


# ─── Set wallet address ──────────────────────────────────────
@router.callback_query(F.data == "owner_set_wallet")
async def owner_set_wallet(callback: CallbackQuery, state: FSMContext):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    await state.set_state(OwnerStates.waiting_for_wallet_address)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="owner_wallet", style="primary")]
    ])

    await callback.message.edit_text(
        "💳 <b>Set Withdrawal Wallet</b>\n\n"
        "Send your <b>BSC (BEP20)</b> wallet address.\n\n"
        "<i>Make sure this is a valid BSC address starting with 0x</i>",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


@router.message(OwnerStates.waiting_for_wallet_address)
async def receive_wallet_address(message: Message, state: FSMContext):
    address = message.text.strip()

    if not address.startswith("0x") or len(address) != 42:
        await message.answer(
            "❌ Invalid address. Please send a valid BSC (BEP20) address starting with <code>0x</code> (42 characters).",
            parse_mode="HTML"
        )
        return

    set_withdrawal_address(message.from_user.id, address)
    await state.clear()

    await message.answer(
        f"✅ <b>Wallet Updated!</b>\n\n"
        f"💳 <code>{address}</code>",
        parse_mode="HTML"
    )


# ─── Withdrawal confirmation ─────────────────────────────────
@router.callback_query(F.data == "owner_withdraw_confirm")
async def owner_withdraw_confirm(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    balance = get_creator_balance(callback.from_user.id)

    if balance["balance_usdt"] <= 0:
        await callback.answer("No funds to withdraw.", show_alert=True)
        return

    if not balance["withdrawal_address"]:
        await callback.answer("Set your wallet address first!", show_alert=True)
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Confirm Withdraw ${balance['balance_usdt']:.2f}", callback_data="owner_withdraw_execute", style="success")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="owner_wallet", style="primary")]
    ])

    await callback.message.edit_text(
        f"💸 <b>Confirm Withdrawal</b>\n\n"
        f"Amount: <b>${balance['balance_usdt']:.2f} USDT</b>\n"
        f"To: <code>{balance['withdrawal_address']}</code>\n\n"
        f"⚠️ This action cannot be undone.",
        reply_markup=markup, parse_mode="HTML"
    )
    await callback.answer()


# ─── Execute withdrawal via /api/transfer ────────────────────
@router.callback_query(F.data == "owner_withdraw_execute")
async def owner_withdraw_execute(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    balance = get_creator_balance(callback.from_user.id)
    amount = balance["balance_usdt"]
    to_address = balance["withdrawal_address"]

    if amount <= 0 or not to_address:
        await callback.answer("Invalid withdrawal.", show_alert=True)
        return

    withdrawal_id = shortuuid.uuid()
    create_withdrawal(withdrawal_id, callback.from_user.id, amount, to_address)

    await callback.message.edit_text("⏳ Processing withdrawal...")

    headers = {"x-api-key": config.BSC_API_KEY}
    payload = {
        "toAddress": to_address,
        "amount": str(amount),
        "token": "USDT"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://bscusdtapi.onrender.com/api/transfer", json=payload, headers=headers) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    tx_hash = data.get("txHash", "N/A")

                    # Debit balance and complete withdrawal
                    debit_creator_balance(callback.from_user.id, amount)
                    complete_withdrawal(withdrawal_id, tx_hash)

                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Back to Wallet", callback_data="owner_wallet", style="primary")]
                    ])

                    await callback.message.edit_text(
                        f"✅ <b>Withdrawal Successful!</b>\n\n"
                        f"💵 Amount: <b>${amount:.2f} USDT</b>\n"
                        f"💳 To: <code>{to_address}</code>\n"
                        f"🔗 TX: <code>{tx_hash}</code>",
                        reply_markup=markup, parse_mode="HTML"
                    )

                    # Notify platform admin
                    try:
                        admin_msg = (
                            f"💸 <b>Creator Withdrawal Processed</b>\n\n"
                            f"👤 User ID: <code>{callback.from_user.id}</code>\n"
                            f"💵 Amount: <b>${amount:.2f} USDT</b>\n"
                            f"💳 To: <code>{to_address}</code>\n"
                            f"🔗 TX: <code>{tx_hash}</code>"
                        )
                        # Use the main bot to notify admin
                        from aiogram import Bot as MainBot
                        main_bot = MainBot(token=config.BOT_TOKEN)
                        await main_bot.send_message(config.ADMIN_ID, admin_msg, parse_mode="HTML")
                        await main_bot.session.close()
                    except Exception as e:
                        logger.error(f"Failed to notify admin about withdrawal: {e}")
                else:
                    error_text = await resp.text()
                    logger.error(f"Withdrawal API failed: {resp.status} - {error_text}")
                    fail_withdrawal(withdrawal_id)

                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Back to Wallet", callback_data="owner_wallet", style="primary")]
                    ])

                    await callback.message.edit_text(
                        "❌ <b>Withdrawal Failed</b>\n\n"
                        "The transfer could not be completed. Your balance has not been deducted.\n"
                        "Please try again later or contact support.",
                        reply_markup=markup, parse_mode="HTML"
                    )
    except Exception as e:
        logger.error(f"Withdrawal exception: {e}")
        fail_withdrawal(withdrawal_id)
        await callback.message.edit_text("❌ Withdrawal failed due to a network error. Please try again.")



# ─── Set group language ────────────────────────────────────
@router.callback_query(F.data.startswith("owner_setlang_"))
async def owner_set_group_lang_picker(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    group_id = int(callback.data.split("_")[2])

    # Build a special lang picker that encodes the group_id
    items = list(LANG_NAMES.items())
    buttons = []
    for i in range(0, len(items), 2):
        row = []
        for code, label in items[i:i+2]:
            row.append(InlineKeyboardButton(text=label, callback_data=f"owner_savelang_{group_id}_{code}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"owner_group_{group_id}", style="primary")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await safe_edit_rich_message(
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        f"<b>🌐 Set Group Language</b>\n\nSelect the language for messages sent in this group.",
        markup
    )
    await callback.answer()


@router.callback_query(F.data.startswith("owner_savelang_"))
async def owner_save_group_lang(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    parts = callback.data.split("_")
    # format: owner_savelang_{group_id}_{lang_code}
    group_id = int(parts[2])
    lang_code = parts[3]

    if lang_code not in LANG_NAMES:
        await callback.answer("Unknown language.", show_alert=True)
        return

    set_group_lang(group_id, lang_code)
    lang_name = LANG_NAMES[lang_code]
    await callback.answer(f"✅ Group language set to {lang_name}!", show_alert=True)

    # Go back to group detail
    callback.data = f"owner_group_{group_id}"
    await owner_group_detail(callback)


# ─── Group Commands Help ──────────────────────────────────────
@router.callback_query(F.data == "owner_grpcmds")
async def owner_group_commands(callback: CallbackQuery):
    if not await is_owner(callback):
        await callback.answer("Only the bot owner can access this.", show_alert=True)
        return

    lang = get_user_lang(callback.from_user.id) or "en"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("BTN_BACK", lang), callback_data="clone_main_menu", style="primary")]
    ])

    help_html = (
        f"<h3>{t('GRP_CMDS_TITLE', lang)}</h3>\n"
        f"<p>{t('GRP_CMDS_INTRO', lang)}</p>\n"
        f"<ul>"
        f"<li>{t('GRP_CMDS_CONNECT', lang)}</li>\n"
        f"<li>{t('GRP_CMDS_WHITE', lang)}</li>\n"
        f"<li>{t('GRP_CMDS_BLACK', lang)}</li>\n"
        f"</ul>"
        f"<p>{t('GRP_CMDS_NOTE_ADMIN', lang)}</p>\n"
        f"<p>{t('GRP_CMDS_NOTE_DELETE', lang)}</p>"
    )

    await safe_edit_rich_message(
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        help_html,
        markup
    )
    await callback.answer()
