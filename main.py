#FILE main.py
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
from src import process
logger.info("Imports completed")

# =================================================
# CLI ENTRYPOINT
# =================================================
def main_cli():
    async def runner():
        if args.loop:
            logger.info("Running in loop mode")
            while True:
                await process.run()
                await asyncio.sleep(300)
        else:
            await process.run()

    asyncio.run(runner())

# =================================================
# CLI EXECUTION
# =================================================
if __name__ == "__main__":
    main_cli()
