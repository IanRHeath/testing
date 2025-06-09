import os
from jira import JIRA, JIRAError
from dotenv import load_dotenv

load_dotenv()

JIRA_SERVER_URL = os.getenv("JIRA_SERVER_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")

class JiraBotError(Exception):
    """Custom exception for Jira Bot related errors."""
    pass

def initialize_jira_client():
    """Initializes and returns a JIRA client using basic_auth with username and password."""
    if not all([JIRA_SERVER_URL, JIRA_USERNAME, JIRA_PASSWORD]):
        raise JiraBotError("JIRA environment variables (URL, USERNAME, PASSWORD) are not set. Please check .env file.")
    try:
        jira_client = JIRA(
            server=JIRA_SERVER_URL,
            basic_auth=(JIRA_USERNAME, JIRA_PASSWORD),
            timeout=10
        )
        print("JIRA client initialized successfully with basic_auth (username/password).")
        return jira_client
    except JIRAError as e:
        raise JiraBotError(f"Failed to initialize JIRA client: {e.text}. Status code: {e.status_code}")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA client initialization: {e}")

def search_jira_issues(jql_query: str, client: JIRA, limit: int = 20) -> list[dict]:
    """
    Searches JIRA issues using a JQL query and returns formatted results.
    :param jql_query: The JQL query string.
    :param client: An initialized JIRA client.
    :param limit: The maximum number of issues to return. Defaults to 20.
    :return: A list of dictionaries, each representing a formatted JIRA issue.
    """
    print(f"\nAttempting JIRA search with JQL: {jql_query} | Limit: {limit}")
    try:
        issues = client.search_issues(jql_query, maxResults=limit)
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
        raise JiraBotError(f"JIRA search failed for JQL '{jql_query}': {e.text}. Status code: {e.status_code}. Please refine the query.")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA search: {e}")
