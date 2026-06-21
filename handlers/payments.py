from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned, save_gem_payment, save_premium_payment
from database.sqlite import log_local_payment, extend_group_subscription, get_pending_crypto_invoices, add_crypto_invoice, update_crypto_invoice_status
import config
import shortuuid
import aiohttp
from rich_utils import safe_send_rich_message, safe_edit_rich_message

router = Router()

@router.callback_query(F.data.startswith("buy_"))
async def process_buy_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_type = parts[1]
    
    if item_type == "groupsub":
        chat_id = parts[2]
        amount = parts[3]
        stars = parts[4]
        # the payload to pass along:
        callback_paystars = f"paystars_{item_type}_{chat_id}_{amount}_{stars}"
        callback_paycrypto = f"paycrypto_{item_type}_{chat_id}_{amount}_{stars}"
        callback_payother = f"payother_{item_type}_{chat_id}_{amount}_{stars}"
    else:
        amount = parts[2]
        stars = parts[3]
        callback_paystars = f"paystars_{item_type}_{amount}_{stars}"
        callback_paycrypto = f"paycrypto_{item_type}_{amount}_{stars}"
        callback_payother = f"payother_{item_type}_{amount}_{stars}"
        
    usdt_amount = 0
    if item_type == "gems":
        for pkg in config.GEMS_PACKAGES:
            if pkg["gems"] == int(amount): usdt_amount = pkg.get("USDT", 0)
    elif item_type == "premium":
        for pkg in config.PREMIUM_PACKAGES:
            if pkg["duration_days"] == int(amount): usdt_amount = pkg.get("USDT", 0)
            
    if usdt_amount <= 0:
        usdt_amount = round(int(stars) * 0.02, 2)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐️ Pay {stars} Stars (Instant)", callback_data=callback_paystars, style="primary")],
        [InlineKeyboardButton(text=f"🪙 Pay {usdt_amount} USDT", callback_data=callback_paycrypto, style="primary")],
        [InlineKeyboardButton(text="💳 Pay with INR (UPI)", callback_data=callback_payother, style="primary")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu")]
    ])
    
    msg_html = (
        f"<h3>🥇 Payment Selection</h3>\n"
        f"<p><i>Please choose your preferred payment method below to complete the purchase.</i></p>"
    )
    
    await safe_edit_rich_message(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        html_content=msg_html,
        reply_markup=markup
    )
    await callback.answer()

@router.callback_query(F.data.startswith("paystars_"))
async def process_paystars_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_type = parts[1] # "gems", "premium", or "groupsub"
    
    if item_type == "gems":
        gems_amount = int(parts[2])
        stars_amount = int(parts[3])
        title = f"{gems_amount} Gems"
        description = f"Purchase {gems_amount} Gems for {stars_amount} Telegram Stars."
        payload = f"gems_{gems_amount}_{stars_amount}"
    elif item_type == "premium":
        duration_days = int(parts[2])
        stars_amount = int(parts[3])
        title = f"{duration_days} Days Premium"
        description = f"Purchase {duration_days} Days Premium for {stars_amount} Telegram Stars."
        payload = f"premium_{duration_days}_{stars_amount}"
    elif item_type == "groupsub":
        chat_id = parts[2]
        duration_days = int(parts[3])
        stars_amount = int(parts[4])
        title = f"Group Access ({duration_days} Days)"
        description = f"Purchase {duration_days} Days of group messaging access for {stars_amount} Telegram Stars."
        payload = f"groupsub_{chat_id}_{duration_days}_{stars_amount}"
    else:
        await callback.answer("Invalid package.", show_alert=True)
        return

    prices = [LabeledPrice(label="XTR", amount=stars_amount)]

    await callback.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="", # Must be empty for Telegram Stars
        currency="XTR",
        prices=prices,
    )
    await callback.answer()

