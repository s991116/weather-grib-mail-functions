import logging
import asyncio
import azure.functions as func

logging.info("Start importing run method")
from main import run  # importér run() fra main.py
logging.info("Imported run method")

app = func.FunctionApp()

# =======================================
# TIMER TRIGGER
# =======================================
@app.function_name(name="process_mails")
@app.timer_trigger(schedule="0 */2 * * * *", arg_name="mytimer") #"schedule": "0 */2 * * * *"  // Hver 2. minut
def process_mails(mytimer: func.TimerRequest):
    logging.info("Timer triggered....")

    if mytimer.past_due:
        logging.warning("Timer trigger is past due")

    try:
        asyncio.run(run())
        logging.info("Mail processing completed successfully")
    except Exception:
        logging.exception("Error running mail processor")
