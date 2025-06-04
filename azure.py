# ───────── 1. CREDENTIALS (Azure) ─────────
AZURE_OPENAI_ENDPOINT      = "https://my‑resource.openai.azure.com"
AZURE_OPENAI_KEY           = "azure‑openai‑key"
AZURE_OPENAI_DEPLOYMENT    = "gpt‑4o‑mini‑dev"         # deployment name, not model
AZURE_OPENAI_API_VERSION   = "2024‑05‑01‑preview"      # or the version you set

import os, warnings
os.environ.update({
    "AZURE_OPENAI_ENDPOINT"   : AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_API_KEY"    : AZURE_OPENAI_KEY,
    "OPENAI_API_VERSION"      : AZURE_OPENAI_API_VERSION,   # what the SDK expects
    "OPENAI_API_TYPE"         : "azure",                    # tells openai‑python to use Azure logic
})
from langchain_openai import AzureChatOpenAI           # <-- use Azure variant
# ...

llm = AzureChatOpenAI(
        azure_deployment = AZURE_OPENAI_DEPLOYMENT,    # deployment name
        openai_api_version = AZURE_OPENAI_API_VERSION, # same string as above
        temperature = 0,
)
llm = AzureChatOpenAI(
        azure_deployment     = AZURE_OPENAI_DEPLOYMENT,
        openai_api_version   = AZURE_OPENAI_API_VERSION,
        temperature          = 0,
    )

    

