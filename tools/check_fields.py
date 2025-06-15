import json
from jira_utils import initialize_jira_client, JiraBotError

# --- CONFIGURATION ---
# Replace with the project key and issue type name you want to check.
# The issue type name must be an exact match to the one in Jira (e.g., "Bug", "Story", "Task").
PROJECT_KEY = 'YOUR_PROJECT_KEY'
ISSUE_TYPE_NAME = 'Your Issue Type Name'
# --- END CONFIGURATION ---

# These are the fields our create_ticket_tool tries to send.
# The script will validate each one.
FIELDS_TO_VALIDATE = {
    'project': 'Project',
    'summary': 'Summary',
    'issuetype': 'Issue Type',
    'description': 'Description',
    'customfield_11607': 'Steps to Reproduce',
    'customfield_12610': 'Severity',
    'customfield_13002': 'Program',
    'customfield_13208': 'System',
    'customfield_14200': 'BIOS Version',
    'customfield_14307': 'Triage Category',
    'customfield_14308': 'Triage Assignment',
    'customfield_17000': 'Silicon Revision'
}


def validate_creation_fields():
    """
    Connects to Jira and validates that the fields required by the 
    create_ticket_tool exist on the target 'Create Issue' screen.
    """
    print("--- Starting Ticket Creation Field Validation ---")
    print(f"Checking configuration for Project='{PROJECT_KEY}' and Issue Type='{ISSUE_TYPE_NAME}'...")

    try:
        jira_client = initialize_jira_client()
        print("Successfully connected to Jira.\n")

        # Fetch the creation metadata from the Jira API
        meta = jira_client.createmeta(
            projectKeys=PROJECT_KEY,
            issuetypeNames=ISSUE_TYPE_NAME,
            expand='projects.issuetypes.fields'
        )

        # Check for valid project and issue type response
        if not meta.get('projects'):
            print(f"[FATAL] Project with key '{PROJECT_KEY}' not found or no permissions.")
            return

        project_meta = meta['projects'][0]
        if not project_meta.get('issuetypes'):
            print(f"[FATAL] Issue type '{ISSUE_TYPE_NAME}' not found in project '{PROJECT_KEY}'.")
            return
            
        # Get the definitive list of fields available on the create screen
        available_fields = project_meta['issuetypes'][0]['fields']
        available_field_ids = set(available_fields.keys())

        print("--- Validating Fields from 'create_ticket_tool' ---")
        error_found = False
        for field_id, field_name in FIELDS_TO_VALIDATE.items():
            if field_id in available_field_ids:
                print(f"  - [OK] Field '{field_name}' (ID: {field_id}) is available on the create screen.")
            else:
                print(f"  - [ERROR] Field '{field_name}' (ID: {field_id}) is NOT available on the create screen.")
                error_found = True
        
        print("\n--- Validation Summary ---")
        if error_found:
            print("Action Required: The fields marked [ERROR] are causing the '400 Bad Request' error.")
            print("We must update the 'create_jira_issue' function in 'jira_utils.py' to remove or replace these fields.")
        else:
            print("Success! All fields required by the bot are present on the Jira create screen.")

    except JiraBotError as e:
        print(f"A JIRA Bot Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    validate_creation_fields()
