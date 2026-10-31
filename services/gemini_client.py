import os
from dotenv import load_dotenv
from google import genai

from core.usage_tracker import log_call

load_dotenv()


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found!")
    return genai.Client(api_key=api_key)


if __name__ == "__main__":
    client = get_client()
    text_model = os.environ.get("GEMINI_TEXT_MODEL")
    if not text_model:
        raise RuntimeError("GEMINI_TEXT_MODEL not found!")
    response = client.models.generate_content(
        model=text_model,
        contents="Ответь одним словом: работает?",
    )
    print(response.text)
    log_call(text_model, tokens=response.usage_metadata.total_token_count)
