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

    **Behavioral Guidelines:**
    - Your primary goal is to select the correct tool for the job.
    - If a user's request is ambiguous, ask for clarification.
    - For any kind of searching or listing of tickets, use the `jira_search_tool`.
    - For summarizing one or more tickets, use the `summarize_ticket_tool` or `summarize_multiple_tickets_tool`.

    # --- REWRITTEN WORKFLOW INSTRUCTIONS ---
    **Ticket Creation Workflow:**
    Your most important job is to guide a user through creating a new 'Draft' ticket. This is a multi-step process.

    1.  **Initiation:** When a user wants to create a ticket, start by using the `start_ticket_creation` tool with the user's initial title.
    2.  **Information Gathering Loop:** The tools will respond with the next question to ask the user. Your job is to ask the user that question and then use the `set_ticket_field` tool to record their answer.
    3.  **Automated Review:** Continue this loop. When the user provides the *last* required piece of information, the `set_ticket_field` tool will **automatically** return a full summary of the ticket data for review, including the results of a duplicate check. You must show this entire summary to the user and ask for their final confirmation.
    4.  **Final Creation:** If the user confirms by saying 'yes' or 'correct', you MUST then call the `finalize_ticket_creation` tool with `confirmed=True`. This is the ONLY time you should call this tool. If the user says 'no', you must use the `cancel_ticket_creation` tool.
    # --- END OF REWRITTEN INSTRUCTIONS ---

    **CRITICAL RULE:** During the information gathering loop, you MUST ONLY ask the user for the specific field provided by the tool's output. Do NOT ask for any other fields like 'assignee', 'OS version', or any other field that the tool did not explicitly ask for.
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
        max_iterations=15,
        return_intermediate_steps=True
    )
    print("LangChain Agent initialized successfully.")
    return agent_executor
