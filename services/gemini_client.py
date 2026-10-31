import os
from dotenv import load_dotenv
from google import genai

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
        raise RuntimeError("GEMINI_TEXT_M0DEL not found!")
    response = client.models.generate_content(
        model=text_model,
        contents="Ответь одним словом: работает?",
    )
    print(response.text)
    print("---")
    for m in client.models.list():
        print(m.name)
