from jira_utils import initialize_jira_client, JiraBotError
from jql_builder import (
    VALID_SEVERITY_LEVELS, VALID_SILICON_REVISIONS, program_map, system_map,
    VALID_TRIAGE_CATEGORIES, triage_assignment_map
)

# --- CONFIGURATION ---
# 1. Set the Project and Issue Type for the 'Create' screen you want to inspect.
PROJECT_KEY = 'PLAT'
ISSUE_TYPE_NAME = 'Draft'

# 2. Set the details of the custom field you want to validate.
#    - FIELD_NAME_FOR_REPORTING is just for clean print outputs.
#    - FIELD_ID_TO_VALIDATE is the actual custom field ID from Jira.
#    - LOCAL_OPTIONS_TO_VALIDATE is the corresponding set/list/dict from your code.

# Example for 'Severity':
FIELD_NAME_FOR_REPORTING = 'Severity'
FIELD_ID_TO_VALIDATE = 'customfield_12610'
LOCAL_OPTIONS_TO_VALIDATE = VALID_SEVERITY_LEVELS

# --- END CONFIGURATION ---

def validate_field():
    """
    Connects to Jira and validates that a specified set of local options
    matches the available options for a custom field in the live Jira instance.
    """
    print(f"--- Starting Validation for '{FIELD_NAME_FOR_REPORTING}' Field ---")
    print(f"Checking on Project='{PROJECT_KEY}' and Issue Type='{ISSUE_TYPE_NAME}'...")

    try:
        jira_client = initialize_jira_client()
        print("Successfully connected to Jira.\n")

        # Step 1: Get all available issue types for the project
        all_issue_types = jira_client.project_issue_types(PROJECT_KEY)
        issue_type_map = {it.name: it.id for it in all_issue_types}

        if ISSUE_TYPE_NAME not in issue_type_map:
            print(f"[FATAL] The issue type '{ISSUE_TYPE_NAME}' is not valid for project '{PROJECT_KEY}'.")
            print("Available issue types are:", list(issue_type_map.keys()))
            return

        issue_type_id = issue_type_map[ISSUE_TYPE_NAME]

        # Step 2: Get all the fields for that specific project and issue type
        fields = jira_client.project_issue_fields(PROJECT_KEY, issue_type_id)
        
        target_field_info = None
        for f in fields:
            if f.fieldId == FIELD_ID_TO_VALIDATE:
                target_field_info = f
                break
        
        if not target_field_info:
            print(f"[FATAL] The field '{FIELD_NAME_FOR_REPORTING}' (ID: {FIELD_ID_TO_VALIDATE}) was not found on this create screen.")
            return

        # Step 3: Extract the allowed values for the target field
        if not hasattr(target_field_info, 'allowedValues'):
             print(f"[ERROR] Field '{FIELD_NAME_FOR_REPORTING}' does not appear to be a dropdown field (it has no 'allowedValues').")
             return

        live_options = {val.value for val in target_field_info.allowedValues}
        code_options = set(LOCAL_OPTIONS_TO_VALIDATE)

        print(f"Found {len(live_options)} options for '{FIELD_NAME_FOR_REPORTING}' in Jira.")
        print("-" * 50)

        # --- Comparison Report ---
        correctly_mapped = code_options.intersection(live_options)
        missing_from_code = live_options - code_options
        missing_from_jira = code_options - live_options

        if correctly_mapped:
            print(f"\n[OK] The following options for '{FIELD_NAME_FOR_REPORTING}' are correctly mapped in your code:")
            for item in sorted(list(correctly_mapped)):
                print(f"  - {item}")
        
        if missing_from_code:
            print(f"\n[INFO] The following options exist in Jira but are NOT in your code's list:")
            for item in sorted(list(missing_from_code)):
                print(f"  - {item}")
        
        if missing_from_jira:
            print(f"\n[WARNING] The following options exist in your code but NOT in Jira and should be removed:")
            for item in sorted(list(missing_from_jira)):
                print(f"  - {item}")

        if not missing_from_code and not missing_from_jira:
            print(f"\nSuccess! Your list for '{FIELD_NAME_FOR_REPORTING}' is perfectly in sync with Jira.")

    except JiraBotError as e:
        print(f"A JIRA Bot Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    validate_field()
