import asyncio
import re
import logging
from datetime import datetime
from html import unescape

from src import configs
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.mail.graph_mail import GraphMailService

logger = logging.getLogger(__name__)

# =========================
# PUBLIC ENTRYPOINT
# =========================
async def process_new_inreach_message():
    """
    Process exactly one unread InReach email using Graph API isRead flag.
    Azure-safe and idempotent.
    """
    mail = GraphMailService()

    messages = await mail.search_messages(
        user_id=configs.MAILBOX,
        sender_email=configs.SERVICE_EMAIL,
        top=1,
        unread_only=True
    )

    if not messages or not messages.value:
        logging.info("No unread InReach messages found")
        return None

    msg = messages.value[0]
    logging.info("Processing unread message %s", msg.id)

    try:
        # 1️⃣ Behandl mail først
        result = await _request_and_process_saildocs_grib(msg.id, mail)

        # 2️⃣ Marker mail som læst efter behandling
        await mail.mark_as_read(configs.MAILBOX, msg.id)

        return result

    except Exception:
        logging.exception("Error processing message %s", msg.id)
        try:
            _, garmin_reply_url = await _fetch_message_text_and_url(msg.id, mail)
            if garmin_reply_url:
                await inreach_func.send_messages_to_inreach(
                    garmin_reply_url,
                    "Internal error while processing your request"
                )
        except Exception:
            logging.exception("Failed to send error reply to InReach")
        return None


# =========================
# INTERNAL HELPERS
# =========================
async def _request_and_process_saildocs_grib(message_id, mail: GraphMailService):
    # Hent mailtekst og reply URL
    msg_text, garmin_reply_url = await _fetch_message_text_and_url(message_id, mail)

    logger.info("Mail msg sent to Saildocs server: %r", msg_text)

    # Send GRIB request til Saildocs
    await mail.send_mail(
        sender=configs.MAILBOX,
        to=configs.SAILDOCS_EMAIL_QUERY,
        subject="",
        body="send " + msg_text
    )

    time_sent = datetime.utcnow()
    # Vent på Saildocs svar
    last_response = await saildoc_func.wait_for_saildocs_response(mail, time_sent)

    if not last_response:
        logger.info("Saildocs timeout. Sending timeout message to Garmin.")
        await inreach_func.send_messages_to_inreach(garmin_reply_url, "Saildocs timeout")
        return None

    # Download GRIB attachment
    grib_path = await mail.download_grib_attachment(
        user_id=configs.MAILBOX,
        message_id=last_response.id,
        file_path=configs.FILE_PATH
    )

    if not grib_path:
        logger.info("Could not download GRIB file. Sending error message to Garmin.")
        await inreach_func.send_messages_to_inreach(garmin_reply_url, "Could not download GRIB file")
        return None

    return grib_path, garmin_reply_url


async def _fetch_message_text_and_url(message_id, mail: GraphMailService):
    """
    Hent mailens indhold og udtræk Saildocs kommando og Garmin reply URL
    """
    message = await mail.client.users \
        .by_user_id(configs.MAILBOX) \
        .messages \
        .by_message_id(message_id) \
        .get()

    body = message.body.content or ""
    body_type = message.body.content_type

    logger.info("Message body type: %s", body_type)

    if body_type == "html":
        decoded = _html_to_text(body)
    else:
        decoded = body

    decoded = decoded.lower()
    logger.info("Decoded message content:\n%s", decoded)

    msg_text = ""
    garmin_reply_url = None

    # -----------------------
    # Find Garmin reply URL
    # -----------------------
    idx = decoded.find(configs.BASE_GARMIN_REPLY_URL)
    if idx != -1:
        url_part = decoded[idx:]
        garmin_reply_url = url_part.split()[0]
        msg_text = decoded[:idx].strip()
    else:
        msg_text = decoded.strip()

    msg_text = msg_text.replace("reply to garmin:", "").strip()

    return msg_text, garmin_reply_url


def _html_to_text(html: str) -> str:
    """
    Simple HTML → text
    """
    html = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text)
