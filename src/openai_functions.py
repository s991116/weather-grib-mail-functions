import sys
sys.path.append(".")
from src import configs
import logging
from openai import OpenAI

client = OpenAI(api_key=configs.OPEN_AI_KEY())

async def request_openai_response(request: str):

    try:
      max_words_str, prompt = request.split(":", 1)  # split at ":" to separate max_words and prompt
      max_words = int(max_words_str)
      logging.info("Max words in response: %s", max_words)
      logging.info("Prompt to ChatGPT: %s", prompt)
    except ValueError:
        print("Invalid message format. Please use 'gpt <max_words>: <prompt>'")
        return

    chatCompletion = client.chat.completions.create(
        model = "gpt-4-1106-preview",
        stop = None,
        n=1,
        messages = [
            {"role": "user", "content": f"Answer this question in maximum {max_words} words: \nUser: {prompt}."}
        ])
    response = chatCompletion.choices[0].message.content

    logging.info("Response from Chat-GPT: %s", response)

    return response