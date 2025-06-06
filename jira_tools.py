# jira_tools.py
from langchain.tools import tool
from typing import List, Dict, Any
from jira import JIRA

from jira_utils import search_jira_issues, initialize_jira_client, JiraBotError
from jql_builder import extract_params, build_jql

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
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized. Cannot perform search.")
    try:
        params = extract_params(query)
        
        # Unpack the JQL string and the maxResults limit
        jql_query, max_results = build_jql(params)
        
        # Pass both to the search function
        results = search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE, max_results)
        return results
    except JiraBotError as e:
        raise e
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred in jira_search_tool: {e}")

ALL_JIRA_TOOLS = [jira_search_tool]
