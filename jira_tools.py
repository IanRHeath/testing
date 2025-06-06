# jira_tools.py
from langchain.tools import tool
from typing import List, Dict, Any
from jira import JIRA # Just for type hinting

# Assuming local imports
from jira_utils import search_jira_issues, initialize_jira_client, JiraBotError
from jql_builder import extract_params, build_jql # Import the JQL builder functions

# Initialize JIRA client once globally for the tools
JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. JIRA search tool will not work: {e}")


@tool
def jira_search_tool(query: str) -> List[Dict[str, Any]]:
    """
    Searches JIRA issues based on a natural language query.
    This tool first extracts parameters from the query using an LLM, then constructs
    a JQL query, and finally executes the JQL to find JIRA tickets.

    **Instructions for LLM Agent:**
    - Call this tool with the full natural language query provided by the user.
    - Do not try to convert the query to JQL yourself; this tool handles it.
    - Focus on identifying user intent (e.g., searching for issues, counting, listing).
    - This tool can understand concepts like 'stale tickets' and 'duplicate tickets' based on internal definitions.

    :param query: The natural language query from the user (e.g., "Show me all stale tickets in PLATFORM project", "Find duplicate tickets related to login errors").
    :return: A list of dictionaries, each representing a formatted JIRA issue.
             Returns an empty list if no issues are found.
             Raises JiraBotError on any error during parameter extraction, JQL building, or JIRA API call.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized. Cannot perform search.")
    try:
        # Step 1: Extract parameters from natural language query
        params = extract_params(query)
        
        # Step 2: Build JQL from extracted parameters
        jql_query = build_jql(params)
        
        # Step 3: Execute JQL against JIRA
        results = search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE)
        return results
    except JiraBotError as e:
        # Re-raise the custom error to be caught by the agent
        raise e
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred in jira_search_tool: {e}")

# You can collect all tools in a list for the agent
ALL_JIRA_TOOLS = [jira_search_tool]
