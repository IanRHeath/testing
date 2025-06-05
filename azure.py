# 1) Minimal test call *outside* LangChain, directly with openai SDK
from openai import AzureOpenAI, APITimeoutError, APIError
client = AzureOpenAI(
    api_key      = AZURE_OPENAI_KEY,
    api_version  = AZURE_OPENAI_API_VERSION,
    azure_endpoint = AZURE_OPENAI_ENDPOINT,
    default_headers={"Ocp-Apim-Subscription-Key": AZURE_OPENAI_SUBSCRIPTION_KEY},
)

try:
    r = client.chat.completions.create(
        model = AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role":"user","content":"ping"}],
        max_tokens=1,
    )
    print("✅ minimal call succeeded:", r.choices[0].message.content)
except APIError as e:
    print("❌ still 500, Azure side problem:", e.status_code, e)
except APITimeoutError:
    print("❌ timeout (capacity issue)")
