from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned, save_gem_payment, save_premium_payment
from database.sqlite import log_local_payment, extend_group_subscription
import config
import shortuuid

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
        callback_payother = f"payother_{item_type}_{chat_id}_{amount}_{stars}"
    else:
        amount = parts[2]
        stars = parts[3]
        callback_paystars = f"paystars_{item_type}_{amount}_{stars}"
        callback_payother = f"payother_{item_type}_{amount}_{stars}"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Stars (Instant)", callback_data=callback_paystars,style="primary"),
        InlineKeyboardButton(text="💳 Other", callback_data=callback_payother,style="primary")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text("<b>🥇How would you like to pay?</b>\n\n<i>✨Direct payment with Telegram Stars Or Manual other Payments</i>", reply_markup=markup, parse_mode="HTML")
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

@router.callback_query(F.data.startswith("payother_"))
async def process_payother_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_type = parts[1]
    amount = parts[2]
    
    # Generate link to chosentwo_bot
    deep_link = f"https://t.me/chosentwo_bot?start={item_type}_{amount}"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Contact Support to Pay", url=deep_link)],
        [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
    ])
    
    msg = (
        "💳 <b>Other Payment Methods</b>\n\n"
        "We accept <b>INR (UPI)</b> and <b>Crypto</b> payments.\n\n"
        "Please click the button below to contact our support bot to process your payment manually."
    )
    
    await callback.message.edit_text(msg, reply_markup=markup, parse_mode="HTML")
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
    
    if item_type == "gems":
        gems_amount = int(parts[1])
        package_name = f"{gems_amount} Gems"
        await save_gem_payment(payment_id, user_id, username, package_name, gems_amount, stars_amount)
        log_local_payment(user_id, payment_id, package_name)
        start_payload = f"gems_{payment_id}"
        
        target_bot = config.TARGET_BOT_USERNAME
        deep_link = f"https://t.me/{target_bot}?start={start_payload}"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Verify Payment & Claim", url=deep_link)]
        ])
        success_msg = (
            f"✅ Payment successful!\n\n"
            f"Item: {package_name}\n"
            f"Payment ID: `{payment_id}`\n\n"
            f"Click the button below to verify and claim your reward in the Promotion Bot."
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
            [InlineKeyboardButton(text="Verify Payment & Claim", url=deep_link)]
        ])
        success_msg = (
            f"✅ Payment successful!\n\n"
            f"Item: {package_name}\n"
            f"Payment ID: `{payment_id}`\n\n"
            f"Click the button below to verify and claim your reward in the Promotion Bot."
        )

    elif item_type == "groupsub":
        chat_id = int(parts[1])
        duration_days = int(parts[2])
        package_name = f"Group Access {duration_days} Days"
        
        # Extend subscription in SQLite
        extend_group_subscription(user_id, chat_id, duration_days)
        log_local_payment(user_id, payment_id, package_name)
        
        markup = None
        success_msg = (
            f"✅ Payment successful!\n\n"
            f"Item: {package_name}\n"
            f"Payment ID: `{payment_id}`\n\n"
            f"Your group subscription is now active! You can now send messages in the group."
        )

    if markup:
        await message.answer(success_msg, reply_markup=markup, parse_mode="Markdown")
    else:
        await message.answer(success_msg, parse_mode="Markdown")
        
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
