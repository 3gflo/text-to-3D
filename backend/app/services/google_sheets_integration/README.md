# Google Sheets Integration

Persists completed generation job metadata to a Google Spreadsheet and uploads generated assets to Google Drive. This acts as the project's lightweight data store — each row represents one generation run and records the prompt chain, models used, asset links, and any QA analysis notes.

---

## Files

| File | Class | Responsibility |
|------|-------|---------------|
| `sheets_client.py` | `GoogleSheetsClient` | Low-level Google Sheets API v4 wrapper — authentication, reads, writes, appends |
| `sheets_manager.py` | `SheetManager` | High-level singleton proxy — maps `{ header: value }` dicts to column positions |
| `sheets_manager.py` | `MockSheetManager` | No-op fallback used when credentials are absent |
| `drive_uploader.py` | `GoogleDriveUploader` | Uploads images and 3D model files to Google Drive; returns shareable links |
| `drive_uploader.py` | `MockDriveUploader` | No-op fallback that returns placeholder URLs when credentials are absent |
| `credentials.json` | — | GCP OAuth 2.0 client credentials (not committed to source control) |

---

## Setup

### 1. Create a Google Cloud OAuth 2.0 client

Both the Sheets API and Drive API are accessed via OAuth 2.0 user credentials (not the service account from before). `GoogleDriveUploader` performs an interactive OAuth flow on first run and caches the resulting token in `token.json`.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project (or use an existing one).
2. Enable the **Google Sheets API** and **Google Drive API** for the project.
3. Create an **OAuth 2.0 Client ID** (Desktop application type) and download its JSON key file.
4. Save it as `credentials.json` in this directory (or at the path set by `GOOGLE_SHEETS_CREDENTIALS_PATH`).

On the first server startup, a browser window will open asking you to authorize access. After approval, `token.json` is written alongside `credentials.json` and reused on subsequent runs.

### 2. Share the spreadsheet

Open the target Google Sheet, click **Share**, and grant **Editor** access to the Google account used during the OAuth flow.

### 3. Configure environment variables

```env
GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_SHEET_ID=your_spreadsheet_id
DRIVE_FOLDER_ID=your_drive_folder_id
```

The spreadsheet ID is the long string in the Sheet URL:
`https://docs.google.com/spreadsheets/d/`**`<GOOGLE_SHEET_ID>`**`/edit`

The Drive folder ID is the string at the end of the folder URL:
`https://drive.google.com/drive/folders/`**`<DRIVE_FOLDER_ID>`**

`DRIVE_FOLDER_ID` is optional — if unset, uploaded files are placed in the root of the Drive.

> If `GOOGLE_SHEETS_CREDENTIALS_PATH` is unset or the file does not exist, the app factory substitutes `MockSheetManager` and `MockDriveUploader`, which silently skip all writes. The rest of the application continues to function normally.

---

## Spreadsheet Format

The integration is **header-driven**: the column order in your spreadsheet determines how data is mapped. The first row must contain column headers. The following headers are expected by the `/api/save-job` endpoint:

| Header | Description |
|--------|-------------|
| User | Name of the person who ran the job |
| Description | Brief description of the generation goal |
| Image Prompt | Original user-entered text |
| LLM Used | Prompt optimization model name |
| System Prompt | Full SYSTEM_INSTRUCTION used by the LLM |
| Optimized Image Prompt | The LLM-generated prompt |
| Image Generator | Image model name |
| Image 1–4 | `=HYPERLINK(drive_url, IMAGE(download_url))` formula; images are uploaded to Drive |
| 3D Model Generator | 3D service name |
| Model link | `=HYPERLINK(drive_url, "View 3D Model")` formula; model file is uploaded to Drive |
| Analysis | QA notes or discrepancy analysis output |

Columns not present in the `data_dict` passed to `update_row` are left unchanged. Unrecognized keys are skipped with a console warning.

---

## Classes

### `GoogleSheetsClient`

Thin wrapper around the Sheets API v4. Handles OAuth authentication and exposes three operations:

```python
client = GoogleSheetsClient(credentials_path)

client.read_range(spreadsheet_id, "Sheet1!A1:Z100")   # → list[list]
client.write_range(spreadsheet_id, "Sheet1!A2", rows) # → API response dict
client.append_to_range(spreadsheet_id, "Sheet1", rows)# → API response dict
```

### `SheetManager`

Singleton that wraps `GoogleSheetsClient` with column-aware read/write logic. Constructed once by the Flask app factory and stored in `app.extensions['sheet_manager']`.

```python
manager = SheetManager(credentials=path, spreadsheet_id=sheet_id)

# Append a new row
manager.add_entry({"User": "Jesse", "Image Prompt": "a chair"}, "Sheet1")

# Update the last existing row (non-destructively)
manager.update_row({"Analysis": "Good detail, missing armrests"}, "Sheet1")
```

**`update_row`** reads the entire sheet on every call to determine the current row count and header order, then writes only the last data row back with the updated values. It is intentionally non-destructive — any column not present in `data_dict` retains its existing value.

### `MockSheetManager`

Drop-in replacement with the same interface but no side effects. Logs a message to stdout for each skipped write. Used automatically when Sheets credentials are not configured.

### `GoogleDriveUploader`

Uploads base64-encoded assets to Google Drive and returns shareable links. Constructed once by the Flask app factory and stored in `app.extensions['drive_uploader']`.

```python
uploader = GoogleDriveUploader(credentials_path=path)

# Upload a PNG image; returns a URL compatible with the Google Sheets =IMAGE() formula
image_url: str = uploader.upload_base64_image(b64_string, "front_view.png")

# Upload a GLB or other binary file; returns a standard Drive sharing link
model_url: str = uploader.upload_base64_file(b64_string, "model.glb", mime_type="model/gltf-binary")
```

Both methods accept an optional `data:...;base64,...` prefix and strip it automatically. Files are uploaded to the folder set by `DRIVE_FOLDER_ID` and made publicly readable so the links work without sign-in.

### `MockDriveUploader`

Drop-in replacement that returns hardcoded placeholder URLs without making any network calls. Used automatically when credentials are not configured.
