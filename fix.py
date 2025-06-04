# ───────── 3.  BUILD AGENT EXECUTOR  ─────────
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_community.tools.jira      import JiraAction
from langchain_openai                    import ChatOpenAI
from langchain.agents                    import (
    create_openai_functions_agent,
    AgentExecutor,
    Tool,
)
from langchain.prompts import ChatPromptTemplate

def build_executor() -> AgentExecutor:
    # 1️⃣  Low‑level wrapper (holds URL, creds, cloud/server flag)
    jira_wrapper = JiraAPIWrapper(
        jira_instance_url = JIRA_INSTANCE_URL,
        jira_username     = JIRA_USERNAME,
        jira_api_token    = JIRA_API_TOKEN,
    )  # keep creds out of source control once you leave the demo stage!

    # 2️⃣  Expose ONE Jira REST call as a LangChain Tool
    jira_search = JiraAction(
        api_wrapper = jira_wrapper,
        action      = "search_issues",   # <-- /rest/api/3/search
        mode        = "cloud",           # REQUIRED in 0.3.x
        name        = "jira_search",     # optional but nice
        description = (
            "Search Jira with a JQL string and return key, summary, and status."
        ),
    )
    tool = Tool.from_function(jira_search)

    # 3️⃣  Prompt & LLM
    SYSTEM = (
        "You are a Jira assistant. Translate the user's request into ONE valid "
        "JQL string that will be sent to the Jira search API. "
        "Return only the JQL in your function call."
    )
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM),
                                               ("human", "{input}")])

    llm   = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_openai_functions_agent(llm, [tool], prompt)

    return AgentExecutor(agent=agent, tools=[tool], verbose=True)