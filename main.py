# main.py
import sys
import traceback # <-- ADD THIS IMPORT
from jira_agent import get_jira_agent
from jira_utils import JiraBotError # Import the custom error

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
            # The agent.invoke will call the LLM and the JIRA tool
            # The 'input' here is the user's natural language query
            result = agent.invoke({"input": user_input})

            # The final answer from the agent will be in result['output']
            # The tool output will be in result['intermediate_steps']
            final_output = result.get('output')

            # We want to display the formatted issues directly from the tool's output
            # Check if the last intermediate step contains the tool output (which should be the list of issues)
            # This part can be tricky and might need adjustment based on how the agent's final output is structured.
            # If the agent summarizes, we might need to parse that. For now, assuming direct display of issues.
            issues_found = None
            if result.get('intermediate_steps'):
                for step in reversed(result['intermediate_steps']):
                    if 'tool_name' in step.thought and step.thought['tool_name'] == 'jira_search_tool':
                        # The tool_output attribute contains the result of the tool execution
                        issues_found = step.tool_output
                        break

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
                if len(issues_found) == 20:
                    print("Note: Displaying a maximum of 20 results. Refine your query for more specific results.")
            elif final_output:
                # If no issues_found could be extracted, but the agent provided an output
                # it means the agent thought it was done, or it provided a message.
                print(f"\nAgent's response: {final_output}")
            else:
                print("\nNo specific issues found, or the agent did not return a clear result.")


        except JiraBotError as e:
            # Our custom JIRA errors from jira_utils
            print(f"\nJIRA Bot Error: {e}", file=sys.stderr)
            print("Please check your JQL query or JIRA connection.", file=sys.stderr)
        except Exception as e:
            # --- MODIFIED BLOCK ---
            # Broader exceptions from LangChain or LLM
            print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
            print("--- FULL TRACEBACK ---", file=sys.stderr)
            traceback.print_exc() # This will print the full error stack
            print("----------------------", file=sys.stderr)
            print("\nPlease try rephrasing your request or contact support if the issue persists.", file=sys.stderr)
            # --- END MODIFICATION ---

if __name__ == "__main__":
    main()
