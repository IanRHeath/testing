from langchain.tools import tool
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira_utils import search_jira_issues, get_ticket_details, initialize_jira_client, JiraBotError
from jql_builder import extract_params, build_jql
from llm_config import get_llm

JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. Tools will not work: {e}")

def _get_single_ticket_summary(issue_key: str, question: str) -> str:
    """
    Internal helper to get a summary for one ticket, tailored to a specific question.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized.")

    sanitized_key = issue_key.replace('_', '-').upper()
    print(f"Generating summary for {sanitized_key} based on question: '{question}'...")
    
    details_text, ticket_url = get_ticket_details(sanitized_key, JIRA_CLIENT_INSTANCE)

    llm = get_llm()
    
    prompt = f"""
    You are an expert engineering assistant. Your task is to answer a user's question based on the provided 'Ticket Details'.

    **User's Question:** "{question}"

    **Ticket Details:**
    ---
    {details_text}
    ---

    **Instructions:**
    1.  Analyze the "User's Question".
    2.  If the question is a generic request for a "full summary", provide a detailed, structured summary with these four points: Problem Statement, Latest Analysis / Debug, Identified Root Cause, and Current Blockers.
    3.  If the question is specific (e.g., "what is the root cause?"), provide a direct, concise answer to only that question.
    4.  If the question implies an audience (e.g., "for a manager"), tailor the summary's content and tone appropriately.
    5.  Do not add the ticket link or any other introductory text to your response.

    **Answer:**
    """
    summary_content = llm.invoke(prompt).content
    final_output = f"Summary for {sanitized_key}: {ticket_url}\n\n{summary_content}"
    
    return final_output

@tool
def summarize_ticket_tool(issue_key: str, question: Optional[str] = "Provide a full 4-point summary.") -> str:
    """
    Use this tool to summarize a SINGLE JIRA ticket. It can provide a full summary or
    answer a specific question about the ticket.
    :param issue_key: The single JIRA issue key (e.g., "PLAT-123").
    :param question: The specific question the user has about the ticket. Defaults to a full summary.
    :return: A summary of the ticket, tailored to the user's question.
    """
    return _get_single_ticket_summary(issue_key, question)

@tool
def summarize_multiple_tickets_tool(issue_keys: List[str]) -> str:
    """
    Use this tool when the user asks to summarize MORE THAN ONE JIRA ticket.
    It takes a list of JIRA issue keys and returns a consolidated report of full summaries.
    :param issue_keys: A Python list of JIRA issue keys (e.g., ["PLAT-123", "PLAT-456"]).
    :return: A single string containing a formatted report of all summaries.
    """
    summaries = []
    question_for_each = "Provide a full 4-point summary."
    for key in issue_keys:
        try:
            summary = _get_single_ticket_summary(key, question_for_each)
            summaries.append(summary)
        except JiraBotError as e:
            summaries.append(f"Could not generate summary for {key}: {e}")

    return "\n\n---\n\n".join(summaries)

@tool
def jira_search_tool(query: str) -> List[Dict[str, Any]]:
    """
    Searches JIRA issues based on a natural language query.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized. Cannot perform search.")
    try:
        params = extract_params(query)
        limit = int(params.get("maxResults", 20))
        jql_query = build_jql(params)
        results = search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE, limit=limit)
        return results
    except JiraBotError as e:
        raise e
    except Exception as e:
        raise JiraBotError(f"An unexpected error occurred in jira_search_tool: {e}")

ALL_JIRA_TOOLS = [jira_search_tool, summarize_ticket_tool, summarize_multiple_tickets_tool]
