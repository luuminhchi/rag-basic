import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from src.config import settings

env_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(env_path)

def get_llm(temperature: float = 0.1, max_tokens: int = 1024):
    provider = settings.llm_provider
    model_name = settings.llm_model

    if provider == "gemini":
        api_key = settings.google_api_key
        if not api_key: raise EnvironmentError("Thiếu GOOGLE_API_KEY")
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,
            api_key=api_key
        )

    elif provider == "deepseek":
        api_key = settings.ds_api_key
        if not api_key: raise EnvironmentError("Thiếu DEEPSEEK_API_KEY")
        
        # DeepSeek dùng chung interface với OpenAI, chỉ cần trỏ URL về server DeepSeek
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url="https://api.deepseek.com/v1" 
        )

    elif provider == "huggingface":
        api_key = settings.hf_api_key
        if not api_key: raise EnvironmentError("Thiếu HUGGINGFACEHUB_API_TOKEN")
        
        # HuggingFace qua Langchain
        hf_endpoint = HuggingFaceEndpoint(
            repo_id=model_name,
            temperature=temperature,
            max_new_tokens=max_tokens,
            huggingfacehub_api_token=api_key
        )
        return ChatHuggingFace(llm=hf_endpoint)

    else:
        raise ValueError(f"Provider '{provider}' không được hỗ trợ!")

# Singleton — khởi tạo 1 lần duy nhất khi import
llm = get_llm()