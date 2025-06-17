import unittest
from unittest.mock import patch, MagicMock, mock_open

# It's important that we can import from the parent directory
# Make sure you run this test from the root of your project, e.g., using 'python -m unittest discover'
from jira_tools import create_ticket_tool, JiraBotError

class TestCreateTicketTool(unittest.TestCase):

    @patch('jira_tools.create_jira_issue')
    @patch('builtins.open', new_callable=mock_open, read_data="---DESCRIPTION---\nTest Description\n\n---STEPS-TO-REPRODUCE---\nTest Steps")
    @patch('builtins.input', side_effect=['', 'yes']) # First input for "Press Enter", second for "confirm creation"
    @patch('jira_tools.get_summary_similarity_score', return_value=2) # Ensure no duplicates are found
    @patch('jira_tools.search_jira_issues', return_value=[]) # Ensure no candidates are found
    @patch('jira_tools.JIRA_CLIENT_INSTANCE', new_callable=MagicMock)
    def test_create_ticket_happy_path(self, mock_jira_client, mock_search, mock_similarity, mock_input, mock_file, mock_create_issue):
        """
        Tests the successful creation of a ticket when all inputs are valid and no duplicates are found.
        """
        # Mock the return value for the final created issue
        mock_created_issue = MagicMock()
        mock_created_issue.key = "PLAT-99999"
        mock_created_issue.permalink.return_value = "http://jira.example.com/browse/PLAT-99999"
        mock_create_issue.return_value = mock_created_issue

        # Define valid arguments for the tool
        args = {
            "summary": "New test summary for happy path",
            "program": "STXH",
            "system": "System-Strix Halo Reference Board",
            "silicon_revision": "A0",
            "bios_version": "1.2.3",
            "triage_category": "CPU",
            "triage_assignment": "Debug",
            "severity": "High",
            "project": "PLAT"
        }

        # Call the tool
        result = create_ticket_tool(**args)

        # Assertions
        # 1. Check if the final API call was made
        self.assertTrue(mock_create_issue.called)
        
        # 2. Get the arguments that our function was called with
        called_args = mock_create_issue.call_args[1]

        # 3. Verify that the arguments passed to the final Jira API call are correct
        self.assertEqual(called_args['project'], 'PLAT')
        self.assertEqual(called_args['summary'], 'New test summary for happy path')
        self.assertEqual(called_args['program'], 'Strix Halo [PRG-000391]') # Check for correct mapping
        self.assertEqual(called_args['description'].strip(), "Test Description")
        self.assertEqual(called_args['steps_to_reproduce'].strip(), "Test Steps")
        self.assertEqual(called_args['severity'], 'High')

        # 4. Verify the final success message
        self.assertIn("Successfully created ticket PLAT-99999", result)

    @patch('builtins.input', return_value='no') # User immediately says "no" to creating the ticket
    @patch('jira_tools.get_summary_similarity_score', return_value=9) # High score means it's a duplicate
    @patch('jira_tools.search_jira_issues', return_value=[{'key': 'PLAT-12345', 'status': 'Open', 'summary': 'A very similar summary', 'url': 'http://...'}])
    @patch('jira_tools.JIRA_CLIENT_INSTANCE', new_callable=MagicMock)
    def test_create_ticket_duplicate_found_and_cancelled(self, mock_jira_client, mock_search, mock_similarity, mock_input):
        """
        Tests the workflow where a duplicate is found and the user chooses to cancel the creation.
        """
        args = {
            "summary": "A very similar summary",
            "program": "STXH",
            "system": "System-Strix Halo Reference Board",
            "silicon_revision": "A0",
            "bios_version": "1.2.3",
            "triage_category": "CPU",
            "triage_assignment": "Debug",
            "severity": "High",
            "project": "PLAT"
        }

        result = create_ticket_tool(**args)
        
        # Check that the function returned the correct cancellation message
        self.assertEqual(result, "Ticket creation cancelled by user after duplicate check.")


if __name__ == '__main__':
    unittest.main()
