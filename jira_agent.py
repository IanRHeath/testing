# jira_agent.py
import sys
from langchain.agents import AgentExecutor, create_react_agent
# Changed import: Use ChatPromptTemplate and MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel

# Assuming local imports
from llm_config import get_llm
from jira_tools import ALL_JIRA_TOOLS
from jira_utils import JiraBotError # Import for error handling

def get_jira_agent() -> AgentExecutor:
    """Configures and returns the LangChain Agent for JIRA queries."""

    llm = get_llm() # Get your configured LLM instance

    # The agent's persona and instructions
    # This is the most crucial part for good performance!
    system_message = """
    You are an expert JQL (Jira Query Language) bot for your company's internal JIRA instance.
    Your primary goal is to accurately translate natural language requests into valid JQL queries
    and execute them using the provided tools.

    **JIRA Context and Rules:**
    1.  **Project Keys:** The main project key is "PLATFORM" (or "PLAT"). Always use "PLATFORM" if no specific project is mentioned.
    2.  **Field Names:** Always use correct JQL field names (e.g., `project`, `status`, `assignee`, `summary`, `updated`, `created`, `priority`, `type`).
    3.  **Current User:** If the user mentions "me" or "my" for assignee/reporter, use `currentUser()`.
    4.  **Statuses:** Common statuses include "To Do", "In Progress", "Done", "Closed", "Resolved", "Open", "Backlog", "Blocked", "Reopened".
    5.  **Priorities:** Priorities are "Highest", "High", "Medium", "Low", "Lowest", "Critical".
    6.  **Issue Types:** Common issue types include "Bug", "Task", "Story", "Epic", "Sub-task", "Change Request".
    7.  **Text Search:** For searching within `summary`, `description`, or `comments`, use the `~` operator (e.g., `summary ~ "keyword phrase"`). Use double quotes for exact phrases.
    8.  **Date Queries:**
        *   Relative dates: `updated >= "-1w"` (last week), `created <= "-3d"` (older than 3 days ago).
        *   Specific dates: `created = "2023-01-01"`.
    9.  **List Operators:** Use `IN` for multiple values (e.g., `status IN ("Open", "In Progress")`).
    10. **Logical Operators:** Use `AND`, `OR`, `NOT` appropriately.
    11. **Order By:** If the user asks for ordering, append `ORDER BY` (e.g., `ORDER BY created DESC`).

    **Specific Definitions for JQL Generation:**
    -   **"Stale" Tickets:** A ticket is considered stale if it is `status in ("Open", "To Do", "In Progress", "Reopened", "Blocked") AND updated < "-30d"`.
    -   **"Duplicate" Tickets:** A duplicate ticket implies a search for issues with *similar content* in their summary or description. Infer relevant keywords/phrases from the user's request and use the `~` operator (e.g., `summary ~ "timeout error" OR description ~ "login failure"`).

    **General Agent Behavior:**
    -   If the user asks for information that requires a JQL query, use the `jira_search_tool`.
    -   Your response should always be concise and directly answer the user's request.
    -   If a query is ambiguous, ask for clarification (e.g., "Which project are you referring to?").
    -   If you cannot fulfill the request, state that clearly and offer alternative actions.
    -   Always prioritize generating valid JQL that accurately reflects the user's intent based on the context provided.
    -   If the JIRA search tool returns an error, acknowledge the error and provide a user-friendly message, potentially suggesting rephrasing the request or checking JQL syntax if applicable.
    """

    # --- CORRECTED PROMPT CREATION ---
    # Use ChatPromptTemplate for messages and MessagesPlaceholder for agent_scratchpad
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"), # This is the correct way for ReAct agents
        ]
    )

    # Create the agent
    agent = create_react_agent(llm, ALL_JIRA_TOOLS, prompt)

    # Create the AgentExecutor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=ALL_JIRA_TOOLS,
        verbose=True, # Set to True to see the agent's thought process
        handle_parsing_errors=True, # Helps catch issues with LLM output
        max_iterations=10, # Prevent infinite loops
        return_intermediate_steps=True # Return intermediate thoughts for verbose output
    )
    print("LangChain Agent initialized successfully.")
    return agent_executor
