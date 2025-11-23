from scipy.signal import upfirdn

from google_sheets.sheets_client import GoogleSheetsClient

class SheetManager:
    """
    High-level proxy for interacting with a specific spreadsheet.
    """

    def __init__(self, credentials, spreadsheet_id):
        self.client = GoogleSheetsClient(credentials)
        self.spreadsheet_id = spreadsheet_id

    def add_entry(self, data_dict, sheet_name):
        """
        Appends a row by mapping a dict of {header: value} to the
        existing column structure in the sheet.
        """
        headers = self.get_headers(sheet_name)

        # 2. Build the ordered row based on headers
        row_values = []
        for header in headers:
            # Get the value from the dict if it exists, otherwise default to empty string
            value = data_dict.get(header, "")
            row_values.append(value)

        # 3. Append the ordered list
        values = [row_values]
        return self.client.append_to_range(self.spreadsheet_id, sheet_name, values)

    def update_row(self, data_dict, sheet_name):
        """
        Updates the last existing row given a dict of {header: value}.
        An existing value will not be overwritten unless it is included in data_dict.
        """
        all_data = self.client.read_range(self.spreadsheet_id, sheet_name)
        last_row_idx = len(all_data)
        last_row_data = all_data[-1]
        headers = all_data[0] # Gathers headers from all_data instead of using get_headers

        new_row = list(last_row_data)

        while len(new_row) < len(headers):
            new_row.append("")

        updated = False
        for header, value in data_dict.items():
            if header in headers:
                col_idx = headers.index(header)
                new_row[col_idx] = value
                updated = True
            else:
                print(f"Header {header} not found in spreadsheet. Skipping.")

        if not updated:
            return None

        update_range = f"{sheet_name}!A{last_row_idx}"
        values = [new_row]
        return self.client.write_range(self.spreadsheet_id, update_range, values)


    def get_headers(self, sheet_name):
        """
        Get current headers to determine column order.
        We assume the headers are in row 1.
        """
        header_range = f"{sheet_name}!1:1"
        header_rows = self.client.read_range(self.spreadsheet_id, header_range)

        if not header_rows:
            raise ValueError(f"No headers found in {sheet_name}. Ensure the first row contains column names.")

        headers = header_rows[0]

        return headers