import asyncio
import re
import logging
from datetime import datetime
from html import unescape
from src import configs
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.mail.graph_mail import GraphMailService

# =========================
# PUBLIC ENTRYPOINT
# =========================
async def process_new_inreach_message():
    """
    Check for new InReach messages, request Saildocs GRIB,
    and return GRIB path + Garmin reply URL.
    """
    previous_messages = _load_previous_messages()
    mail = GraphMailService()

    # Fetch the latest messages from SERVICE_EMAIL
    messages = await mail.search_messages(
        user_id=configs.MAILBOX,
        sender_email=configs.SERVICE_EMAIL
    )

    if not messages or not messages.value:
        return None
    
    unanswered_ids = {msg.id for msg in messages.value if msg.id not in previous_messages}
    if not unanswered_ids:
        return None

    grib_path = None
    garmin_reply_url = None

    for message_id in unanswered_ids:
        logging.info("New message received: %s", message_id)
        try:
            grib_path, garmin_reply_url = await _request_and_process_saildocs_grib(message_id, mail)
            logging.info("Answered message %s", message_id)
        except Exception as e:
            logging.error("Error processing message %s: %s", message_id, e)
        finally:
            _append_to_previous_messages(message_id)

    return grib_path, garmin_reply_url

# =========================
# INTERNAL HELPERS
# =========================
async def _request_and_process_saildocs_grib(message_id, mail: GraphMailService):
    # Fetch message text and reply URL
    msg_text, garmin_reply_url = await _fetch_message_text_and_url(message_id, mail)

    logging.info(
        "Mail msg sent to Saildocs server: %r",
        msg_text
    )

    # Send GRIB request to Saildocs
    await mail.send_mail(
        sender=configs.MAILBOX,
        to=configs.SAILDOCS_EMAIL_QUERY,
        subject="",
        body="send " + msg_text
    )

    time_sent = datetime.utcnow()
    # Wait for Saildocs response (synchronous function in saildoc_functions)   
    last_response = await saildoc_func.wait_for_saildocs_response(mail, time_sent)

    if not last_response:
        # Send single message to InReach (timeout)
        logging.info("Sail docs timeout messages to garmin_inreacy.")
        await inreach_func.send_messages_to_inreach(garmin_reply_url, "Saildocs timeout")
        return None

    # Download GRIB attachment
    grib_path = await mail.download_grib_attachment(
        user_id=configs.MAILBOX,
        message_id=last_response.id,
        file_path=configs.FILE_PATH
    )

    if not grib_path:
        # Send single message to InReach (GRIB download failure)
        logging.info("Could not download GRIB file.")
        await inreach_func.send_messages_to_inreach(garmin_reply_url, "Could not download GRIB file")
        return None

    return grib_path, garmin_reply_url


async def _fetch_message_text_and_url(message_id, mail: GraphMailService):
    """
    Fetch message body and extract Saildocs request text (first line / text)
    and Garmin reply URL.
    """
    message = await mail.client.users \
        .by_user_id(configs.MAILBOX) \
        .messages \
        .by_message_id(message_id) \
        .get()

    body = message.body.content or ""
    body_type = message.body.content_type

    logging.info("Message body type: %s", body_type)

    # Convert HTML → text if needed
    if body_type == "html":
        decoded = _html_to_text(body)
    else:
        decoded = body

    decoded = decoded.lower()
    logging.info("Decoded message content:\n%s", decoded)

    msg_text = ""
    garmin_reply_url = None

    # -----------------------
    # Extract Garmin reply URL
    # -----------------------
    idx = decoded.find(configs.BASE_GARMIN_REPLY_URL)
    if idx != -1:
        # Everything from BASE_GARMIN_REPLY_URL until whitespace/end
        url_part = decoded[idx:]
        garmin_reply_url = url_part.split()[0]

        # Everything before reply URL is the message text
        msg_text = decoded[:idx].strip()
    else:
        # No reply URL → whole content is message text
        msg_text = decoded.strip()

    # Remove trailing "reply to garmin:" if present
    msg_text = msg_text.replace("reply to garmin:", "").strip()

    return msg_text, garmin_reply_url


def _html_to_text(html: str) -> str:
    """
    Very lightweight HTML → text conversion.
    Good enough for emails and Saildocs commands.
    """
    # Remove scripts and styles
    html = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.S | re.I)
    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", "", html)
    # Decode HTML entities (&nbsp; etc.)
    text = unescape(text)
    return text


# =========================
# MESSAGE TRACKING
# =========================
def _load_previous_messages():
    try:
        with open(configs.PREVIOUS_MESSAGES_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def _append_to_previous_messages(message_id):
    with open(configs.PREVIOUS_MESSAGES_FILE, "a") as f:
        f.write(f"{message_id}\n")
