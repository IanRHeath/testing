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

    # Initialize chat history for stateful conversation
    chat_history = []

    while True:
        user_input = input("\nYour JIRA Query Request: ")
        if user_input.lower() == 'exit':
            print("Exiting JiraTriageLLMAgent. Goodbye!")
            break

        if not user_input.strip():
            print("Please enter a query.")
            continue

        try:
            # Invoke the agent with the user's input and conversation history
            result = agent.invoke({"input": user_input, "chat_history": chat_history})

            issues_found = None
            # Check intermediate steps for raw tool output from jira_search_tool
            if result.get('intermediate_steps'):
                for action, tool_output in result['intermediate_steps']:
                    # Check if the tool was the search tool and if the output is a list (as expected)
                    if action.tool == 'jira_search_tool' and isinstance(tool_output, list):
                        issues_found = tool_output
                        break  # We found our structured data, no need to look further

            # If we got a list of issues from the search tool, format it nicely
            if issues_found is not None:
                if not issues_found:
                     print("\nJIRA Bot: I searched, but couldn't find any issues matching your query.")
                else:
                    print(f"\n--- Found {len(issues_found)} JIRA Issues ---")
                    for i, issue in enumerate(issues_found):
                        print(f"{i+1}. Key: {issue['key']}")
                        print(f"   Summary: {issue['summary']}")
                        print(f"   Status: {issue['status']}")
                        print(f"   Assignee: {issue['assignee']}")
                        print(f"   Priority: {issue['priority']}")
                        print(f"   URL: {issue['url']}")
                        print("-" * 20)
                    if len(issues_found) >= 20:
                        print("Note: Displaying the maximum of 20 results. Refine your query for more specific results.")
            # Otherwise, print the agent's conversational response
            else:
                final_output = result.get('output')
                print(f"\nJIRA Bot: {final_output}")

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
