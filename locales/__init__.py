"""
Localization helper.

Usage:
    from locales import t
    text = t("WELCOME_TITLE", lang)
"""
from locales import en, ru, uk, zh, hi, ar, ur, bn

_LANGS = {
    "en": en,
    "ru": ru,
    "uk": uk,
    "zh": zh,
    "hi": hi,
    "ar": ar,
    "ur": ur,
    "bn": bn,
}

LANG_NAMES = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "uk": "🇺🇦 Українська",
    "zh": "🇨🇳 中文",
    "hi": "🇮🇳 हिन्दी",
    "ar": "🇸🇦 العربية",
    "ur": "🇵🇰 اردو",
    "bn": "🇧🇩 বাংলা",
}


def t(key: str, lang: str = "en") -> str:
    """Return a translated string for the given key and language code."""
    module = _LANGS.get(lang, en)
    value = getattr(module, key, None)
    if value is None:
        # Fall back to English
        value = getattr(en, key, key)
    return value
