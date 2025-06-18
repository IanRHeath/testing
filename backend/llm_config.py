import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
import openai

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_VERSION = os.getenv("LLM_API_VERSION")
LLM_RESOURCE_ENDPOINT = os.getenv("LLM_RESOURCE_ENDPOINT")
LLM_CHAT_DEPLOYMENT_NAME = os.getenv("LLM_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_DEFAULT_HEADERS = {'Ocp-Apim-Subscription-Key': LLM_API_KEY}

def get_llm() -> BaseChatModel:
    """Configures and returns the AzureChatOpenAI instance for LangChain agents."""
    if not all([LLM_API_KEY, LLM_API_VERSION, LLM_RESOURCE_ENDPOINT, LLM_CHAT_DEPLOYMENT_NAME]):
        raise ValueError("Azure LLM environment variables are not fully set. Please check .env file.")
    try:
        llm = AzureChatOpenAI(
            api_key=LLM_API_KEY,
            api_version=LLM_API_VERSION,
            azure_endpoint=LLM_RESOURCE_ENDPOINT,
            azure_deployment=LLM_CHAT_DEPLOYMENT_NAME,
            default_headers=AZURE_OPENAI_DEFAULT_HEADERS
        )
        print(f"LangChain Azure LLM configured: Model={LLM_CHAT_DEPLOYMENT_NAME}, Endpoint={LLM_RESOURCE_ENDPOINT}")
        return llm
    except Exception as e:
        raise Exception(f"Failed to configure LangChain Azure LLM: {e}")

def get_azure_openai_client() -> openai.AzureOpenAI:
    """Configures and returns a raw openai.AzureOpenAI client for parameter extraction."""
    if not all([LLM_API_KEY, LLM_API_VERSION, LLM_RESOURCE_ENDPOINT, LLM_CHAT_DEPLOYMENT_NAME]):
        raise ValueError("Azure LLM environment variables are not fully set for raw client. Please check .env file.")
    try:
        client = openai.AzureOpenAI(
            api_key=LLM_API_KEY,
            api_version=LLM_API_VERSION,
            base_url=f"{LLM_RESOURCE_ENDPOINT}/openai/deployments/{LLM_CHAT_DEPLOYMENT_NAME}",
            default_headers=AZURE_OPENAI_DEFAULT_HEADERS
        )
        print("Raw Azure OpenAI client configured.")
        return client
    except Exception as e:
        raise Exception(f"Failed to configure raw Azure OpenAI client: {e}")
