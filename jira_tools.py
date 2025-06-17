import os
from langchain.tools import tool, Tool
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

# --- NEW TICKET CREATION LOGIC ---

class TicketCreator:
    """A stateful class to manage the ticket creation process."""
    def __init__(self):
        self.reset()

    def reset(self):
        """Resets the state to start a new ticket creation."""
        print("INFO: TicketCreator state has been reset.")
        self.draft_data = {}
        self.required_fields = [
            # The order of fields matters for the conversational flow
            "project", "program", "system", "severity", 
            "triage_category", "triage_assignment", 
            "silicon_revision", "iod_silicon_die_revision", "ccd_silicon_die_revision",
            "bios_version", "description", "steps_to_reproduce"
        ]
        self.is_active = False

    def start(self, summary: str, project: str = "PLAT"):
        """Starts the creation process and runs the duplicate check."""
        self.reset()
        self.is_active = True
        self.draft_data['summary'] = summary
        self.draft_data['project'] = project
        
        print("\n--- Running proactive duplicate check before creating ticket... ---")
        try:
            # For the duplicate check, we need the Program. Let's ask for it first.
            return self._get_next_required_field()

        except Exception as e:
            print(f"\nWARNING: Could not perform duplicate check due to an error: {e}.")
        
        return self._get_next_required_field()

    def set_field(self, field_name: str, field_value: str) -> str:
        """Sets a field in the draft and returns the next required field."""
        if not self.is_active:
            return "Error: No ticket creation is currently in progress. Please start by using 'start_ticket_creation'."
        
        field_name_lower = field_name.lower().replace(" ", "_")
        
        # --- Run duplicate check after we get the program ---
        if field_name_lower == 'program':
            self.draft_data[field_name_lower] = field_value
            self._run_duplicate_check()
            return self._get_next_required_field()

        self.draft_data[field_name_lower] = field_value
        return self._get_next_required_field()

    def _get_next_required_field(self) -> str:
        """Helper to determine which required field to ask for next."""
        for field in self.required_fields:
            if field not in self.draft_data:
                # Provide options for fields that have them
                if field == 'program':
                    return f"Next, please provide the 'Program'. Valid options are: {list(program_map.keys())}"
                if field == 'system':
                    program_code = self.draft_data.get('program', '').upper()
                    valid_systems = system_map.get(program_code, [])
                    return f"Next, please provide the 'System'. Valid options for program {program_code} are: {valid_systems}"
                if field == 'severity':
                    return f"Next, please provide the 'Severity'. Valid options are: {list(VALID_SEVERITY_LEVELS)}"
                
                return f"Next, please provide the '{field.replace('_', ' ').title()}'."
        return "All required fields are set. You can now use 'finalize_ticket_creation' to create the ticket."

    def _run_duplicate_check(self):
        """Internal method to run duplicate check once program is known."""
        summary = self.draft_data['summary']
        project = self.draft_data['project']
        program_code = self.draft_data.get('program', '').upper()
        
        if program_code in program_map:
            program_full_name = program_map[program_code]
            dupe_jql = f'project = "{project}" AND "Program" = "{program_full_name}"'
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
                # This part will be enhanced in the GUI step to be more interactive
                for issue in potential_duplicates:
                    print(f"  - {issue['key']}: {issue['summary']}")
                print("Note: The agent has found potential duplicates. For now, creation will continue.")

    def finalize(self) -> str:
        """Validates all data and creates the final ticket."""
        if not self.is_active:
            return "Error: No ticket creation is currently in progress."
            
        # Check if all fields are present
        for field in self.required_fields:
            if field not in self.draft_data:
                return f"Error: Cannot finalize ticket. Missing required field: '{field}'."
        
        # This part will be made more interactive in the GUI phase
        print("--- Final ticket data ---")
        print(self.draft_data)
        
        try:
            new_issue = create_jira_issue(
                client=JIRA_CLIENT_INSTANCE,
                project=self.draft_data['project'],
                summary=self.draft_data['summary'],
                description=self.draft_data.get('description', 'No description provided.'),
                program=program_map[self.draft_data['program'].upper()],
                system=self.draft_data['system'],
                silicon_revision=self.draft_data['silicon_revision'],
                bios_version=self.draft_data['bios_version'],
                triage_category=self.draft_data['triage_category'],
                triage_assignment=self.draft_data['triage_assignment'],
                severity=self.draft_data['severity'],
                steps_to_reproduce=self.draft_data.get('steps_to_reproduce', 'Not provided.'),
                iod_silicon_die_revision=self.draft_data['iod_silicon_die_revision'],
                ccd_silicon_die_revision=self.draft_data['ccd_silicon_die_revision']
            )
            self.reset() # Reset state after successful creation
            return f"Successfully created ticket {new_issue.key}. You can view it here: {new_issue.permalink()}"
        except Exception as e:
            return f"Failed to create ticket. Error: {e}"

