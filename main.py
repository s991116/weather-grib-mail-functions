# main.py
import asyncio
import logging
import azure.functions as func
import argparse

from src.email_functions import process_new_inreach_message
from src.email_functions import process_new_saildocs_response
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.mail.graph_mail import GraphMailService

logger = logging.getLogger(__name__)

# ========================================
# CORE ASYNC FUNCTION
# ========================================
async def run():
    logger.info("Starting mail processor")
    mail = GraphMailService()
    
    try:
        # 1️⃣ Behandl evt. ny Garmin inReach request
        saildocs_request_result = await process_new_inreach_message(mail)

        if saildocs_request_result:
            saildocs_command, garmin_reply_url = saildocs_request_result
            logger.info("Processed new InReach request")

            # 2️⃣ Poll efter Saildocs svar i op til 1 min
            saildocs_response = await process_new_saildocs_response(mail, saildocs_command, garmin_reply_url)

            if saildocs_response:
                grib_path, reply_url = saildocs_response
                logger.info("Saildocs GRIB ready: %s", grib_path)

                encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_path)
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
# LOCAL CLI ENTRYPOINT
# ========================================
def main_cli():
    parser = argparse.ArgumentParser(description="InReach mail processor")
    parser.add_argument("--loop", action="store_true", help="Run continuously (poll every 5 minutes)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

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
async def main(mytimer: func.TimerRequest):
    if mytimer.past_due:
        logger.warning("Timer trigger is running late")
    await run()


# ========================================
# PYTHON ENTRYPOINT
# ========================================
if __name__ == "__main__":
    main_cli()
