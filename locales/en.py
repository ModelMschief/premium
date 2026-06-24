# ── English (source of truth) ──────────────────────────────────

# Language Picker
LANG_PICKER_PROMPT = "👋 Welcome! Please choose your language to continue:"

# Main Bot Welcome
WELCOME_TITLE = "👋 Welcome to the Official Payment Bot! ✨"
WELCOME_BODY = (
    "<p>🤝 This bot is your central hub for purchasing Gems and Premium plans for our network of bots. "
    "All purchases are securely processed.</p>\n"
    "<ul>"
    "<li><b>💎 Gems:</b> Use gems for special in-bot actions. (in @anoni67_bot)</li>"
    "<li><b>👑 Premium:</b> Unlock exclusive features and remove restrictions. (in @anoni67_bot)</li>"
    "<li><b>💬 Group Sub:</b> Buy access to send messages in our exclusive groups.</li>"
    "</ul>"
    "<p>Select an option below to browse our packages:</p>"
)

# Main Bot Keyboard
BTN_BUY_GEMS = "💎 Buy Gems"
BTN_BUY_PREMIUM = "👑 Buy Premium"
BTN_BUY_GROUP_SUB = "💬 Buy Group Subscription"
BTN_CLONE_BOT = "🤖 Clone Bot"
BTN_CHANGE_LANGUAGE = "🌐 Language"
BTN_BACK = "🔙 Back"
BTN_BACK_MAIN = "🔙 Back to Main Menu"

# Gems
GEMS_TITLE = "💎 Buy Gems"
GEMS_BODY = (
    "<p>Gems power <b>Promo Join Campaigns</b>, helping you gain verified members for your channel or group.</p>"
    "<p>✨ <b>With Gems you can:</b></p>"
    "<ul>"
    "<li>🚀 Launch Promo Join campaigns</li>"
    "<li>👥 Get verified joins</li>"
    "<li>📈 Grow your community faster</li>"
    "<li>🎯 Access higher campaign tiers</li>"
    "</ul>"
    "<blockquote>More Gems = More campaigns = More opportunities to gain verified members.</blockquote>"
    "<p>💡 Premium users spend fewer Gems on Promo Join tiers.</p>"
    '<p>📖 <a href="https://promoter-jwe5.onrender.com/promo-join.html?lang=en">Learn More About Promo Join</a></p>'
    "<p>👇 Choose a Gem package below.</p>"
)
BTN_CUSTOM_AMOUNT = "✍️ Custom Amount"

# Premium
PREMIUM_TITLE = "💎 Upgrade to Premium"
PREMIUM_BODY = (
    "<p>Unlock stronger visibility, faster promotion handling, and powerful tools designed to help your content reach more people.</p>"
    "<p>✨ <b>Premium Benefits</b></p>"
    "<ul>"
    "<li>🚀 Priority task placement</li>"
    "<li>📢 Up to <b>10 Group Promotions</b> per day</li>"
    "<li>🖼️ <b>Pic Broad</b> access</li>"
    "<li>💎 Lower <b>Promo Join</b> gem costs</li>"
    "<li>⚡ Faster processing</li>"
    "<li>🛟 Priority support</li>"
    "</ul>"
    "<blockquote>Premium helps your campaigns get noticed faster while unlocking advanced promotion features.</blockquote>"
    '<p>📖 <a href="https://promoter-jwe5.onrender.com/premium.html?lang=en">View Full Premium Details</a></p>'
    "<pre>Perfect for users who want better reach, faster growth, and stronger campaign performance.</pre>"
    "<p>👇 Select a premium plan below to purchase</p>"
)

