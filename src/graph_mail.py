#FILE src/graph_mail.py
import os
import logging
from io import BytesIO
import base64

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder

from src import configs

logger = logging.getLogger(__name__)

class GraphMailService:

    def __init__(self):
        self.credential = ClientSecretCredential(
            tenant_id = configs.TENANT_ID(), 
            client_id = configs.CLIENT_ID(),
            client_secret = configs.CLIENT_SECRET()
        )
        self.client = GraphServiceClient(self.credential)

    # -------------------------
    # SEND MAIL
    # -------------------------
    async def send_mail(self, sender, to, subject, body):
        message = Message(
            subject=subject,
            body=ItemBody(
                content_type=BodyType.Text,
                content=body
            ),
            to_recipients=[
                Recipient(email_address=EmailAddress(address=to))
            ]
        )

        request_body = SendMailPostRequestBody(
            message=message,
            save_to_sent_items=True
        )

        await self.client.users.by_user_id(sender).send_mail.post(body=request_body)
        logger.info("Mail sent from %s to %s", sender, to)

    # -------------------------
    # SEARCH MESSAGES
    # -------------------------
    async def search_messages(self, user_id: str, sender_email: str | None = None, subject_contains: str | None =None, top: int = 50, unread_only: bool=False):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=top
        )

        filters = []
        if unread_only:
            filters.append("isRead eq false")
        if subject_contains:
            filters.append(f"contains(subject,'{subject_contains}')")

        filter_string = " and ".join(filters) if filters else None

        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        if filter_string:
            request_config.query_parameters.filter = filter_string

        try:
            result = await self.client.users.by_user_id(user_id).messages.get(
                request_configuration=request_config
            )

            messages = result.value or []

            # Filter sender in Python to avoid InefficientFilter
            if sender_email:
                messages = [
                    m for m in messages
                    if m.from_ and m.from_.email_address.address.lower() == sender_email.lower()
                ]

            # Sort in Python (nyeste først)
            messages.sort(key=lambda m: m.received_date_time, reverse=True)

            # Return as fake object with .value to match SDK interface
            class DummyCollection:
                def __init__(self, val):
                    self.value = val

            return DummyCollection(messages)

        except Exception as e:
            logger.exception("Failed to search messages: %s", e)
            raise

    

    # -------------------------
    # DOWNLOAD GRIB ATTACHMENT (IN-MEMORY)
    # -------------------------
    async def download_grib_attachment(self, user_id, message_id):
        try:
            attachments = await self.client.users.by_user_id(user_id)\
                .messages.by_message_id(message_id)\
                .attachments.get()

            for att in attachments.value:
                if att.name and att.name.lower().endswith(".grb"):

                    # contentBytes fra Graph er ALTID Base64
                    raw_bytes = base64.b64decode(att.content_bytes)

                    grib_file = BytesIO(raw_bytes)
                    grib_file.name = att.name
                    grib_file.seek(0)

                    logger.info(
                        "Downloaded GRIB %s (decoded size=%d)",
                        att.name,
                        len(raw_bytes),
                    )
                    return grib_file

            logger.info("No GRIB attachment found in message %s", message_id)
            return None

        except Exception:
            logger.exception("Failed to download attachment from message %s", message_id)
            raise

    # -------------------------
    # MARK MAIL AS READ
    # -------------------------
    async def mark_as_read(self, user_id: str, message_id: str):
        """
        Mark a Microsoft Graph email as read.
        SDK-kompatibel og fremtidssikker.
        """
        try:
            # Brug en Message-model, ikke dict
            message_update = Message(is_read=True)
            await self.client.users.by_user_id(user_id).messages.by_message_id(message_id).patch(message_update)
            logger.info("Marked message %s as read", message_id)
        except Exception as e:
            logger.exception("Failed to mark message %s as read: %s", message_id, e)
            raise
