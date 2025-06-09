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

    **Your Capabilities (so far):**
    - You can search for JIRA tickets using natural language.

    **Behavioral Guidelines:**
    - Your primary goal is to select the correct tool and pass the user's query to it.
    - When the user wants to search for tickets, you MUST use the `jira_search_tool`.
    - Directly pass the user's natural language query for searching into the `jira_search_tool`. Do not attempt to modify it or create JQL yourself. The tool handles the entire conversion process.
    - If a user's request is ambiguous, ask for clarification. For example, if a query is too broad, you might ask them to be more specific.
    - Do not make up information. Use the output from the tools to construct your answer.
    - If the tool returns an error, inform the user clearly and politely.
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
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        return_intermediate_steps=True
    )
    print("LangChain Agent initialized successfully.")
    return agent_executor
