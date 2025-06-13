from jira_utils import initialize_jira_client, JiraBotError
from jql_builder import project_map, priority_map, program_map

def validate_jira_mappings():
    """
    Connects to Jira and validates the hardcoded maps in the application
    against the live configuration of the Jira instance.
    """
    print("--- Starting Jira Configuration Validation ---")
    
    try:
        jira_client = initialize_jira_client()
        print("\nSuccessfully connected to Jira.")
    except JiraBotError as e:
        print(f"FATAL ERROR: Could not connect to Jira. {e}")
        return

    # --- 1. Validate Projects ---
    print("\n--- 1. Validating Project Mappings ---")
    try:
        live_projects = jira_client.projects()
        live_project_keys = {p.key: p.name for p in live_projects}
        
        code_project_keys = set(project_map.keys())
        live_keys_set = set(live_project_keys.keys())

        print(f"Found {len(live_project_keys)} projects in Jira.")
        
        # Check for projects in your code that are NOT in Jira
        missing_from_jira = code_project_keys - live_keys_set
        if missing_from_jira:
            print(f"\n[WARNING] The following projects exist in your code but NOT in Jira:")
            for key in missing_from_jira:
                print(f"  - {key}")
        
        # Check for projects in Jira that are NOT in your code
        missing_from_code = live_keys_set - code_project_keys
        if missing_from_code:
            print(f"\n[INFO] The following projects exist in Jira but are NOT in your 'project_map':")
            for key in missing_from_code:
                print(f"  - {key} (Name: {live_project_keys[key]})")

        correct_projects = code_project_keys.intersection(live_keys_set)
        if correct_projects:
            print("\n[OK] The following projects are correctly mapped:")
            for key in correct_projects:
                print(f"  - {key}")
        
    except Exception as e:
        print(f"\n[ERROR] Could not validate projects. Details: {e}")

    # --- 2. Validate Priorities ---
    print("\n--- 2. Validating Priority Mappings ---")
    try:
        live_priorities = jira_client.priorities()
        live_priority_names = {p.name for p in live_priorities}
        
        # Your code maps P1 -> "P1 (Gating)". We need to check against the values.
        code_priority_values = set(priority_map.values())

        print(f"Found {len(live_priority_names)} priorities in Jira.")

        missing_from_jira = code_priority_values - live_priority_names
        if missing_from_jira:
            print("\n[WARNING] The following priorities exist in your code but NOT in Jira:")
            for name in missing_from_jira:
                print(f"  - {name}")

        missing_from_code = live_priority_names - code_priority_values
        if missing_from_code:
            print("\n[INFO] The following priorities exist in Jira but are NOT in your 'priority_map':")
            for name in missing_from_code:
                print(f"  - {name}")

        correct_priorities = code_priority_values.intersection(live_priority_names)
        if correct_priorities:
            print("\n[OK] The following priorities are correctly mapped:")
            for name in correct_priorities:
                print(f"  - {name}")

    except Exception as e:
        print(f"\n[ERROR] Could not validate priorities. Details: {e}")

    # --- 3. Validate Program Custom Field ---
    # We can't validate the *values* of a custom field easily without knowing its ID,
    # but we can check if a field named "Program" exists.
    print("\n--- 3. Validating 'Program' Custom Field ---")
    try:
        all_fields = jira_client.fields()
        program_field_found = any(field['name'].lower() == 'program' for field in all_fields)
        
        if program_field_found:
            program_field = next(field for field in all_fields if field['name'].lower() == 'program')
            print(f"[OK] Found a custom field named 'Program'. Its ID is: {program_field['id']}")
            print("NOTE: This script cannot validate the *values* inside the Program field (e.g., 'Strix1 [PRG-000384]').")
            print("Please ensure the values in your 'program_map' match the options in Jira for this field.")
        else:
            print("[WARNING] Could not find a custom field named 'Program'. Your program-based searches may fail.")

    except Exception as e:
        print(f"\n[ERROR] Could not validate custom fields. Details: {e}")
        
    # --- 4. List All Statuses ---
    print("\n--- 4. Listing All Available Statuses ---")
    print("Use this list to ensure your stale ticket logic uses the correct status names.")
    try:
        live_statuses = jira_client.statuses()
        for status in sorted(live_statuses, key=lambda x: x.name):
            print(f"  - \"{status.name}\"")
    except Exception as e:
        print(f"\n[ERROR] Could not retrieve statuses. Details: {e}")
        
    print("\n--- Validation Complete ---")


if __name__ == "__main__":
    validate_jira_mappings()
