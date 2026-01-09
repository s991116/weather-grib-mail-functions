import asyncio
import logging
from datetime import datetime
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

    # Hent de seneste mails fra SERVICE_EMAIL
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
    # Hent tekst og reply URL
    msg_text, garmin_reply_url = await _fetch_message_text_and_url(message_id, mail)

    # Send GRIB request til Saildocs
    await mail.send_mail(
        sender=configs.MAILBOX,
        to=configs.SAILDOCS_EMAIL_QUERY,
        subject="",
        body="send " + msg_text
    )

    time_sent = datetime.utcnow()
    # Vent på Saildocs svar (synkron funktion i saildoc_functions)
    last_response = saildoc_func.wait_for_saildocs_response(time_sent)
    if not last_response:
        inreach_func.send_reply_to_inreach(garmin_reply_url, "Saildocs timeout")
        return None

    # Download GRIB attachment
    grib_path = await mail.download_grib_attachment(
        user_id=configs.MAILBOX,
        message_id=last_response.id,
        file_path=configs.FILE_PATH
    )

    if not grib_path:
        inreach_func.send_reply_to_inreach(garmin_reply_url, "Could not download GRIB file")
        return None

    return grib_path, garmin_reply_url


async def _fetch_message_text_and_url(message_id, mail: GraphMailService):
    """
    Fetch message body and extract Saildocs request text
    and Garmin reply URL.
    """
    message = await mail.client.users \
        .by_user_id(configs.MAILBOX) \
        .messages \
        .by_message_id(message_id) \
        .get()

    decoded = message.body.content.lower()
    msg_text = decoded.split("\r")[0]

    garmin_reply_url = next(
        (line.replace("\r", "") for line in decoded.split("\n")
         if configs.BASE_GARMIN_REPLY_URL in line),
        None
    )

    return msg_text, garmin_reply_url

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
