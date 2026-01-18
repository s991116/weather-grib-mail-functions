#FILE src/config_loader.py
import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.cfg")

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# Eksempel på at hente værdier
AZURE_CLIENT_ID = config['azure']['clientId']
AZURE_CLIENT_SECRET = config['azure']['clientSecret']
AZURE_TENANT_ID = config['azure']['tenantId']

MAILBOX = config['mail']['mailbox']
SERVICE_EMAIL = config['mail']['service_email']
SAILDOCS_EMAIL_QUERY = config['mail']['saildocs_email_query']
FILE_PATH = config['mail']['file_path']
PREVIOUS_MESSAGES_FILE = config['mail']['previous_messages_file']
BASE_GARMIN_REPLY_URL = config['mail']['base_garmin_reply_url']
