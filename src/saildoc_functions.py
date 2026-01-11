import asyncio
import logging
import base64
from src import configs
from src import email_functions as email_func

async def process_new_saildocs_response(mail):
    """
    Fetch exactly one unread Saildocs response email.
    Marks it as read immediately for idempotency.
    Returns the message object or None if no unread messages exist.
    """

    messages = await mail.search_messages(
        user_id=configs.MAILBOX,
        sender_email=configs.SAILDOCS_RESPONSE_EMAIL,
        unread_only=True,
        top=1
    )

    if not messages or not messages.value:
        logging.info("No unread Saildocs responses")
        return None

    msg = messages.value[0]
    logging.info("Processing unread Saildocs response: %s", msg.id)

    try:
        await mail.mark_as_read(configs.MAILBOX, msg.id)
        logging.info("Marked Saildocs response as read: %s", msg.id)
    except Exception:
        logging.exception("Failed to mark Saildocs response as read")
        return None

    return msg

def encode_saildocs_grib_file(file):
    """
    Accepts either a file path (str) or a BytesIO object.
    Returns base64-encoded content as a string.
    """
    if isinstance(file, str):
        with open(file, "rb") as f:
            data = f.read()
    else:
        file.seek(0)
        data = file.read()
    return base64.b64encode(data).decode("ascii")
