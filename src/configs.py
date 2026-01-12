import os
import json

# -------------------------
# Azure / Microsoft Graph
# -------------------------
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# -------------------------
# Mail / InReach / Saildocs
# -------------------------
MAILBOX = os.getenv("MAILBOX")
SERVICE_EMAIL = os.getenv("SERVICE_EMAIL")
SAILDOCS_EMAIL_QUERY = os.getenv("SAILDOCS_EMAIL_QUERY")
SAILDOCS_RESPONSE_EMAIL = os.getenv("SAILDOCS_RESPONSE_EMAIL")

# -------------------------
# Garmin / InReach
# -------------------------
BASE_GARMIN_REPLY_URL = os.getenv("BASE_GARMIN_REPLY_URL")

MESSAGE_SPLIT_LENGTH = int(os.getenv("MESSAGE_SPLIT_LENGTH", "120"))
DELAY_BETWEEN_MESSAGES = int(os.getenv("DELAY_BETWEEN_MESSAGES", "5"))

# -------------------------
# InReach HTTP headers & cookies
# These are static and therefore kept in code
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

# -------------------------
# Optional startup validation (recommended)
# -------------------------
REQUIRED_VARS = [
    "TENANT_ID",
    "CLIENT_ID",
    "CLIENT_SECRET",
    "MAILBOX",
    "SERVICE_EMAIL",
    "SAILDOCS_EMAIL_QUERY",
    "SAILDOCS_RESPONSE_EMAIL",
    "BASE_GARMIN_REPLY_URL",
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing)}"
    )
