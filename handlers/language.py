"""
Shared language picker handler.
Registered by BOTH the main bot and every clone bot dispatcher.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.sqlite import set_user_lang
from locales import LANG_NAMES, t

router = Router()

LANGS = list(LANG_NAMES.keys())  # ['en', 'ru', 'uk', 'zh', 'hi', 'ar', 'ur', 'bn']


def build_lang_picker_markup(callback_prefix: str = "setlang") -> InlineKeyboardMarkup:
    """Build the 2-column language picker keyboard."""
    buttons = []
    items = list(LANG_NAMES.items())
    for i in range(0, len(items), 2):
        row = []
        for code, label in items[i:i+2]:
            row.append(InlineKeyboardButton(text=label, callback_data=f"{callback_prefix}_{code}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Main-bot language change (settings) ─────────────────────
@router.callback_query(F.data == "show_language_picker")
async def show_language_picker_callback(callback: CallbackQuery):
    """Re-show the language picker from within the main menu (language button)."""
    await callback.message.edit_text(
        t("LANG_PICKER_PROMPT", "en"),  # always show picker prompt in English for discoverability
        reply_markup=build_lang_picker_markup("setlang")
    )
    await callback.answer()


# ── Handle selection ─────────────────────────────────────────
@router.callback_query(F.data.startswith("setlang_"))
async def handle_lang_selection(callback: CallbackQuery):
    lang = callback.data.split("_", 1)[1]
    if lang not in LANGS:
        await callback.answer("Unknown language.", show_alert=True)
        return

    set_user_lang(callback.from_user.id, lang)
    lang_name = LANG_NAMES.get(lang, lang)

    await callback.answer(f"✅ Language set to {lang_name}", show_alert=True)

    # Dismiss the picker — the next time the user interacts the correct language will load.
    # We just edit the message to show a brief confirmation.
    await callback.message.edit_text(
        f"✅ Language set to <b>{lang_name}</b>!\n\n"
        f"Use /start to go back to the main menu.",
        parse_mode="HTML"
    )
