import asyncio
import base64
from io import BytesIO

import pytest

from src.saildoc_functions import encode_saildocs_grib_file
from src.inreach_functions import send_messages_to_inreach


@pytest.mark.asyncio
async def test_grib_encode_split_send_merge_decode(monkeypatch):
    # ======================
    # Arrange
    # ======================

    original_bytes = b"GRIB-DATA-" * 500  # deterministic binary payload
    fake_grib = BytesIO(original_bytes)

    encoded = encode_saildocs_grib_file(fake_grib)

    sent_messages = []

    # ----------------------
    # Mock asyncio.sleep
    # ----------------------
    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # ----------------------
    # Mock httpx.AsyncClient.post
    # ----------------------
    class FakeResponse:
        status_code = 200
        text = "OK"

    async def fake_post(self, url, cookies=None, headers=None, data=None):
        sent_messages.append(data["ReplyMessage"])
        return FakeResponse()

    monkeypatch.setattr(
        "httpx.AsyncClient.post",
        fake_post
    )

    # ======================
    # Act
    # ======================
    await send_messages_to_inreach(
        url="https://garmin.com/sendmessage?extId=TEST-GUID",
        gribmessage=encoded
    )

    # ======================
    # Assert: messages sent
    # ======================
    assert len(sent_messages) > 1

    # ======================
    # Reassemble payload
    # ======================
    extracted_chunks = []

    for msg in sent_messages:
        # msg format:
        # msg X/Y:\n<chunk>\nend
        lines = msg.splitlines()
        extracted_chunks.append(lines[1])

    merged_encoded = "".join(extracted_chunks)
    decoded = base64.b64decode(merged_encoded.encode("ascii"))

    assert decoded == original_bytes
