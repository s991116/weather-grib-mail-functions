import datetime
import logging
# import sys
import azure.functions as func

# sys.path.append(".")

from src import email_functions as email_func
from src import saildoc_functions as saildoc_func
from src import inreach_functions as inreach_func

app = func.FunctionApp()

_auth_service = None

def get_auth_service():
    global _auth_service
    if _auth_service is None:
        try:
            logging.info("Authenticating Gmail")
            _auth_service = email_func.gmail_authenticate()
        except Exception:
            logging.exception("gmail_authenticate() failed")
            raise
    return _auth_service

@app.function_name(name="mytimer")
@app.timer_trigger(schedule="0 */2 * * * *", arg_name="mytimer")
def test_function(mytimer: func.TimerRequest) -> None:
    logging.info("HELLO - Timer triggered")

    if mytimer.past_due:
        logging.info("The timer is past due")

    auth = get_auth_service()
    # result = email_func.process_new_inreach_message(auth)

    # if result:
    #     grib_path, garmin_reply_url = result
    #     encoded_grib = saildoc_func.encode_saildocs_grib_file(grib_path)
    #     inreach_func.send_messages_to_inreach(garmin_reply_url, encoded_grib)
    #     logging.info("GRIB sent")
    # else:
    #     logging.info("No messages")
