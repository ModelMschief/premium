from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned
import config

router = Router()

def get_gems_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.GEMS_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"💎 {pkg['name']} - {pkg['stars']} ⭐️", callback_data=f"buy_gems_{pkg['gems']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text="✍️ Custom Amount", callback_data="custom_gems",style="success")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.PREMIUM_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"👑 {pkg['name']} - {pkg['stars']} ⭐️", callback_data=f"buy_premium_{pkg['duration_days']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Buy Gems", callback_data="show_gems", style="primary")],
        [InlineKeyboardButton(text="👑 Buy Premium", callback_data="show_premium", style="primary")]
    ])

def get_welcome_text() -> str:
    return (
        "👋 *Welcome to the Official Payment Bot!*\n\n"
        "🤝This bot is your central hub for purchasing Gems and Premium plans For our network of bots."
        "All purchases are securely processed \n\n"
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
        msg = f"""💎 <b>Buy Gems</b>

Gems power <b>Promo Join Campaigns</b>, helping you gain verified members for your channel or group.

✨ <b>With Gems you can:</b>
• 🚀 Launch Promo Join campaigns
• 👥 Get verified joins
• 📈 Grow your community faster
• 🎯 Access higher campaign tiers
<blockquote>
More Gems = More campaigns = More opportunities to gain verified members.
</blockquote>
💡 Premium users spend fewer Gems on Promo Join tiers.

📖 <a href="https://promoter-jwe5.onrender.com/promo-join.html?lang=en">Learn More About Promo Join</a>

👇 Choose a Gem package below."""
        await message.answer(msg, reply_markup=get_gems_keyboard(), parse_mode="HTML")
    elif args == "buypremium":
        msg = f"""💎 <b>Upgrade to Premium</b>

Unlock stronger visibility, faster promotion handling, and powerful tools designed to help your content reach more people.

✨ <b>Premium Benefits</b>

• 🚀 Priority task placement
• 📢 Up to <b>10 Group Promotions</b> per day
• 🖼️ <b>Pic Broad</b> access
• 💎 Lower <b>Promo Join</b> gem costs
• ⚡ Faster processing
• 🛟 Priority support
<blockquote>
Premium helps your campaigns get noticed faster while unlocking advanced promotion features.
</blockquote>
📖 <a href="https://promoter-jwe5.onrender.com/premium.html?lang=en">View Full Premium Details</a>
<pre>Perfect for users who want better reach, faster growth, and stronger campaign performance.</pre>
👇 Select a premium plan below to to purchase"""
        await message.answer(msg, reply_markup=get_premium_keyboard(), parse_mode="HTML")
    else:
        await message.answer(get_welcome_text(), reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "show_gems")
async def process_show_gems(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    msg = f"""💎 <b>Buy Gems</b>

Gems power <b>Promo Join Campaigns</b>, helping you gain verified members for your channel or group.

✨ <b>With Gems you can:</b>
• 🚀 Launch Promo Join campaigns
• 👥 Get verified joins
• 📈 Grow your community faster
• 🎯 Access higher campaign tiers
<blockquote>
More Gems = More campaigns = More opportunities to gain verified members.
</blockquote>
💡 Premium users spend fewer Gems on Promo Join tiers.

📖 <a href="https://promoter-jwe5.onrender.com/promo-join.html?lang=en">Learn More About Promo Join</a>

👇 Choose a Gem package below."""
    await callback.message.edit_text(msg, reply_markup=get_gems_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "show_premium")
async def process_show_premium(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    
    msg = f"""💎 <b>Upgrade to Premium</b>

Unlock stronger visibility, faster promotion handling, and powerful tools designed to help your content reach more people.

✨ <b>Premium Benefits</b>

• 🚀 Priority task placement
• 📢 Up to <b>10 Group Promotions</b> per day
• 🖼️ <b>Pic Broad</b> access
• 💎 Lower <b>Promo Join</b> gem costs
• ⚡ Faster processing
• 🛟 Priority support
<blockquote>
Premium helps your campaigns get noticed faster while unlocking advanced promotion features.
</blockquote>
📖 <a href="https://promoter-jwe5.onrender.com/premium.html?lang=en">View Full Premium Details</a>
<pre>Perfect for users who want better reach, faster growth, and stronger campaign performance.</pre>
👇 Select a premium plan below to to purchase"""
    await callback.message.edit_text(msg, reply_markup=get_premium_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    await callback.message.edit_text(get_welcome_text(), reply_markup=get_main_keyboard(), parse_mode="Markdown")
