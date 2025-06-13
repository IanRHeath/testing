import os
from jira import JIRA, JIRAError
from dotenv import load_dotenv
from typing import Tuple, Optional

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
    """
    print(f"\nAttempting JIRA search with JQL: {jql_query} | Limit: {limit}")
    try:
        issues = client.search_issues(jql_query, maxResults=limit)
        if not issues:
            print("No issues found for the given JQL.")
            return []

        formatted_issues = []
        for issue in issues:
            # Safer way to access potentially missing fields
            assignee_name = "Unassigned"
            if hasattr(issue.fields, 'assignee') and issue.fields.assignee:
                assignee_name = issue.fields.assignee.displayName

            status_name = "Unknown"
            if hasattr(issue.fields, 'status') and issue.fields.status:
                status_name = issue.fields.status.name

            priority_name = "Unknown"
            if hasattr(issue.fields, 'priority') and issue.fields.priority:
                priority_name = issue.fields.priority.name

            formatted_issues.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": status_name,
                "assignee": assignee_name,
                "priority": priority_name,
                "url": f"{JIRA_SERVER_URL}/browse/{issue.key}",
                "created": issue.fields.created[:10],
                "updated": issue.fields.updated[:10]
            })
        print(f"Successfully found {len(issues)} issues.")
        return formatted_issues
    except JIRAError as e:
        raise JiraBotError(f"JIRA search failed for JQL '{jql_query}': {e.text}. Status code: {e.status_code}. Please refine the query.")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred during JIRA search: {e}")

def get_ticket_details(issue_key: str, client: JIRA) -> Tuple[str, str]:
    """
    Fetches detailed information for a single JIRA ticket for summarization.
    Returns a tuple containing (details_as_text, ticket_url).
    """
    print(f"Fetching details for ticket: {issue_key}")
    try:
        issue = client.issue(issue_key, expand="comments")
        details = []
        
        ticket_url = f"{JIRA_SERVER_URL}/browse/{issue.key}"

        details.append(f"Project: {issue.fields.project.key}")
        try:
            program_field = issue.raw['fields']['Program']
            details.append(f"Program: {program_field}")
        except KeyError:
            details.append("Program: Not found.")
            
        details.append(f"Title: {issue.fields.summary}")
        details.append(f"Status: {issue.fields.status.name}")
        
        resolution = issue.fields.resolution
        details.append(f"Resolution: {resolution.name if resolution else 'Unresolved'}")
        
        assignee = issue.fields.assignee
        details.append(f"Assignee: {assignee.displayName if assignee else 'Unassigned'}")
        
        details.append(f"Created: {issue.fields.created[:10]}")
        details.append(f"Updated: {issue.fields.updated[:10]}")

        details.append("\n-- Description --")
        details.append(issue.fields.description if issue.fields.description else "No description.")
        
        details.append("\n-- Comments --")
        if issue.fields.comment.comments:
            for comment in reversed(issue.fields.comment.comments[-5:]):
                details.append(f"Comment by {comment.author.displayName} on {comment.created[:10]}:")
                details.append(comment.body)
                details.append("-" * 10)
        else:
            details.append("No comments.")
            
        details_text = "\n".join(details)
        return (details_text, ticket_url)

    except JIRAError as e:
        if e.status_code == 404:
            raise JiraBotError(f"Ticket '{issue_key}' not found.")
        raise JiraBotError(f"Failed to get details for '{issue_key}': {e.text}")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred while fetching ticket details: {e}")

def create_jira_issue(client: JIRA, project: str, summary: str, description: str, issuetype: str, program: str, system: str, silicon_revision: str, bios_version: str, triage_category: str, triage_assignment: str, severity: str, steps_to_reproduce: str, assignee: Optional[str] = None) -> JIRA.issue:
    """
    Creates a new issue in Jira.
    """
    print(f"Attempting to create ticket in project '{project}' with summary '{summary}'...")
    
    fields = {
        'project':          {'key': project},
        'summary':          summary,
        'issuetype':        {'name': issuetype},
        'description':      description,
        'customfield_11607': steps_to_reproduce,
        'customfield_12610': {'value': severity },
        'customfield_13002': {'value': program },
        'customfield_13208': {'value': system },
        'customfield_14200': bios_version,
        'customfield_14307': {'value': triage_category},
        'customfield_14308': {'value': triage_assignment},
        'customfield_17000': {'value': silicon_revision }
    }
    
    if assignee:
        fields['assignee'] = {'name': assignee}

    try:
        print("[LIVE MODE] Sending data to Jira API...")
        new_issue = client.create_issue(fields=fields)
        return new_issue
    except JIRAError as e:
        error_details = f"JIRA API Error on ticket creation: {str(e)}"
        raise JiraBotError(error_details)
