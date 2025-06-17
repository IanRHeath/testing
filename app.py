import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import the core agent logic from your existing files
from jira_agent import get_jira_agent
from jira_utils import JiraBotError
from langchain_core.messages import HumanMessage, AIMessage

# --- Flask App Initialization ---
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) to allow our React frontend
# to communicate with this backend.
CORS(app)

# --- Agent Initialization ---
# We initialize the agent once when the server starts.
# This is much more efficient than re-initializing it for every request.
print("Initializing Jira Agent for the web server...")
try:
    # We pass an empty list for chat history initially.
    # The actual history will be managed per-request.
    agent_executor = get_jira_agent()
    print("Jira Agent initialized successfully.")
except Exception as e:
    print(f"FATAL: Could not initialize agent at startup: {e}")
    agent_executor = None

# --- API Endpoint Definition ---
@app.route('/api/query', methods=['POST'])
def query_agent():
    """
    Handles POST requests to query the Jira agent.
    Expects a JSON payload with 'input' and 'history' keys.
    """
    if not agent_executor:
        return jsonify({"error": "Agent not initialized. Please check server logs."}), 500

    # Get data from the incoming request
    data = request.json
    user_input = data.get('input')
    chat_history_json = data.get('history', [])

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    # Reconstruct the chat history from the JSON payload
    chat_history = []
    for msg in chat_history_json:
        if msg.get('role') == 'user':
            chat_history.append(HumanMessage(content=msg.get('content')))
        elif msg.get('role') == 'ai':
            chat_history.append(AIMessage(content=msg.get('content')))

    print(f"\n--- Received query: '{user_input}' ---")

    try:
        # Invoke the agent with the user's input and history
        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": chat_history
        })

        # --- Process the result to send a structured response to the frontend ---
        response_data = {}
        
        # Check if the result came from our custom search tool
        search_results = None
        if 'intermediate_steps' in result and result['intermediate_steps']:
            for action, tool_output in result['intermediate_steps']:
                # We identify which tool was used
                if action.tool in ['jira_search_tool', 'find_similar_tickets_tool', 'find_duplicate_tickets_tool']:
                    if isinstance(tool_output, list) and tool_output:
                        search_results = tool_output
                        break
        
        if search_results:
            # If search results exist, package them nicely
            response_data = {
                "type": "search_result",
                "content": search_results,
                "raw_output": result.get('output', '') # Also send the raw text for history
            }
        else:
            # For all other tools (summarize, create, etc.), send a simple text response
            response_data = {
                "type": "text",
                "content": result.get('output', 'Sorry, I encountered an issue.'),
                "raw_output": result.get('output', '')
            }
        
        return jsonify(response_data)

    except JiraBotError as e:
        print(f"JiraBotError occurred: {e}")
        return jsonify({"type": "error", "content": str(e)}), 400
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        return jsonify({"type": "error", "content": "An unexpected server error occurred."}), 500

# --- Main execution block ---
if __name__ == '__main__':
    # Runs the Flask server.
    # 'debug=True' allows for automatic reloading when you save the file.
    # 'port=5001' is used to avoid conflicts with the React frontend's default port.
    app.run(debug=True, port=5001)
