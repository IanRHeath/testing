import unittest
import re
from unittest.mock import patch, mock_open

from jira_tools import create_ticket_tool, JIRA_CLIENT_INSTANCE

class TestLiveTicketCreation(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data="---DESCRIPTION---\nThis is a live integration test.\n\n---STEPS-TO-REPRODUCE---\n1. Run test\n2. Observe ticket creation\n3. Observe ticket deletion")
    @patch('builtins.input', side_effect=['', 'yes'])
    @patch('jira_tools.get_summary_similarity_score', return_value=2)
    @patch('jira_tools.search_jira_issues', return_value=[])
    def test_live_ticket_creation_and_deletion(self, mock_search, mock_similarity, mock_input, mock_file):
        """
        Tests the end-to-end creation of a ticket in a live Jira instance,
        and then immediately cleans up by deleting the created ticket.
        """
        new_ticket_key = None
        
        # Add the new required fields to the args dictionary
        args = {
            "summary": "Integration Test Ticket - PLEASE DELETE IF FOUND",
            "program": "STXH",
            "system": "System-Strix Halo Reference Board",
            "silicon_revision": "A0",
            "bios_version": "IT-1.0",
            "triage_category": "CPU",
            "triage_assignment": "Debug",
            "severity": "Low",
            "project": "PLAT",
            "iod_silicon_die_revision": "A0", # Provide a valid value
            "ccd_silicon_die_revision": "A0"  # Provide a valid value
        }

        try:
            print("\n--- [Integration Test] Attempting to create a live ticket... ---")
            result = create_ticket_tool.invoke(args)

            self.assertIn("Successfully created ticket", result)

            match = re.search(r'Successfully created ticket (PLAT-\d+)', result)
            self.assertIsNotNone(match, "Could not find created ticket key in result string.")
            new_ticket_key = match.group(1)
            print(f"--- [Integration Test] Successfully created ticket {new_ticket_key}. ---")

        finally:
            if new_ticket_key and JIRA_CLIENT_INSTANCE:
                print(f"--- [Integration Test] Cleaning up: Deleting ticket {new_ticket_key}... ---")
                try:
                    issue_to_delete = JIRA_CLIENT_INSTANCE.issue(new_ticket_key)
                    issue_to_delete.delete()
                    print(f"--- [Integration Test] Successfully deleted ticket {new_ticket_key}. ---")
                except Exception as e:
                    print(f"\nCRITICAL WARNING: FAILED TO DELETE TICKET {new_ticket_key}.")
                    print(f"Please delete it manually. Error: {e}")
            elif not new_ticket_key:
                print("\nWARNING: No ticket key was captured, cleanup could not be performed.")


if __name__ == '__main__':
    unittest.main()
