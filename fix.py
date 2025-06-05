from langchain_openai import ChatOpenAI
from langchain.agents   import create_openai_functions_agent, AgentExecutor, Tool
from langchain_community.tools.jira.tool import JiraAction
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_openai                    import ChatOpenAI
from langchain.agents                    import (
    create_openai_functions_agent,
    AgentExecutor,
    Tool,
)
from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
import os, warnings, sys
from openai import AzureOpenAI

JIRA_INSTANCE_URL = "https://ontrack-internal.amd.com"   
JIRA_USERNAME     = "iheath12"                  
JIRA_API_TOKEN    = "MTk3NzYzMTQxNzg4Olqxo3LJfC2bcC8R6XVE1XzbF+bo"        
OPENAI_API_KEY    = "37f0bc138e7944eab89e3421d445675f"             

AZURE_OPENAI_ENDPOINT      = "https://llm-api.amd.com"
AZURE_OPENAI_KEY           = "37f0bc138e7944eab89e3421d445675f"
AZURE_OPENAI_DEPLOYMENT    = "gpt‑4o‑mini‑dev"         
AZURE_OPENAI_API_VERSION   = "2024‑05‑01‑preview"     
AZURE_OPENAI_SUBSCRIPTION_KEY = "37f0bc138e7944eab89e3421d445675f" 

url = 'https://llm-api.amd.com'
chat_dep = 'o3-mini'

client = AzureChatOpenAI(
    api_key="37f0bc138e7944eab89e3421d445675f",
    api_version='2024-06-01',
    base_url=f"{url}/openai/deployments/{chat_dep}",
    default_headers={'Ocp-Apim-Subscription-Key': "37f0bc138e7944eab89e3421d445675f"}
)

os.environ.update({
    "AZURE_OPENAI_ENDPOINT"   : AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_API_KEY"    : AZURE_OPENAI_KEY,
    "OPENAI_API_VERSION"      : AZURE_OPENAI_API_VERSION,   
    "OPENAI_API_TYPE"         : "azure",                  
})

for k, v in {
    "JIRA_INSTANCE_URL": JIRA_INSTANCE_URL,
    "JIRA_USERNAME"    : JIRA_USERNAME,
    "JIRA_API_TOKEN"   : JIRA_API_TOKEN,
    "OPENAI_API_KEY"   : OPENAI_API_KEY,
}.items():
    if not v or "here" in v:
        warnings.warn(f"‼ {k} is still a placeholder fill it in before running.")
    os.environ[k] = v

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
        description = (
            "Search Jira with a JQL string and return key, summary, and status."
        ),
    )
    tools = [jira_search]

    SYSTEM = (
        "You are a Jira assistant. Translate the user's request into ONE valid "
        "JQL string that will be sent to the Jira search API. "
        "Return only the JQL in your function call."
    )
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM),
                                               ("human", "{input}"),
                                               MessagesPlaceholder(variable_name="agent_scratchpad")])

    llm = ChatOpenAI(
        client = client,
        azure_deployment = AZURE_OPENAI_DEPLOYMENT,    
        openai_api_version = AZURE_OPENAI_API_VERSION, 
        temperature = 0,
)
    agent = create_openai_functions_agent(llm, tools, prompt)

    return AgentExecutor(agent=agent, tools=tools, verbose=True)
def main() -> None:
    executor = build_executor()
    print("  Ask me about Jira tickets (type 'quit' to exit)\n")
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
        print("\nBye!")

if __name__ == "__main__":
    main()
