# llm_config.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME")

def get_llm() -> BaseChatModel:
    """Configures and returns the ChatOpenAI instance for your AMD LLM."""
    if not all([LLM_API_BASE, LLM_API_KEY, LLM_MODEL_NAME]):
        raise ValueError("LLM environment variables are not set. Please check .env file.")
    try:
        llm = ChatOpenAI(
            openai_api_base=LLM_API_BASE,
            openai_api_key=LLM_API_KEY,
            model_name=LLM_MODEL_NAME,
            temperature=0.0 # Set low temperature for factual JQL generation
        )
        print(f"LLM configured: Model={LLM_MODEL_NAME}, Base={LLM_API_BASE}")
        return llm
    except Exception as e:
        raise Exception(f"Failed to configure LLM: {e}")
