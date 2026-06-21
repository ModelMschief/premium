from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from database.sqlite import (
    get_group_package_by_id, get_cloned_bot_by_id,
    extend_clone_subscription, get_pending_clone_invoice,
    add_clone_crypto_invoice, update_clone_invoice_status,
    credit_creator_balance, get_connected_group, log_local_payment
)
import config
import aiohttp
import shortuuid
import logging
from rich_utils import safe_send_rich_message, safe_edit_rich_message

logger = logging.getLogger(__name__)

router = Router()

def get_viral_button() -> list:
    main_bot = config.MAIN_BOT_USERNAME
    if main_bot:
        return [InlineKeyboardButton(text="🤖 Get Your Own Premium Group Bot — FREE!", url=f"https://t.me/{main_bot}?start=clone")]
    return []

# ═══════════════════════════════════════════════════════════════
# PAYMENT METHOD SELECTION
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clonebuy_"))
async def clone_buy_package(callback: CallbackQuery):
    """User selected a package — show Stars vs USDT choice."""
    parts = callback.data.split("_")
    group_id = int(parts[1])
    package_id = int(parts[2])

    pkg = get_group_package_by_id(package_id)
    if not pkg:
        await callback.answer("Package not found.", show_alert=True)
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐️ Pay {pkg['stars_price']} Stars (Instant)",
            callback_data=f"clonepaystars_{group_id}_{package_id}",
            style="primary"
        )],
        [InlineKeyboardButton(
            text=f"🪙 Pay {pkg['usdt_price']} USDT",
            callback_data=f"clonepaycrypto_{group_id}_{package_id}",
            style="primary"
        )],
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"clonesub_{group_id}")]
    ])

    msg_html = (
        f"<h3>🥇 Payment Selection</h3>\n"
        f"<ul>"
        f"<li>📦 <b>{pkg['duration_days']} Days</b> Access</li>"
        f"<li>⭐️ {pkg['stars_price']} Stars / 🪙 {pkg['usdt_price']} USDT</li>"
        f"</ul>"
        f"<p><i>Choose your preferred payment method:</i></p>"
    )
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
# STARS PAYMENT
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clonepaystars_"))
async def clone_pay_stars(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[1])
    package_id = int(parts[2])

    pkg = get_group_package_by_id(package_id)
    if not pkg:
        await callback.answer("Package not found.", show_alert=True)
        return

    title = f"Group Access ({pkg['duration_days']} Days)"
    description = f"Purchase {pkg['duration_days']} days of group messaging access."
    payload = f"clonesub_{group_id}_{pkg['duration_days']}_{pkg['stars_price']}"

    prices = [LabeledPrice(label="XTR", amount=pkg["stars_price"])]

    await callback.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


