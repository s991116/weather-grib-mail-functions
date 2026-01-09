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

async def wait_for_saildocs_response(mail, time_sent, timeout_seconds=600, poll_interval=10):
    """
    Wait for a Saildocs response email received after time_sent.

    Args:
        mail (GraphMailService): Initialized GraphMailService
        time_sent (datetime): Timestamp when Saildocs request was sent (UTC)
        timeout_seconds (int): Max wait time
        poll_interval (int): Seconds between polls

    Returns:
        Message | None: Microsoft Graph Message or None on timeout
    """
    deadline = datetime.now(timezone.utc).timestamp() + timeout_seconds

    while datetime.now(timezone.utc).timestamp() < deadline:
        logging.info("Polling for Saildocs response...")

        messages = await mail.search_messages(
            user_id=configs.MAILBOX,
            sender_email=configs.SAILDOCS_RESPONSE_EMAIL,
            top=25
        )

        if messages and messages.value:
            logging.info("Saildocs messages receives from %s", configs.SAILDOCS_RESPONSE_EMAIL)
            
            time_sent_utc = time_sent.replace(tzinfo=timezone.utc)
            logging.info("Looking for new mails received after (UTC): %s", time_sent_utc)

            for msg in messages.value:
                received = msg.received_date_time
                received_utc = received.replace(tzinfo=timezone.utc)
                logging.info("Saildocs message receive at (UTC): %s", received_utc)

                if received and received.replace(tzinfo=timezone.utc) > time_sent_utc:
                    logging.info("Saildocs response received: %s", msg.id)
                    return msg

        await asyncio.sleep(poll_interval)

    logging.warning("Timeout waiting for Saildocs response")
    return None
