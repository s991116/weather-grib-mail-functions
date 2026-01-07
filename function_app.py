import sys
import logging
import azure.functions as func

# Sørg for at src-mappen kan importeres
sys.path.append(".")

from src import email_functions as email_func
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func

app = func.FunctionApp()

# Gmail-auth udføres én gang ved cold start
auth_service = email_func.gmail_authenticate()


@app.timer_trigger(
    schedule="0 */1 * * * *",  # hvert minut
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function started - checking InReach messages")

    try:
        # check for new messages and retrieve GRIB path and Garmin reply URL
        result = email_func.process_new_inreach_message(auth_service)

        if result is not None:
            grib_path, garmin_reply_url = result
            logging.info(f"New InReach message received. GRIB path: {grib_path}")

            # encode GRIB to binary
            encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_path)

            # send the encoded GRIB to InReach
            inreach_func.send_messages_to_inreach(
                garmin_reply_url,
                encoded_grib
            )

            logging.info("GRIB file successfully sent to InReach")
        else:
            logging.info("No new InReach messages found")

    except Exception as e:
        logging.error("Error while processing InReach messages", exc_info=True)

    logging.info("Python timer trigger function finished")
