JIRA_INSTANCE_URL = "https://ontrack-internal.amd.com"
JIRA_USERNAME     = "iheath12"
JIRA_API_TOKEN    = "MTk3NzYzMTQxNzg4Olqxo3LJfC2bcC8R6XVE1XzbF+bo"

AZURE_OPENAI_ENDPOINT         = "https://llm-api.amd.com"
AZURE_OPENAI_API_VERSION      = "2024-05-01-preview"
AZURE_OPENAI_DEPLOYMENT       = "gpt‑4o‑mini‑dev"
AZURE_OPENAI_KEY              = "37f0bc138e7944eab89e3421d445675f"
AZURE_OPENAI_SUBSCRIPTION_KEY = "37f0bc138e7944eab89e3421d445675f"

from openai import AzureOpenAI
from langchain_openai import ChatOpenAI
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_community.tools.jira.tool import JiraAction
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_openai_functions_agent, AgentExecutor

aoai_client = AzureOpenAI(
    api_key        = AZURE_OPENAI_KEY,
    api_version    = AZURE_OPENAI_API_VERSION,
    azure_endpoint = AZURE_OPENAI_ENDPOINT,
    default_headers={
        "Ocp-Apim-Subscription-Key": AZURE_OPENAI_SUBSCRIPTION_KEY,
    },
)

llm = ChatOpenAI(
    client  = aoai_client,              
    model   = AZURE_OPENAI_DEPLOYMENT,  
    temperature = 0,
)

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

def main() -> None:
    executor = build_executor()
    print("Ask me about Jira tickets (type 'quit' to exit)\n")
    try:
        while True:
            q = input("➜ ")
            if q.lower() in {"quit", "exit"}:
                break
            res = executor.invoke({"input": q})
            issues = res["output"]
            if not issues:
                print("No matches.\n")
                continue
            print("\n--- Matching tickets ---")
            for i in issues:
                print(f"{i.key:<10} {i.fields.summary} [{i.fields.status.name}]")
            print()
    except KeyboardInterrupt:
        print("\nBye!")

if __name__ == "__main__":
    main()
