import logging
import uuid
import asyncio
from urllib.parse import urlparse, parse_qs

import httpx

import src.configs as configs


# =========================
# PUBLIC API
# =========================

async def send_messages_to_inreach(url: str, gribmessage: str):
    """
    Splits the gribmessage and sends each part to InReach asynchronously.

    Parameters:
    - url (str): The target URL for the InReach API.
    - gribmessage (str): The full message string to be split and sent.

    Returns:
    - list[httpx.Response]: Responses from the InReach API
    """
    message_parts = _split_message(gribmessage)

    responses = []

    async with httpx.AsyncClient(timeout=10) as client:
        for part in message_parts:
            response = await _post_request_to_inreach(client, url, part)
            responses.append(response)

            # Delay between messages (non-blocking)
            await asyncio.sleep(configs.DELAY_BETWEEN_MESSAGES)

    return responses


# =========================
# HELPERS
# =========================

def _split_message(gribmessage: str):
    """
    Splits a GRIB message into chunks.

    Returns:
    list[str]: Formatted message chunks.
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


async def _post_request_to_inreach(
    client: httpx.AsyncClient,
    url: str,
    message_str: str
):
    """
    Sends a POST request to the InReach reply URL.
    """
    logging.info("Garmin InReach URL: %s", url)
    logging.info("Garmin InReach message chunk len %s", len(message_str))
    logging.info("Garmin InReach message: %s", message_str)

    guid = _extract_guid_from_url(url)

    data = {
        "ReplyAddress": configs.MAILBOX(),
        "ReplyMessage": message_str,
        "MessageId": str(uuid.uuid4()),
        "Guid": guid,
    }

    response = await client.post(
        url,
        cookies=configs.INREACH_COOKIES,
        headers=configs.INREACH_HEADERS,
        data=data,
    )

    if response.status_code == 200:
        logging.info("InReach reply sent successfully")
    else:
        logging.error(
            "Failed to send InReach reply (%s): %s",
            response.status_code,
            response.text
        )

    return response


def _extract_guid_from_url(url: str) -> str:
    """
    Extract extId/extid GUID from Garmin reply URL.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    guid = qs.get("extId") or qs.get("extid")
    if not guid:
        raise ValueError(f"No extId found in InReach URL: {url}")

    return guid[0]
