#FILE function_app.py
import logging
import asyncio
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="process_mails")
@app.timer_trigger(schedule="0 */2 * * * *", arg_name="mytimer")
def process_mails(mytimer: func.TimerRequest):
    logging.info("Timer triggered")

    if mytimer.past_due:
        logging.warning("Timer trigger is past due")

    try:
        logging.info("Importing run() from main")
        from src import process
        logging.info("Successfully imported run()")

        asyncio.run(process.run())
        logging.info("Mail processing completed successfully")

    except Exception:
        logging.exception("❌ Error during import or execution of mail processor")
        raise