# Instantiate the state manager
ticket_creator = TicketCreator()

# Define the new tools
@tool
def start_ticket_creation(summary: str, project: str = "PLAT") -> str:
    """
    Starts the process of creating a new Jira ticket.
    This is the first step and must be called with an initial summary for the ticket.
    """
    return ticket_creator.start(summary, project)

@tool
def set_ticket_field(field_name: str, field_value: str) -> str:
    """
    Sets a specific field for the ticket currently being created.
    Use this to provide information as the agent asks for it (e.g., program, system, severity).
    """
    return ticket_creator.set_field(field_name, field_value)

@tool
def finalize_ticket_creation() -> str:
    """
    Finalizes the ticket creation after all required fields have been provided.
    This should only be called when the agent confirms all information is collected.
    """
    return ticket_creator.finalize()

@tool
def cancel_ticket_creation() -> str:
    """Cancels the current ticket creation process, clearing all entered data."""
    ticket_creator.reset()
    return "Ticket creation process has been cancelled."


# --- EXISTING TOOLS (UNCHANGED) ---
# ... All other tools like _get_single_ticket_summary, jira_search_tool, etc., remain here ...
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
    2.  If the question is a generic request for a "full summary", provide a detailed, structured summary with these four points: Problem Statement, Latest Analysis / Debug, Identified Root Cause, and Current Blockers.
    3.  If the question is specific (e.g., "what is the root cause?"), provide a direct, concise answer to only that question.
    **Answer:**
    """
    summary_content = llm.invoke(prompt).content
    if ticket_url in summary_content:
        final_output = summary_content
    else:
        final_output = f"Summary for {sanitized_key}: {ticket_url}\n\n{summary_content}"
    return final_output

@tool
def summarize_ticket_tool(issue_key: str, question: Optional[str] = "Provide a full 4-point summary.") -> str:
    """Use this tool to summarize a SINGLE JIRA ticket OR to get its URL."""
    return _get_single_ticket_summary(issue_key, question)
    
@tool
def summarize_multiple_tickets_tool(issue_keys: List[str]) -> str:
    """
    Use this tool to summarize MORE THAN ONE JIRA ticket. 
    It will provide individual summaries and then a final aggregate analysis of all tickets together.
    """
    if not issue_keys:
        return "Please provide at least one issue key."
    summaries = []
    question_for_each = "Provide a full 4-point summary."
    for key in issue_keys:
        try:
            summary_text = _get_single_ticket_summary(key, question_for_each)
            summaries.append(summary_text)
        except JiraBotError as e:
            summaries.append(f"Could not generate summary for {key}: {e}")
    individual_summaries_text = "\n\n---\n\n".join(summaries)
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
    # The old create_ticket_tool is removed
    get_field_options_tool,
    find_similar_tickets_tool,
    find_duplicate_tickets_tool,
    # The new creation tools are added
    start_ticket_creation,
    set_ticket_field,
    finalize_ticket_creation,
    cancel_ticket_creation
]
