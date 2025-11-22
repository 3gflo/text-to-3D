from sheets_client import GoogleSheetsClient

class SheetManager:
    """
    High-level proxy for interacting with a specific spreadsheet.
    """

    def __init__(self, credentials, spreadsheet_id):
        self.client = GoogleSheetsClient(credentials)
        self.spreadsheet_id = spreadsheet_id

    def add_entry(self, data_list, sheet_name):
        """Appends a single row of data."""
        values = [data_list]
        return self.client.append_to_range(self.spreadsheet_id, sheet_name, values)

    def update_single_cell(self, cell_address, value, sheet_name):
        """Updates a specific cell (e.g., 'B2')."""
        full_range = f"{sheet_name}!{cell_address}"
        values = [[value]]
        return self.client.write_range(self.spreadsheet_id, full_range, values)