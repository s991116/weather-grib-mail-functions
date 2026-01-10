# main.py
import asyncio
import logging
import azure.functions as func
import argparse

from src.email_functions import process_new_inreach_message
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func

logger = logging.getLogger(__name__)

# ========================================
# CORE ASYNC FUNCTION
# ========================================

async def run():

    logger.info("Starting mail processor")

    try:
        # Get new InReach message + GRIB path
        result = await process_new_inreach_message()
        if result:
            grib_path, garmin_reply_url = result

            logger.info("Downloaded GRIB successfully")
            logger.info("GRIB path: %s", grib_path)
            logger.info("Garmin reply URL: %s", garmin_reply_url)

            # Encode GRIB to binary
            encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_path)
            logger.info("Encoded GRIB file successfully")

            # Send GRIB back to InReach
            await inreach_func.send_messages_to_inreach(garmin_reply_url, encoded_grib)
            logger.info("GRIB sent back to InReach")
        else:
            logger.info("No new messages")
        return True
    except Exception as e:
        logger.exception("Fatal error during processing: %s", e)
        return False


# ========================================
# LOCAL CLI ENTRYPOINT
# ========================================

def main_cli():
    """
    Local CLI entrypoint for testing.
    Supports optional loop and verbose logging.
    """

    parser = argparse.ArgumentParser(description="InReach mail processor")
    parser.add_argument("--loop", action="store_true", help="Run continuously (poll every 5 minutes)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Sæt logniveau baseret på --verbose
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    async def runner():
        if args.loop:
            while True:
                await run()
                await asyncio.sleep(300)  # 5 min polling
        else:
            await run()

    asyncio.run(runner())

# ========================================
# AZURE FUNCTION ENTRYPOINT
# ========================================

async def main(mytimer: func.TimerRequest):
    """
    Azure Function Timer Trigger entrypoint.
    """
    if mytimer.past_due:
        logger.warning("Timer trigger is running late")

    await run()


# ========================================
# PYTHON ENTRYPOINT
# ========================================

if __name__ == "__main__":
    main_cli()
