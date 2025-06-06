# main.py
import sys
import traceback
from jira_agent import get_jira_agent
from jira_utils import JiraBotError

def main():
    print("Welcome to the JiraTriageLLMAgent!")
    print("Type your request in natural language. Type 'exit' to quit.")
    print("Examples: 'Show me all stale tickets in PLATFORM project'")
    print("          'Find duplicate tickets related to login errors'")
    print("          'Bugs assigned to me in PLATFORM with high priority'")

    agent = None
    try:
        agent = get_jira_agent()
    except Exception as e:
        print(f"FATAL ERROR: Could not initialize agent. Exiting. Details: {e}", file=sys.stderr)
        sys.exit(1)

    while True:
        user_input = input("\nYour JIRA Query Request: ")
        if user_input.lower() == 'exit':
            print("Exiting JiraTriageLLMAgent. Goodbye!")
            break

        if not user_input.strip():
            print("Please enter a query.")
            continue

        try:
            result = agent.invoke({"input": user_input})

            # --- MODIFIED BLOCK TO FIX ATTRIBUTEERROR AND UNWANTED OUTPUT ---
            
            issues_found = None
            # The new structure for intermediate_steps is a list of tuples: (action, observation)
            # action is an AgentAction object, observation is the tool's return value.
            if result.get('intermediate_steps'):
                # We only care about the last tool run, which should be our jira_search_tool
                last_step = result['intermediate_steps'][-1]
                agent_action, tool_output = last_step

                # The AgentAction object has a 'tool' attribute with the tool's name
                if agent_action.tool == 'jira_search_tool':
                    issues_found = tool_output

            if issues_found:
                print(f"\n--- Found {len(issues_found)} JIRA Issues ---")
                for i, issue in enumerate(issues_found):
                    print(f"{i+1}. Key: {issue['key']}")
                    print(f"   Summary: {issue['summary']}")
                    print(f"   Status: {issue['status']}")
                    print(f"   Assignee: {issue['assignee']}")
                    print(f"   Priority: {issue['priority']}")
                    print(f"   URL: {issue['url']}")
                    print("-" * 20)
                if len(issues_found) >= 20: # Use >= to be safe
                    print("Note: Displaying a maximum of 20 results. Refine your query for more specific results.")
            else:
                # If we couldn't find tool output, print the agent's final answer as a fallback.
                print("\nAgent's response:")
                print(result.get('output', "No result found."))

            # --- END MODIFICATION ---

        except JiraBotError as e:
            print(f"\nJIRA Bot Error: {e}", file=sys.stderr)
            print("Please check your JQL query or JIRA connection.", file=sys.stderr)
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
            print("--- FULL TRACEBACK ---", file=sys.stderr)
            traceback.print_exc()
            print("----------------------", file=sys.stderr)
            print("\nPlease try rephrasing your request or contact support if the issue persists.", file=sys.stderr)

if __name__ == "__main__":
    main()
