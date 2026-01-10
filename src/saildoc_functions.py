import time
import pandas as pd
import base64
import zlib
import asyncio
import logging
from datetime import datetime, timezone
from src import configs

from src import configs
from src import email_functions as email_func

async def process_new_saildocs_response(mail):
    """
    Fetch exactly one unread Saildocs response email.
    Marks it as read immediately for idempotency.
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

def encode_saildocs_grib_file(file_path):
    """
    Reads the content of a GRIB file, compresses it using zlib, then encodes the compressed data into a base64 string.

    Args:
    file_path (str): Path to the GRIB file that needs to be encoded.

    Returns:
    str: Base64 encoded string representation of the zlib compressed GRIB file content.
    """

    # Open the file in binary read mode and read its content
    with open(file_path, 'rb') as file:
        grib_binary = file.read()

    # Compress the binary content using zlib
    compressed_grib = zlib.compress(grib_binary)

    # Convert the compressed content to a base64 encoded string
    encoded_data = base64.b64encode(compressed_grib).decode('utf-8')

    return encoded_data

