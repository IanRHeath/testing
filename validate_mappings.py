from jira_utils import initialize_jira_client, JiraBotError
from jql_builder import project_map, priority_map, program_map

def validate_jira_mappings():
    """
    Connects to Jira and validates that the hardcoded map values in the application
    exist in the live configuration of the Jira instance.
    """
    print("--- Starting Jira Configuration Validation ---")
    
    try:
        jira_client = initialize_jira_client()
        print("\nSuccessfully connected to Jira.")
    except JiraBotError as e:
        print(f"FATAL ERROR: Could not connect to Jira. {e}")
        return

    # --- 1. Validate Projects in project_map ---
    print("\n--- 1. Validating 'project_map' ---")
    try:
        live_projects = jira_client.projects()
        live_project_keys = {p.key for p in live_projects}
        
        print("Checking if projects in your code exist in Jira...")
        all_ok = True
        for key in project_map.keys():
            if key in live_project_keys:
                print(f"  - [OK] Project '{key}' found in Jira.")
            else:
                print(f"  - [WARNING] Project '{key}' from your map was NOT found in Jira.")
                all_ok = False
        if all_ok:
            print("All projects in your map are valid.")
        
    except Exception as e:
        print(f"\n[ERROR] Could not validate projects. Details: {e}")

    # --- 2. Validate Priorities in priority_map ---
    print("\n--- 2. Validating 'priority_map' ---")
    try:
        live_priorities = jira_client.priorities()
        live_priority_names = {p.name for p in live_priorities}
        
        print("Checking if priorities in your code exist in Jira...")
        all_ok = True
        for name in priority_map.values():
            if name in live_priority_names:
                print(f"  - [OK] Priority '{name}' found in Jira.")
            else:
                print(f"  - [WARNING] Priority '{name}' from your map was NOT found in Jira.")
                all_ok = False
        if all_ok:
            print("All priorities in your map are valid.")

    except Exception as e:
        print(f"\n[ERROR] Could not validate priorities. Details: {e}")

    # --- 3. Validate Program Custom Field ---
    print("\n--- 3. Validating 'Program' Custom Field ---")
    try:
        all_fields = jira_client.fields()
        program_field_found = any(field['name'].lower() == 'program' for field in all_fields)
        
        if program_field_found:
            program_field = next(field for field in all_fields if field['name'].lower() == 'program')
            print(f"[OK] Found a custom field named 'Program'. Its ID is: {program_field['id']}")
            print("NOTE: This script cannot validate the *values* inside the Program field (e.g., 'Strix1 [PRG-000384]').")
        else:
            print("[WARNING] Could not find a custom field named 'Program'. Your program-based searches may fail.")

    except Exception as e:
        print(f"\n[ERROR] Could not validate custom fields. Details: {e}")
        
    # --- 4. List All Statuses (for reference) ---
    print("\n--- 4. Listing All Available Statuses (for Stale Ticket Logic) ---")
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
