"""
jira_llm_search.py
Minimal PoC: ask a natural‑language question → GPT‑4o turns it into JQL →
Jira REST search results are printed.

⚠️  DO NOT COMMIT REAL KEYS.  Hard‑coding secrets is only for a local demo.
"""

# ──────────────────────── 1. CREDENTIALS ──────────────────────────────
JIRA_INSTANCE_URL = "https://your-org.atlassian.net"   # e.g. Cloud base URL
JIRA_USERNAME     = "you@example.com"                  # Atlassian login or bot
JIRA_API_TOKEN    = "atlassian_api_token_here"         # Generate under: Profile ▸ Security ▸ API tokens

OPENAI_API_KEY    = "sk-your-openai-key"               # or Azure OpenAI key
# ───────────────────────────────────────────────────────────────────────

# Inject creds into env vars so the helper libs pick them up automatically
import os, warnings, sys
for k, v in {
    "JIRA_INSTANCE_URL": JIRA_INSTANCE_URL,
    "JIRA_USERNAME"    : JIRA_USERNAME,
    "JIRA_API_TOKEN"   : JIRA_API_TOKEN,
    "OPENAI_API_KEY"   : OPENAI_API_KEY,
}.items():
    if not v or "here" in v:
        warnings.warn(f"‼️  {k} is still a placeholder – fill it in before running.")
    os.environ[k] = v

# ───────────────────── 2. DEPENDENCIES  ───────────────────────────────
# pip install langchain langchain-community atlassian-python-api openai
from langchain_openai import ChatOpenAI
from langchain.agents   import create_openai_functions_agent, AgentExecutor, Tool
from langchain_community.tools.jira import JiraAction
from langchain.prompts import ChatPromptTemplate

# ───────────────────── 3. BUILD THE EXECUTOR  ─────────────────────────
def build_executor() -> AgentExecutor:
    # Wrap Jira’s /search endpoint
    jira_search = JiraAction(
        action="search_issues",
        description="Search Jira issues with JQL and return key, summary, status.",
    )
    tool = Tool.from_function(jira_search)

    SYSTEM = (
        "You are a Jira assistant. "
        "Translate the user's request into ONE valid JQL string that will be "
        "sent to the Jira search API. **Return only the JQL in your function call.**"
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM), ("human", "{input}")]
    )

    llm   = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_openai_functions_agent(llm, [tool], prompt)

    # verbose=True prints the chain‑of‑thought and REST URLs—handy for debugging
    return AgentExecutor(agent=agent, tools=[tool], verbose=True)

# ───────────────────── 4. CLI LOOP  ────────────────────────────────────
def main() -> None:
    executor = build_executor()
    print("🤖  Ask me about Jira tickets (type 'quit' to exit)\n")
    try:
        while True:
            query = input("➜ ")
            if query.lower() in {"exit", "quit"}:
                break

            result  = executor.invoke({"input": query})
            issues  = result["output"]

            if not issues:
                print("No matches.\n")
                continue

            print("\n--- Matching tickets ---")
            for issue in issues:
                print(f"{issue.key:<10} {issue.fields.summary} "
                      f"[{issue.fields.status.name}]")
            print()
    except KeyboardInterrupt:
        print("\nBye! 👋")

if __name__ == "__main__":
    main()
