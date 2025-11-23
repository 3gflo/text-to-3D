import unittest
import os
from google_sheets.sheets_manager import SheetManager

test_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(test_dir)
CREDENTIALS_FILE = os.path.join(root, "credentials.json")
SPREADSHEET_ID = "1bEiceW4zLOk4I0wxWtPYsiIuP4BsNQIUvp_Pyzh4znk"

class TestSheets(unittest.TestCase):

    def setUp(self):
        """
        Initializes the real SheetManager with actual credentials.
        """
        # Check if creds exist before trying to authenticate
        if not os.path.exists(CREDENTIALS_FILE):
            self.fail(f"Credentials file not found at: {CREDENTIALS_FILE}. "
                      "Please place your JSON key file there.")

        self.manager = SheetManager(CREDENTIALS_FILE, SPREADSHEET_ID)

    def test_connection(self):
        """
        Ensure authentication and connection works.
        """
        print(self.manager.client.service)
        self.assertIsNotNone(self.manager.client.service, "API Service should be initialized.")

    def test_read_range(self):
        """
        Test read_range by attempting to get the headers
        """
        header_range = "Sheet1!1:1"
        header_rows = self.manager.client.read_range(SPREADSHEET_ID, header_range)
        print(header_rows)
        self.assertIsNotNone(header_rows)

    def test_add_entry(self):
        """
        Tests adding a real row to the spreadsheet.
        """
        print("\n...Attempting to append a row...")

        # Tests of order input
        new_data = {
            'Description': 'Test append row',
            'User': 'Jesse',
        }

        # Attempt to append to 'Sheet1' (Ensure a sheet named 'Sheet1' exists)
        response = self.manager.add_entry(new_data, "Sheet1")
        print(response)

        self.assertIsNotNone(response, "API response should not be None")
        self.assertIn('updates', response, "Response should contain update details")

    def test_update_row(self):
        """
        Tests updating a specific cell (e.g., A1).
        """
        print("\n...Attempting to update cell A1...")
        new_data = {
            'Description': 'This should be in row 5',
            'User': 'Jesse',
        }

        response = self.manager.update_row(new_data, "Sheet1")

        self.assertIsNotNone(response, "API response should not be None")
        self.assertIn('updatedCells', response, "Response should indicate cells updated")


if __name__ == '__main__':
    # Sort tests by name to ensure connection runs before logic
    unittest.main()