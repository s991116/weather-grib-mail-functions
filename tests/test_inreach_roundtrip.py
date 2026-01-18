import asyncio
import base64
import pytest

from io import BytesIO
from pathlib import Path

from src.saildoc_functions import encode_saildocs_grib_file
from src.inreach_functions import send_messages_to_inreach


# --------------------------------------------------
# Shared fake sender (Dependency Injection)
# --------------------------------------------------
class FakeResponse:
    status_code = 200
    text = "OK"


class FakeInReachSender:
    def __init__(self):
        self.sent_messages: list[str] = []

    async def send(self, url: str, message: str):
        self.sent_messages.append(message)
        return FakeResponse()


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

    # encode + split
    message_parts = encode_saildocs_grib_file(fake_grib)

    fake_sender = FakeInReachSender()

    # speed up test
    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    url = "https://garmin.com/sendmessage?extId=TEST-GUID"

    # =====================================================
    # Act
    # =====================================================
    await send_messages_to_inreach(
        url,
        message_parts,
        fake_sender,
    )

    sent_messages = fake_sender.sent_messages
    assert sent_messages, "No InReach messages were sent"

    # =====================================================
    # Assert – merge & decode
    # =====================================================
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

    # =====================================================
    # Arrange
    # =====================================================
    original_bytes = b"GRIB-DATA-" * 500
    fake_grib = BytesIO(original_bytes)

    message_parts = encode_saildocs_grib_file(fake_grib)

    fake_sender = FakeInReachSender()

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    url="https://garmin.com/sendmessage?extId=TEST-GUID"
    # =====================================================
    # Act
    # =====================================================
    await send_messages_to_inreach(
        url,
        message_parts,
        fake_sender,
    )

    sent_messages = fake_sender.sent_messages
    assert len(sent_messages) > 1

    # =====================================================
    # Assert – merge & decode
    # =====================================================
    merged_encoded = "".join(
        msg.split(":\n", 1)[1].rsplit("\nend", 1)[0]
        for msg in sent_messages
    )

    decoded = base64.b64decode(merged_encoded)

    assert decoded == original_bytes
