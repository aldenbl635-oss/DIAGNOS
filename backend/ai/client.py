import json
import requests
from config import settings

class AIClient:
    def __init__(self):
        self.use_gemini = False
        self.use_openai = False
        self._gemini_client = None
        
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.use_gemini = True
                print("AIClient: Configured Gemini API client (google-genai SDK).")
            except Exception as e:
                print(f"AIClient: Failed to configure Gemini ({e}).")
        elif settings.OPENAI_API_KEY:
            self.use_openai = True
            print("AIClient: Configured OpenAI API client via REST.")
        else:
            print("AIClient: No LLM keys found. Operating in OFFLINE DEMO MODE.")

    def generate_text(self, system_prompt: str, prompt: str, json_mode: bool = False) -> str:
        """Generate text via configured LLM. Raises ConnectionError if no API configured."""
        if settings.DEMO_MODE or (not self.use_gemini and not self.use_openai):
            raise ConnectionError("LLM offline or Demo Mode active")

        try:
            if self.use_gemini:
                from google import genai
                from google.genai import types
                
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                
                config_params = {}
                if json_mode:
                    config_params["response_mime_type"] = "application/json"
                
                response = self._gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=full_prompt,
                    config=types.GenerateContentConfig(**config_params) if config_params else None
                )
                return response.text
                
            elif self.use_openai:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                }
                
                url = settings.OPENAI_API_BASE if settings.OPENAI_API_BASE else "https://api.openai.com/v1"
                url = f"{url.rstrip('/')}/chat/completions"
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}
                    
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"]
                
        except Exception as e:
            print(f"AIClient Error: {e}. Falling back to offline engine.")
            raise e

ai_client = AIClient()
