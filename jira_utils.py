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
        # --- MODIFICATION HERE ---
        # First, try token_auth for PAT (standard for Jira Cloud)
        jira_client = JIRA(
            server=JIRA_SERVER_URL,
            token_auth=JIRA_PAT,
            timeout=10
        )
        print("Attempted JIRA client initialization with token_auth.")

    except JIRAError as e:
        # If token_auth failed, try basic_auth as a fallback for Jira Server/Data Center PATs
        print(f"Token_auth failed ({e.text}). Trying basic_auth with PAT as password...")
        try:
            jira_client = JIRA(
                server=JIRA_SERVER_URL,
                basic_auth=(JIRA_USERNAME, JIRA_PAT), # Use PAT as password
                timeout=10
            )
            print("Attempted JIRA client initialization with basic_auth using PAT.")
        except JIRAError as e_basic:
            raise JiraBotError(f"Failed to initialize JIRA client with both token_auth and basic_auth: {e_basic.text}")
        except Exception as e_basic_other:
            raise JiraBotError(f"An unexpected error occurred during JIRA client basic_auth initialization: {e_basic_other}")

    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA client initialization: {e}")

    # If we reached here, one of the methods succeeded
    print("JIRA client initialized successfully.")
    return jira_client

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
        raise JiraBotError(f"JIRA search failed for JQL '{jql_query}': {e.text}. Please refine the query.")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA search: {e}")