@router.callback_query(F.data.startswith("paycrypto_"))
async def process_paycrypto_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_type = parts[1]
    
    usdt_amount = 0
    package_name = ""
    
    if item_type == "gems":
        gems_amount = int(parts[2])
        stars_amount = int(parts[3])
        package_name = f"{gems_amount} Gems"
        for pkg in config.GEMS_PACKAGES:
            if pkg["gems"] == gems_amount:
                usdt_amount = pkg.get("USDT", 0)
                break
    elif item_type == "premium":
        duration_days = int(parts[2])
        stars_amount = int(parts[3])
        package_name = f"{duration_days} Days Premium"
        for pkg in config.PREMIUM_PACKAGES:
            if pkg["duration_days"] == duration_days:
                usdt_amount = pkg.get("USDT", 0)
                break
    elif item_type == "groupsub":
        chat_id = parts[2]
        duration_days = int(parts[3])
        stars_amount = int(parts[4])
        package_name = f"Group Access {duration_days} Days"
        usdt_amount = stars_amount * 0.02
        
    if usdt_amount <= 0:
        # Fallback for custom amounts not defined in config
        usdt_amount = round(stars_amount * 0.02, 2)
        
    if usdt_amount <= 0:
        await callback.answer("Crypto payment is not available for this package.", show_alert=True)
        return
        
    user_id = callback.from_user.id
    pending_invoices = get_pending_crypto_invoices(user_id)
    if len(pending_invoices) >= 3:
        buttons = []
        for inv in pending_invoices:
            buttons.append([InlineKeyboardButton(text=f"❌ Cancel {inv['package_name']} ({inv['invoice_id'][:8]})", callback_data=f"cancelinvoice_{inv['invoice_id']}", style="danger")])
        buttons.append([InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        msg_html = (
            "<h3>⚠️ Limit Reached</h3>\n"
            "<p>You have 3 pending crypto invoices. Please cancel one of them before creating a new one.</p>"
        )
        await safe_edit_rich_message(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            html_content=msg_html,
            reply_markup=markup
        )
        return
        
    callback_data_claim = callback.data.replace("paycrypto_", "claimcrypto_", 1)
    
    payload = {
        "customerId": str(user_id),
        "amount": str(usdt_amount),
        "receivingAddress": config.BSC_RECEIVING_ADDRESS,
        "callbackData": callback_data_claim,
        "tempBotToken": config.BOT_TOKEN,
        "botMessage": f"✅ Payment of {{amountPaid}} USDT verified!\n\nClick below to claim your {package_name}.",
        "buttonText": "Claim Reward"
    }
    
    headers = {"x-api-key": config.BSC_API_KEY}
    
    await callback.message.edit_text("⏳ Generating crypto invoice... Please wait.")
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"[DEBUG] Sending payload to BSC API: {payload}")
            print(f"[DEBUG] Headers: {headers}")
            async with session.post("https://bscusdtapi.onrender.com/api/invoices", json=payload, headers=headers) as resp:
                print(f"[DEBUG] API Response Status: {resp.status}")
                if resp.status in [200, 201]:
                    data = await resp.json()
                    print(f"[DEBUG] API Response Data: {data}")
                    invoice_id = data["invoice"]["invoiceId"]
                    temp_address = data["tempWallet"]["address"]
                    
                    add_crypto_invoice(invoice_id, user_id, package_name, temp_address)
                    
                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Cancel Invoice", callback_data=f"cancelinvoice_{invoice_id}", style="danger")],
                        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
                    ])
                    
                    msg_html = (
                        f"<h3>🪙 Crypto Payment (USDT BEP20)</h3>\n"
                        f"<p>Package: <b>{package_name}</b></p>\n"
                        f"<p>Amount Required: <code>{usdt_amount}</code> USDT</p>\n"
                        f"<p>Send <b>exactly</b> {usdt_amount} USDT via the <b>Binance Smart Chain (BEP20)</b> network to the address below:</p>\n"
                        f"<pre><code>{temp_address}</code></pre>\n"
                        f"<p><i>Note: The system will automatically detect the payment and send you a claim button here. This may take a few minutes.</i></p>"
                    )
                    await safe_edit_rich_message(
                        bot=callback.bot,
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id,
                        html_content=msg_html,
                        reply_markup=markup
                    )
                else:
                    error_data = await resp.text()
                    print(f"[ERROR] API Request Failed: Status {resp.status}, Response: {error_data}")
                    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>❌ Failed to generate crypto invoice. Please try again later or use a different payment method.</p>")
        except Exception as e:
            print(f"[ERROR] Exception during BSC API call: {e}")
            await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>❌ Failed to generate crypto invoice. Please try again later or use a different payment method.</p>")
    await callback.answer()

