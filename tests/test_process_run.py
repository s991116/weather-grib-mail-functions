#FILE test_process_run.py
import pytest
from src.InReachRequest import InReachRequest
from src.process import run

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


@pytest.mark.asyncio
async def test_run_triggers_chatgpt_and_sends_response_to_inreach(monkeypatch):
    """
    End-to-end test for Chat GPT InReach request.

    Flow:
    - InReach mail received (mocked)
    - OpenAI called (mocked)
    - Response sent back to Garmin InReach (spy)
    """

    # -------------------------------------------------
    # State / spies
    # -------------------------------------------------
    openai_called = False
    sent_messages: list[str] = []

    # -------------------------------------------------
    # Fake InReach request (chat)
    # -------------------------------------------------
    async def fake_retrieve_new_inreach_request(mail):
        return InReachRequest(
            type="chat",
            payload_text="What is the weather like tomorrow?",
            reply_url="https://garmin.com/sendmessage?extId=CHAT-GUID"
        )

    monkeypatch.setattr(
        "src.process.retrieve_new_inreach_request",
        fake_retrieve_new_inreach_request,
    )

    # -------------------------------------------------
    # Mock OpenAI call
    # -------------------------------------------------
    async def fake_request_openai_response(prompt: str) -> str:
        nonlocal openai_called
        openai_called = True

        assert prompt == "What is the weather like tomorrow?"

        return "Tomorrow will be sunny with light winds."

    monkeypatch.setattr(
        "src.process.openai_func.request_openai_response",
        fake_request_openai_response,
    )

    # -------------------------------------------------
    # Spy InReach sender (POST)
    # -------------------------------------------------
    class FakeSender:
        async def send(self, url: str, message: str):
            sent_messages.append(message)

            class Response:
                status_code = 200
                text = "OK"

            return Response()

    # -------------------------------------------------
    # Run
    # -------------------------------------------------
    result = await run(
        mail=None,
        inreach_sender=FakeSender(),
    )

    # -------------------------------------------------
    # Assertions
    # -------------------------------------------------
    assert result is True
    assert openai_called is True
    assert len(sent_messages) == 1
    assert "Tomorrow will be sunny" in sent_messages[0]
