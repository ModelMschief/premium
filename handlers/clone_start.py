from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.sqlite import (
    get_cloned_bot_by_id, get_connected_groups, get_group_packages,
    get_clone_subscription, get_user_lang, get_group_lang
)
import config
import datetime
from rich_utils import safe_send_rich_message, safe_edit_rich_message
from locales import t
from handlers.language import build_lang_picker_markup

router = Router()


def get_viral_button() -> list:
    """Returns the viral growth button that appears on every screen."""
    main_bot = config.MAIN_BOT_USERNAME
    if main_bot:
        return [InlineKeyboardButton(text="🤖Get Your Own Bot FREE!", url=f"https://t.me/{main_bot}?start=clone")]
    return []


def _resolve_lang(user_id: int, group_id: int = None) -> str:
    """Resolve language: group lang → user lang → English."""
    if group_id:
        gl = get_group_lang(group_id)
        if gl and gl != "en":
            return gl
    ul = get_user_lang(user_id)
    return ul if ul else "en"


@router.message(CommandStart())
async def clone_cmd_start(message: Message, command: CommandObject):
    bot_info = await message.bot.get_me()
    bot_id = bot_info.id
    clone_data = get_cloned_bot_by_id(bot_id)

    if not clone_data:
        await message.answer("⚠️ This bot is not configured properly.")
        return

    owner_user_id = clone_data["owner_user_id"]
    user_id = message.from_user.id

    # ─── Owner enters dashboard ──────────────────────────
    if user_id == owner_user_id:
        await show_owner_dashboard(message, bot_id, bot_info.username)
        return

    # ─── First-time user: show language picker ───────────
    if get_user_lang(user_id) is None:
        await safe_send_rich_message(
            message.bot, message.chat.id,
            "<h2>🌐 Select Language / Выберите язык / 语言选择</h2>",
            build_lang_picker_markup("setlang")
        )
        return

    # ─── Handle /start sub_{group_id} ────────────────────
    args = command.args
    if args and args.startswith("sub_"):
        try:
            group_id = int(args.split("_")[1])
        except (IndexError, ValueError):
            await message.answer("Invalid subscription link.")
            return

        await show_group_subscription(message, group_id, bot_id, bot_info.username)
        return

    # ─── Regular user — show available groups ────────────
    lang = _resolve_lang(user_id)
    groups = get_connected_groups(bot_id)

    if not groups:
        viral = get_viral_button()
        buttons = []
        if viral:
            buttons.append(viral)
        markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

        msg_html = (
            f"<h3>{t('CLONE_WELCOME_TITLE', lang)}</h3>\n"
            f"{t('CLONE_NO_GROUPS', lang)}"
        )
        await safe_send_rich_message(message.bot, message.chat.id, msg_html, markup)
        return

    buttons = []
    for g in groups:
        buttons.append([InlineKeyboardButton(
            text=f"📢 {g['group_title']}",
            callback_data=f"clonesub_{g['group_id']}",
            style="primary"
        )])

    viral = get_viral_button()
    if viral:
        buttons.append(viral)

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    msg_html = (
        f"<h3>{t('CLONE_WELCOME_TITLE', lang)}</h3>\n"
        f"{t('CLONE_WELCOME_BODY', lang)}"
    )
    await safe_send_rich_message(message.bot, message.chat.id, msg_html, markup)


async def show_owner_dashboard(message: Message, bot_id: int, bot_username: str):
    """Show the owner's management dashboard."""
    groups = get_connected_groups(bot_id)
    group_count = len(groups)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Connect New Group", callback_data="owner_connect_group", style="primary")],
        [InlineKeyboardButton(text=f"📋 Manage Groups ({group_count})", callback_data="owner_manage_groups", style="primary")],
        [InlineKeyboardButton(text="💰 Wallet & Withdrawals", callback_data="owner_wallet", style="primary")],
    ])

    msg_html = (
        f"<h3>🏠 Owner Dashboard</h3>\n"
        f"<ul>"
        f"<li>🤖 Bot: @{bot_username}</li>\n"
        f"<li>📢 Connected Groups: <b>{group_count}</b></li>\n"
        f"</ul>"
        f"<p>Select an option below to manage your bot.</p>"
    )
    await safe_send_rich_message(message.bot, message.chat.id, msg_html, markup)


