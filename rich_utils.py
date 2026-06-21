import logging
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.methods import SendRichMessage, EditMessageText
from aiogram.types import InputRichMessage
from typing import Optional, Union

logger = logging.getLogger(__name__)

async def safe_send_rich_message(
    bot: Bot,
    chat_id: Union[int, str],
    html_content: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs
) -> Message:
    """
    Attempts to send a rich message using Bot API 10.1 features.
    If it fails, it falls back to a standard HTML message.
    """
    try:
        rich_payload = InputRichMessage(html=html_content)
        return await bot(
            SendRichMessage(
                chat_id=chat_id,
                rich_message=rich_payload,
                reply_markup=reply_markup,
                **kwargs
            )
        )
    except Exception as e:
        logger.error(f"SendRichMessage failed: {e}\nFallback to standard message. HTML: {html_content}")
        return await bot.send_message(
            chat_id=chat_id,
            text=html_content,
            parse_mode="HTML",
            reply_markup=reply_markup,
            **kwargs
        )

async def safe_edit_rich_message(
    bot: Bot,
    chat_id: Union[int, str],
    message_id: int,
    html_content: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    **kwargs
):
    """
    Attempts to edit a message into a rich message using Bot API 10.1 features.
    If it fails, it falls back to a standard HTML edit.
    """
    try:
        rich_payload = InputRichMessage(html=html_content)
        return await bot(
            EditMessageText(
                chat_id=chat_id,
                message_id=message_id,
                rich_message=rich_payload,
                reply_markup=reply_markup,
                **kwargs
            )
        )
    except Exception as e:
        logger.error(f"EditRichMessage failed: {e}\nFallback to standard edit. HTML: {html_content}")
        from aiogram.methods import EditMessageText as StandardEditMessageText
        return await bot(
            StandardEditMessageText(
                chat_id=chat_id,
                message_id=message_id,
                text=html_content,
                parse_mode="HTML",
                reply_markup=reply_markup,
                **kwargs
            )
        )
