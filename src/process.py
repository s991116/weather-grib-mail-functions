#FILE src/process.py
import logging

from src.email_functions import (
    request_weather_report,
    process_new_saildocs_response,
    retrieve_new_inreach_request,
)
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.graph_mail import GraphMailService
from src.inreach_sender import InReachSender

# =================================================
# CORE ASYNC PROCESSOR
# =================================================
async def run(
    *,
    mail: GraphMailService | None = None,
    inreach_sender: InReachSender | None = None,
) -> bool:
    """
    Main processing loop.

    Parameters:
    - mail (GraphMailService, optional): injectable for tests
    - inreach_sender (InReachSender, optional): injectable for tests

    Returns:
    - bool: success/failure
    """
    logging.info("Starting mail processor run()")

    mail = mail or GraphMailService()
    inreach_sender = inreach_sender or InReachSender()

    try:
        # -------------------------------------------------
        # Step 1: Fetch InReach request
        # -------------------------------------------------
        inreach_request = await retrieve_new_inreach_request(mail)

        if not inreach_request:
            logging.info("No new InReach requests")
            return True

        # -------------------------------------------------
        # Step 2: Handle weather request
        # -------------------------------------------------
        if(inreach_request.type == "weather"):
            await request_weather_report(mail, inreach_request.payload_text)

            grib_file = await process_new_saildocs_response(
                mail,
                inreach_request.payload_text
            )

            if not grib_file:
                logging.info("No Saildocs response received within timeout")
                return True
            
            message_parts = saildoc_func.encode_saildocs_grib_file(grib_file)

        elif(inreach_request.type == "chat"):
            logging.warning("Chat request not implemented yet.")
            return True
        else:
            logging.warning("Chat request type is not handled: %s", inreach_request.type)
            return True
            
        # -------------------------------------------------
        # Step 4: Send to InReach
        # -------------------------------------------------
        wrapped_message_parts = inreach_func.wrap_messages(message_parts)
        await inreach_func.send_messages_to_inreach(
            inreach_request.reply_url,
            wrapped_message_parts,
            inreach_sender,
        )

        logging.info("GRIB sent back to InReach")
        return True

    except Exception:
        logging.exception("Fatal error during mail processing")
        return False
