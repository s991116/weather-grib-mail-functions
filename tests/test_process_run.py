import pytest
from io import BytesIO
from src.InReachRequest import InReachRequest
from src.process import run


import pytest
from src.process import run
from src.inreach_sender import InReachSender


@pytest.mark.asyncio
async def test_run_triggers_weather_request_for_weather_inreach_message(monkeypatch):
    """
    run() should trigger request_weather_report when receiving
    a weather InReach request (SEND format).
    """

    weather_called = False

    # -------------------------------------------------
    # Fake InReach request (weather)
    # -------------------------------------------------
    async def fake_retrieve_new_inreach_request(mail):
        return InReachRequest(
            "weather",
            "TEST-COMMAND",
            "https://garmin.com/sendmessage?extId=TEST-GUID"
        )

    monkeypatch.setattr(
        "src.process.retrieve_new_inreach_request",
        fake_retrieve_new_inreach_request,
    )

    # -------------------------------------------------
    # Spy: request_weather_report
    # -------------------------------------------------
    async def fake_request_weather_report(mail, payload_text):
        nonlocal weather_called
        weather_called = True

        # Assert only what matters
        assert payload_text == "TEST-COMMAND"

    monkeypatch.setattr(
        "src.process.request_weather_report",
        fake_request_weather_report,
    )

    # -------------------------------------------------
    # Short-circuit downstream processing
    # -------------------------------------------------
    async def fake_process_new_saildocs_response(mail, payload_text):
        return None  # stop pipeline early

    monkeypatch.setattr(
        "src.process.process_new_saildocs_response",
        fake_process_new_saildocs_response,
    )

    # -------------------------------------------------
    # Run
    # -------------------------------------------------
    result = await run(mail=None, inreach_sender=None)

    # -------------------------------------------------
    # Assertions
    # -------------------------------------------------
    assert result is True
    assert weather_called is True
