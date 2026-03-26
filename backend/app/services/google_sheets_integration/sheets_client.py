import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:

    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/spreadsheets'
    ]

    def __init__(self, credentials):
        self.creds = None
        self.service = None

        # Looks for credentials.json directly in google_sheets_integration folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.credentials_source = os.path.join(current_dir, 'credentials.json')
        self._authenticate()

    def _authenticate(self):
        """Authenticates using OAuth 2.0 credentials"""
        try:
            creds = None
            # Define path for token.json next to credentials.json
            token_path = os.path.join(os.path.dirname(self.credentials_source), 'token.json')

            # Load existing user token if it exists
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            # If no valid credentials, run the OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_source):
                        raise FileNotFoundError(f"OAuth Credentials file not found at: {self.credentials_source}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_source, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.creds = creds
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