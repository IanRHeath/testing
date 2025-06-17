import os
from langchain.tools import tool
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira_utils import search_jira_issues, get_ticket_details, initialize_jira_client, create_jira_issue, JiraBotError, get_ticket_data_for_analysis
from jql_builder import (
    extract_params, build_jql, program_map, system_map,
    VALID_SILICON_REVISIONS, VALID_TRIAGE_CATEGORIES, triage_assignment_map,
    VALID_SEVERITY_LEVELS, extract_keywords_from_text
)
from llm_config import get_llm

# This part of the file is unchanged
JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. Tools will not work: {e}")

def _get_single_ticket_summary(issue_key: str, question: str) -> str:
    """Internal helper to get a summary for one ticket, tailored to a specific question."""
    # This function is unchanged
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
    1.  Begin your answer *always* with the ticket key and the link, like this: `Summary for PLAT-123: [Link]`
    2.  Then, analyze the "User's Question".
    3.  If the question is a generic request for a "full summary", "summary", "details", or similar, provide a detailed, structured summary with these four points: Problem Statement, Latest Analysis / Debug, Identified Root Cause, and Current Blockers.
    4.  If the question is specific (e.g., "what is the root cause?", "who is assigned?", "what are the blockers?"), provide a direct, concise answer to only that question.
    5.  If the question implies an audience (e.g., "for a manager"), tailor the summary's content and tone appropriately, focusing on status, impact, and blockers.

    **Answer:**
    """
    summary_content = llm.invoke(prompt).content
    # Small fix to avoid double-printing the URL if the LLM includes it.
    if ticket_url in summary_content:
        final_output = summary_content
    else:
        final_output = f"Summary for {sanitized_key}: {ticket_url}\n\n{summary_content}"
    return final_output

@tool
def get_field_options_tool(field_name: str, depends_on: Optional[str] = None) -> str:
    """
    Use this tool when the user asks for the available or valid options for a specific ticket field...
    """
    # This function is unchanged
    field_lower = field_name.lower()

    if "program" in field_lower:
        return f"The valid options for Program are: {list(program_map.keys())}"
    elif "triage category" in field_lower:
        return f"The valid options for Triage Category are: {list(VALID_TRIAGE_CATEGORIES)}"
    elif "silicon revision" in field_lower:
        return f"The valid options for Silicon Revision are: {list(VALID_SILICON_REVISIONS)}"
    elif "severity" in field_lower:
        return f"The valid options for Severity are: {list(VALID_SEVERITY_LEVELS)}"
    elif "system" in field_lower:
        if not depends_on:
            return "To list the valid Systems, you must first provide a Program code."
        options = system_map.get(depends_on.upper())
        if options:
            return f"For Program '{depends_on.upper()}', the valid Systems are: {options}"
        else:
            return f"Could not find a Program with the code '{depends_on.upper()}'."
    elif "triage assignment" in field_lower:
        if not depends_on:
            return "To list the Triage Assignments, you must first provide a Triage Category."
        options = triage_assignment_map.get(depends_on.upper())
        if options:
            return f"For Triage Category '{depends_on.upper()}', the valid Triage Assignments are: {options}"
        else:
            return f"Could not find a Triage Category named '{depends_on.upper()}'."
    
    return f"Sorry, I cannot provide options for the field '{field_name}'."

@tool
def create_ticket_tool(summary: str, issuetype: str, program: str, system: str, silicon_revision: str, bios_version: str, triage_category: str, triage_assignment: str, severity: str, project: str = "PLATFORM") -> str:
    """
    Use this tool to create a new Jira ticket. It gathers structured fields, then interactively prompts the user to complete a detailed template for the description and steps to reproduce.
    """
    # This function is unchanged
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized.")
   
    valid_issue_types = ['Issue', 'enhancement', 'draft']
    if issuetype.lower() not in [t.lower() for t in valid_issue_types]:
        return f"Error: Invalid issue type '{issuetype}'. It must be one of {valid_issue_types}."
    program_code = program.upper()
    if program_code not in program_map:
        return f"Error: Invalid program code '{program}'. It must be one of {list(program_map.keys())}."
    valid_systems = system_map.get(program_code)
    if not valid_systems or system not in valid_systems:
        return f"Error: Invalid system '{system}' for program '{program_code}'. Valid options are: {valid_systems}"
    if silicon_revision.upper() not in VALID_SILICON_REVISIONS:
        return f"Error: Invalid silicon revision '{silicon_revision}'. Please provide a valid option."
    triage_cat_upper = triage_category.upper()
    if triage_cat_upper not in VALID_TRIAGE_CATEGORIES:
        return f"Error: Invalid triage category '{triage_category}'. It must be one of {list(VALID_TRIAGE_CATEGORIES)}."
    valid_assignments = triage_assignment_map.get(triage_cat_upper)
    if not valid_assignments or triage_assignment not in valid_assignments:
        return f"Error: Invalid triage assignment '{triage_assignment}' for category '{triage_cat_upper}'. Valid options are: {valid_assignments}"
    severity_title = severity.title()
    if severity_title not in VALID_SEVERITY_LEVELS:
        return f"Error: Invalid severity '{severity}'. It must be one of {list(VALID_SEVERITY_LEVELS)}."

    program_full_name = program_map[program_code]

    steps_delimiter = "\n\n---STEPS-TO-REPRODUCE---\n"
    description_template = f"""---DESCRIPTION---
