from _.services.google_sheets_integration.sheets_client import GoogleSheetsClient


class MockSheetManager:
    """No-op sheet manager used when Google Sheets credentials are unavailable."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def update_row(self, data: dict, sheet_name: str) -> None:
        print(f"MockSheetManager: skipping write to '{sheet_name}'")


class SheetManager:
    """
    High-level proxy for interacting with a specific Google Spreadsheet.

    Implemented as a singleton so the Sheets API client is initialized only once
    per application lifetime. Column order is derived from the sheet's header row,
    so the spreadsheet structure drives the data mapping.
    """

    _instance = None
    _initialized = False

    def __new__(cls, credentials: str | None = None, spreadsheet_id: str | None = None) -> 'SheetManager':
        if cls._instance is None:
            if credentials is None or spreadsheet_id is None:
                raise ValueError(
                    "SheetManager requires 'credentials' and 'spreadsheet_id' on first initialization."
                )
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, credentials: str | None = None, spreadsheet_id: str | None = None) -> None:
        if SheetManager._initialized:
            return

        self.client = GoogleSheetsClient(credentials)
        self.spreadsheet_id = spreadsheet_id
        SheetManager._initialized = True

    @classmethod
    def get_instance(cls) -> 'SheetManager':
        if cls._instance is None:
            raise RuntimeError(
                "SheetManager has not been initialized. "
                "Call SheetManager(credentials, spreadsheet_id) first."
            )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None
        cls._initialized = False

    def get_headers(self, sheet_name: str) -> list[str]:
        """Return the column headers from row 1 of the given sheet."""
        header_range = f"{sheet_name}!1:1"
        header_rows = self.client.read_range(self.spreadsheet_id, header_range)
        if not header_rows:
            raise ValueError(f"No headers found in '{sheet_name}'. Ensure the first row contains column names.")
        return header_rows[0]

    def add_entry(self, data_dict: dict, sheet_name: str) -> dict | None:
        """
        Append a new row by mapping { header: value } to the sheet's column order.

        Columns not present in data_dict are left blank.
        """
        headers = self.get_headers(sheet_name)
        row_values = [data_dict.get(header, "") for header in headers]
        return self.client.append_to_range(self.spreadsheet_id, sheet_name, [row_values])

    def update_row(self, data_dict: dict, sheet_name: str) -> dict | None:
        """
        Update the last existing row with the values in data_dict.

        Only columns included in data_dict are changed; existing values in
        other columns are preserved. Unrecognized headers are skipped with a warning.
        """
        all_data = self.client.read_range(self.spreadsheet_id, sheet_name)
        last_row_idx = len(all_data)
        last_row_data = all_data[-1]
        headers = all_data[0]

        new_row = list(last_row_data)
        while len(new_row) < len(headers):
            new_row.append("")

        updated = False
        for header, value in data_dict.items():
            if header in headers:
                new_row[headers.index(header)] = value
                updated = True
            else:
                print(f"Header '{header}' not found in spreadsheet — skipping.")

        if not updated:
            return None

        update_range = f"{sheet_name}!A{last_row_idx}"
        return self.client.write_range(self.spreadsheet_id, update_range, [new_row])
