import logging
import asyncio
from src.email_functions import (
    process_new_inreach_message,
    process_new_saildocs_response,
)

from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.graph_mail import GraphMailService

# =================================================
# CORE ASYNC PROCESSOR
# =================================================
async def run():
    logging.info("Starting mail processor run()")

    mail = GraphMailService()

    try:
        saildocs_request = await process_new_inreach_message(mail)

        if not saildocs_request:
            logging.info("No new InReach requests")
            return True

        saildocs_command, garmin_reply_url = saildocs_request
        logging.info("Processed new InReach request")

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

        encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_file)
        await inreach_func.send_messages_to_inreach(reply_url, encoded_grib)

        logging.info("GRIB sent back to InReach")
        return True

    except Exception:
        logging.exception("Fatal error during mail processing")
        return False
