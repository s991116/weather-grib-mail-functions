# FILE src/saildoc_functions.py
import asyncio
import logging
import base64
import hashlib
import src.configs as configs
from io import BytesIO
from src.graph_mail import GraphMailService

# =========================
# SAILDOCS EMAIL PROCESSING
# =========================
async def process_new_saildocs_response(mail : GraphMailService):
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
def encode_saildocs_grib_file(file: str | BytesIO):
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
    logging.info("Raw Grib data: %s", data)

    encoded = base64.b64encode(data).decode("ascii")
    logging.info("Base64 encode data: %s", encoded)
    encoded_split = _split_message(encoded)

    return encoded_split


# =========================
# DECODE GRIB
# =========================
def decode_saildocs_grib_file(message_chunks: list[str]):
    """
    Accepts a list of base64-encoded message chunks and reconstructs
    the original GRIB file.

    Each element in message_chunks MUST be a plain base64 string
    with no headers, footers, or newlines.

    Args:
        message_chunks (list[str]): Base64 chunks in correct order
        output (str | BytesIO | None):
            - str: file path to write GRIB
            - BytesIO: in-memory buffer
            - None: defaults to 'decoded.grb'

    Returns:
        str | BytesIO
    """
    logging.info("Decoding %d base64 chunks", len(message_chunks))

    if not message_chunks:
        raise ValueError("message_chunks is empty")

    # 1. Concatenate base64 chunks directly
    encoded_data = "".join(message_chunks)

    logging.info("Total encoded length: %d", len(encoded_data))

    # 2. Decode base64 → raw GRIB bytes
    grib_bytes = base64.b64decode(encoded_data)

    logging.info("Decoded GRIB size: %d bytes", len(grib_bytes))

    return grib_bytes


# ===================================================
# PARSE TEXT_RECEIVED → list[str]
# ===================================================
import logging

def unwrap_messages_to_payload_chunks(text: str) -> list[str]:
    """
    Parse InReach messages of the form:

        msg 1/31
        <base64>
        end

    Returns:
        list[str]: base64 payloads in correct order
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

    payloads: list[str] = []
    i = 0

    while i < len(lines):
        header = lines[i]
        payload = lines[i + 1]
        footer = lines[i + 2]

        if not header.startswith("msg "):
            raise ValueError(f"Expected 'msg x/y' at line {i}, got: {header}")

        if footer != "end":
            raise ValueError(f"Expected 'end' at line {i+2}, got: {footer}")

        payloads.append(payload)
        i += 3

    logging.info("Parsed %d payload chunks", len(payloads))
    logging.info("Total base64 length: %d", sum(len(p) for p in payloads))

    return payloads


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

    return chunks