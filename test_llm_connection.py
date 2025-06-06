# test_llm_connection.py
from llm_config import get_llm
from jira_utils import JiraBotError

def test_connection():
    """
    Tests the basic connectivity to the Azure LLM endpoint
    without the complexity of the agent.
    """
    print("Attempting to initialize the LLM...")
    try:
        llm = get_llm()
        print("LLM initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        return

    print("\nSending a simple test prompt to the LLM...")
    try:
        # We use a very simple prompt to test the core functionality
        response = llm.invoke("Hello, are you working?")
        print("--- LLM Test Successful ---")
        print("Response from LLM:")
        print(response.content)
        print("---------------------------")
    except Exception as e:
        print("\n--- LLM Test FAILED ---")
        print(f"An error occurred while trying to invoke the LLM: {e}")
        print("This confirms the issue is with the LLM server or your connection to it.")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()
