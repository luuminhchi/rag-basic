import os
from pathlib import Path
from dotenv import load_dotenv
from src.config import settings

env_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(env_path)


class LLMClient:
    """
    Wrapper thống nhất cho các LLM provider: Gemini, OpenAI, Hugging Face.
    Chỉ cần thay đổi llm_provider và llm_model trong src/config.py là đổi được provider,
    không cần sửa bất kỳ chỗ nào khác trong code.
    """

    def __init__(self):
        self.provider   = settings.llm_provider
        self.model_name = settings.llm_model
        self._client    = self._init_client()

    def _init_client(self):
        if self.provider == "gemini":
            from google import genai
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise EnvironmentError("Thiếu GOOGLE_API_KEY trong file .env")
            return genai.Client(api_key=api_key)

        else:
            # Hugging Face InferenceClient
            from huggingface_hub import InferenceClient
            api_key = os.getenv('HUGGINGFACEHUB_API_TOKEN')
            if not api_key:
                raise EnvironmentError("Thiếu HUGGINGFACEHUB_API_TOKEN trong file .env")
            return InferenceClient(model=self.model_name, token=api_key)

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.1) -> str:
        """
        Gọi LLM và trả về chuỗi kết quả (str).
        Giao diện thống nhất cho mọi provider — bên ngoài chỉ cần gọi hàm này.
        """
        if self.provider == "gemini":
            return self._call_gemini(prompt, max_tokens, temperature)
        else:
            return self._call_huggingface(prompt, max_tokens, temperature)

    # ── Các hàm gọi riêng từng provider ─────────────────────────────────────

    def _call_gemini(self, prompt: str, max_tokens: int, temperature: float) -> str:
        from google.genai import types
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        return response.text.strip()


    def _call_huggingface(self, prompt: str, max_tokens: int, temperature: float) -> str:
        response = self._client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()


# Singleton — khởi tạo 1 lần duy nhất khi import, tái sử dụng cho mọi request
llm = LLMClient()