@router.callback_query(F.data.startswith("cancelinvoice_"))
async def process_cancelinvoice_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return
        
    invoice_id = callback.data.replace("cancelinvoice_", "")
    
    try:
        headers = {"x-api-key": config.BSC_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"https://bscusdtapi.onrender.com/api/invoices/{invoice_id}/cancel", headers=headers) as resp:
                pass # Best effort to cancel on gateway
    except Exception as e:
        print(f"API cancel error: {e}")
        
    update_crypto_invoice_status(invoice_id, "canceled")
    await safe_edit_rich_message(
        bot=callback.bot, chat_id=callback.message.chat.id, message_id=callback.message.message_id,
        html_content="<p>❌ Invoice canceled successfully.</p>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("claimcrypto_"))
async def process_claimcrypto_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    user_id = callback.from_user.id
    parts = callback.data.split("_")
    item_type = parts[1]
    
    package_name = ""
    stars_amount = 0
    if item_type == "gems":
        gems_amount = int(parts[2])
        stars_amount = int(parts[3])
        package_name = f"{gems_amount} Gems"
    elif item_type == "premium":
        duration_days = int(parts[2])
        stars_amount = int(parts[3])
        package_name = f"{duration_days} Days Premium"
    elif item_type == "groupsub":
        chat_id = int(parts[2])
        duration_days = int(parts[3])
        stars_amount = int(parts[4])
        package_name = f"Group Access {duration_days} Days"
        
    pending_invoices = get_pending_crypto_invoices(user_id, package_name)
    if not pending_invoices:
        await callback.answer("No pending invoices found for this package.", show_alert=True)
        return
        
    invoice_id = pending_invoices[0]["invoice_id"]
    
    await callback.message.edit_text("⏳ Verifying your payment...")
    
    headers = {"x-api-key": config.BSC_API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://bscusdtapi.onrender.com/api/claims", json={"invoiceId": invoice_id}, headers=headers) as resp:
            data = await resp.json()
            if resp.status in [200, 201] and data.get("claimed"):
                update_crypto_invoice_status(invoice_id, "claimed")
                
                payment_id = shortuuid.uuid()
                username = callback.from_user.username or str(user_id)
                
                markup = None
                if item_type == "gems":
                    await save_gem_payment(payment_id, user_id, username, package_name, gems_amount, stars_amount)
                    log_local_payment(user_id, payment_id, package_name)
                    start_payload = f"gems_{payment_id}"
                    
                    target_bot = config.TARGET_BOT_USERNAME
                    deep_link = f"https://t.me/{target_bot}?start={start_payload}"
                    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Verify Payment & Claim", url=deep_link, style="primary")]])
                    success_msg = f"<h3>✅ Payment successful!</h3>\n<p>Item: {package_name}<br>Payment ID: <code>{payment_id}</code></p>\n<p>Click the button below to verify and claim your reward in the Promotion Bot.</p>"
                elif item_type == "premium":
                    await save_premium_payment(payment_id, user_id, username, package_name, duration_days, stars_amount)
                    log_local_payment(user_id, payment_id, package_name)
                    start_payload = f"premium_{payment_id}"
                    
                    target_bot = config.TARGET_BOT_USERNAME
                    deep_link = f"https://t.me/{target_bot}?start={start_payload}"
                    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Verify Payment & Claim", url=deep_link, style="primary")]])
                    success_msg = f"<h3>✅ Payment successful!</h3>\n<p>Item: {package_name}<br>Payment ID: <code>{payment_id}</code></p>\n<p>Click the button below to verify and claim your reward in the Promotion Bot.</p>"
                elif item_type == "groupsub":
                    extend_group_subscription(user_id, chat_id, duration_days)
                    log_local_payment(user_id, payment_id, package_name)
                    success_msg = f"<h3>✅ Payment successful!</h3>\n<p>Item: {package_name}<br>Payment ID: <code>{payment_id}</code></p>\n<p>Your group subscription is now active! You can now send messages in the group.</p>"

                await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, success_msg, markup)
                    
                try:
                    admin_msg = (
                        f"🔔 <b>New Crypto Payment Received!</b>\n\n"
                        f"👤 User: <a href='tg://user?id={user_id}'>{callback.from_user.first_name}</a> (ID: <code>{user_id}</code>)\n"
                        f"🛍 Item: <b>{package_name}</b>\n"
                        f"🧾 Payment ID: <code>{payment_id}</code>"
                    )
                    await callback.bot.send_message(config.ADMIN_ID, admin_msg, parse_mode="HTML")
                except Exception:
                    pass
            else:
                await safe_edit_rich_message(
                    bot=callback.bot, chat_id=callback.message.chat.id, message_id=callback.message.message_id,
                    html_content="<p>❌ Payment not verified. If you have just paid, please wait a few more minutes and click the claim button again.</p>",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Try Again", callback_data=callback.data, style="primary")],
                        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu")]
                    ])
                )
    await callback.answer()

