import base64
import io
import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

class GoogleDriveUploader:
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/spreadsheets'
    ]

    def __init__(self, credentials_path=None):
        self.folder_id = os.getenv('DRIVE_FOLDER_ID')

        if not credentials_path or not os.path.exists(credentials_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            credentials_path = os.path.join(current_dir, 'credentials.json')
            
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"DriveUploader could not find credentials at: {credentials_path}")

        # Path for the token.json file to save user login
        token_path = os.path.join(os.path.dirname(credentials_path), 'token.json')
        creds = None

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        self.creds = creds
        self.service = build('drive', 'v3', credentials=self.creds)


    # FOR IMAGES
    def upload_base64_image(self, b64_string: str, filename: str) -> str:
        try:
            if ',' in b64_string:
                b64_string = b64_string.split(',')[1]

            image_bytes = base64.b64decode(b64_string)
            file_stream = io.BytesIO(image_bytes)

            file_metadata = {'name': filename}
            
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]

            media = MediaIoBaseUpload(file_stream, mimetype='image/png', resumable=True)

            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()

            file_id = uploaded_file.get('id')

            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            # Specific URL format required for Google Sheets =IMAGE() to work
            return f'https://drive.google.com/uc?export=view&id={file_id}'

        except Exception as e:
            print(f"Drive Upload Error (Image): {e}")
            return ""


    # FOR 3D MODELS
    def upload_base64_file(self, b64_string: str, filename: str, mime_type: str = 'application/octet-stream') -> str:
        """Uploads any base64 encoded file to Google Drive and returns a viewing link."""
        try:
            if ',' in b64_string:
                # Extract the base64 part if it has a "data:..." prefix
                b64_string = b64_string.split(',')[1]

            file_bytes = base64.b64decode(b64_string)
            file_stream = io.BytesIO(file_bytes)

            file_metadata = {'name': filename}
            
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]

            # Upload the file using the dynamic mime_type
            media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)

            uploaded_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()

            file_id = uploaded_file.get('id')

            # Make the file readable by anyone with the link
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            # Standard Google Drive viewing/download link for UI clickability
            return f'https://drive.google.com/file/d/{file_id}/view?usp=sharing'

        except Exception as e:
            print(f"Drive Upload Error (File): {e}")
            return ""