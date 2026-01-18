#FILE src/inreach_functions.py
import logging
import asyncio

async def send_messages_to_inreach(
    reply_url: str,
    messages: list[str],
    sender,
    delay_seconds: float = 1.0,
):
    """
    Sends split messages to InReach using the provided sender.
    Attempts to send all messages, even if some fail.
    Logs errors per message instead of raising immediately.
    """
    for idx, part in enumerate(messages, start=1):
        try:
            logging.info("Sending InReach message %s/%s", idx, len(messages))
            response = await sender.send(reply_url, part)

            if response.status_code == 200:
                logging.info("Message %s/%s sent successfully", idx, len(messages))
            else:
                logging.error(
                    "Failed to send message %s/%s: %s %s",
                    idx,
                    len(messages),
                    response.status_code,
                    response.text,
                )

        except Exception as e:
            logging.exception("Exception sending message %s/%s: %s", idx, len(messages), e)

        if idx < len(messages):
            await asyncio.sleep(delay_seconds)
