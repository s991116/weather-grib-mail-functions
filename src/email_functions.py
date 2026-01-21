#FILE src/email_functions.py
import asyncio
import re
import logging
from html import unescape

import src.configs as configs

from src.graph_mail import GraphMailService
from src.InReachRequest import InReachRequest

logger = logging.getLogger(__name__)

# ======================================================
# 1️⃣ GARMIN INREACH MAIL → INREACH REQUEST
# ======================================================
async def retrieve_new_inreach_request(mail: GraphMailService):
    """
    Process exactly one unread InReach request mail.
    Extracts Saildocs command and Garmin reply URL.
    Marks InReach mail as read.
    Returns: InReachRequest (type, payload_text, garmin_reply_url) or None
    """
    logger.info("Search for mail in mail account: %s", configs.MAILBOX())
    logger.info("Search for mail from Service Mail: %s", configs.SERVICE_EMAIL())
    messages = await mail.search_messages(
        user_id = configs.MAILBOX(),
        sender_email = configs.SERVICE_EMAIL(),
        unread_only=True,
        top=configs.TOP_SEARCH_COUNT_MAILBOX
    )

    if not messages or not messages.value:
        logger.info("No unread InReach requests found")
        return None

    msg = messages.value[0]
    logger.info("Processing InReach request %s", msg.id)

    try:
        body_message = await _fetch_message_body_from_mail(msg.id, mail)

        inreach_request = _decode_inreach_request(body_message)
        if inreach_request:
            logger.info("InReach request from mail %s", inreach_request)
        else:
            logger.info("InReach request could not be created from mail %s", inreach_request)
    except Exception:
        logger.exception("Failed processing InReach request %s", msg.id)
        return None
    
    await mail.mark_as_read(configs.MAILBOX(), msg.id)
    logger.info("InReach mail marked as read.")
    return inreach_request


# ======================================================
# 1️⃣ GARMIN INREACH → SAILDOCS (REQUEST)
# ======================================================
async def request_weather_report(mail: GraphMailService, message_request: str):
    """
    Request weather report from Saildoc
    Returns: None
    """

    try:
        # Send only the Saildocs command text
        await mail.send_mail(
            sender=configs.MAILBOX(),
            to=configs.SAILDOCS_EMAIL_QUERY(),
            subject="",
            body="send " + message_request.strip()
        )
    except Exception:
        logger.exception("Failed processing InReach request %s", msg.id)


# ======================================================
# 2️⃣ SAILDOCS → GARMIN INREACH (RESPONSE)
# ======================================================
async def process_new_saildocs_response(mail: GraphMailService, saildocs_command: str):
    """
    Poll for unread Saildocs response for the given command.
    Poll every 10 sec, up to 6 times (1 min total).
    Downloads GRIB in-memory and returns (BytesIO, garmin_reply_url)
    """

    poll_attempts = 6
    for attempt in range(poll_attempts):
        logger.info("Polling for Saildocs response (%d/%d)...", attempt + 1, poll_attempts)

        messages = await mail.search_messages(
            user_id=configs.MAILBOX(),
            sender_email=configs.SAILDOCS_RESPONSE_EMAIL(),
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
                    # Download GRIB attachment in-memory
                    grib_file = await mail.download_grib_attachment(
                        user_id=configs.MAILBOX(),
                        message_id=msg.id
                    )

                    if not grib_file:
                        logger.warning("No GRIB attachment found in %s", msg.id)
                        await mail.mark_as_read(configs.MAILBOX(), msg.id)
                        return None

                    await mail.mark_as_read(configs.MAILBOX(), msg.id)
                    logger.info("Saildocs response %s processed and marked as read", msg.id)

                    return grib_file

        await asyncio.sleep(10)

    logger.warning("No Saildocs response found for command after polling")
    return None


# ======================================================
# HELPERS
# ======================================================
async def _fetch_message_body_from_mail(message_id, mail: GraphMailService):
    """
    Extract Saildocs command text and Garmin reply URL from an InReach request mail.
    """
    message = await mail.client.users \
        .by_user_id(configs.MAILBOX()) \
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

    return decoded


def _decode_inreach_request(raw_text: str) -> InReachRequest:
    """
    Decode an InReach email body into an InReachRequest.

    Supported formats (case-insensitive):

    Multi-line:
        GRIB <saildocs-command>

        Reply to Garmin: <url>

    Single-line:
        grib <saildocs-command> reply to garmin: <url>
    """

    GRIB_PREFIX = "GRIB"
    CHAT_PREFIX = "CHAT"
    REPLY_PREFIX = "Reply to Garmin:"

    logging.info("Decode InReach request: %s", raw_text)

    if not raw_text or not raw_text.strip():
        raise ValueError("Empty InReach message")

    # -------------------------------------------------
    # Normalize whitespace
    # -------------------------------------------------
    text = " ".join(raw_text.strip().split())
    lower_text = text.lower()

    # -------------------------------------------------
    # Extract reply URL
    # -------------------------------------------------
    reply_idx = lower_text.find(REPLY_PREFIX.lower())
    if reply_idx == -1:
        raise ValueError("Reply to Garmin URL not found")

    reply_url = text[reply_idx + len(REPLY_PREFIX):].strip()

    if not reply_url:
        raise ValueError("Reply to Garmin URL not found")

    # -------------------------------------------------
    # Extract request part (everything before Reply)
    # -------------------------------------------------
    request_part = text[:reply_idx].strip()

    # -------------------------------------------------
    # Detect request type + payload
    # -------------------------------------------------
    if request_part.upper().startswith(GRIB_PREFIX):
        request_type = "weather"
        payload_text = request_part[len(GRIB_PREFIX):].lstrip()

    elif request_part.upper().startswith(CHAT_PREFIX):
        request_type = "chat"
        payload_text = request_part[len(CHAT_PREFIX):].lstrip()

    else:
        raise ValueError(f"Unknown request type: {request_part}")

    if not payload_text:
        raise ValueError("Missing GRIB payload")

    return InReachRequest(
        request_type,
        payload_text,
        reply_url,
    )


def _html_to_text(html: str) -> str:
    html = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text)