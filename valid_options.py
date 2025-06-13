from jira_utils import initialize_jira_client, JiraBotError
from jql_builder import VALID_SEVERITY_LEVELS

# --- CONFIGURATION ---
# We will use the Project and Issue Type we discovered works for creation.
PROJECT_KEY = 'PLAT'
ISSUE_TYPE_NAME = 'Draft'
# The known ID for the "Severity" custom field.
SEVERITY_FIELD_ID = 'customfield_12610'
# --- END CONFIGURATION ---

def validate_severity():
    """
    Connects to Jira and validates that the hardcoded VALID_SEVERITY_LEVELS
    matches the available options in the live Jira instance.
    """
    print("--- Starting Severity Field Validation ---")
    print(f"Checking Severity options for Project='{PROJECT_KEY}' and Issue Type='{ISSUE_TYPE_NAME}'...")

    try:
        jira_client = initialize_jira_client()
        print("Successfully connected to Jira.\n")

        # Get all the fields for the specific create screen
        fields = jira_client.project_issue_fields(PROJECT_KEY, jira_client.project_issue_types(PROJECT_KEY, ISSUE_TYPE_NAME)[0].id)
        
        severity_field_info = None
        for f in fields:
            if f.fieldId == SEVERITY_FIELD_ID:
                severity_field_info = f
                break
        
        if not severity_field_info:
            print(f"[FATAL] The Severity field (ID: {SEVERITY_FIELD_ID}) was not found on this create screen.")
            return

        # Extract the names from the 'allowedValues' property
        live_severity_options = {val.value for val in severity_field_info.allowedValues}
        
        # The set of severities hardcoded in jql_builder.py
        code_severity_options = VALID_SEVERITY_LEVELS

        print(f"Found {len(live_severity_options)} Severity options in Jira.")
        print("-" * 50)

        # --- Comparison Report ---
        correctly_mapped = code_severity_options.intersection(live_severity_options)
        missing_from_code = live_severity_options - code_severity_options
        missing_from_jira = code_severity_options - live_severity_options

        if correctly_mapped:
            print("\n[OK] The following severities are correctly mapped in your code:")
            for item in sorted(list(correctly_mapped)):
                print(f"  - {item}")
        
        if missing_from_code:
            print("\n[INFO] The following severities exist in Jira but are NOT in your code's VALID_SEVERITY_LEVELS list:")
            for item in sorted(list(missing_from_code)):
                print(f"  - {item}")
        
        if missing_from_jira:
            print("\n[WARNING] The following severities exist in your code but NOT in Jira and should be removed:")
            for item in sorted(list(missing_from_jira)):
                print(f"  - {item}")

        if not missing_from_code and not missing_from_jira:
            print("\nSuccess! Your `VALID_SEVERITY_LEVELS` list is perfectly in sync with Jira.")

    except JiraBotError as e:
        print(f"A JIRA Bot Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    validate_severity()