@router.pre_checkout_query()
async def clone_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def clone_successful_payment(message: Message):
    """Handle successful Stars payment for clone subscriptions."""
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")

    if parts[0] != "clonesub":
        return

    group_id = int(parts[1])
    duration_days = int(parts[2])
    stars_amount = int(parts[3])
    user_id = message.from_user.id

    bot_info = await message.bot.get_me()
    bot_id = bot_info.id

    # Extend subscription
    extend_clone_subscription(user_id, group_id, bot_id, duration_days)

    payment_id = shortuuid.uuid()
    package_name = f"Group Access {duration_days} Days"
    log_local_payment(user_id, payment_id, package_name)

    # Build success message
    viral = get_viral_button()
    buttons = []
    if viral:
        buttons.append(viral)
    markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    msg_html = (
        f"<h3>✅ Payment Successful!</h3>\n"
        f"<ul>"
        f"<li>📦 {package_name}</li>"
        f"<li>💰 {stars_amount} Stars</li>"
        f"<li>🧾 <code>{payment_id}</code></li>"
        f"</ul>"
        f"<p>Your subscription is now active! You can send messages in the group.</p>"
    )
    await safe_send_rich_message(message.bot, message.chat.id, msg_html, markup)

    # Notify group owner
    clone_data = get_cloned_bot_by_id(bot_id)
    if clone_data:
        try:
            await message.bot.send_message(
                clone_data["owner_user_id"],
                f"🔔 <b>New Stars Payment!</b>\n\n"
                f"👤 <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                f"📦 {package_name}\n"
                f"⭐️ {stars_amount} Stars",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# USDT PAYMENT (1-invoice limit)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clonepaycrypto_"))
async def clone_pay_crypto(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[1])
    package_id = int(parts[2])

    pkg = get_group_package_by_id(package_id)
    if not pkg:
        await callback.answer("Package not found.", show_alert=True)
        return

    user_id = callback.from_user.id
    bot_info = await callback.bot.get_me()
    bot_id = bot_info.id

    # ─── 1-invoice limit check ───────────────────────────
    pending = get_pending_clone_invoice(user_id)
    if pending:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"❌ Cancel Pending: {pending['package_name']}",
                callback_data=f"cancelcloneinvoice_{pending['invoice_id']}",
                style="primary"
            )],
            [InlineKeyboardButton(text="🔙 Back", callback_data=f"clonesub_{group_id}")]
        ])
        msg_html = (
            "<h3>⚠️ Pending Payment Exists</h3>\n"
            f"<p>You already have a pending payment for <b>{pending['package_name']}</b>.</p>\n"
            "<p>Please cancel it or complete the payment first before creating a new invoice.</p>"
        )
        await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
        await callback.answer()
        return

    # ─── Create invoice via BSC API ──────────────────────
    usdt_amount = pkg["usdt_price"]
    package_name = f"Group Access {pkg['duration_days']} Days"
    clone_data = get_cloned_bot_by_id(bot_id)
    bot_token = clone_data["bot_token"] if clone_data else config.BOT_TOKEN

    claim_callback = f"claimclonesub_{group_id}_{pkg['duration_days']}"

    api_payload = {
        "customerId": str(user_id),
        "amount": str(usdt_amount),
        "receivingAddress": config.PLATFORM_RECEIVING_ADDRESS,
        "callbackData": claim_callback,
        "tempBotToken": bot_token,
        "botMessage": f"✅ Payment of {{amountPaid}} USDT verified!\n\nClick below to activate your {package_name}.",
        "buttonText": "Activate Subscription"
    }

    headers = {"x-api-key": config.BSC_API_KEY}

    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>⏳ Generating crypto invoice... Please wait.</p>")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("https://bscusdtapi.onrender.com/api/invoices", json=api_payload, headers=headers) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    invoice_id = data["invoice"]["invoiceId"]
                    temp_address = data["tempWallet"]["address"]

                    # Save to clone_crypto_invoices
                    add_clone_crypto_invoice(invoice_id, user_id, bot_id, group_id, package_name, usdt_amount, temp_address)

                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Cancel Invoice", callback_data=f"cancelcloneinvoice_{invoice_id}", style="primary")],
                        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="clone_main_menu")]
                    ])

                    msg_html = (
                        f"<h3>🪙 Crypto Payment (USDT BEP20)</h3>\n"
                        f"<p>Package: <b>{package_name}</b></p>\n"
                        f"<p>Amount: <code>{usdt_amount}</code> USDT</p>\n"
                        f"<p>Send <b>exactly</b> {usdt_amount} USDT via <b>BSC (BEP20)</b> to:</p>\n"
                        f"<pre><code>{temp_address}</code></pre>\n"
                        f"<p><i>The system will automatically detect your payment and send you an activation button.</i></p>"
                    )
                    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
                else:
                    error_text = await resp.text()
                    logger.error(f"Clone invoice creation failed: {resp.status} - {error_text}")
                    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>❌ Failed to generate invoice. Please try again later.</p>")
        except Exception as e:
            logger.error(f"Clone invoice exception: {e}")
            await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>❌ Failed to generate invoice. Please try again later.</p>")

    await callback.answer()


# ─── Cancel clone invoice ────────────────────────────────────
@router.callback_query(F.data.startswith("cancelcloneinvoice_"))
async def cancel_clone_invoice(callback: CallbackQuery):
    invoice_id = callback.data.replace("cancelcloneinvoice_", "")

    try:
        headers = {"x-api-key": config.BSC_API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"https://bscusdtapi.onrender.com/api/invoices/{invoice_id}/cancel", headers=headers) as resp:
                pass # Best effort to cancel on gateway
    except Exception as e:
        logger.error(f"Clone API cancel error: {e}")

    update_clone_invoice_status(invoice_id, "canceled")
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="clone_main_menu")]
    ])
    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>❌ Invoice canceled successfully.</p>", markup)
    await callback.answer()


