import logging
import uuid
import asyncio
from urllib.parse import urlparse, parse_qs

import httpx

import src.configs as configs
from src.inreach_sender import InReachSender


# =========================
# PUBLIC API
# =========================

# src/inreach_functions.py

import asyncio
import logging


async def send_messages_to_inreach(
    reply_url: str,
    messages: list[str],
    sender,
    delay_seconds: float = 1.0,
):
    """
    Sends split messages to InReach using the provided sender.
    """

    for idx, part in enumerate(messages, start=1):
        logging.info("Sending InReach message %s/%s", idx, len(messages))

        response = await sender.send(reply_url, part)

        if response.status_code != 200:
            raise RuntimeError(
                f"InReach send failed: {response.status_code} {response.text}"
            )

        if idx < len(messages):
            await asyncio.sleep(delay_seconds)


# =========================
# DEFAULT HTTP IMPLEMENTATION
# =========================

async def _post_request_to_inreach(
    client: httpx.AsyncClient,
    url: str,
    message_str: str,
) -> httpx.Response:
    """
    Default HTTP implementation of InReachSender.
    """
    logging.info("Garmin InReach URL: %s", url)
    logging.info("Garmin InReach message chunk len %s", len(message_str))

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
            response.text,
        )

    return response


# =========================
# HELPERS
# =========================

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
