from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from database.mongo import is_banned, save_gem_payment, save_premium_payment
from database.sqlite import log_local_payment
import config
import shortuuid

router = Router()

@router.callback_query(F.data.startswith("buy_"))
async def process_buy_callback(callback: CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("You are banned.", show_alert=True)
        return

    parts = callback.data.split("_")
    item_type = parts[1] # "gems" or "premium"
    
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

    await message.answer(
        f"✅ Payment successful!\n\n"
        f"Item: {package_name}\n"
        f"Payment ID: `{payment_id}`\n\n"
        f"Click the button below to verify and claim your reward in the Promotion Bot.",
        reply_markup=markup,
        parse_mode="Markdown"
    )
