import asyncio
import base64
import pytest

from io import BytesIO
from pathlib import Path

from src.saildoc_functions import encode_saildocs_grib_file
from src.inreach_functions import send_messages_to_inreach
from src.saildoc_functions import encode_saildocs_grib_file, decode_saildocs_grib_file
from src.saildoc_functions import unwrap_messages_to_payload_chunks


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
async def test_encode_decode_roundtrip_with_function():
    """
    Test that encoding and then decoding a GRIB file reconstructs the original bytes,
    using decode_saildocs_grib_file function and BytesIO.
    """
    original_bytes = b"TEST-GRIB-DATA-" * 100
    fake_grib = BytesIO(original_bytes)

    # encode + split
    message_parts = encode_saildocs_grib_file(fake_grib)
    assert message_parts, "Encoding returned empty message parts"

    # decode into BytesIO using the real function
    decoded_buffer = BytesIO()

    combined_message_parts = "\n".join(message_parts)
    payload_parts = unwrap_messages_to_payload_chunks(combined_message_parts)
    decoded_bytes = decode_saildocs_grib_file(payload_parts)

    # read decoded bytes
    assert decoded_bytes == original_bytes, "Decoded bytes do not match original"


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
