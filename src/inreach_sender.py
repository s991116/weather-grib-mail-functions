#FILE src/inreach_sender.py

import httpx
import logging
import uuid
import src.configs as configs
from urllib.parse import urlparse, parse_qs


class InReachSender:
    async def send(self, url: str, message: str) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            logging.info("Sending InReach message")
            return await self.post_request_to_inreach(client, url, message)
        
    # =========================
    # DEFAULT HTTP IMPLEMENTATION
    # =========================

    async def post_request_to_inreach(
        self,
        client: httpx.AsyncClient,
        url: str,
        message_str: str,
    ) -> httpx.Response:
        """
        Default HTTP implementation of InReachSender.
        """
        logging.info("Garmin InReach URL: %s", url)
        logging.info("Garmin InReach message chunk len %s", len(message_str))
        logging.info("Garmin InReach message: %s", message_str)

        guid = self._extract_guid_from_url(url)

        data = {
            "ReplyAddress": configs.MAILBOX(),
            "ReplyMessage": message_str,
            "MessageId": str(uuid.uuid4()),
            "Guid": guid,
        }

        response = await client.post(
            url,
            cookies=configs.INREACH_COOKIES,
            headers=configs.INREACH_HEADERS,
            data=data,
        )

        if response.status_code == 200:
            logging.info("InReach reply sent successfully")
        else:
            logging.error(
                "Failed to send InReach reply (%s): %s",
                response.status_code,
                response.text,
            )

        return response


    # =========================
    # HELPERS
    # =========================

    def _extract_guid_from_url(self, url: str) -> str:
        """
        Extract extId/extid GUID from Garmin reply URL.
        """
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        guid = qs.get("extId") or qs.get("extid")
        if not guid:
            raise ValueError(f"No extId found in InReach URL: {url}")

        return guid[0]

