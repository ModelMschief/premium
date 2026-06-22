from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned
from database.sqlite import get_user_lang
import config
from rich_utils import safe_send_rich_message, safe_edit_rich_message
from locales import t
from handlers.language import build_lang_picker_markup

router = Router()


# ── Helper: resolve user language ────────────────────────────
def _lang(user_id: int) -> str:
    return get_user_lang(user_id) or "en"


# ── Keyboards ────────────────────────────────────────────────
def get_gems_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.GEMS_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"💎 {pkg['name']} | ⭐️ {pkg['stars']} | 🪙 {pkg['USDT']} USDT", callback_data=f"buy_gems_{pkg['gems']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text=t("BTN_CUSTOM_AMOUNT", lang), callback_data="custom_gems", style="primary")])
    buttons.append([InlineKeyboardButton(text=t("BTN_BACK_MAIN", lang), callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.PREMIUM_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"👑 {pkg['name']} | ⭐️ {pkg['stars']} | 🪙 {pkg['USDT']} USDT", callback_data=f"buy_premium_{pkg['duration_days']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text=t("BTN_BACK_MAIN", lang), callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("BTN_BUY_GEMS", lang), callback_data="show_gems", style="primary")],
        [InlineKeyboardButton(text=t("BTN_BUY_PREMIUM", lang), callback_data="show_premium", style="primary")],
        [InlineKeyboardButton(text=t("BTN_BUY_GROUP_SUB", lang), callback_data="show_groupsub_list", style="primary")],
        [InlineKeyboardButton(text=t("BTN_CLONE_BOT", lang), callback_data="show_clone", style="primary")],
        [InlineKeyboardButton(text=t("BTN_CHANGE_LANGUAGE", lang), callback_data="show_language_picker")],
    ])

def get_welcome_text(lang: str = "en") -> str:
    return f"<h1>{t('WELCOME_TITLE', lang)}</h1>\n{t('WELCOME_BODY', lang)}"


# ── /start ───────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    if await is_banned(message.from_user.id):
        await message.answer("You are banned from using this bot. Request a unban @chosentwo_bot")
        return

    user_id = message.from_user.id
    lang_code = get_user_lang(user_id)

    # ── First-time user: show language picker ────────────────
    if lang_code is None:
        await safe_send_rich_message(
            message.bot, message.chat.id,
            f"<h2>🌐 Select Language / Выберите язык / 语言选择</h2>",
            build_lang_picker_markup("setlang")
        )
        return

    lang = lang_code
    args = command.args

    if args and args.startswith("subs_"):
        try:
            chat_id = int(args.split("_")[1])
        except (IndexError, ValueError):
            await message.answer("Invalid subscription link.")
            return

        if chat_id not in config.SUPPORTED_GROUPS:
            await message.answer("This group is not supported for subscriptions.")
            return

        try:
            member = await message.bot.get_chat_member(chat_id, user_id)
            if member.status in ['left', 'kicked', 'banned']:
                await message.answer("You must be a member of the group to purchase a subscription.")
                return
        except Exception:
            pass

        try:
            chat = await message.bot.get_chat(chat_id)
            title = chat.title or f"Group {chat_id}"
            invite_link = chat.invite_link
            if not invite_link:
                invite_link = await message.bot.export_chat_invite_link(chat_id)
        except Exception:
            title = f"Group {chat_id}"
            invite_link = None

        chat_link = f"<a href='{invite_link}'>{title}</a>" if invite_link else f"<b>{title}</b>"

        buttons = []
        table_html = f"<table border=\"1\"><tr><th>{t('TABLE_PACKAGE', lang)}</th><th>{t('TABLE_STARS', lang)}</th><th>{t('TABLE_USDT', lang)}</th></tr>"
        for pkg in config.GROUP_SUB_PACKAGES:
            usdt_val = round(pkg['stars'] * 0.02, 2)
            table_html += f"<tr><td>{pkg['name']}</td><td>{pkg['stars']} ⭐️</td><td>{usdt_val} USDT</td></tr>"
            buttons.append([InlineKeyboardButton(
                text=t("BTN_SELECT", lang).format(name=pkg['name']),
                callback_data=f"buy_groupsub_{chat_id}_{pkg['duration_days']}_{pkg['stars']}",
                style="primary"
            )])
        table_html += "</table>"

        buttons.append([InlineKeyboardButton(text=t("BTN_BACK_MAIN", lang), callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        msg_html = (
            f"<h3>{t('SUB_PACKAGES_TITLE', lang).format(group=chat_link)}</h3>\n"
            f"{t('SUB_PACKAGES_NOTE', lang)}"
            f"{table_html}\n"
            f"{t('SUB_PACKAGES_FOOTER', lang)}"
        )

        await safe_send_rich_message(
            bot=message.bot,
            chat_id=message.chat.id,
            html_content=msg_html,
            reply_markup=markup,
            disable_web_page_preview=True
        )

    elif args == "buygems":
        await safe_send_rich_message(message.bot, message.chat.id, f"<h3>{t('GEMS_TITLE', lang)}</h3>\n{t('GEMS_BODY', lang)}", get_gems_keyboard(lang))

    elif args == "buypremium":
        await safe_send_rich_message(message.bot, message.chat.id, f"<h3>{t('PREMIUM_TITLE', lang)}</h3>\n{t('PREMIUM_BODY', lang)}", get_premium_keyboard(lang))

    elif args == "clone":
        from handlers.clone import show_clone_info
        from database.sqlite import get_clone_quota, get_cloned_bots_by_owner
        quota = get_clone_quota(user_id)
        remaining = quota["total_slots"] - quota["used_slots"]

        msg = (
            "<h3>🤖 Clone Your Own Premium Group Bot!</h3>\n"
            "<p>Turn any Telegram group into a <b>premium membership</b> community.</p>\n"
            "<p>✨ <b>How it works:</b></p>\n"
            "<ol>"
            "<li>Create a bot with <a href='https://t.me/BotFather'>@BotFather</a></li>"
            "<li>Send us the token</li>"
            "<li>Add the bot to your group as admin</li>"
            "<li>Set subscription packages</li>"
            "<li>Start earning from group memberships!</li>"
            "</ol>\n"
            "<p>💰 <b>You earn 90%</b> of all USDT payments + 100% of Telegram Stars.</p>\n"
            f"<p>📊 <b>Your Slots:</b> {quota['used_slots']}/{quota['total_slots']} used ({remaining} remaining)</p>\n"
        )

        buttons = [[InlineKeyboardButton(text="🤖 Create My Bot", callback_data="clone_create", style="primary")]]
        if remaining <= 0:
            buttons.append([InlineKeyboardButton(text=f"🛒 Buy +5 Slots (⭐️ {config.CLONE_SLOT_STARS_PRICE} / 🪙 {config.CLONE_SLOT_USDT_PRICE} USDT)", callback_data="clone_buy_slots", style="primary")])

        my_bots = get_cloned_bots_by_owner(user_id)
        if my_bots:
            msg += "<p><b>Your Bots:</b></p><ul>"
            for b in my_bots:
                status_icon = "🟢" if b["clone_status"] == "active" else "🔴"
                msg += f"<li>{status_icon} @{b['bot_username']}</li>"
            msg += "</ul>"

        buttons.append([InlineKeyboardButton(text=t("BTN_BACK_MAIN", lang), callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await safe_send_rich_message(message.bot, message.chat.id, msg, markup, disable_web_page_preview=True)
    else:
        await safe_send_rich_message(message.bot, message.chat.id, get_welcome_text(lang), get_main_keyboard(lang))


@router.callback_query(F.data == "show_gems")
async def process_show_gems(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    lang = _lang(callback.from_user.id)
    msg = f"<h3>{t('GEMS_TITLE', lang)}</h3>\n{t('GEMS_BODY', lang)}"
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg, get_gems_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "show_premium")
async def process_show_premium(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    lang = _lang(callback.from_user.id)
    msg = f"<h3>{t('PREMIUM_TITLE', lang)}</h3>\n{t('PREMIUM_BODY', lang)}"
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg, get_premium_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    lang = _lang(callback.from_user.id)
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, get_welcome_text(lang), get_main_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "show_groupsub_list")
async def process_show_groupsub_list(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    lang = _lang(callback.from_user.id)
    buttons = []
    for chat_id in config.SUPPORTED_GROUPS:
        try:
            chat = await callback.bot.get_chat(chat_id)
            title = chat.title or f"Group {chat_id}"
            buttons.append([InlineKeyboardButton(text=f"📢 {title}", callback_data=f"check_group_{chat_id}", style="primary")])
        except Exception:
            buttons.append([InlineKeyboardButton(text=f"📢 Group {chat_id}", callback_data=f"check_group_{chat_id}", style="primary")])

    buttons.append([InlineKeyboardButton(text=t("BTN_BACK_MAIN", lang), callback_data="main_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    msg = f"<h3>{t('GROUP_SUB_TITLE', lang)}</h3>\n{t('GROUP_SUB_BODY', lang)}"
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg, markup)
    await callback.answer()

@router.callback_query(F.data.startswith("check_group_"))
async def process_check_group(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    lang = _lang(callback.from_user.id)
    chat_id = int(callback.data.split("_")[2])

    try:
        chat = await callback.bot.get_chat(chat_id)
        title = chat.title or f"Group {chat_id}"
        invite_link = chat.invite_link
        if not invite_link:
            invite_link = await callback.bot.export_chat_invite_link(chat_id)
    except Exception:
        title = f"Group {chat_id}"
        invite_link = None

    try:
        member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
        is_member = member.status not in ['left', 'kicked', 'banned']
    except Exception:
        is_member = False

    if not is_member:
        inline_buttons = []
        if invite_link:
            inline_buttons.append([InlineKeyboardButton(text=t("BTN_JOIN_GROUP", lang), url=invite_link, style="primary")])
        inline_buttons.append([InlineKeyboardButton(text=t("BTN_BACK", lang), callback_data="show_groupsub_list")])

        markup = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
        msg_html = (
            f"<h3>{t('NOT_MEMBER_TITLE', lang)}</h3>\n"
            f"<p>{t('NOT_MEMBER_BODY', lang).format(title=title)}</p>"
        )
        await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
        await callback.answer()
        return

    buttons = []
    table_html = f"<table border=\"1\"><tr><th>{t('TABLE_PACKAGE', lang)}</th><th>{t('TABLE_STARS', lang)}</th><th>{t('TABLE_USDT', lang)}</th></tr>"
    for pkg in config.GROUP_SUB_PACKAGES:
        usdt_val = round(pkg['stars'] * 0.02, 2)
        table_html += f"<tr><td>{pkg['name']}</td><td>{pkg['stars']} ⭐️</td><td>{usdt_val} USDT</td></tr>"
        buttons.append([InlineKeyboardButton(
            text=t("BTN_SELECT", lang).format(name=pkg['name']),
            callback_data=f"buy_groupsub_{chat_id}_{pkg['duration_days']}_{pkg['stars']}",
            style="primary"
        )])
    table_html += "</table>"
    buttons.append([InlineKeyboardButton(text=t("BTN_BACK", lang), callback_data="show_groupsub_list")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    chat_link = f"<a href='{invite_link}'>{title}</a>" if invite_link else f"<b>{title}</b>"
    msg_html = (
        f"<h3>{t('SUB_PACKAGES_TITLE', lang).format(group=chat_link)}</h3>\n"
        f"{t('SUB_PACKAGES_NOTE', lang)}"
        f"{table_html}\n"
        f"{t('SUB_PACKAGES_FOOTER', lang)}"
    )

    await safe_edit_rich_message(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        html_content=msg_html,
        reply_markup=markup,
        disable_web_page_preview=True
    )
    await callback.answer()
