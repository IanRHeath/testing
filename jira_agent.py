import sys
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from llm_config import get_llm
from jira_tools import ALL_JIRA_TOOLS
from jira_utils import JiraBotError

def get_jira_agent() -> AgentExecutor:
    llm = get_llm()

    system_message = """
    You are a helpful JIRA assistant. Your job is to understand the user's request and use the provided tools to fulfill it.

    **Your Capabilities:**
    - You can search for JIRA tickets using natural language.
    - You can summarize a single JIRA ticket. If the user asks a specific question about a ticket (e.g., "what is the root cause of..."), pass that question to the tool. Otherwise, a default summary will be generated.
    - You can summarize a list of multiple JIRA tickets at once.

    **Behavioral Guidelines:**
    - Your primary goal is to select the correct tool for the job.
    - If the user provides a single issue key for summary, use the `summarize_ticket_tool`.
    - If the user provides more than one issue key for summary, use the `summarize_multiple_tickets_tool`.
    - For searching, pass the user's full natural language query to the `jira_search_tool`.
    - If a user's request is ambiguous, ask for clarification.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, ALL_JIRA_TOOLS, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=ALL_JIRA_TOOLS,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=15,
        return_intermediate_steps=True
    )
    print("LangChain Agent initialized successfully.")
    return agent_executor
