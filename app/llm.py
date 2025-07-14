from langchain_core.language_models import LLM
from typing import Optional, List
import requests
from dotenv import load_dotenv
import os
load_dotenv()

# Now your API key is available
api_key = os.environ.get("GEMINI_API_KEY")

class GeminiLLM(LLM):
    model_name: str = "gemini-2.0-flash"
    api_key: str = os.getenv("GEMINI_API_KEY")  # or set manually

    @property
    def _llm_type(self) -> str:
        return "gemini-custom-rest"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 256
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")
