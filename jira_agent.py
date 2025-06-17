import os
from langchain.tools import tool
from typing import List, Dict, Any, Optional
from jira import JIRA
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from jira_utils import search_jira_issues, get_ticket_details, initialize_jira_client, create_jira_issue, JiraBotError
from jql_builder import (
    extract_params, build_jql, program_map, system_map,
    VALID_SILICON_REVISIONS, VALID_TRIAGE_CATEGORIES, triage_assignment_map,
    VALID_SEVERITY_LEVELS
)
from llm_config import get_llm
from jira_tools import ALL_JIRA_TOOLS

def get_jira_agent() -> AgentExecutor:
    llm = get_llm()

    system_message = """
    You are a helpful JIRA assistant. Your job is to understand the user's request and use the provided tools to fulfill it.

    **Your Capabilities:**
    - You can search for JIRA tickets using natural language.
    - You can summarize a single JIRA ticket.
    - You can summarize a list of multiple JIRA tickets at once.
    - You can find tickets that are similar to an existing ticket.
    - You can create a new ticket.

    **Behavioral Guidelines:**
    - Your primary goal is to select the correct tool for the job and provide it with the correct parameters.
    - For any kind of searching or listing of tickets, you MUST use the `jira_search_tool`. When you use this tool, you MUST pass the user's entire, original query to the tool's `original_query` parameter.
    - If the user provides a single issue key for summary, use the `summarize_ticket_tool`.
    - If the user provides more than one issue key for summary, use the `summarize_multiple_tickets_tool`.
    - For creating a ticket, use the `create_ticket_tool`.
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
