import logging

from src.email_functions import (
    process_new_inreach_message,
    process_new_saildocs_response,
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

    try:
        # -------------------------------------------------
        # Step 1: Fetch InReach request
        # -------------------------------------------------
        saildocs_request = await process_new_inreach_message(mail)

        if not saildocs_request:
            logging.info("No new InReach requests")
            return True

        saildocs_command, garmin_reply_url = saildocs_request
        logging.info("Processed new InReach request")

        # -------------------------------------------------
        # Step 2: Fetch Saildocs response
        # -------------------------------------------------
        saildocs_response = await process_new_saildocs_response(
            mail,
            saildocs_command,
            garmin_reply_url,
        )

        if not saildocs_response:
            logging.info("No Saildocs response received within timeout")
            return True

        grib_file, reply_url = saildocs_response
        logging.info("Saildocs GRIB received in-memory")

        # -------------------------------------------------
        # Step 3: Encode + split GRIB
        # -------------------------------------------------
        message_parts = saildoc_func.encode_saildocs_grib_file(grib_file)

        # -------------------------------------------------
        # Step 4: Send to InReach
        # -------------------------------------------------
        await inreach_func.send_messages_to_inreach(
            reply_url,
            message_parts,
            sender=inreach_sender,
        )


        logging.info("GRIB sent back to InReach")
        return True

    except Exception:
        logging.exception("Fatal error during mail processing")
        return False
