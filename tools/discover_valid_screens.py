from jira_utils import initialize_jira_client, JiraBotError

# --- CONFIGURATION ---
# Set this to the Project Key you want to investigate.
PROJECT_KEY = 'PLAT'
# --- END CONFIGURATION ---

def discover_screen_configurations():
    """
    Connects to Jira and iterates through every available issue type for a project,
    printing the list of available "Create" fields for each one.
    """
    print("--- Starting Screen Configuration Discovery ---")
    print(f"Investigating all issue types for Project='{PROJECT_KEY}'...")

    try:
        jira_client = initialize_jira_client()
        print("Successfully connected to Jira.\n")

        # Step 1: Get all available issue types for the project
        issue_types = jira_client.project_issue_types(PROJECT_KEY)
        if not issue_types:
            print(f"[FATAL] No issue types found for project '{PROJECT_KEY}'. Please check the project key.")
            return

        print(f"Found {len(issue_types)} issue types. Checking fields for each...")

        # Step 2: Loop through each issue type and get its specific fields
        for issue_type in issue_types:
            try:
                print("\n" + "="*50)
                print(f"Issue Type: '{issue_type.name}'")
                print("="*50)

                fields = jira_client.project_issue_fields(PROJECT_KEY, issue_type.id)
                available_field_ids = {f.fieldId for f in fields}

                if not available_field_ids:
                    print("  - No fields returned for this issue type.")
                    continue

                # Check for our most critical fields
                summary_ok = 'summary' in available_field_ids
                project_ok = 'project' in available_field_ids

                print(f"  - Contains 'summary' field: {summary_ok}")
                print(f"  - Contains 'project' field: {project_ok}")

                print("\n  --- All available fields for this issue type ---")
                for field_id in sorted(list(available_field_ids)):
                    print(f"    - {field_id}")

            except Exception as e:
                print(f"  - Could not fetch fields for '{issue_type.name}'. Error: {e}")

        print("\n--- Discovery Complete ---")
        print("Please review the output above to find an issue type that contains both 'summary' and 'project'.")

    except JiraBotError as e:
        print(f"A JIRA Bot Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    discover_screen_configurations()
