"""
jira_llm_search_sdk.py
Natural‑language ➜ Azure GPT‑4o ➜ JQL ➜ Jira (direct SDK) search
Prints at most TWO matching tickets.
"""

# ─── 1. HARD‑CODED CREDENTIALS (local dev only!) ──────────────────────
JIRA_INSTANCE_URL = "https://ontrack-internal.amd.com"
JIRA_API_TOKEN    = "MjQ0MzM3NDQzNTY0OsLr4yZLHgekftk2OkuNGC+Ngumk"   # PAT

AZURE_OPENAI_ENDPOINT         = "https://llm-api.amd.com"
AZURE_OPENAI_DEPLOYMENT       = "o3-mini"                 # deployment name
AZURE_OPENAI_API_VERSION      = "2024-05-01-preview"
AZURE_OPENAI_KEY              = "37f0bc138e7944eab89e3421d445675f"
AZURE_OPENAI_SUBSCRIPTION_KEY = "37f0bc138e7944eab89e3421d445675f"

# ─── 2. DEPENDENCIES ──────────────────────────────────────────────────
import os
from atlassian import Jira                                      # direct SDK
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_functions_agent, AgentExecutor, Tool

# Make sure fallback OpenAI client sees the key
os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_KEY

# ─── 3. AZURE LLM SETUP ───────────────────────────────────────────────
llm = AzureChatOpenAI(
    azure_deployment     = AZURE_OPENAI_DEPLOYMENT,
    azure_endpoint       = AZURE_OPENAI_ENDPOINT,
    openai_api_version   = AZURE_OPENAI_API_VERSION,
    default_headers      = {
        "Ocp-Apim-Subscription-Key": AZURE_OPENAI_SUBSCRIPTION_KEY
    },
    max_tokens           = 512,
    temperature          = 0,
)

# ─── 4. DIRECT JIRA CLIENT  ───────────────────────────────────────────
jira_client = Jira(
    url   = JIRA_INSTANCE_URL,
    token = JIRA_API_TOKEN,          # PAT ‑ works as Bearer on DC
    cloud = False                    # Data‑Center / Server mode
    # username not required when using PAT
)

def search_jira(jql: str, max_results: int = 50):
    """Return Jira issues for a given JQL string (dicts, not Jira Issue objects)."""
    result = jira_client.jql(jql, limit=max_results)
    return result["issues"]

# Wrap helper as a LangChain tool
jira_tool = Tool.from_function(
    name        = "jira_search",
    description = "Search Jira issues with JQL and return raw issue dicts.",
    func        = search_jira,
)

# ─── 5. BUILD AGENT EXECUTOR  ─────────────────────────────────────────
def build_executor() -> AgentExecutor:
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

    agent = create_openai_functions_agent(llm, [jira_tool], prompt)
    return AgentExecutor(agent=agent, tools=[jira_tool], verbose=True)

# ─── 6. CLI LOOP (prints max 2 issues) ────────────────────────────────
def main() -> None:
    executor = build_executor()
    print("🤖  Ask me about Jira tickets (type 'quit' to exit)\n")
    try:
        while True:
            q = input("➜ ")
            if q.lower() in {"quit", "exit"}:
                break
            res = executor.invoke({"input": q})
            issues = res["output"][:2]           # cap list to 2 tickets
            if not issues:
                print("No matches.\n")
                continue
            print("\n--- Matching tickets ---")
            for i in issues:
                fields = i["fields"]
                print(f"{i['key']:<10} {fields['summary']} "
                      f"[{fields['status']['name']}]")
            print()
    except KeyboardInterrupt:
        print("\nBye! 👋")

if __name__ == "__main__":
    main()
