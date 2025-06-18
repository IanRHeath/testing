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

def get_ticket_data_for_analysis(issue_key: str, client: JIRA) -> dict:
    """
    Fetches the key data from a single JIRA ticket for analysis.
    Returns a dictionary of the raw field data.
    """
    print(f"Fetching data for ticket {issue_key} for analysis...")
    try:
        fields = "summary,description,project,customfield_13002"
        issue = client.issue(issue_key, fields=fields)
        
        data = {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description or "",
            "project": issue.fields.project.key
        }
        
        if hasattr(issue.fields, 'customfield_13002') and getattr(issue.fields, 'customfield_13002'):
             data['program'] = issue.fields.customfield_13002

        return data
    except JIRAError as e:
        if e.status_code == 404:
            raise JiraBotError(f"Ticket '{issue_key}' not found.")
        raise JiraBotError(f"Failed to get data for '{issue_key}': {e.text}")
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred while fetching ticket data: {e}")


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
            assignee = issue.fields.assignee.displayName if hasattr(issue.fields, 'assignee') and issue.fields.assignee else "Unassigned"
            status = issue.fields.status.name if hasattr(issue.fields, 'status') and issue.fields.status else "Unknown"
            priority = issue.fields.priority.name if hasattr(issue.fields, 'priority') and issue.fields.priority else "Undefined"
            formatted_issues.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": status,
                "assignee": assignee,
                "priority": priority,
                "url": getattr(issue, 'permalink', lambda: f"{JIRA_SERVER_URL}/browse/{issue.key}")(),
                "created": issue.fields.created[:10] if hasattr(issue.fields, 'created') and issue.fields.created else "Unknown",
                "updated": issue.fields.updated[:10] if hasattr(issue.fields, 'updated') and issue.fields.updated else "Unknown"
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
        
        ticket_url = getattr(issue, 'permalink', lambda: f"{JIRA_SERVER_URL}/browse/{issue.key}")()

        details.append(f"Project: {issue.fields.project.key}")
        
        program_field_obj = getattr(issue.fields, 'Program', None)
        details.append(f"Program: {program_field_obj if program_field_obj else 'Not Found'}")
            
        details.append(f"Title: {issue.fields.summary}")
        details.append(f"Status: {issue.fields.status.name if hasattr(issue.fields, 'status') and issue.fields.status else 'Unknown'}")
        
        resolution = getattr(issue.fields, 'resolution', None)
        details.append(f"Resolution: {resolution.name if resolution else 'Unresolved'}")
        
        assignee = getattr(issue.fields, 'assignee', None)
        details.append(f"Assignee: {assignee.displayName if assignee else 'Unassigned'}")
        
        details.append(f"Created: {issue.fields.created[:10] if hasattr(issue.fields, 'created') and issue.fields.created else 'Unknown'}")
        details.append(f"Updated: {issue.fields.updated[:10] if hasattr(issue.fields, 'updated') and issue.fields.updated else 'Unknown'}")

        details.append("\n-- Description --")
        details.append(issue.fields.description if issue.fields.description else "No description.")
        
        details.append("\n-- Comments --")
        if hasattr(issue.fields.comment, 'comments') and issue.fields.comment.comments:
            for comment in reversed(issue.fields.comment.comments[-5:]):
                author_name = getattr(comment.author, 'displayName', 'Unknown author')
                details.append(f"Comment by {author_name} on {comment.created[:10]}:")
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

def create_jira_issue(client: JIRA, project: str, summary: str, description: str, program: str, system: str, silicon_revision: str, bios_version: str, triage_category: str, triage_assignment: str, severity: str, steps_to_reproduce: str, iod_silicon_die_revision: str, ccd_silicon_die_revision: str) -> JIRA.issue:
    """
    Creates a new issue in Jira with a hardcoded issuetype of 'Draft'.
    """
    print(f"Attempting to create ticket in project '{project}' with summary '{summary}'...")
    
    fields = {
        'project':          {'key': project},
        'summary':          summary,
        'issuetype':        {'name': 'Draft'},
        'description':      description,
        'customfield_11607': steps_to_reproduce,
        'customfield_12610': {'value': severity },
        'customfield_13002': program,
        'customfield_13208': system,
        'customfield_14200': bios_version,
        'customfield_14307': triage_category,
        'customfield_14308': triage_assignment,
        'customfield_17000': silicon_revision,
        'customfield_27209': iod_silicon_die_revision, 
        'customfield_27210': ccd_silicon_die_revision  
    }

    try:
        print("[LIVE MODE] Sending data to Jira API...")
        new_issue = client.create_issue(fields=fields)
        return new_issue
    except JIRAError as e:
        error_details = f"JIRA API Error on ticket creation: {str(e)}"
        raise JiraBotError(error_details)