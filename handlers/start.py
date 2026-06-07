from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned
import config

router = Router()

def get_gems_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.GEMS_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"💎 {pkg['name']}-{pkg['stars']} ⭐️ or ({pkg['USDT']} USDT)", callback_data=f"buy_gems_{pkg['gems']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text="✍️ Custom Amount", callback_data="custom_gems",style="success")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.PREMIUM_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"👑 {pkg['name']}-{pkg['stars']} ⭐️ or ({pkg['USDT']} USDT)", callback_data=f"buy_premium_{pkg['duration_days']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Buy Gems", callback_data="show_gems", style="primary")],
        [InlineKeyboardButton(text="👑 Buy Premium", callback_data="show_premium", style="primary")],
        [InlineKeyboardButton(text="💬 Buy Group Subscription", callback_data="show_groupsub_list", style="primary")]
    ])

def get_welcome_text() -> str:
    return (
        "👋 <b>Welcome! to the Official Payment Bot!</b>✨\n\n"
        "🤝 This bot is your central hub for purchasing Gems and Premium plans For our network of bots. "
        "All purchases are securely processed.\n\n"
        "🔹 <b>Gems:</b> Use gems for special in-bot actions. (in @anoni67_bot)\n"
        "🔹 <b>Premium:</b> Unlock exclusive features and remove restrictions. (in @anoni67_bot)\n"
        "🔹 <b>Group Sub:</b> Buy access to send messages in our exclusive groups.\n\n"
        "Select an option below to browse our packages:"
    )

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    if await is_banned(message.from_user.id):
        await message.answer("You are banned from using this bot. Request a unban @chosentwo_bot")
        return

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
            
        # Verify user is in group
        try:
            member = await message.bot.get_chat_member(chat_id, message.from_user.id)
            if member.status in ['left', 'kicked', 'banned']:
                await message.answer("You must be a member of the group to purchase a subscription.")
                return
        except Exception:
            pass # Ignore if bot can't check
            
        # Try to get chat info for a nice display
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
        for pkg in config.GROUP_SUB_PACKAGES:
            buttons.append([InlineKeyboardButton(
                text=f"💎 {pkg['name']} - {pkg['stars']} ⭐️", 
                callback_data=f"buy_groupsub_{chat_id}_{pkg['duration_days']}_{pkg['stars']}",
                style="primary"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            f"💎 <b>Subscription for {chat_link}</b>\n\n"
            "✅ You are a member!\n\n"
            "Choose a subscription package below to enable messaging in this group.",
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    elif args == "buygems":
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
        await message.answer(get_welcome_text(), reply_markup=get_main_keyboard(), parse_mode="HTML")

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
    await callback.message.edit_text(get_welcome_text(), reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.callback_query(F.data == "show_groupsub_list")
async def process_show_groupsub_list(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
        
    buttons = []
    for chat_id in config.SUPPORTED_GROUPS:
        try:
            chat = await callback.bot.get_chat(chat_id)
            title = chat.title or f"Group {chat_id}"
            buttons.append([InlineKeyboardButton(text=f"📢 {title}", callback_data=f"check_group_{chat_id}", style="primary")])
        except Exception:
            buttons.append([InlineKeyboardButton(text=f"📢 Group {chat_id}", callback_data=f"check_group_{chat_id}", style="primary")])
            
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    msg = (
        "💬 <b>Group Subscriptions</b>\n\n"
        "To send messages in our exclusive groups, you need an active subscription. "
        "This helps us maintain a high-quality community and prevent spam.\n\n"
        "👇 Please select a group below to check your status or purchase a subscription:"
    )
    await callback.message.edit_text(msg, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("check_group_"))
async def process_check_group(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
        
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
        # Not in group, send invite link
        inline_buttons = []
        if invite_link:
            inline_buttons.append([InlineKeyboardButton(text="🔗 Join Group First", url=invite_link)])
        inline_buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="show_groupsub_list")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
        await callback.message.edit_text(
            f"❌ You are not a member of <b>{title}</b>.\n\n"
            f"You must join the group before you can purchase a subscription for it.",
            reply_markup=markup,
            parse_mode="HTML"
        )
        return
        
    # Is a member, show packages
    buttons = []
    for pkg in config.GROUP_SUB_PACKAGES:
        buttons.append([InlineKeyboardButton(
            text=f"💎 {pkg['name']} - {pkg['stars']} ⭐️", 
            callback_data=f"buy_groupsub_{chat_id}_{pkg['duration_days']}_{pkg['stars']}",
            style="primary"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="show_groupsub_list")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    chat_link = f"<a href='{invite_link}'>{title}</a>" if invite_link else f"<b>{title}</b>"
    
    await callback.message.edit_text(
        f"💎 <b>Subscription for {chat_link}</b>\n\n"
        "✅ You are a member!\n\n"
        "Choose a subscription package below to enable messaging in this group.",
        reply_markup=markup,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

