import os
from langchain.tools import tool
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira_utils import search_jira_issues, get_ticket_details, initialize_jira_client, create_jira_issue, JiraBotError, get_ticket_data_for_analysis
from jql_builder import (
    extract_params, build_jql, program_map, system_map,
    VALID_SILICON_REVISIONS, VALID_TRIAGE_CATEGORIES, triage_assignment_map,
    VALID_SEVERITY_LEVELS, extract_keywords_from_text, get_summary_similarity_score
)
from llm_config import get_llm

JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. Tools will not work: {e}")

def _get_single_ticket_summary(issue_key: str, question: str) -> str:
    """Internal helper to get a summary for one ticket, tailored to a specific question."""
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
            return f"Could not find a Program with the code '{depends_on.upper()}' or it has no defined systems."
    elif "triage assignment" in field_lower:
        if not depends_on:
            return "To list the Triage Assignments, you must first provide a Triage Category."
        options = triage_assignment_map.get(depends_on.upper())
        if options:
            return f"For Triage Category '{depends_on.upper()}', the valid Triage Assignments are: {options}"
        else:
            return f"Could not find a Triage Category named '{depends_on.upper()}' or it has no defined assignments."

    return f"Sorry, I cannot provide options for the field '{field_name}'."


@tool
def create_ticket_tool(summary: str, program: str, system: str, silicon_revision: str, bios_version: str, triage_category: str, triage_assignment: str, severity: str, project: str = "PLATFORM") -> str:
    """
    Use this tool to create a new Jira ticket with a hardcoded issue type of 'Draft'. 
    It will first automatically check for potential duplicates.
    """
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized.")

    # Proactive Duplicate Check
    print("\n--- Running proactive duplicate check before creating ticket... ---")
    try:
        program_code_for_dupe_check = program.upper()
        if program_code_for_dupe_check in program_map:
            program_full_name_for_dupe_check = program_map[program_code_for_dupe_check]
            dupe_jql = f'project = "{project}" AND "Program" = "{program_full_name_for_dupe_check}"'
            candidate_tickets = search_jira_issues(dupe_jql, JIRA_CLIENT_INSTANCE, limit=25)
            potential_duplicates = []
            if candidate_tickets:
                print(f"--- Found {len(candidate_tickets)} candidates. Comparing summaries... ---")
                SIMILARITY_THRESHOLD = 8
                for candidate in candidate_tickets:
                    if candidate_summary := candidate.get('summary'):
                        score = get_summary_similarity_score(summary, candidate_summary)
                        if score >= SIMILARITY_THRESHOLD:
                            potential_duplicates.append(candidate)
            if potential_duplicates:
                print("\n--- WARNING: Found potential duplicate tickets! ---")
                for i, issue in enumerate(potential_duplicates):
                    print(f"{i+1}. Key: {issue['key']} - {issue['status']}")
                    print(f"   Summary: {issue['summary']}")
                    print(f"   URL: {issue['url']}")
                    print("-" * 20)
                confirmation = input("Do you still want to continue creating a new ticket? (yes/no): ")
                if confirmation.lower().strip() != 'yes':
                    return "Ticket creation cancelled by user after duplicate check."
    except Exception as e:
        print(f"\nWARNING: Could not perform duplicate check due to an error: {e}. Proceeding with ticket creation.")
    
    # Validation logic
    program_code = program.upper()
    if program_code not in program_map:
        return f"Error: Invalid program code '{program}'. Valid options are: {list(program_map.keys())}."

    valid_systems = system_map.get(program_code)
    if valid_systems is None:
        return f"Error: The program '{program_code}' exists, but has no valid Systems defined for it."
    if system not in valid_systems:
        return f"Error: Invalid system '{system}' for program '{program_code}'. Valid options are: {valid_systems}"

    if silicon_revision.upper() not in VALID_SILICON_REVISIONS:
        return f"Error: Invalid silicon revision '{silicon_revision}'. Valid options are: {list(VALID_SILICON_REVISIONS)}."
    
    triage_cat_upper = triage_category.upper()
    if triage_cat_upper not in VALID_TRIAGE_CATEGORIES:
        return f"Error: Invalid triage category '{triage_category}'. Valid options are: {list(VALID_TRIAGE_CATEGORIES)}."

    valid_assignments = triage_assignment_map.get(triage_cat_upper)
    if valid_assignments is None:
        return f"Error: The Triage Category '{triage_cat_upper}' exists, but has no valid Triage Assignments defined for it."
    if triage_assignment not in valid_assignments:
        return f"Error: Invalid triage assignment '{triage_assignment}' for category '{triage_cat_upper}'. Valid options are: {valid_assignments}"
    
    severity_title = severity.title()
    if severity_title not in VALID_SEVERITY_LEVELS:
        return f"Error: Invalid severity '{severity}'. Valid options are: {list(VALID_SEVERITY_LEVELS)}."

    program_full_name = program_map[program_code]

    # Description file workflow
    steps_delimiter = "\n\n---STEPS-TO-REPRODUCE---\n"
    description_template = f"""---DESCRIPTION---
Detailed Summary: {summary}

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
        print(f"ACTION REQUIRED: I have created a template file named '{description_filename}'.")
        print("Please open it, complete the details, and save the file.")
        input("Press Enter here when you are ready to continue...")
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
        program=program_full_name, system=system, silicon_revision=silicon_revision.upper(),
        bios_version=bios_version, triage_category=triage_cat_upper, triage_assignment=triage_assignment,
        severity=severity_title, steps_to_reproduce=final_steps
    )
    return f"Successfully created ticket {new_issue.key}. You can view it here: {new_issue.permalink()}"


@tool
def summarize_ticket_tool(issue_key: str, question: Optional[str] = "Provide a full 4-point summary.") -> str:
    """Use this tool to summarize a SINGLE JIRA ticket OR to get its URL."""
    return _get_single_ticket_summary(issue_key, question)

# --- MODIFIED summarize_multiple_tickets_tool ---
@tool
def summarize_multiple_tickets_tool(issue_keys: List[str]) -> str:
    """
    Use this tool to summarize MORE THAN ONE JIRA ticket. 
    It will provide individual summaries and then a final aggregate analysis of all tickets together.
    """
    if not issue_keys:
        return "Please provide at least one issue key."

    # 1. Generate individual summaries
    summaries = []
    question_for_each = "Provide a full 4-point summary."
    for key in issue_keys:
        try:
            summary_text = _get_single_ticket_summary(key, question_for_each)
            summaries.append(summary_text)
        except JiraBotError as e:
            summaries.append(f"Could not generate summary for {key}: {e}")

    individual_summaries_text = "\n\n---\n\n".join(summaries)

    # 2. Generate the aggregate summary if there's more than one successful summary
    successful_summaries = [s for s in summaries if not s.startswith("Could not generate summary")]
    
    if len(successful_summaries) > 1:
        print("\n--- Generating aggregate summary for all tickets... ---")
        llm = get_llm()
        
        aggregate_prompt = f"""
        You are an expert engineering program manager. Your task is to analyze the following collection of JIRA ticket summaries and provide a high-level aggregate summary.
        
        Identify any common themes, recurring root causes, shared blockers, or patterns across all the tickets provided.
        
        Structure your response with these headings:
        - **Overall Status & Common Themes:**
        - **Potential Shared Root Causes:**
        - **Overarching Blockers or Dependencies:**

        **Individual Ticket Summaries:**
        ---
        {individual_summaries_text}
        ---

        **Aggregate Analysis:**
        """
        
        try:
            aggregate_summary = llm.invoke(aggregate_prompt).content
            
            # 3. Combine everything for the final output
            final_output = (
                f"{individual_summaries_text}\n\n"
                f"----------------------------------------\n"
                f"**Aggregate Summary of {len(successful_summaries)} Tickets**\n"
                f"----------------------------------------\n"
                f"{aggregate_summary}"
            )
            return final_output
        except Exception as e:
            print(f"WARNING: Could not generate aggregate summary due to an error: {e}")
            return individual_summaries_text

    return individual_summaries_text


@tool
def jira_search_tool(original_query: str) -> List[Dict[str, Any]]:
    """
    Use this tool to search for Jira issues based on a user's natural language query.
    You must pass the user's complete, original query to the 'original_query' parameter.
    """
    if JIRA_CLIENT_INSTANCE is None: raise JiraBotError("JIRA client not initialized.")
    try:
        params = extract_params(original_query)
        print(f"DEBUG: Extracted parameters from LLM: {params}")
        limit_str = params.get("maxResults", "20")
        try:
            limit = int(limit_str)
            print(f"DEBUG: Successfully set limit to {limit}.")
        except (ValueError, TypeError):
            limit = 20
            print(f"DEBUG: Could not parse '{limit_str}' as an integer. Defaulting limit to {limit}.")
        jql_query = build_jql(params)
        return search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE, limit=limit)
    except JiraBotError as e:
        raise e
    except Exception as e:
        error_message = f"An unexpected error occurred in jira_search_tool for query: '{original_query}'. Details: {e}"
        raise JiraBotError(error_message)

@tool
def find_similar_tickets_tool(issue_key: str) -> List[Dict[str, Any]]:
    """
    Use this tool to find Jira tickets that are similar to an existing ticket.
    The user must provide a single, valid issue key (e.g., 'PLAT-123').
    """
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

@tool
def find_duplicate_tickets_tool(issue_key: str) -> List[Dict[str, Any]]:
    """
    Use this tool to find potential duplicate Jira tickets based on a source ticket key.
    This tool checks for other tickets in the same Program and Project with a very similar summary.
    """
    print(f"\n--- TOOL CALLED: find_duplicate_tickets_tool ---")
    print(f"--- Received source issue_key: {issue_key} ---")
    source_ticket_data = get_ticket_data_for_analysis(issue_key, JIRA_CLIENT_INSTANCE)
    source_summary = source_ticket_data.get('summary')
    source_project = source_ticket_data.get('project')
    program_field_value = source_ticket_data.get('program')
    source_program = ""
    if isinstance(program_field_value, str):
        source_program = program_field_value
    elif isinstance(program_field_value, list) and len(program_field_value) > 0:
        source_program = str(program_field_value[0])
    elif program_field_value is not None:
        source_program = str(program_field_value)
    source_program = source_program.strip("[]'")
    if not all([source_summary, source_project, source_program]):
        return [f"Source ticket {issue_key} is missing a summary, project, or program field. Cannot search for duplicates."]
    jql_query = f'project = "{source_project}" AND "Program" = "{source_program}" AND key != "{issue_key}"'
    print(f"--- Searching for candidate tickets with JQL: {jql_query} ---")
    candidate_tickets = search_jira_issues(jql_query, JIRA_CLIENT_INSTANCE, limit=25)
    if not candidate_tickets:
        return [f"No other tickets found in the same project and program as {issue_key}."]
    print(f"--- Found {len(candidate_tickets)} candidates. Now comparing summaries... ---")
    SIMILARITY_THRESHOLD = 8
    duplicate_tickets = []
    for candidate in candidate_tickets:
        candidate_summary = candidate.get('summary')
        if not candidate_summary:
            continue
        try:
            similarity_score = get_summary_similarity_score(source_summary, candidate_summary)
            if similarity_score >= SIMILARITY_THRESHOLD:
                print(f"--- Found likely duplicate: {candidate['key']} with score {similarity_score} ---")
                duplicate_tickets.append(candidate)
        except JiraBotError as e:
            print(f"WARNING: Could not compare summary for {candidate['key']}. Error: {e}")
            continue
    if not duplicate_tickets:
         return [f"Searched {len(candidate_tickets)} tickets, but no likely duplicates were found for {issue_key}."]
    return duplicate_tickets


ALL_JIRA_TOOLS = [
    jira_search_tool,
    summarize_ticket_tool,
    summarize_multiple_tickets_tool,
    create_ticket_tool,
    get_field_options_tool,
    find_similar_tickets_tool,
    find_duplicate_tickets_tool
]
