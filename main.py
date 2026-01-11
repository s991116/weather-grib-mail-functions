import asyncio
import logging
import argparse
import sys
import os

# ========================================
# ARGUMENT PARSING (kun CLI)
# ========================================
parser = argparse.ArgumentParser(description="InReach mail processor")
parser.add_argument("--loop", action="store_true", help="Run continuously (poll every 5 minutes)")
parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
args, unknown = parser.parse_known_args()

# ========================================
# CONFIGURE LOGGING
# ========================================
if "FUNCTIONS_WORKER_RUNTIME" in os.environ:
    logger = logging.getLogger(__name__)  # Azure Functions logger
else:
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)

logger.info("Starting mail processor imports")

# ========================================
# IMPORTS (efter logging opsætning)
# ========================================
from src.email_functions import (
    process_new_inreach_message,
    process_new_saildocs_response,
)
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.mail.graph_mail import GraphMailService

logger.info("Imports completed")

# ========================================
# CORE ASYNC FUNCTION
# ========================================
async def run():
    logger.info("Starting mail processor run()")
    mail = GraphMailService()

    try:
        saildocs_request_result = await process_new_inreach_message(mail)

        if saildocs_request_result:
            saildocs_command, garmin_reply_url = saildocs_request_result
            logger.info("Processed new InReach request")

            saildocs_response = await process_new_saildocs_response(
                mail,
                saildocs_command,
                garmin_reply_url,
            )

            if saildocs_response:
                grib_file, reply_url = saildocs_response
                logger.info("Saildocs GRIB received in-memory")

                encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_file)
                await inreach_func.send_messages_to_inreach(reply_url, encoded_grib)

                logger.info("GRIB sent back to InReach")
            else:
                logger.info("No Saildocs response received within timeout")
        else:
            logger.info("No new InReach requests")

        return True

    except Exception:
        logger.exception("Fatal error during processing")
        return False

# ========================================
# CLI ENTRYPOINT
# ========================================
def main_cli():
    async def runner():
        if args.loop:
            while True:
                await run()
                await asyncio.sleep(300)
        else:
            await run()

    asyncio.run(runner())


# ========================================
# AZURE FUNCTION ENTRYPOINT
# ========================================
async def main(req=None):
    success = await run()
    return success


# ========================================
# CLI CHECK
# ========================================
if __name__ == "__main__":
    main_cli()