async def show_group_subscription(message_or_callback, group_id: int, bot_id: int, bot_username: str):
    """Show subscription packages for a specific group to a regular user."""
    packages = get_group_packages(group_id)
    user_id = message_or_callback.from_user.id
    lang = _resolve_lang(user_id, group_id)

    if not packages:
        viral = get_viral_button()
        buttons = [[InlineKeyboardButton(text=t("BTN_BACK_CLONE_MENU", lang), callback_data="clone_main_menu")]]
        if viral:
            buttons.append(viral)
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        msg_html = (
            f"<h3>{t('CLONE_NO_PACKAGES_TITLE', lang)}</h3>\n"
            f"{t('CLONE_NO_PACKAGES_BODY', lang)}"
        )
        if isinstance(message_or_callback, Message):
            await safe_send_rich_message(message_or_callback.bot, message_or_callback.chat.id, msg_html, markup)
        else:
            await safe_edit_rich_message(message_or_callback.bot, message_or_callback.message.chat.id, message_or_callback.message.message_id, msg_html, markup)
        return

    # Check current subscription
    sub_expiry = get_clone_subscription(user_id, group_id)
    sub_status = ""
    if sub_expiry:
        expiry_dt = datetime.datetime.fromisoformat(sub_expiry)
        now = datetime.datetime.now(datetime.timezone.utc)
        if expiry_dt > now:
            remaining = (expiry_dt - now).days
            sub_status = f"<p>{t('CLONE_SUB_ACTIVE', lang).format(days=remaining)}</p>\n"
        else:
            sub_status = f"<p>{t('CLONE_SUB_EXPIRED', lang)}</p>\n"

    buttons = []
    table_html = f"<table border=\"1\"><tr><th>{t('TABLE_DURATION', lang)}</th><th>{t('TABLE_STARS', lang)}</th><th>{t('TABLE_USDT', lang)}</th></tr>"
    for pkg in packages:
        table_html += f"<tr><td>{pkg['duration_days']} {'Days' if lang == 'en' else 'Days'}</td><td>{pkg['stars_price']} ⭐️</td><td>{pkg['usdt_price']} USDT</td></tr>"
        buttons.append([InlineKeyboardButton(
            text=t("CLONE_SUB_SELECT", lang).format(days=pkg['duration_days']),
            callback_data=f"clonebuy_{group_id}_{pkg['package_id']}",
            style="primary"
        )])
    table_html += "</table>"

    buttons.append([InlineKeyboardButton(text=t("BTN_BACK_CLONE_MENU", lang), callback_data="clone_main_menu")])
    viral = get_viral_button()
    if viral:
        buttons.append(viral)

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    msg_html = (
        f"<h3>{t('CLONE_SUB_PACKAGES_TITLE', lang)}</h3>\n"
        f"{sub_status}"
        f"{table_html}\n"
        f"{t('CLONE_SUB_FOOTER', lang)}"
    )

    if isinstance(message_or_callback, Message):
        await safe_send_rich_message(message_or_callback.bot, message_or_callback.chat.id, msg_html, markup)
    else:
        await safe_edit_rich_message(message_or_callback.bot, message_or_callback.message.chat.id, message_or_callback.message.message_id, msg_html, markup)


# ─── Callback: View group subscription packages ─────────────
@router.callback_query(F.data.startswith("clonesub_"))
async def view_group_sub(callback: CallbackQuery):
    group_id = int(callback.data.split("_")[1])
    bot_info = await callback.bot.get_me()
    await show_group_subscription(callback, group_id, bot_info.id, bot_info.username)
    await callback.answer()


# ─── Callback: Back to clone main menu ───────────────────────
@router.callback_query(F.data == "clone_main_menu")
async def clone_main_menu(callback: CallbackQuery):
    bot_info = await callback.bot.get_me()
    bot_id = bot_info.id
    clone_data = get_cloned_bot_by_id(bot_id)

    if not clone_data:
        await callback.answer("Bot not configured.", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = _resolve_lang(user_id)

    # Check if owner
    if user_id == clone_data["owner_user_id"]:
        groups = get_connected_groups(bot_id)
        group_count = len(groups)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Connect New Group", callback_data="owner_connect_group", style="primary")],
            [InlineKeyboardButton(text=f"📋 Manage Groups ({group_count})", callback_data="owner_manage_groups", style="primary")],
            [InlineKeyboardButton(text="💰 Wallet & Withdrawals", callback_data="owner_wallet", style="primary")],
        ])
        msg_html = (
            f"<h3>🏠 Owner Dashboard</h3>\n"
            f"<ul>"
            f"<li>🤖 Bot: @{bot_info.username}</li>\n"
            f"<li>📢 Connected Groups: <b>{group_count}</b></li>\n"
            f"</ul>"
            f"<p>Select an option below to manage your bot.</p>"
        )
        await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
    else:
        groups = get_connected_groups(bot_id)
        buttons = []
        for g in groups:
            buttons.append([InlineKeyboardButton(
                text=f"📢 {g['group_title']}",
                callback_data=f"clonesub_{g['group_id']}",
                style="primary"
            )])
        viral = get_viral_button()
        if viral:
            buttons.append(viral)
        markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

        msg_html = (
            f"<h3>{t('CLONE_WELCOME_TITLE', lang)}</h3>\n"
            f"{t('CLONE_WELCOME_BODY', lang)}"
        )
        await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
    await callback.answer()
