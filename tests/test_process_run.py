import pytest
from io import BytesIO

from src.process import run


@pytest.mark.asyncio
async def test_run_with_inreach_and_saildocs(monkeypatch):
    """
    End-to-end test of run() with:
    - a fake InReach request
    - a fake Saildocs response
    """

    sent_messages = []

    # --- Fake process_new_inreach_message ---
    async def fake_inreach_request(mail):
        return "TEST-COMMAND", "https://garmin.com/sendmessage?extId=TEST-GUID"

    monkeypatch.setattr(
        "src.process.process_new_inreach_message",
        fake_inreach_request
    )

    # --- Fake Saildocs response ---
    async def fake_process_new_saildocs_response(mail, command, url):
        fake_grib = BytesIO(b"TEST-GRIB-DATA")
        return fake_grib, url

    monkeypatch.setattr(
        "src.process.process_new_saildocs_response",
        fake_process_new_saildocs_response
    )

    # --- Fake encoding + split ---
    from src import saildoc_functions as saildoc_func

    def fake_encode_split(file):
        return [
            f"msg {i}/3:\nTEST-GRIB-DATA\nend"
            for i in range(1, 4)
        ]

    monkeypatch.setattr(
        saildoc_func,
        "encode_saildocs_grib_file",
        fake_encode_split
    )

    # --- Fake InReachSender ---
    class FakeSender:
        async def send(self, url, message_str):
            sent_messages.append(message_str)

            class Response:
                status_code = 200
                text = "OK"

            return Response()

    # --- Mock asyncio.sleep ---
    async def fake_sleep(_):
        return None

    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    # --- Run processor ---
    result = await run(
        mail=None,
        inreach_sender=FakeSender()
    )

    # --- Assertions ---
    assert result is True
    assert len(sent_messages) == 3
    for chunk in sent_messages:
        assert "TEST-GRIB-DATA" in chunk