# ─── Claim clone subscription (after USDT payment verified) ──
@router.callback_query(F.data.startswith("claimclonesub_"))
async def claim_clone_subscription(callback: CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[1])
    duration_days = int(parts[2])

    user_id = callback.from_user.id
    bot_info = await callback.bot.get_me()
    bot_id = bot_info.id

    # Find the pending invoice for this user
    pending = get_pending_clone_invoice(user_id, bot_id)
    if not pending:
        await callback.answer("No pending invoices found.", show_alert=True)
        return

    invoice_id = pending["invoice_id"]
    usdt_amount = pending["usdt_amount"]

    await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, "<p>⏳ Verifying your payment...</p>")

    headers = {"x-api-key": config.BSC_API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://bscusdtapi.onrender.com/api/claims", json={"invoiceId": invoice_id}, headers=headers) as resp:
            data = await resp.json()
            if resp.status in [200, 201] and data.get("claimed"):
                update_clone_invoice_status(invoice_id, "claimed")

                # ─── Revenue split: 90% creator, 10% platform ───
                creator_share = round(usdt_amount * config.CREATOR_REVENUE_SHARE, 4)
                clone_data = get_cloned_bot_by_id(bot_id)
                if clone_data:
                    credit_creator_balance(clone_data["owner_user_id"], creator_share)

                # ─── Extend subscription ─────────────────────────
                extend_clone_subscription(user_id, group_id, bot_id, duration_days)

                payment_id = shortuuid.uuid()
                package_name = f"Group Access {duration_days} Days"
                log_local_payment(user_id, payment_id, package_name)

                viral = get_viral_button()
                buttons = []
                if viral:
                    buttons.append(viral)
                markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

                msg_html = (
                    f"<h3>✅ Subscription Activated!</h3>\n"
                    f"<ul>"
                    f"<li>📦 {package_name}</li>"
                    f"<li>💵 {usdt_amount} USDT</li>"
                    f"<li>🧾 <code>{payment_id}</code></li>"
                    f"</ul>"
                    f"<p>You can now send messages in the group!</p>"
                )
                await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)

                # Notify owner
                if clone_data:
                    try:
                        await callback.bot.send_message(
                            clone_data["owner_user_id"],
                            f"🔔 <b>New USDT Payment!</b>\n\n"
                            f"👤 <a href='tg://user?id={user_id}'>{callback.from_user.first_name}</a>\n"
                            f"📦 {package_name}\n"
                            f"💵 {usdt_amount} USDT\n"
                            f"💰 Your share: <b>${creator_share:.2f}</b>",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

                # Notify platform admin
                try:
                    from aiogram import Bot as MainBot
                    main_bot = MainBot(token=config.BOT_TOKEN)
                    await main_bot.send_message(
                        config.ADMIN_ID,
                        f"🔔 <b>Clone USDT Payment</b>\n\n"
                        f"🤖 Bot: @{bot_info.username}\n"
                        f"👤 User: <code>{user_id}</code>\n"
                        f"💵 Total: {usdt_amount} USDT\n"
                        f"📊 Platform: ${round(usdt_amount * (1 - config.CREATOR_REVENUE_SHARE), 4):.2f}",
                        parse_mode="HTML"
                    )
                    await main_bot.session.close()
                except Exception:
                    pass
            else:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Try Again", callback_data=callback.data, style="primary")],
                    [InlineKeyboardButton(text="🔙 Main Menu", callback_data="clone_main_menu")]
                ])
                msg_html = (
                    "<h3>❌ Payment not verified yet</h3>\n"
                    "<p>If you just sent the payment, please wait a few minutes and try again.</p>"
                )
                await safe_edit_rich_message(callback.bot, callback.message.chat.id, callback.message.message_id, msg_html, markup)
    await callback.answer()
