import os
from langchain.tools import tool, Tool
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira_utils import (
    search_jira_issues, get_ticket_details, initialize_jira_client,
    create_jira_issue, JiraBotError, get_ticket_data_for_analysis,
    JIRA_SERVER_URL
)
from jql_builder import (
    extract_params, build_jql, program_map, system_map,
    VALID_SILICON_REVISIONS, VALID_TRIAGE_CATEGORIES, triage_assignment_map,
    VALID_SEVERITY_LEVELS, extract_keywords_from_text, get_summary_similarity_score,
    descriptive_priority_map
)
from llm_config import get_llm

JIRA_CLIENT_INSTANCE = None
try:
    JIRA_CLIENT_INSTANCE = initialize_jira_client()
except JiraBotError as e:
    print(f"CRITICAL ERROR: Could not initialize JIRA client at startup. Tools will not work: {e}")

class TicketCreator:
    def __init__(self):
        self.reset()

      def reset(self):
        """Resets the state to start a new ticket creation."""
        print("INFO: TicketCreator state has been reset.")
        self.draft_data = {}
        self.required_fields = [
            "project", "program", "system", "summary",
            "severity", "triage_category", "triage_assignment",
            "silicon_revision", "iod_silicon_die_revision", "ccd_silicon_die_revision",
            "bios_version", "description", "steps_to_reproduce"
        ]
        self.is_active = False

    def start(self, summary: str, project: str = "PLAT"):
        self.reset()
        self.is_active = True
        self.draft_data['summary'] = summary
        self.draft_data['project'] = project
        return self._get_next_required_field()

    def set_field(self, field_name: str, field_value: str) -> dict:
        """Sets a field in the draft and returns the next required field question."""
        if not self.is_active:
            return {
                "question": "Error: No ticket creation is currently in progress. Please start by using 'start_ticket_creation'.",
                "options": []
            }

        field_name_lower = field_name.lower().replace(" ", "_")

        if field_name_lower == 'summary' and field_value.strip().lower() == 'keep':
            print("INFO: Keeping existing summary.")
        else:
            self.draft_data[field_name_lower] = field_value

        if field_name_lower == 'program':
            self._run_duplicate_check()
            
        return self._get_next_required_field()

    def _get_next_required_field(self) -> dict:
        """Helper to determine the next required field and return a structured question."""
        for field in self.required_fields:
            if field not in self.draft_data:
                question = f"Next, please provide the '{field.replace('_', ' ').title()}'."
                options = []

                if field == 'program':
                    options = list(program_map.keys())
                    question = "What Program is this ticket for?"
                elif field == 'system':
                    program_code = self.draft_data.get('program', '').upper()
                    options = system_map.get(program_code, [])
                    question = f"What System is this for (Program: {program_code})?"
                elif field == 'summary':
                    current_summary = self.draft_data.get('summary', '')
                    question = f"The current summary is: \"{current_summary}\". Please provide the final summary, or type 'keep' to use this one."
                    options = [] 
                elif field == 'severity':
                    options = list(VALID_SEVERITY_LEVELS)
                    question = "What is the Severity?"
                elif field == 'triage_category':
                    options = list(VALID_TRIAGE_CATEGORIES)
                    question = "What is the Triage Category?"
                elif field == 'triage_assignment':
                    category_code = self.draft_data.get('triage_category', '').upper()
                    options = triage_assignment_map.get(category_code, [])
                    question = f"What is the Triage Assignment (Category: {category_code})?"

                return {"next_field": field, "question": question, "options": options}

        return {"next_field": "None", "question": "All required fields are set. You can now finalize the ticket.", "options": ["Finalize Ticket", "Cancel"]}

    def _run_duplicate_check(self):
        summary = self.draft_data.get('summary', '')
        project = self.draft_data.get('project', '')
        program_code = self.draft_data.get('program', '').upper()

        if program_code and program_code in program_map:
            program_full_name = program_map[program_code]
            dupe_jql = f'project = "{project}" AND "Program" = "{program_full_name}"'
            candidate_tickets = search_jira_issues(dupe_jql, JIRA_CLIENT_INSTANCE, limit=25)

            if candidate_tickets:
                print(f"--- Found {len(candidate_tickets)} candidates. Comparing summaries for duplicates... ---")

    def finalize(self) -> str:
        if not self.is_active:
            return "Error: No ticket creation is currently in progress."

        for field in self.required_fields:
            if field not in self.draft_data:
                return f"Error: Cannot finalize ticket. Missing required field: '{field}'."

        print("--- Finalizing ticket with data ---")
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
            self.reset()
            return f"Successfully created ticket {new_issue.key}. You can view it here: {new_issue.permalink()}"
        except Exception as e:
            return f"Failed to create ticket. Error: {e}"

ticket_creator = TicketCreator()

@tool
def start_ticket_creation(summary: str, project: str = "PLAT") -> dict:
    """
    Starts the process of creating a new Jira ticket.
    This is the first step and must be called with an initial summary for the ticket.
    """
    return ticket_creator.start(summary, project)

@tool
def set_ticket_field(field_name: str, field_value: str) -> dict:
    """
    Sets a specific field for the ticket currently being created.
    Use this to provide information as the agent asks for it (e.g., program, system, severity).
    """
    return ticket_creator.set_field(field_name, field_value)

@tool
def finalize_ticket_creation() -> str:
    """
    Finalizes the ticket creation after all required fields have been provided.
    """
    return ticket_creator.finalize()

@tool
def cancel_ticket_creation() -> str:
    """Cancels the current ticket creation process, clearing all entered data."""
    ticket_creator.reset()
    return "Ticket creation process has been cancelled."

