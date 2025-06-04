# ───────── 3.  BUILD AGENT EXECUTOR  ─────────
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_community.tools.jira import JiraAction      # same import path

def build_executor() -> AgentExecutor:
    # 1️⃣  Create the low‑level API wrapper once
    jira_wrapper = JiraAPIWrapper(
        jira_instance_url = JIRA_INSTANCE_URL,
        jira_username     = JIRA_USERNAME,
        jira_api_token    = JIRA_API_TOKEN,
        mode              = "cloud",          # ← **this is the “mode” Pydantic wants**
    )

    # 2️⃣  Wrap the *single* operation we care about as a Tool
    jira_search = JiraAction(
        api_wrapper = jira_wrapper,
        action      = "search_issues",
        name        = "search_issues",        # optional but nice for function‑calling
        description = "Search Jira issues with a JQL string "
                      "and return key, summary, status.",
    )

    tool = Tool.from_function(jira_search)

    # (unchanged prompt + LLM setup)
    SYSTEM = (
        "You are a Jira assistant. "
        "Translate the user's request into ONE valid JQL string that will be "
        "sent to the Jira search API. Return only the JQL in your function call."
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM), ("human", "{input}")]
    )

    llm   = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_openai_functions_agent(llm, [tool], prompt)

    return AgentExecutor(agent=agent, tools=[tool], verbose=True)