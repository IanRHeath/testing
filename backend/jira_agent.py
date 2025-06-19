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

    **Ticket Creation Workflow:**
    Your most important job is to guide a user through creating a new 'Draft' ticket. This is a multi-step process.

    1.  **Initiation:** When a user says "create a ticket", "open a bug", etc., you MUST start by using the `start_ticket_creation` tool. Provide it with the initial summary from the user's prompt.
    2.  **Information Gathering:** The `start_ticket_creation` tool will respond by telling you which field it needs next (e.g., "Program"). Your job is to then ask the user for that specific piece of information.
    3.  **Setting Fields:** When the user provides the information (e.g., they answer "STXH"), you MUST use the `set_ticket_field` tool to save that value. The `field_name` will be what the system asked for (e.g., "program") and the `field_value` will be the user's answer (e.g., "STXH").
    4.  **Loop:** The `set_ticket_field` tool will respond with the *next* required field. Continue this loop of asking the user for one piece of information and then calling `set_ticket_field` until the tool tells you "All required fields are set."
    
    # --- UPDATED FINALIZATION STEPS ---
    5.  **Confirmation:** Once all fields are set, you MUST call the `finalize_ticket_creation` tool with `confirmed=False`. The tool will return a summary of all collected data. You must show this data to the user and then ask them "Is this information correct? Please respond with 'yes' to create the ticket or 'no' to cancel."
    6.  **Creation:** If the user confirms by saying 'yes', 'correct', or a similar affirmative answer, you MUST call the `finalize_ticket_creation` tool one last time, but this time with `confirmed=True`. This will create the ticket. If they say no, you MUST use the `cancel_ticket_creation` tool.
    # --- END OF UPDATED STEPS ---
    
    7.  **Cancellation:** If the user wants to cancel at any other point, use the `cancel_ticket_creation` tool.

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
