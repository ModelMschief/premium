from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned
import config
from rich_utils import safe_send_rich_message, safe_edit_rich_message

router = Router()

def get_gems_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.GEMS_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"💎 {pkg['name']} | ⭐️ {pkg['stars']} | 🪙 {pkg['USDT']} USDT", callback_data=f"buy_gems_{pkg['gems']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text="✍️ Custom Amount", callback_data="custom_gems", style="primary")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for pkg in config.PREMIUM_PACKAGES:
        buttons.append([InlineKeyboardButton(text=f"👑 {pkg['name']} | ⭐️ {pkg['stars']} | 🪙 {pkg['USDT']} USDT", callback_data=f"buy_premium_{pkg['duration_days']}_{pkg['stars']}", style="primary")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Buy Gems", callback_data="show_gems", style="primary")],
        [InlineKeyboardButton(text="👑 Buy Premium", callback_data="show_premium", style="primary")],
        [InlineKeyboardButton(text="💬 Buy Group Subscription", callback_data="show_groupsub_list", style="primary")],
        [InlineKeyboardButton(text="🤖 Clone Bot", callback_data="show_clone", style="primary")]
    ])

def get_welcome_text() -> str:
    return (
        "<h1>👋 Welcome to the Official Payment Bot! ✨</h1>\n"
        "<p>🤝 This bot is your central hub for purchasing Gems and Premium plans for our network of bots. "
        "All purchases are securely processed.</p>\n"
        "<ul>"
        "<li><b>💎 Gems:</b> Use gems for special in-bot actions. (in @anoni67_bot)</li>"
        "<li><b>👑 Premium:</b> Unlock exclusive features and remove restrictions. (in @anoni67_bot)</li>"
        "<li><b>💬 Group Sub:</b> Buy access to send messages in our exclusive groups.</li>"
        "</ul>"
        "<p>Select an option below to browse our packages:</p>"
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
        table_html = "<table border=\"1\"><tr><th>Package</th><th>Stars</th><th>USDT</th></tr>"
        for pkg in config.GROUP_SUB_PACKAGES:
            usdt_val = round(pkg['stars'] * 0.02, 2)
            table_html += f"<tr><td>{pkg['name']}</td><td>{pkg['stars']} ⭐️</td><td>{usdt_val} USDT</td></tr>"
            buttons.append([InlineKeyboardButton(
                text=f"💎 Select {pkg['name']}", 
                callback_data=f"buy_groupsub_{chat_id}_{pkg['duration_days']}_{pkg['stars']}",
                style="primary"
            )])
        table_html += "</table>"

        buttons.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        msg_html = (
            f"<h3>💎 Subscription for {chat_link}</h3>\n"
            "<p>✅ You are a member!</p>\n"
            f"{table_html}\n"
            "<p>Choose a subscription package below to enable messaging in this group.</p>"
        )

        await safe_send_rich_message(
            bot=message.bot,
            chat_id=message.chat.id,
            html_content=msg_html,
            reply_markup=markup,
            disable_web_page_preview=True
        )

    elif args == "buygems":
        msg = f"""<h3>💎 Buy Gems</h3>
<p>Gems power <b>Promo Join Campaigns</b>, helping you gain verified members for your channel or group.</p>
<p>✨ <b>With Gems you can:</b></p>
<ul>
<li>🚀 Launch Promo Join campaigns</li>
<li>👥 Get verified joins</li>
<li>📈 Grow your community faster</li>
<li>🎯 Access higher campaign tiers</li>
</ul>
<blockquote>More Gems = More campaigns = More opportunities to gain verified members.</blockquote>
<p>💡 Premium users spend fewer Gems on Promo Join tiers.</p>
<p>📖 <a href="https://promoter-jwe5.onrender.com/promo-join.html?lang=en">Learn More About Promo Join</a></p>
<p>👇 Choose a Gem package below.</p>"""
        await safe_send_rich_message(message.bot, message.chat.id, msg, get_gems_keyboard())
    elif args == "buypremium":
        msg = f"""<h3>💎 Upgrade to Premium</h3>
<p>Unlock stronger visibility, faster promotion handling, and powerful tools designed to help your content reach more people.</p>
<p>✨ <b>Premium Benefits</b></p>
<ul>
<li>🚀 Priority task placement</li>
<li>📢 Up to <b>10 Group Promotions</b> per day</li>
<li>🖼️ <b>Pic Broad</b> access</li>
<li>💎 Lower <b>Promo Join</b> gem costs</li>
<li>⚡ Faster processing</li>
<li>🛟 Priority support</li>
</ul>
<blockquote>Premium helps your campaigns get noticed faster while unlocking advanced promotion features.</blockquote>
<p>📖 <a href="https://promoter-jwe5.onrender.com/premium.html?lang=en">View Full Premium Details</a></p>
<pre>Perfect for users who want better reach, faster growth, and stronger campaign performance.</pre>
<p>👇 Select a premium plan below to purchase</p>"""
        await safe_send_rich_message(message.bot, message.chat.id, msg, get_premium_keyboard())
    elif args == "clone":
        # Redirect to clone feature — handled by clone.py router
        from handlers.clone import show_clone_info
        from database.sqlite import get_clone_quota, get_cloned_bots_by_owner
        quota = get_clone_quota(message.from_user.id)
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

        my_bots = get_cloned_bots_by_owner(message.from_user.id)
        if my_bots:
            msg += "<p><b>Your Bots:</b></p><ul>"
            for b in my_bots:
                status_icon = "🟢" if b["clone_status"] == "active" else "🔴"
                msg += f"<li>{status_icon} @{b['bot_username']}</li>"
            msg += "</ul>"

        buttons.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await safe_send_rich_message(message.bot, message.chat.id, msg, markup, disable_web_page_preview=True)
    else:
        await safe_send_rich_message(message.bot, message.chat.id, get_welcome_text(), get_main_keyboard())

@router.callback_query(F.data == "show_gems")
async def process_show_gems(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    msg = f"""<h3>💎 Buy Gems</h3>
<p>Gems power <b>Promo Join Campaigns</b>, helping you gain verified members for your channel or group.</p>
<p>✨ <b>With Gems you can:</b></p>
<ul>
<li>🚀 Launch Promo Join campaigns</li>
<li>👥 Get verified joins</li>
<li>📈 Grow your community faster</li>
<li>🎯 Access higher campaign tiers</li>
</ul>
<blockquote>More Gems = More campaigns = More opportunities to gain verified members.</blockquote>
<p>💡 Premium users spend fewer Gems on Promo Join tiers.</p>
<p>📖 <a href="https://promoter-jwe5.onrender.com/promo-join.html?lang=en">Learn More About Promo Join</a></p>
<p>👇 Choose a Gem package below.</p>"""
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg, get_gems_keyboard())
    await callback.answer()

@router.callback_query(F.data == "show_premium")
async def process_show_premium(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    
    msg = f"""<h3>💎 Upgrade to Premium</h3>
<p>Unlock stronger visibility, faster promotion handling, and powerful tools designed to help your content reach more people.</p>
<p>✨ <b>Premium Benefits</b></p>
<ul>
<li>🚀 Priority task placement</li>
<li>📢 Up to <b>10 Group Promotions</b> per day</li>
<li>🖼️ <b>Pic Broad</b> access</li>
<li>💎 Lower <b>Promo Join</b> gem costs</li>
<li>⚡ Faster processing</li>
<li>🛟 Priority support</li>
</ul>
<blockquote>Premium helps your campaigns get noticed faster while unlocking advanced promotion features.</blockquote>
<p>📖 <a href="https://promoter-jwe5.onrender.com/premium.html?lang=en">View Full Premium Details</a></p>
<pre>Perfect for users who want better reach, faster growth, and stronger campaign performance.</pre>
<p>👇 Select a premium plan below to purchase</p>"""
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg, get_premium_keyboard())
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, get_welcome_text(), get_main_keyboard())
    await callback.answer()

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
        "<h3>💬 Group Subscriptions</h3>\n"
        "<p>To send messages in our exclusive groups, you need an active subscription. "
        "This helps us maintain a high-quality community and prevent spam.</p>\n"
        "<p>👇 Please select a group below to check your status or purchase a subscription:</p>"
    )
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg, markup)
    await callback.answer()

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
            inline_buttons.append([InlineKeyboardButton(text="🔗 Join Group First", url=invite_link, style="primary")])
        inline_buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="show_groupsub_list")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
        msg_html = (
            f"<h3>❌ Not a Member</h3>\n"
            f"<p>You are not a member of <b>{title}</b>.</p>\n"
            f"<p>You must join the group before you can purchase a subscription for it.</p>"
        )
        await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
        await callback.answer()
        return
        
    # Is a member, show packages
    buttons = []
    table_html = "<table border=\"1\"><tr><th>Package</th><th>Stars</th><th>USDT</th></tr>"
    for pkg in config.GROUP_SUB_PACKAGES:
        usdt_val = round(pkg['stars'] * 0.02, 2)
        table_html += f"<tr><td>{pkg['name']}</td><td>{pkg['stars']} ⭐️</td><td>{usdt_val} USDT</td></tr>"
        buttons.append([InlineKeyboardButton(
            text=f"💎 Select {pkg['name']}", 
            callback_data=f"buy_groupsub_{chat_id}_{pkg['duration_days']}_{pkg['stars']}",
            style="primary"
        )])
    table_html += "</table>"
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="show_groupsub_list")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    chat_link = f"<a href='{invite_link}'>{title}</a>" if invite_link else f"<b>{title}</b>"
    
    msg_html = (
        f"<h3>💎 Subscription for {chat_link}</h3>\n"
        "<p>✅ You are a member!</p>\n"
        f"{table_html}\n"
        "<p>Choose a subscription package below to enable messaging in this group.</p>"
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
