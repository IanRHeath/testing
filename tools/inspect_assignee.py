from jira_utils import initialize_jira_client, JiraBotError

# --- CONFIGURATION ---
# Replace this with the key of a ticket that is already assigned to a user.
TICKET_KEY = 'YOUR-TICKET-KEY-HERE'
# --- END CONFIGURATION ---

def inspect_assignee_format():
    """
    Connects to Jira and inspects the data structure of the assignee
    on a single ticket to determine the correct format for API calls.
    """
    print("--- Starting Assignee Format Inspection ---")
    print(f"Fetching ticket '{TICKET_KEY}' to inspect its assignee field...")

    try:
        jira_client = initialize_jira_client()
        print("Successfully connected to Jira.\n")

        # Fetch the full details of a single issue
        issue = jira_client.issue(TICKET_KEY)

        if not hasattr(issue.fields, 'assignee') or not issue.fields.assignee:
            print(f"[ERROR] The ticket '{TICKET_KEY}' is not assigned to anyone. Please choose a different ticket.")
            return

        assignee_object = issue.fields.assignee

        print("\n--- Assignee Inspection Report ---")
        print(f"Display Name: {assignee_object.displayName}")
        
        print("\n--- Assignee Object Raw Data (from __dict__) ---")
        # This will print the underlying JSON structure of the user object.
        # This tells us exactly what keys and values we need to use.
        # Look for 'name', 'key', or 'accountId'.
        print(assignee_object.__dict__)

        print("\n--- Inspection Complete ---")
        print("Please review the 'Raw Data' above to see the correct format for the assignee.")

    except JiraBotError as e:
        print(f"A JIRA Bot Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    inspect_assignee_format()
