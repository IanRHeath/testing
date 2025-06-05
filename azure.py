# ─── 4. BUILD AGENT EXECUTOR  (patched for Jira Data‑Center PAT) ───────
def build_executor() -> AgentExecutor:
    # 1)  Jira wrapper for Data‑Center / Server
    jira_wrapper = JiraAPIWrapper(
        jira_instance_url = JIRA_INSTANCE_URL,      # https://ontrack‑internal.amd.com
        jira_api_token    = JIRA_API_TOKEN,         # PAT that worked in curl
        # NOTE: omit jira_username – PAT auth uses the token alone
    )

    # 2)  Expose search_issues as a LangChain tool
    jira_search = JiraAction(
        api_wrapper = jira_wrapper,
        action      = "search_issues",
        mode        = "server",                     # ← SWITCHED from "cloud"
        name        = "jira_search",
        description = (
            "Search Jira with a JQL string and return key, summary, and status."
        ),
    )
    tools = [jira_search]

    # 3)  Prompt with scratchpad placeholder
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
