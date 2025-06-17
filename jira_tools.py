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

class TicketCreator:
    """A stateful class to manage the ticket creation process."""
    def __init__(self):
        self.reset()

    def reset(self):
        """Resets the state to start a new ticket creation."""
        print("INFO: TicketCreator state has been reset.")
        self.draft_data = {}
        self.required_fields = [
            "project", "program", "system", "severity", 
            "triage_category", "triage_assignment", 
            "silicon_revision", "iod_silicon_die_revision", "ccd_silicon_die_revision",
            "bios_version", "description", "steps_to_reproduce"
        ]
        self.is_active = False

    def start(self, summary: str, project: str = "PLAT"):
        """Starts the creation process and returns the first question."""
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
        
        if field_name_lower == 'program':
            self.draft_data[field_name_lower] = field_value
            self._run_duplicate_check() # Run duplicate check now that we have the program
        else:
            self.draft_data[field_name_lower] = field_value
            
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
        """Internal method to run duplicate check once program is known."""
        summary = self.draft_data.get('summary', '')
        project = self.draft_data.get('project', '')
        program_code = self.draft_data.get('program', '').upper()
        
        if program_code and program_code in program_map:
            program_full_name = program_map[program_code]
            dupe_jql = f'project = "{project}" AND "Program" = "{program_full_name}"'
            candidate_tickets = search_jira_issues(dupe_jql, JIRA_CLIENT_INSTANCE, limit=25)
            
            if candidate_tickets:
                print(f"--- Found {len(candidate_tickets)} candidates. Comparing summaries for duplicates... ---")
                # In a real GUI, this would trigger a proper warning. For now, it logs to the console.
                # The proactive check will be fully integrated in the GUI phase.

    def finalize(self) -> str:
        """Validates all data and creates the final ticket."""
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

# --- Existing Tools (Unchanged) ---
# ... (summarize_ticket_tool, jira_search_tool, etc. are unchanged and omitted for brevity) ...
