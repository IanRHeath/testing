from langchain.tools import tool
from typing import List, Dict, Any
from jira import JIRA
from jira_utils import search_jira_issues, get_ticket_details, initialize_jira_client, JiraBotError
from jql_builder import extract_params, build_jql
from llm_config import get_llm # Import the LLM config

JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. Tools will not work: {e}")

@tool
def summarize_ticket_tool(issue_key: str) -> str:
    """
    Use this tool when a user asks to summarize, get details of, or understand a specific ticket.
    It takes a single JIRA issue key and returns a concise summary of its content,
    including the description and the latest comments.
    :param issue_key: The JIRA issue key (e.g., "PLAT-123").
    :return: A text summary of the ticket's content and status.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized.")

    # **FIX:** Sanitize the input to ensure correct JIRA key format (hyphen, not underscore).
    sanitized_key = issue_key.replace('_', '-').upper()

    print(f"Summarizing ticket {sanitized_key} (sanitized from input: '{issue_key}')...")
    # 1. Get the raw details and comments from Jira using the sanitized key
    details_text = get_ticket_details(sanitized_key, JIRA_CLIENT_INSTANCE)

    # 2. Use an LLM to generate a summary of the details
    llm = get_llm()
    prompt = f"""
    Based on the following Jira ticket details, provide a concise summary in 3-4 sentences.
    Focus on the main problem, the current status, and what the latest updates are about.

    Ticket Details:
    ---
    {details_text}
    ---
    Concise Summary:
    """
    summary = llm.invoke(prompt).content
    return summary

@tool
def jira_search_tool(query: str) -> List[Dict[str, Any]]:
    """
    Searches JIRA issues based on a natural language query.
    This tool first extracts parameters from the query using an LLM, then constructs
    a JQL query, and finally executes the JQL to find JIRA tickets.
    This tool can understand a requested number of results, like "top 5" or "latest 10".

    **Instructions for LLM Agent:**
    - Call this tool with the full natural language query provided by the user.
    - Do not try to convert the query to JQL yourself; this tool handles it.
    - Focus on identifying user intent (e.g., searching for issues, counting, listing).
    - This tool can understand concepts like 'stale tickets' and 'duplicate tickets' based on internal definitions.

    :param query: The natural language query from the user (e.g., "Show me the top 10 stale tickets", "Find 5 duplicate tickets related to login errors").
    :return: A list of dictionaries, each representing a formatted JIRA issue.
             Returns an empty list if no issues are found.
             Raises JiraBotError on any error during parameter extraction, JQL building, or JIRA API call.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized. Cannot perform search.")
    try:
        # Extract structured parameters from the natural language query
        params = extract_params(query)

        # Get the user-specified limit, defaulting to 20 if not provided
        limit = int(params.get("maxResults", 20))

        # Build the JQL query string from the parameters
        jql_query = build_jql(params)

        # Perform the search with the dynamic limit
        results = search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE, limit=limit)
        return results
    except JiraBotError as e:
        raise e
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred in jira_search_tool: {e}")

# Add the new tool to the list of tools available to the agent
ALL_JIRA_TOOLS = [jira_search_tool, summarize_ticket_tool]
