import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

from jira_agent import get_jira_agent
from jira_utils import JiraBotError
from langchain_core.messages import HumanMessage, AIMessage

app = Flask(__name__)
CORS(app)

print("Initializing Jira Agent for the web server...")
try:
    agent_executor = get_jira_agent()
    print("Jira Agent initialized successfully.")
except Exception as e:
    print(f"FATAL: Could not initialize agent at startup: {e}")
    agent_executor = None

@app.route('/api/query', methods=['POST'])
def query_agent():
    """
    Handles POST requests to query the Jira agent.
    Expects a JSON payload with 'input' and 'history' keys.
    """
    if not agent_executor:
        return jsonify({"error": "Agent not initialized. Please check server logs."}), 500

    data = request.json
    user_input = data.get('input')
    chat_history_json = data.get('history', [])

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    chat_history = []
    for msg in chat_history_json:
        if msg.get('role') == 'user':
            chat_history.append(HumanMessage(content=msg.get('content')))
        elif msg.get('role') == 'ai':
            chat_history.append(AIMessage(content=str(msg.get('raw_output', msg.get('content')))))


    print(f"\n--- Received query: '{user_input}' ---")

    try:
        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": chat_history
        })

        response_data = {}
        
        tool_output = None
        tool_used = None
        if 'intermediate_steps' in result and result['intermediate_steps']:
            action, tool_output = result['intermediate_steps'][-1] 
            tool_used = action.tool

        if isinstance(tool_output, dict) and tool_output.get("type") == "confirmation_request":
            response_data = {
                "type": "confirmation_request",
                "content": tool_output['content'],
                "raw_output": "The user is currently reviewing the ticket details."
            }

        elif tool_used in ['summarize_ticket_tool', 'summarize_multiple_tickets_tool'] and isinstance(tool_output, list):
            response_data = {
                "type": "summary_result",
                "content": tool_output,
                "raw_output": result.get('output', '') 
            }
        elif tool_used in ['start_ticket_creation', 'set_ticket_field'] and isinstance(tool_output, dict) and 'options' in tool_output:
            response_data = {
                "type": "options_request",
                "content": tool_output,
                "raw_output": tool_output.get('question', '') 
            }
        elif tool_used in ['jira_search_tool', 'find_similar_tickets_tool', 'find_duplicate_tickets_tool'] and isinstance(tool_output, list):
            response_data = {
                "type": "search_result",
                "content": tool_output,
                "raw_output": result.get('output', '')
            }
        else:
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
