import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:
    """Low-level wrapper around the Google Sheets API v4."""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, credentials: str) -> None:
        self.creds = None
        self.service = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.credentials_source = os.path.join(current_dir, 'credentials.json')
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with a service account credentials file."""
        try:
            if not os.path.exists(self.credentials_source):
                raise FileNotFoundError(f"Credentials file not found at: {self.credentials_source}")

            self.creds = Credentials.from_service_account_file(
                self.credentials_source, scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=self.creds)

        except Exception as e:
            raise RuntimeError(f"Failed to authenticate: {e}")

    def read_range(self, spreadsheet_id: str, range_name: str) -> list[list] | None:
        """Read and return cell values from a spreadsheet range."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except HttpError as e:
            print(f"Sheets API error reading range: {e}")
            return None

    def write_range(self, spreadsheet_id: str, range_name: str, values: list[list]) -> dict | None:
        """Overwrite values in a specific spreadsheet range."""
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            return result
        except HttpError as e:
            print(f"Sheets API error writing range: {e}")
            return None

    def append_to_range(self, spreadsheet_id: str, sheet_name: str, values: list[list]) -> dict | None:
        """Append rows to the end of a sheet."""
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            return result
        except HttpError as e:
            print(f"Sheets API error appending data: {e}")
            return None
