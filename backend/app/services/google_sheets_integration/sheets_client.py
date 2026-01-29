import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, credentials):
        self.creds = None
        self.service = None
        self.credentials_source = credentials
        self._authenticate()

    def _authenticate(self):
        """Authenticates using Service Account credentials"""
        try:
            if not os.path.exists(self.credentials_source):
                raise FileNotFoundError(f"Credentials file not found at: {self.credentials_source}")

            self.creds = Credentials.from_service_account_file(
                self.credentials_source, scopes=self.SCOPES)

            self.service = build('sheets', 'v4', credentials=self.creds)

        except Exception as e:
            raise RuntimeError(f"Failed to authenticate: {e}")

    def read_range(self, spreadsheet_id, range_name):
        """
        Reads and returns the headers for the given spreadsheet_id.
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            return result.get('values', [])
        except HttpError as e:
            print(f"API error reading range: {e}")
            return None

    def write_range(self, spreadsheet_id, range_name, values):
        """Writes (overwrites) values to a specific range."""
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            return result
        except HttpError as err:
            print(f"API Error writing range: {err}")
            return None

    def append_to_range(self, spreadsheet_id, sheet_name, values):
        """Appends rows to a sheet."""
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
        except HttpError as err:
            print(f"API Error appending data: {err}")
            return None