@tool
def get_ticket_link_tool(issue_key: str) -> str:
    """
    Use this tool only when the user explicitly asks for the link, URL, or web address of a single Jira ticket.
    It takes a single 'issue_key' as input.
    """
    if not JIRA_SERVER_URL:
        raise JiraBotError("JIRA_SERVER_URL is not configured. Cannot generate link.")
    sanitized_key = issue_key.strip().upper().replace(" ", "-")
    return f"{JIRA_SERVER_URL}/browse/{sanitized_key}"


def _get_single_ticket_summary(issue_key: str, question: str) -> Dict[str, str]:
    """Internal helper to get a summary for one ticket, tailored to a specific question."""
    if JIRA_CLIENT_INSTANCE is None:
        raise JiraBotError("JIRA client not initialized.")

    if not isinstance(issue_key, str):
        raise JiraBotError(f"Error: A single ticket key (string) is required, but received a list.")

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
    1. If the question is a generic request for a "full summary", provide a detailed, structured summary with these four points: Problem Statement, Latest Analysis / Debug, Identified Root Cause, and Current Blockers.
    2. If the question is specific (e.g., "what is the root cause?"), provide a direct, concise answer to only that question.
    3. Do NOT include the ticket key or URL in your answer. Just provide the summary body.
    **Answer:**
    """
    summary_content = llm.invoke(prompt).content

    return {
        "key": sanitized_key,
        "url": ticket_url,
        "body": summary_content
    }

@tool
def get_field_options_tool(field_name: str, depends_on: Optional[str] = None) -> str:
    """
    Use this tool when a user asks for the available or valid options for a specific ticket field, such as 'program', 'system', or 'severity'.
    The 'field_name' is the name of the field they are asking about.
    For fields that depend on another value (like 'system' depends on 'program'), provide the value of the dependency in the 'depends_on' argument.
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
def summarize_ticket_tool(issue_key: str, question: Optional[str] = "Provide a full 4-point summary.") -> List[Dict[str, str]]:
    """Use this tool to summarize a SINGLE JIRA ticket OR to get its URL. Returns a list containing one summary object."""
    summary_object = _get_single_ticket_summary(issue_key, question)
    return [summary_object]

@tool
def summarize_multiple_tickets_tool(issue_keys: List[str]) -> List[Dict[str, str]]:
    """
    Use this tool to summarize MORE THAN ONE JIRA ticket.
    It will provide individual summaries and then a final aggregate analysis of all tickets together.
    Returns a list of summary objects.
    """
    if not issue_keys:
        return [{"key": "Error", "url": "#", "body": "Please provide at least one issue key."}]

    summaries = []
    all_details_text = []
    question_for_each = "Provide a full 4-point summary."
    for key in issue_keys:
        try:
            summary_object = _get_single_ticket_summary(key, question_for_each)
            summaries.append(summary_object)
            details_text, _ = get_ticket_details(key, JIRA_CLIENT_INSTANCE)
            all_details_text.append(f"--- Ticket {key} ---\n{details_text}")
        except JiraBotError as e:
            summaries.append({"key": key, "url": "#", "body": f"Could not generate summary for {key}: {e}"})

    successful_summaries = [s for s in summaries if not s['body'].startswith("Could not generate summary")]

    if len(successful_summaries) > 1:
        print("\n--- Generating aggregate summary for all tickets... ---")
        llm = get_llm()

        individual_summaries_for_prompt = "\n\n".join([f"Ticket {s['key']}:\n{s['body']}" for s in successful_summaries])

        aggregate_prompt = f"""
        You are an expert engineering program manager. Your task is to analyze the following collection of JIRA ticket summaries and provide a high-level aggregate summary.
        Identify any common themes, recurring root causes, shared blockers, or patterns across all the tickets provided.
        Structure your response with these headings:
        - **Overall Status & Common Themes:**
        - **Potential Shared Root Causes:**
        - **Overarching Blockers or Dependencies:**

        **Individual Ticket Summaries:**
        ---
        {individual_summaries_for_prompt}
        ---
        **Aggregate Analysis:**
        """

        try:
            aggregate_summary_body = llm.invoke(aggregate_prompt).content
            aggregate_summary_object = {
                "key": f"Aggregate Summary of {len(successful_summaries)} Tickets",
                "url": "#",
                "body": aggregate_summary_body
            }
            summaries.append(aggregate_summary_object)
        except Exception as e:
            print(f"WARNING: Could not generate aggregate summary due to an error: {e}")
            summaries.append({"key": "Aggregate Summary", "url": "#", "body": f"Failed to generate aggregate summary: {e}"})

    return summaries


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
    Use this tool to find Jira tickets that are similar in content to an existing ticket.
    This is useful for finding related issues or tickets that discuss the same topic.
    You must provide a single, valid 'issue_key' (e.g., 'PLAT-123') for the source ticket.
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
    Use this tool to find potential *duplicate* Jira tickets for a given source ticket.
    This tool is more specific than finding similar tickets; it looks for tickets in the same Program and Project with a very similar summary text.
    You must provide a single, valid 'issue_key' (e.g., 'PLAT-123').
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
    print(f"--- Found {len(candidate_tickets)} candidates. Comparing summaries... ---")
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
    get_ticket_link_tool,
    get_field_options_tool,
    find_similar_tickets_tool,
    find_duplicate_tickets_tool,
    start_ticket_creation,
    set_ticket_field,
    finalize_ticket_creation,
    cancel_ticket_creation
]
