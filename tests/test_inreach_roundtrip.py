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
    Saildocs attachment → encode+split → send → merge → decode
    """

    # =====================================================
    # Arrange
    # =====================================================

    fixture_path = Path(__file__).parent / "fixtures" / "ecmwf20260113071001417.grb"
    original_bytes = fixture_path.read_bytes()

    fake_grib = BytesIO(original_bytes)

    # encode + split (NEW responsibility)
    message_parts = encode_saildocs_grib_file(fake_grib)

    sent_messages = []

    # -----------------------------------------
    # Mock asyncio.sleep
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
        sent_messages.append(data["ReplyMessage"])
        return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    # =====================================================
    # Act
    # =====================================================
    await send_messages_to_inreach(
        url="https://garmin.com/sendmessage?extId=TEST-GUID",
        message_parts=message_parts,
    )

    # =====================================================
    # Assert – merge & decode
    # =====================================================

    assert sent_messages, "No InReach messages were sent"

    # Sort by msg X/Y index
    sent_messages.sort(
        key=lambda m: int(m.split()[1].split("/")[0])
    )

    merged_encoded = "".join(
        msg.split(":\n", 1)[1].rsplit("\nend", 1)[0]
        for msg in sent_messages
    )

    decoded_bytes = base64.b64decode(merged_encoded)

    assert decoded_bytes == original_bytes


@pytest.mark.asyncio
async def test_grib_encode_split_send_merge_decode(monkeypatch):
    """
    Deterministic payload test without filesystem dependency
    """

    # ======================
    # Arrange
    # ======================

    original_bytes = b"GRIB-DATA-" * 500
    fake_grib = BytesIO(original_bytes)

    message_parts = encode_saildocs_grib_file(fake_grib)
    sent_messages = []

    # ----------------------
    # Mock asyncio.sleep
    # ----------------------
    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # ----------------------
    # Mock HTTP POST
    # ----------------------
    class FakeResponse:
        status_code = 200
        text = "OK"

    async def fake_post(self, url, cookies=None, headers=None, data=None):
        sent_messages.append(data["ReplyMessage"])
        return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    # ======================
    # Act
    # ======================
    await send_messages_to_inreach(
        url="https://garmin.com/sendmessage?extId=TEST-GUID",
        message_parts=message_parts,
    )

    # ======================
    # Assert
    # ======================
    assert len(sent_messages) > 1

    merged_encoded = "".join(
        msg.split(":\n", 1)[1].rsplit("\nend", 1)[0]
        for msg in sent_messages
    )

    decoded = base64.b64decode(merged_encoded)

    assert decoded == original_bytes
