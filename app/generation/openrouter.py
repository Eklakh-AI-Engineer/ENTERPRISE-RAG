import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class OpenRouterClient:

    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL")

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is missing")

        if not model:
            raise ValueError("OPENROUTER_MODEL is missing")

        self.model = model

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def generate(self, prompt: str) -> str:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.choices[0].message.content