# Group Subscriptions
GROUP_SUB_TITLE = "💬 Group Subscriptions"
GROUP_SUB_BODY = (
    "<p>To send messages in our exclusive groups, you need an active subscription. "
    "This helps us maintain a high-quality community and prevent spam.</p>\n"
    "<p>👇 Please select a group below to check your status or purchase a subscription:</p>"
)
NOT_MEMBER_TITLE = "❌ Not a Member"
NOT_MEMBER_BODY = "You are not a member of <b>{title}</b>.\nYou must join the group before you can purchase a subscription for it."
BTN_JOIN_GROUP = "🔗 Join Group First"
BTN_SELECT = "💎 Select {name}"
SUB_PACKAGES_TITLE = "💎 Subscription for {group}"
SUB_PACKAGES_NOTE = "<p>✅ You are a member!</p>\n"
SUB_PACKAGES_FOOTER = "<p>Choose a subscription package below to enable messaging in this group.</p>"
TABLE_PACKAGE = "Package"
TABLE_STARS = "Stars"
TABLE_USDT = "USDT (BEP20)"

# Clone bot (user-facing)
CLONE_WELCOME_TITLE = "👋 Welcome!"
CLONE_WELCOME_BODY = "<p>Select a group below to view subscription options and gain access to premium content.</p>"
CLONE_NO_GROUPS = "<p>This bot manages premium group subscriptions.</p>\n<p>No groups are configured yet. Please check back later!</p>"
CLONE_NO_PACKAGES_TITLE = "📦 No Packages Available"
CLONE_NO_PACKAGES_BODY = "<p>The group owner hasn't configured any subscription packages yet.</p>"
CLONE_SUB_PACKAGES_TITLE = "📦 Subscription Packages"
CLONE_SUB_ACTIVE = "✅ <b>Active subscription:</b> {days} days remaining"
CLONE_SUB_EXPIRED = "⚠️ <b>Subscription expired.</b> Renew below!"
CLONE_SUB_SELECT = "💎 Select {days} Days Plan"
CLONE_SUB_FOOTER = "<p>Select a package to purchase access:</p>"
BTN_BACK_CLONE_MENU = "🔙 Back"
TABLE_DURATION = "Duration"

# Clone bot — payment
PAYMENT_SELECT_TITLE = "🥇 Payment Selection"
PAYMENT_SELECT_FOOTER = "<p><i>Choose your preferred payment method:</i></p>"
BTN_PAY_STARS = "⭐️ Pay {stars} Stars (Instant)"
BTN_PAY_USDT = "🪙 Pay {usdt} USDT (BEP20)"
STARS_PAYMENT_SUCCESS_TITLE = "✅ Payment Successful!"
STARS_PAYMENT_ACTIVE = "<p>Your subscription is now active! You can send messages in the group.</p>"
USDT_ACTIVATED_TITLE = "✅ Subscription Activated!"
USDT_ACTIVATED_BODY = "<p>You can now send messages in the group!</p>"
PENDING_INVOICE_TITLE = "⚠️ Pending Payment Exists"
PENDING_INVOICE_BODY = "<p>You already have a pending payment for <b>{name}</b>.</p>\n<p>Please cancel it or complete the payment first before creating a new invoice.</p>"
BTN_CANCEL_PENDING = "❌ Cancel Pending: {name}"
INVOICE_TITLE = "🪙 Crypto Payment (USDT BEP20)"
INVOICE_BODY = (
    "<p>Package: <b>{name}</b></p>\n"
    "<p>Amount: <code>{amount}</code> USDT</p>\n"
    "<p>Send <b>exactly</b> {amount} USDT via <b>BSC (BEP20)</b> to:</p>\n"
    "<p><code>{address}</code></p>\n"
    "<p><i>The system will automatically detect your payment and send you an activation button.</i></p>"
)
BTN_COPY_ADDRESS = "📋 Copy Address"
BTN_CANCEL_INVOICE = "❌ Cancel Invoice"
INVOICE_CANCELED = "<p>❌ Invoice canceled successfully.</p>"
INVOICE_FAILED = "<p>❌ Failed to generate invoice. Please try again later.</p>"
VERIFY_NOT_YET_TITLE = "❌ Payment not verified yet"
VERIFY_NOT_YET_BODY = "<p>If you just sent the payment, please wait a few minutes and try again.</p>"
BTN_TRY_AGAIN = "🔄 Try Again"