@router.callback_query(F.data.startswith("payother_"))
async def process_payother_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_type = parts[1]
    amount = parts[2]
    
    deep_link = f"https://t.me/chosentwo_bot?start={item_type}_{amount}"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Contact Support to Pay", url=deep_link, style="primary")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])
    
    msg_html = (
        "<h3>💳 Other Payment Methods</h3>\n"
        "<p>We accept <b>INR (UPI)</b> payments manually.</p>\n"
        "<p>Please click the button below to contact our support bot to process your payment.</p>"
    )
    
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    if await is_banned(pre_checkout_query.from_user.id):
        await pre_checkout_query.answer(ok=False, error_message="You are banned from making purchases.")
        return
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    parts = payload.split("_")
    item_type = parts[0]
    
    payment_id = shortuuid.uuid()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    stars_amount = payment_info.total_amount # amount in XTR
    
    markup = None
    if item_type == "gems":
        gems_amount = int(parts[1])
        package_name = f"{gems_amount} Gems"
        await save_gem_payment(payment_id, user_id, username, package_name, gems_amount, stars_amount)
        log_local_payment(user_id, payment_id, package_name)
        start_payload = f"gems_{payment_id}"
        
        target_bot = config.TARGET_BOT_USERNAME
        deep_link = f"https://t.me/{target_bot}?start={start_payload}"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Verify Payment & Claim", url=deep_link, style="primary")]
        ])
        success_msg = (
            f"<h3>✅ Payment successful!</h3>\n"
            f"<p>Item: {package_name}<br>"
            f"Payment ID: <code>{payment_id}</code></p>\n"
            f"<p>Click the button below to verify and claim your reward in the Promotion Bot.</p>"
        )

    elif item_type == "premium":
        duration_days = int(parts[1])
        package_name = f"{duration_days} Days Premium"
        await save_premium_payment(payment_id, user_id, username, package_name, duration_days, stars_amount)
        log_local_payment(user_id, payment_id, package_name)
        start_payload = f"premium_{payment_id}"
        
        target_bot = config.TARGET_BOT_USERNAME
        deep_link = f"https://t.me/{target_bot}?start={start_payload}"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Verify Payment & Claim", url=deep_link, style="primary")]
        ])
        success_msg = (
            f"<h3>✅ Payment successful!</h3>\n"
            f"<p>Item: {package_name}<br>"
            f"Payment ID: <code>{payment_id}</code></p>\n"
            f"<p>Click the button below to verify and claim your reward in the Promotion Bot.</p>"
        )

    elif item_type == "groupsub":
        chat_id = int(parts[1])
        duration_days = int(parts[2])
        package_name = f"Group Access {duration_days} Days"
        
        # Extend subscription in SQLite
        extend_group_subscription(user_id, chat_id, duration_days)
        log_local_payment(user_id, payment_id, package_name)
        
        success_msg = (
            f"<h3>✅ Payment successful!</h3>\n"
            f"<p>Item: {package_name}<br>"
            f"Payment ID: <code>{payment_id}</code></p>\n"
            f"<p>Your group subscription is now active! You can now send messages in the group.</p>"
        )

    await safe_send_rich_message(message.bot, message.chat.id, success_msg, markup)
        
    try:
        admin_msg = (
            f"🔔 <b>New Payment Received!</b>\n\n"
            f"👤 User: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> (ID: <code>{user_id}</code>)\n"
            f"🛍 Item: <b>{package_name}</b>\n"
            f"💰 Amount: <b>{stars_amount} Stars</b>\n"
            f"🧾 Payment ID: <code>{payment_id}</code>"
        )
        await message.bot.send_message(config.ADMIN_ID, admin_msg, parse_mode="HTML")
    except Exception as e:
        import logging
        logging.error(f"Failed to notify admin: {e}")
