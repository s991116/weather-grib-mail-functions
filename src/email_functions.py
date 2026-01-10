import asyncio
import re
import logging
from html import unescape

from src import configs
from src.mail.graph_mail import GraphMailService

logger = logging.getLogger(__name__)

# ======================================================
# 1️⃣ GARMIN INREACH → SAILDOCS (REQUEST)
# ======================================================
async def process_new_inreach_message(mail: GraphMailService):
    """
    Process exactly one unread InReach request mail.
    Extracts Saildocs command and Garmin reply URL.
    Marks InReach mail as read.
    Returns: (saildocs_command_text, garmin_reply_url) or None
    """

    messages = await mail.search_messages(
        user_id=configs.MAILBOX,
        sender_email=configs.SERVICE_EMAIL,
        unread_only=True,
        top=1
    )

    if not messages or not messages.value:
        logger.info("No unread InReach requests found")
        return None

    msg = messages.value[0]
    logger.info("Processing InReach request %s", msg.id)

    try:
        msg_text, garmin_reply_url = await _fetch_message_text_and_url(msg.id, mail)

        if not garmin_reply_url:
            logger.warning("No Garmin reply URL found in InReach request %s", msg.id)
            await mail.mark_as_read(configs.MAILBOX, msg.id)
            return None

        # Send only the Saildocs command text, NOT the reply URL
        await mail.send_mail(
            sender=configs.MAILBOX,
            to=configs.SAILDOCS_EMAIL_QUERY,
            subject="",
            body="send " + msg_text.strip()
        )

        await mail.mark_as_read(configs.MAILBOX, msg.id)
        logger.info("InReach request %s processed and marked as read", msg.id)

        return msg_text.strip(), garmin_reply_url

    except Exception:
        logger.exception("Failed processing InReach request %s", msg.id)
        return None


# ======================================================
# 2️⃣ SAILDOCS → GARMIN INREACH (RESPONSE)
# ======================================================
async def process_new_saildocs_response(mail: GraphMailService, saildocs_command, garmin_reply_url):
    """
    Poll for unread Saildocs response for the given command.
    Poll every 10 sec, up to 6 times (1 min total).
    Downloads GRIB and returns (path, garmin_reply_url)
    """

    poll_attempts = 6
    for attempt in range(poll_attempts):
        logger.info("Polling for Saildocs response (%d/%d)...", attempt + 1, poll_attempts)

        messages = await mail.search_messages(
            user_id=configs.MAILBOX,
            sender_email=configs.SAILDOCS_RESPONSE_EMAIL,
            unread_only=True,
            top=5
        )

        if messages and messages.value:
            for msg in messages.value:
                message_body = msg.body.content or ""
                if msg.body.content_type == "html":
                    decoded = _html_to_text(message_body)
                else:
                    decoded = message_body

                decoded = decoded.lower()

                # Check if this Saildocs mail corresponds to our command
                if saildocs_command.lower() in decoded:
                    # Download GRIB attachment
                    grib_path = await mail.download_grib_attachment(
                        user_id=configs.MAILBOX,
                        message_id=msg.id,
                        file_path=configs.FILE_PATH
                    )

                    if not grib_path:
                        logger.warning("No GRIB attachment found in %s", msg.id)
                        await mail.mark_as_read(configs.MAILBOX, msg.id)
                        return None

                    await mail.mark_as_read(configs.MAILBOX, msg.id)
                    logger.info("Saildocs response %s processed and marked as read", msg.id)

                    return grib_path, garmin_reply_url

        await asyncio.sleep(10)

    logger.warning("No Saildocs response found for command after polling")
    return None


# ======================================================
# HELPERS
# ======================================================
async def _fetch_message_text_and_url(message_id, mail: GraphMailService):
    """
    Extract Saildocs command text and Garmin reply URL from an InReach request mail.
    """
    message = await mail.client.users \
        .by_user_id(configs.MAILBOX) \
        .messages \
        .by_message_id(message_id) \
        .get()

    body = message.body.content or ""
    body_type = message.body.content_type

    if body_type == "html":
        decoded = _html_to_text(body)
    else:
        decoded = body

    decoded = decoded.lower()

    msg_text = ""
    garmin_reply_url = None

    idx = decoded.find(configs.BASE_GARMIN_REPLY_URL)
    if idx != -1:
        garmin_reply_url = decoded[idx:].split()[0]
        msg_text = decoded[:idx].strip()
    else:
        msg_text = decoded.strip()

    msg_text = msg_text.replace("reply to garmin:", "").strip()

    return msg_text, garmin_reply_url


def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text)