# Group kick message
GROUP_KICK_MSG = (
    "🔒 <a href='tg://user?id={user_id}'>{name}</a>, this is a restricted premium community.\n\n"
    "To unlock chat privileges and become one of our privileged members, you need an <b>active subscription</b>. "
    "Join our exclusive ranks and gain full access today!\n\n"
    "Click below to secure your spot."
)
GROUP_KICK_BTN = "💎 Get Premium Access"

# Owner dashboard — group lang picker
GROUP_LANG_SET_TITLE = "🌐 Set Group Language"
GROUP_LANG_SET_BODY = "Select the language for messages sent in this group."
GROUP_LANG_SAVED = "✅ Group language set to {lang}!"
BTN_SET_GROUP_LANG = "🌐 Set Group Language"

# Owner dashboard — group commands help
GRP_CMDS_TITLE = "⚙️ Group Commands Guide"
GRP_CMDS_INTRO = "Use these commands inside your connected groups:"
GRP_CMDS_CONNECT = "<b>/connect</b> — Connect the group to your bot. The bot must be an admin first."
GRP_CMDS_WHITE = "<b>/white @username</b> (or reply to a message) — Whitelist a user so they can chat freely without a subscription."
GRP_CMDS_BLACK = "<b>/black @username</b> (or reply to a message) — Remove a user from the whitelist."
GRP_CMDS_NOTE_ADMIN = "💡 Group admins and the bot owner are <b>always allowed</b> to chat freely."
GRP_CMDS_NOTE_DELETE = "⏱ Command messages auto-delete after 5 minutes to keep the group clean."

# Owner Dashboard
OWNER_DASH_TITLE = "🏠 Owner Dashboard"
OWNER_DASH_BODY = "<ul><li>🤖 Bot: @{bot_username}</li><li>📢 Connected Groups: <b>{group_count}</b></li></ul><p>Select an option below to manage your bot.</p>"
BTN_CONNECT_GROUP = "➕ Connect New Group"
BTN_MANAGE_GROUPS = "📋 Manage Groups ({count})"
BTN_WALLET = "💰 Wallet & Withdrawals"
BTN_GROUP_CMDS = "⚙️ Group Commands"
OWNER_PKG_ADDED = "✅ <b>Package Added!</b>\n\n📦 {days} Days | ⭐️ {stars} Stars | 🪙 {usdt} USDT"
BTN_ADD_MORE_PKG = "➕ Add More Package"

# Clone Bot Menu (Main Bot)
CLONE_MAIN_TITLE = "🤖 Clone Your Own Premium Group Bot!"
CLONE_MAIN_BODY = "<p>Turn any Telegram group into a <b>premium membership</b> community.</p><p>✨ <b>How it works:</b><br>1️⃣ Create a bot with <a href='https://t.me/BotFather'>@BotFather</a><br>2️⃣ Send us the token<br>3️⃣ Add the bot to your group as admin<br>4️⃣ Set subscription packages<br>5️⃣ Start earning from group memberships!</p><p>💰 <b>You earn 90%</b> of all USDT payments + 100% of Telegram Stars.</p><p>📊 <b>Your Slots:</b> {used}/{total} used ({remaining} remaining)</p>"
BTN_CREATE_BOT = "🤖 Create My Bot"
BTN_BUY_SLOTS = "🛒 Buy +5 Slots (⭐️ {stars} / 🪙 {usdt} USDT)"
BTN_MANAGE_BOT = "{icon} Manage @{username}"
CLONE_SEND_TOKEN_TITLE = "🔑 Send Your Bot Token"
CLONE_SEND_TOKEN_BODY = "<p>Open <a href='https://t.me/BotFather'>@BotFather</a>, create a new bot, and send me the <b>API token</b> here.</p><p>It looks like:<br><code>123456:ABCdefGHIjkl...</code></p>"
