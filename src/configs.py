#FILE src/configs.py
import os

# -------------------------
# HELPER FUNCTION
# -------------------------
def _get_env(name, default=None, required=True, cast=str):
    """
    Lazy load an environment variable.
    """
    value = os.getenv(name, default)
    if required and value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    if value is not None and cast is not None:
        try:
            value = cast(value)
        except Exception as e:
            raise RuntimeError(f"Environment variable {name} cannot be cast: {e}")
    return value

# -------------------------
# Azure / Microsoft Graph
# -------------------------
TENANT_ID = lambda: _get_env("TENANT_ID")
CLIENT_ID = lambda: _get_env("CLIENT_ID")
CLIENT_SECRET = lambda: _get_env("CLIENT_SECRET")

#--------------------------
# OpenAI
#--------------------------
OPEN_AI_KEY = lambda: _get_env("OPEN_AI_KEY")

# -------------------------
# Mail / InReach / Saildocs
# -------------------------
MAILBOX = lambda: _get_env("MAILBOX")
SERVICE_EMAIL = lambda: _get_env("SERVICE_EMAIL")
SAILDOCS_EMAIL_QUERY = lambda: _get_env("SAILDOCS_EMAIL_QUERY")
SAILDOCS_RESPONSE_EMAIL = lambda: _get_env("SAILDOCS_RESPONSE_EMAIL")
TOP_SEARCH_COUNT_MAILBOX = 25

# -------------------------
# Garmin / InReach
# -------------------------
BASE_GARMIN_REPLY_URL = "https://garmin.com/sendmessage"
MESSAGE_SPLIT_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

# -------------------------
# InReach HTTP headers & cookies (static)
# -------------------------
INREACH_HEADERS = {
    "authority": "explore.garmin.com",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://explore.garmin.com",
    "sec-ch-ua": "\"Chromium\";v=\"106\", \"Not;A=Brand\";v=\"99\", \"Google Chrome\";v=\"106.0.5249.119\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/106.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

INREACH_COOKIES = {
    "BrowsingMode": "Desktop",
}
