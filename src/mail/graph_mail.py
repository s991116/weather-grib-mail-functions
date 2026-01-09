import os
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


class GraphMailService:
    def __init__(self):
        self.credential = ClientSecretCredential(
            tenant_id=configs.TENANT_ID,
            client_id=configs.CLIENT_ID,
            client_secret=configs.CLIENT_SECRET
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

    # -------------------------
    # SEARCH MESSAGES
    # -------------------------
    async def search_messages(self, user_id, sender_email=None, subject_contains=None, top=50):
        """
        Search messages for a user with optional sender or subject filter.
        """
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            top=top
        )

        filters = []
        if sender_email:
            filters.append(f"from/emailAddress/address eq '{sender_email}'")
        if subject_contains:
            filters.append(f"contains(subject,'{subject_contains}')")

        filter_string = " and ".join(filters) if filters else None

        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        if filter_string:
            request_config.query_parameters.filter = filter_string

        return await self.client.users.by_user_id(user_id).messages.get(
            request_configuration=request_config
        )

    # -------------------------
    # DOWNLOAD GRIB ATTACHMENT
    # -------------------------
    async def download_grib_attachment(self, user_id, message_id, file_path):
        attachments = await self.client.users.by_user_id(user_id)\
            .messages.by_message_id(message_id)\
            .attachments.get()

        for att in attachments.value:
            if att.name and att.name.endswith(".grb"):
                full_path = os.path.join(file_path, att.name)
                with open(full_path, "wb") as f:
                    f.write(att.content_bytes)
                return full_path

        return None

