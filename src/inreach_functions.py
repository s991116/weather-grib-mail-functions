#FILE src/inreach_functions.py
import logging
import asyncio
from src.inreach_sender import InReachSender

async def send_messages_to_inreach(
    reply_url: str,
    wrapped_messages: list[str],
    sender: InReachSender,
    delay_seconds: float = 1.0,
):
    """
    Sends split messages to InReach using the provided sender.
    Attempts to send all messages, even if some fail.
    Logs errors per message instead of raising immediately.
    """

    for idx, part in enumerate(wrapped_messages, start=1):
        try:
            logging.info("Sending InReach message %s/%s", idx, len(wrapped_messages))
            response = await sender.send(reply_url, part)

            if response.status_code == 200:
                logging.info("Message %s/%s sent successfully", idx, len(wrapped_messages))
            else:
                logging.error(
                    "Failed to send message %s/%s: %s %s",
                    idx,
                    len(wrapped_messages),
                    response.status_code,
                    response.text,
                )

        except Exception as e:
            logging.exception("Exception sending message %s/%s: %s", idx, len(wrapped_messages), e)

        if idx < len(wrapped_messages):
            await asyncio.sleep(delay_seconds)

def wrap_messages(encodedmessages: list[str]):
    """
    Wrap each message with into the format "msg x/y:\n<data>\nend")
    Where x is message nr from 1 to y, and y is the total number of messages
    """

    total_splits = len(encodedmessages)
    return [
        f"msg {index + 1}/{total_splits}:\n{encodedMessage}\nend"
        for index, encodedMessage in enumerate(encodedmessages)
    ]
