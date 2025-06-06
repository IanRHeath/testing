# jira_utils.py
import os
from jira import JIRA, JIRAError
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

JIRA_SERVER_URL = os.getenv("JIRA_SERVER_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PAT = os.getenv("JIRA_PAT") # Personal Access Token

class JiraBotError(Exception):
    """Custom exception for Jira Bot related errors."""
    pass

def initialize_jira_client():
    """Initializes and returns a JIRA client."""
    if not all([JIRA_SERVER_URL, JIRA_USERNAME, JIRA_PAT]):
        raise JiraBotError("JIRA environment variables are not set. Please check .env file.")
    try:
        # Using token_auth for PAT. If this fails, try basic_auth=(JIRA_USERNAME, JIRA_PAT)
        jira_client = JIRA(
            server=JIRA_SERVER_URL,
            token_auth=JIRA_PAT,
            # For older JIRA Server/Data Center versions, basic_auth might be required:
            # basic_auth=(JIRA_USERNAME, JIRA_PAT),
            timeout=10
        )
        print("JIRA client initialized successfully.")
        return jira_client
    except JIRAError as e:
        raise JiraBotError(f"Failed to initialize JIRA client: {e.text}")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA client initialization: {e}")

def search_jira_issues(jql_query: str, client: JIRA) -> list[dict]:
    """
    Searches JIRA issues using a JQL query and returns formatted results.
    :param jql_query: The JQL query string.
    :param client: An initialized JIRA client.
    :return: A list of dictionaries, each representing a formatted JIRA issue.
    """
    print(f"\nAttempting JIRA search with JQL: {jql_query}")
    try:
        issues = client.search_issues(jql_query, maxResults=20) # Limit results for CLI display
        if not issues:
            print("No issues found for the given JQL.")
            return []

        formatted_issues = []
        for issue in issues:
            assignee_name = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
            status_name = issue.fields.status.name if issue.fields.status else "Unknown"
            priority_name = issue.fields.priority.name if issue.fields.priority else "Unknown"

            formatted_issues.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": status_name,
                "assignee": assignee_name,
                "priority": priority_name,
                "url": f"{JIRA_SERVER_URL}/browse/{issue.key}"
            })
        print(f"Successfully found {len(issues)} issues.")
        return formatted_issues
    except JIRAError as e:
        # JIRAError.text contains the detailed error message from JIRA
        raise JiraBotError(f"JIRA search failed for JQL '{jql_query}': {e.text}. Please refine the query.")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA search: {e}")
