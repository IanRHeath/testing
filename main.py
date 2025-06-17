import sys
import traceback
from jira_agent import get_jira_agent
from jira_utils import JiraBotError
from langchain_core.messages import HumanMessage, AIMessage

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
            result = agent.invoke({"input": user_input, "chat_history": chat_history})

            # Always update chat history with the raw output for context
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=result["output"]))

            # --- MODIFIED SECTION ---
            # Default to assuming a search was not performed
            search_tool_used = False
            issues_found = None

            # Check if the search tool was used by inspecting the intermediate steps
            if result.get('intermediate_steps'):
                for action, tool_output in result['intermediate_steps']:
                    if action.tool == 'jira_search_tool':
                        search_tool_used = True
                        if isinstance(tool_output, list):
                            issues_found = tool_output
                        break # Stop after finding the search tool

            # If the search tool was used, print our custom formatted list
            if search_tool_used:
                if issues_found:
                    print(f"\n--- Found {len(issues_found)} JIRA Issues ---")
                    for i, issue in enumerate(issues_found):
                        print(f"{i+1}. Key: {issue['key']}")
                        print(f"   Summary: {issue['summary']}")
                        print(f"   Status: {issue['status']}")
                        print(f"   Assignee: {issue['assignee']}")
                        print(f"   Priority: {issue['priority']}")
                        print(f"   Created: {issue['created']}")
                        print(f"   Updated: {issue['updated']}")
                        print(f"   URL: {issue['url']}")
                        print("-" * 20)
                    # Handle max results note
                    if len(issues_found) >= 20: # You might want to make this dynamic later
                        print("Note: Displaying the maximum of 20 results. Refine your query for more specific results.")
                else:
                    # This handles cases where the search ran but found nothing
                    print("\nJIRA Bot: I searched, but couldn't find any issues matching your query.")
            
            # For any OTHER tool (summarize, create, etc.), print the agent's direct output
            else:
                final_output = result.get('output')
                # Avoid printing empty or boilerplate responses
                if final_output and "Is this information correct? (yes/no):" not in final_output:
                    print(f"\nJIRA Bot: {final_output}")
            # --- END MODIFIED SECTION ---

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
