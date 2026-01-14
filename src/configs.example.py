"""
Example configuration file.

This file documents all required and optional configuration values.
Do NOT put secrets in this file.

Copy this file to configs.py or configure the values as environment variables.
"""

# -------------------------
# Azure / Microsoft Graph
# -------------------------
TENANT_ID = "your-tenant-id"
CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"


# -------------------------
# Mail / InReach / Saildocs
# -------------------------
MAILBOX = "user@domain.com"  # The mailbox used in GraphMailService
SERVICE_EMAIL = "sender@domain.com"  # Sender of InReach emails
SAILDOCS_EMAIL_QUERY = "query@saildocs.com"  # Saildocs query address
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"  # Saildocs response address
TOP_SEARCH_COUNT_MAILBOX = 25

# -------------------------
# Garmin / InReach
# -------------------------
BASE_GARMIN_REPLY_URL = "https://garmin.com/sendmessage"
# Split length for outgoing InReach messages
MESSAGE_SPLIT_LENGTH = 120
# Delay between outgoing messages (seconds)
DELAY_BETWEEN_MESSAGES = 5


# -------------------------
# HTTP Headers (non-secret)
# -------------------------
INREACH_HEADERS = {
    "authority": "explore.garmin.com",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://explore.garmin.com",
    "sec-ch-ua": '"Chromium";v="106", "Not;A=Brand";v="99", "Google Chrome";v="106.0.5249.119"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-requested-with": "XMLHttpRequest",
}

INREACH_COOKIES = {
    "BrowsingMode": "Desktop",
}
