# FILE src/saildoc_functions.py
import asyncio
import logging
import base64
import hashlib
import src.configs as configs
from src import email_functions as email_func
from io import BytesIO


# =========================
# SAILDOCS EMAIL PROCESSING
# =========================
async def process_new_saildocs_response(mail):
    """
    Fetch exactly one unread Saildocs response email.
    Marks it as read immediately for idempotency.
    Returns the message object or None if no unread messages exist.
    """
    messages = await mail.search_messages(
        user_id=configs.MAILBOX(),
        sender_email=configs.SAILDOCS_RESPONSE_EMAIL(),
        unread_only=True,
        top=1
    )

    if not messages or not messages.value:
        logging.info("No unread Saildocs responses")
        return None

    msg = messages.value[0]
    logging.info("Processing unread Saildocs response: %s", msg.id)

    try:
        await mail.mark_as_read(configs.MAILBOX(), msg.id)
        logging.info("Marked Saildocs response as read: %s", msg.id)
    except Exception:
        logging.exception("Failed to mark Saildocs response as read")
        return None

    return msg


# =========================
# ENCODE GRIB
# =========================
def encode_saildocs_grib_file(file):
    """
    Accepts either a file path (str) or a BytesIO object.
    Returns a list of base64-encoded message chunks.
    """
    logging.info("Type: %s", type(file))
    logging.info("Tell before read: %s", file.tell() if hasattr(file, "tell") else "N/A")

    if isinstance(file, str):
        with open(file, "rb") as f:
            data = f.read()
    else:
        file.seek(0)
        data = file.read()

    logging.info("Raw Grib data size: %s", len(data))
    logging.info("Raw bytes hash: %s", hashlib.sha256(data).hexdigest())

    encoded = base64.b64encode(data).decode("ascii")
    encoded_split = _split_message(encoded)

    return encoded_split


# =========================
# DECODE GRIB
# =========================
def decode_saildocs_grib_file(message_chunks: list[str], output=None):
    """
    Accepts a list of message parts (from InReach) and reconstructs the original GRIB file.
    Decodes base64 content and writes binary GRIB file to either:
        - output (str): path to save file
        - output (BytesIO): in-memory buffer

    Returns:
    - str | BytesIO: path or buffer containing decoded GRIB
    """
    logging.info("Decoding %d message chunks", len(message_chunks))

    # Saml alle chunks til én base64 string
    encoded_data = ''
    for chunk in message_chunks:
        lines = chunk.strip().split("\n")
        if len(lines) >= 2:
            encoded_data += lines[1]

    # Decode base64
    grib_bytes = base64.b64decode(encoded_data)

    if isinstance(output, BytesIO):
        output.write(grib_bytes)
        output.seek(0)
        logging.info("Decoded GRIB written to BytesIO (%d bytes)", len(grib_bytes))
        return output
    elif isinstance(output, str) or output is None:
        out_path = output or "decoded.grb"
        with open(out_path, 'wb') as f:
            f.write(grib_bytes)
        logging.info("Decoded GRIB file written to %s (%d bytes)", out_path, len(grib_bytes))
        return out_path
    else:
        raise TypeError("output must be either None, str (file path), or BytesIO")


# =========================
# HELPERS
# =========================
def _split_message(gribmessage: str):
    """
    Splits a GRIB message into chunks for InReach messages.

    Returns:
    list[str]: formatted message chunks ("msg x/y:\n<data>\nend")
    """
    logging.info(
        "Split message: encoded_len=%s split_len=%s",
        len(gribmessage),
        configs.MESSAGE_SPLIT_LENGTH
    )

    chunks = [
        gribmessage[i:i + configs.MESSAGE_SPLIT_LENGTH]
        for i in range(0, len(gribmessage), configs.MESSAGE_SPLIT_LENGTH)
    ]

    total_splits = len(chunks)
    return [
        f"msg {index + 1}/{total_splits}:\n{chunk}\nend"
        for index, chunk in enumerate(chunks)
    ]
