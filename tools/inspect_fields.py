from jira_utils import initialize_jira_client, JiraBotError

# --- CONFIGURATION ---
PROJECT_KEY = 'PLAT'
ISSUE_TYPE_NAME = 'Issue'
# --- END CONFIGURATION ---

def inspect_jira_field_object():
    """
    Connects to Jira and inspects the structure of the Field object
    to definitively determine the correct attribute for its ID.
    """
    print("--- Starting Field Object Inspection ---")
    print(f"Attempting to fetch fields for Project='{PROJECT_KEY}' and Issue Type='{ISSUE_TYPE_NAME}'...")

    try:
        jira_client = initialize_jira_client()
        print("Successfully connected to Jira.\n")

        # Step 1: Get issue types for the project
        issue_types = jira_client.project_issue_types(PROJECT_KEY)
        issue_type_map = {it.name: it.id for it in issue_types}

        if ISSUE_TYPE_NAME not in issue_type_map:
            print(f"[FATAL] The issue type '{ISSUE_TYPE_NAME}' is not valid for project '{PROJECT_KEY}'.")
            return
            
        issue_type_id = issue_type_map[ISSUE_TYPE_NAME]

        # Step 2: Get the fields for that specific project and issue type
        fields = jira_client.project_issue_fields(PROJECT_KEY, issue_type_id)

        if not fields:
            print("[FATAL] No fields were returned from Jira to inspect.")
            return

        # Take just the first field from the list to inspect it
        first_field = fields[0]

        print("\n--- Field Object Introspection Report ---")
        print(f"Inspecting the first available field object to determine its structure.")
        print(f"Object Type: {type(first_field)}")
        
        print("\n--- Available Attributes and Methods (from dir()) ---")
        # The dir() function returns a list of all properties and methods available on the object.
        # The correct ID attribute (e.g., 'id', 'key', 'fieldId', etc.) will be in this list.
        print(dir(first_field))

        print("\n--- Raw Object Data (from __dict__, if available) ---")
        try:
            # __dict__ often holds the raw JSON data the object was created from.
            # This can be very revealing.
            print(first_field.__dict__)
        except Exception as e:
            print(f"Could not access __dict__ on this object: {e}")
            
        print("\n--- Inspection Complete ---")
        print("Please send the entire output above to resolve the issue.")

    except JiraBotError as e:
        print(f"A JIRA Bot Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    inspect_jira_field_object()
