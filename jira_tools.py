# jira_tools.py
from langchain.tools import tool
from typing import List, Dict, Any
from jira import JIRA # Just for type hinting, not initialization here
from datetime import datetime

# Assuming jira_utils is in the same directory
from jira_utils import search_jira_issues, initialize_jira_client, JiraBotError

# Initialize JIRA client globally or pass it around
# For simplicity in this example, we'll initialize it once globally.
# In a more complex application, you might use dependency injection.
JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. Tool will not work: {e}")
    # Exit or handle gracefully if JIRA is absolutely required.
    # For now, we let it try to proceed, but functions will fail if client is None.


@tool
def jira_search_tool(jql_query: str) -> List[Dict[str, Any]]:
    """
    Executes a JQL (Jira Query Language) query to search for issues.
    This tool is designed to be called by an LLM agent that needs to find
    JIRA tickets based on user requests.

    **Instructions for LLM:**
    - Always provide a complete and valid JQL query string as input.
    - DO NOT include any explanatory text, only the JQL query string.
    - Ensure field names are correct (e.g., 'project', 'status', 'assignee', 'summary', 'updated').
    - When user asks for 'stale' tickets, interpret this as:
      'status in ("Open", "To Do", "In Progress", "Reopened", "Blocked") AND updated < "-30d"'
      Adjust the list of "open" statuses if "To Do", "In Progress", etc., are considered "open" in your context.
    - When user asks for 'duplicate' tickets, interpret this as a search for issues
      with similar summary or description content. Infer relevant keywords/phrases from
      the user's request and use the `~` (text search) operator on `summary` or `description` fields.
      Example: `summary ~ "login failure" OR description ~ "authentication error"`
    - Use `currentUser()` for the current user's assignee/reporter.
    - For date ranges, use relative JQL like `created >= "-1w"` (last week), `updated < "-30d"` (older than 30 days).
    - Available project keys: "PLATFORM", "PLAT".
    - Available standard fields: project, status, assignee, reporter, summary, description, comments, labels, components, fixVersion, affectedVersion, resolution, created, updated, priority, due.
    - Available issue types: Bug, Task, Story, Epic, Sub-task, Change Request (assume common ones).
    - Available priorities: Highest, High, Medium, Low, Lowest, Critical.
    - **Example JQL:**
        - `project = PLATFORM AND status in ("Open", "In Progress") AND assignee = currentUser()`
        - `type = Bug AND priority = High AND updated >= "-1d"`
        - `project = PLAT AND summary ~ "database connection refused" AND status = "To Do"`
        - `status in ("Open", "To Do") AND updated < "-30d"` (for stale tickets)
        - `summary ~ "timeout error" OR description ~ "connection reset"` (for duplicate-like search)

    :param jql_query: The JQL string to execute.
    :return: A list of dictionaries, each representing a formatted JIRA issue.
             Returns an empty list if no issues are found.
             Raises JiraBotError on JIRA API errors.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized. Cannot perform search.")
    try:
        return search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE)
    except JiraBotError as e:
        # Re-raise the custom error to be caught by the agent
        raise e
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred in jira_search_tool: {e}")

# You can collect all tools in a list for the agent
ALL_JIRA_TOOLS = [jira_search_tool]
