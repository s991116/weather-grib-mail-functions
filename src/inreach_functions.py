#FILE src/inreach_functions.py
import logging
import asyncio
import src.configs as configs
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

def split_message(message: str):
    """
    Splits a message into chunks for InReach messages.

    Returns:
    list[str]: where input message is split to configured MESSAGE_SPLIT_LENGTH
    """
    logging.info(
        "Split message: encoded_len=%s split_len=%s",
        len(message),
        configs.MESSAGE_SPLIT_LENGTH
    )

    chunks = [
        message[i:i + configs.MESSAGE_SPLIT_LENGTH]
        for i in range(0, len(message), configs.MESSAGE_SPLIT_LENGTH)
    ]

    return chunks

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
