import asyncio
import base64
import logging
import pytest

from io import BytesIO
from pathlib import Path

from src.saildoc_functions import encode_saildocs_grib_file
from src.inreach_functions import send_messages_to_inreach


@pytest.mark.asyncio
async def test_saildocs_to_inreach_roundtrip(monkeypatch):
    """
    End-to-end test:
    Saildocs attachment → encode → split → send → merge → decode
    """

    # =====================================================
    # Arrange
    # =====================================================

    # Load real test attachment
    fixture_path = Path(__file__).parent / "fixtures" / "ecmwf20260113071001417.grb"
    original_bytes = fixture_path.read_bytes()

    fake_grib = BytesIO(original_bytes)

    # Encode as Saildocs does
    encoded = encode_saildocs_grib_file(fake_grib)

    sent_messages = []

    # -----------------------------------------
    # Mock asyncio.sleep (speed up test)
    # -----------------------------------------
    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # -----------------------------------------
    # Mock Garmin InReach HTTP POST
    # -----------------------------------------
    class FakeResponse:
        status_code = 200
        text = "OK"

    async def fake_post(self, url, cookies=None, headers=None, data=None):
        # Capture the actual InReach payload
        sent_messages.append(data["ReplyMessage"])
        return FakeResponse()

    monkeypatch.setattr(
        "httpx.AsyncClient.post",
        fake_post
    )

    # =====================================================
    # Act
    # =====================================================

    await send_messages_to_inreach(
        url="https://garmin.com/sendmessage?extId=TEST-GUID",
        gribmessage=encoded,
    )

    # =====================================================
    # Assert – merge & decode
    # =====================================================

    assert sent_messages, "No InReach messages were sent"

    logger = logging.getLogger(__name__)

    logger.info("===== InReach messages sent =====")
    for i, msg in enumerate(sent_messages, 1):
        logger.info("Message %d:\n%s", i, msg)
    logger.info("===== End messages =====")


    # Sort by msg X/Y index
    sent_messages.sort(key=lambda m: int(m.split()[1].split("/")[0]))

    # Extract payload text only
    merged_encoded = "".join(
        msg.split(":\n", 1)[1].rsplit("\nend", 1)[0]
        for msg in sent_messages
    )

    # Decode base64 back to bytes
    decoded_bytes = base64.b64decode(merged_encoded)

    # 🔥 Final assertion: bit-for-bit equality
    assert decoded_bytes == original_bytes


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
