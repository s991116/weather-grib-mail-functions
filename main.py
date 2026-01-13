import os
import asyncio
import logging
import argparse
import json
from pathlib import Path
import sys

# =================================================
# LOGGING CONFIGURATION
# =================================================
# Root logger
logger = logging.getLogger()

if "FUNCTIONS_WORKER_RUNTIME" not in os.environ:

    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


    if "--verbose" in sys.argv:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
else:

    logger.setLevel(logging.INFO)

logger.info("Logger initialized")


# =================================================
# LOCAL CLI SUPPORT
# Load Azure Functions local.settings.json
# =================================================
def load_local_settings():
    """
    Load Azure Functions local.settings.json into environment variables.
    Only used for local CLI execution.
    """
    settings_path = Path(__file__).resolve().parent / "local.settings.json"

    if not settings_path.exists():
        return

    with open(settings_path) as f:
        data = json.load(f)

    values = data.get("Values", {})

    for key, value in values.items():
        # Do not override already-set environment variables
        os.environ.setdefault(key, value)


# =================================================
# CLI ARGUMENT PARSING (CLI ONLY)
# =================================================
if __name__ == "__main__":
    load_local_settings()

    parser = argparse.ArgumentParser(description="InReach mail processor")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously (poll every 5 minutes)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args, _ = parser.parse_known_args()
else:
    # Defaults when running in Azure Functions
    args = argparse.Namespace(loop=False, verbose=False)


# =================================================
# APPLICATION IMPORTS (after logging setup)
# =================================================
from src.email_functions import (
    process_new_inreach_message,
    process_new_saildocs_response,
)
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func
from src.mail.graph_mail import GraphMailService

logger.info("Imports completed")


# =================================================
# CORE ASYNC PROCESSOR
# =================================================
async def run():
    logger.info("Starting mail processor run()")

    mail = GraphMailService()

    try:
        saildocs_request = await process_new_inreach_message(mail)

        if not saildocs_request:
            logger.info("No new InReach requests")
            return True

        saildocs_command, garmin_reply_url = saildocs_request
        logger.info("Processed new InReach request")

        saildocs_response = await process_new_saildocs_response(
            mail,
            saildocs_command,
            garmin_reply_url,
        )

        if not saildocs_response:
            logger.info("No Saildocs response received within timeout")
            return True

        grib_file, reply_url = saildocs_response
        logger.info("Saildocs GRIB received in-memory")

        encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_file)
        await inreach_func.send_messages_to_inreach(reply_url, encoded_grib)

        logger.info("GRIB sent back to InReach")
        return True

    except Exception:
        logger.exception("Fatal error during mail processing")
        return False


# =================================================
# CLI ENTRYPOINT
# =================================================
def main_cli():
    async def runner():
        if args.loop:
            logger.info("Running in loop mode")
            while True:
                await run()
                await asyncio.sleep(300)
        else:
            await run()

    asyncio.run(runner())


# =================================================
# CLI EXECUTION
# =================================================
if __name__ == "__main__":
    main_cli()