Detailed Summary:

System Level Signature:

Failure Rate:

Additional Information:

SUT Configuration:

Board details / revision: {system}
OS version:
GFX driver version:
Chipset:
BIOS Ver: {bios_version}
BIOS Edits:
OS Edits:
All external devices connected:

Regression Details: 

Link to Test Case:

Expected behavior:

Actual Behavior:

All Scandump Links:
{steps_delimiter}(Please provide detailed steps to reproduce the issue below this line)
"""
    description_filename = "ticket_description.txt"
    try:
        with open(description_filename, "w") as f:
            f.write(description_template)
        
        print("\n----------------------------------------------------------------")
        print(f"ACTION REQUIRED: I have created a template file named '{description_filename}' in this directory.")
        print("Please open the file, fill in the Description and Steps to Reproduce, and save it.")
        input("Press Enter here when you have saved the file and are ready to continue...")
        
        with open(description_filename, "r") as f:
            full_text_input = f.read()
            
    finally:
        if os.path.exists(description_filename):
            os.remove(description_filename)
    
    if steps_delimiter in full_text_input:
        description_part, steps_part = full_text_input.split(steps_delimiter, 1)
        final_description = description_part.replace("---DESCRIPTION---", "").strip()
        final_steps = steps_part.strip()
    else:
        final_description = full_text_input.replace("---DESCRIPTION---", "").strip()
        final_steps = "Not provided."

    print("\n---")
    print("A new Jira ticket will be created with the following details:")
    print(f"  Project:           {project}")
    print(f"  Summary:           {summary}")
    print("\n--- Description Preview ---")
    print(final_description)
    print("\n--- Steps to Reproduce Preview ---")
    print(final_steps)
    print("----------------------------------\n")
    
    confirmation = input("Is this information correct? (yes/no): ")

    if confirmation.lower().strip() != 'yes':
        return "Ticket creation cancelled by user."

    new_issue = create_jira_issue(
        client=JIRA_CLIENT_INSTANCE, project=project, summary=summary, description=final_description,
        issuetype=issuetype, program=program_full_name, system=system, silicon_revision=silicon_revision.upper(),
        bios_version=bios_version, triage_category=triage_cat_upper, triage_assignment=triage_assignment,
        severity=severity_title, steps_to_reproduce=final_steps
    )
    return f"Successfully created ticket {new_issue.key}. You can view it here: {new_issue.permalink()}"


@tool
def summarize_ticket_tool(issue_key: str, question: Optional[str] = "Provide a full 4-point summary.") -> str:
    """Use this tool to summarize a SINGLE JIRA ticket OR to get its URL."""
    return _get_single_ticket_summary(issue_key, question)

@tool
def summarize_multiple_tickets_tool(issue_keys: List[str]) -> str:
    """Use this tool when the user asks to summarize MORE THAN ONE JIRA ticket."""
    # This function is unchanged
    summaries = []
    question_for_each = "Provide a full 4-point summary."
    for key in issue_keys:
        try:
            summaries.append(_get_single_ticket_summary(key, question_for_each))
        except JiraBotError as e:
            summaries.append(f"Could not generate summary for {key}: {e}")
    return "\n\n---\n\n".join(summaries)

# --- MODIFIED SECTION ---
@tool
def jira_search_tool(query: str) -> List[Dict[str, Any]]:
    """Searches JIRA issues based on a natural language query."""
    if JIRA_CLIENT_INSTANCE is None: raise JiraBotError("JIRA client not initialized.")
    try:
        params = extract_params(query)
        
        # --- NEW LOGIC ---
        # Default to 1 if the user asks for "a ticket" or "the ticket" and doesn't specify another limit.
        singular_phrases = [' a ticket', ' the ticket', ' a plat ticket', ' a bug', ' the bug']
        query_lower = query.lower()
        
        # Check if a singular phrase is in the query AND no limit was extracted by the LLM
        if any(phrase in query_lower for phrase in singular_phrases) and "maxResults" not in params:
            limit = 1
            print("INFO: User query implies a single result. Setting search limit to 1.")
        else:
            # Use the limit from the LLM, or default to 20 if none is found.
            limit = int(params.get("maxResults", 20)) 
        # --- END NEW LOGIC ---

        jql_query = build_jql(params)
        return search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE, limit=limit)
    except JiraBotError as e:
        raise e
    except Exception as e:
        # It's good practice to log the original query for debugging.
        error_message = f"An unexpected error occurred in jira_search_tool for query: '{query}'. Details: {e}"
        raise JiraBotError(error_message)
# --- END MODIFIED SECTION ---

@tool
def find_similar_tickets_tool(issue_key: str) -> List[Dict[str, Any]]:
    """
    Use this tool to find Jira tickets that are similar to an existing ticket.
    The user must provide a single, valid issue key (e.g., 'PLAT-123').
    """
    # This function is unchanged
    print(f"\n--- TOOL CALLED: find_similar_tickets_tool ---")
    print(f"--- Received issue_key: {issue_key} ---")
    
    source_ticket_data = get_ticket_data_for_analysis(issue_key, JIRA_CLIENT_INSTANCE)
    
    text_to_analyze = f"{source_ticket_data.get('summary', '')}\n{source_ticket_data.get('description', '')}"
    if not text_to_analyze.strip():
        return ["Could not find enough text in the source ticket to perform a similarity search."]
    
    extracted_keywords = extract_keywords_from_text(text_to_analyze)
    print(f"--- Extracted Keywords: '{extracted_keywords}' ---")

    params = {
        'project': source_ticket_data.get('project'),
        'keywords': extracted_keywords,
        'maxResults': 10
    }
    
    similar_jql = build_jql(params, exclude_key=issue_key)
    
    similar_issues = search_jira_issues(similar_jql, JIRA_CLIENT_INSTANCE, limit=params['maxResults'])
    
    if not similar_issues:
        return [f"No similar issues found for {issue_key} based on keywords: '{extracted_keywords}'."]

    return similar_issues


ALL_JIRA_TOOLS = [
    jira_search_tool,
    summarize_ticket_tool,
    summarize_multiple_tickets_tool,
    create_ticket_tool,
    get_field_options_tool,
    find_similar_tickets_tool
]
