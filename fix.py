"""
jira_llm_search_retry.py
Natural‑language ➜ Azure GPT‑4o ➜ JQL ➜ Jira search
"""

# ─── 1. HARD‑CODED CREDENTIALS (local dev only!) ───────────────────────
JIRA_INSTANCE_URL = "https://ontrack-internal.amd.com"
JIRA_USERNAME     = "iheath12"
JIRA_API_TOKEN    = "MTk3NzYzMTQxNzg4Olqxo3LJfC2bcC8R6XVE1XzbF+bo"

AZURE_OPENAI_ENDPOINT         = "https://llm-api.amd.com"
AZURE_OPENAI_DEPLOYMENT       = "o3-mini"                 # <- exact name in portal
AZURE_OPENAI_API_VERSION      = "2024-05-01-preview"
AZURE_OPENAI_KEY              = "37f0bc138e7944eab89e3421d445675f"
AZURE_OPENAI_SUBSCRIPTION_KEY = "37f0bc138e7944eab89e3421d445675f"

# ─── 2. DEPENDENCIES ──────────────────────────────────────────────────
import os, openai
from tenacity import retry, wait_exponential, stop_after_attempt          # pip install tenacity
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_community.tools.jira.tool import JiraAction
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_functions_agent, AgentExecutor

#  Ensure fallback client always has a key
os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_KEY

# ─── 3. LLM (built internally by LangChain) ───────────────────────────
llm = AzureChatOpenAI(
    azure_deployment     = AZURE_OPENAI_DEPLOYMENT,
    azure_endpoint       = AZURE_OPENAI_ENDPOINT,
    openai_api_version   = AZURE_OPENAI_API_VERSION,
    default_headers      = {
        "Ocp-Apim-Subscription-Key": AZURE_OPENAI_SUBSCRIPTION_KEY
    },
    max_tokens           = 512,       # stay well under limit during triage
    temperature          = 0,
)

# ─── 4. BUILD AGENT EXECUTOR ──────────────────────────────────────────
def build_executor() -> AgentExecutor:
    jira_wrapper = JiraAPIWrapper(
        jira_instance_url = JIRA_INSTANCE_URL,
        jira_username     = JIRA_USERNAME,
        jira_api_token    = JIRA_API_TOKEN,
    )

    jira_search = JiraAction(
        api_wrapper = jira_wrapper,
        action      = "search_issues",
        mode        = "cloud",
        name        = "jira_search",
        description = "Search Jira with a JQL string and return key, summary, status.",
    )
    tools = [jira_search]

    SYSTEM = (
        "You are a Jira assistant. Translate the user's request into ONE valid "
        "JQL string that will be sent to the Jira search API. "
        "Return only the JQL in your function call."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# ─── 5. RETRY WRAPPER FOR LLM CALLS ────────────────────────────────────
@retry(                                     # 2 s → 4 s → 8 s → 16 s
    wait=wait_exponential(multiplier=1, min=2, max=16),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda rs: (_ for _ in ()).throw(rs.outcome.exception()),
)
def invoke_with_retry(executor, user_prompt: str):
    """Run the agent with back‑off on transient 5xx Azure errors."""
    return executor.invoke({"input": user_prompt})

# ─── 6. CLI LOOP ───────────────────────────────────────────────────────
def main() -> None:
    executor = build_executor()
    print("🤖  Ask me about Jira tickets (type 'quit' to exit)\n")
    try:
        while True:
            q = input("➜ ")
            if q.lower() in {"quit", "exit"}:
                break
            res = invoke_with_retry(executor, q)     # <‑ use retry wrapper
            issues = res["output"]
            if not issues:
                print("No matches.\n")
                continue
            print("\n--- Matching tickets ---")
            for i in issues:
                print(f"{i.key:<10} {i.fields.summary} [{i.fields.status.name}]")
            print()
    except KeyboardInterrupt:
        print("\nBye! 👋")

if __name__ == "__main__":
    main()


# ─── 7. (Optional) CURL PROBE  ─────────────────────────────────────────
"""
curl -X POST \
  "https://llm-api.amd.com/openai/deployments/o3-mini/chat/completions?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "api-key: 37f0bc138e7944eab89e3421d445675f" \
  -H "Ocp-Apim-Subscription-Key: 37f0bc138e7944eab89e3421d445675f" \
  -d '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":1}'
"""
