# Google Sheets Integration

Persists completed generation job metadata to a Google Spreadsheet. This acts as the project's lightweight data store — each row represents one generation run and records the prompt chain, models used, and any QA analysis notes.

---

## Files

| File | Class | Responsibility |
|------|-------|---------------|
| `sheets_client.py` | `GoogleSheetsClient` | Low-level Google Sheets API v4 wrapper — authentication, reads, writes, appends |
| `sheets_manager.py` | `SheetManager` | High-level singleton proxy — maps `{ header: value }` dicts to column positions |
| `sheets_manager.py` | `MockSheetManager` | No-op fallback used when credentials are absent |
| `credentials.json` | — | GCP service account key (not committed to source control) |

---

## Setup

### 1. Create a Google Cloud service account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project (or use an existing one).
2. Enable the **Google Sheets API** for the project.
3. Create a **Service Account** and download its JSON key file.
4. Save the key file somewhere accessible on the server (e.g., alongside `credentials.json` in this directory).

### 2. Share the spreadsheet

Open the target Google Sheet, click **Share**, and grant **Editor** access to the service account's email address (found in the JSON key file under `client_email`).

### 3. Configure environment variables

```env
GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_SHEET_ID=your_spreadsheet_id
```

The spreadsheet ID is the long string in the Sheet URL:
`https://docs.google.com/spreadsheets/d/`**`<GOOGLE_SHEET_ID>`**`/edit`

> If either variable is unset, the app factory substitutes a `MockSheetManager` that silently skips all writes. The rest of the application continues to function normally.

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
| Image 1–4 | Generated image references |
| 3D Model Generator | 3D service name |
| Model link | Link to the generated model |
| Analysis | QA notes or discrepancy analysis output |

Columns not present in the `data_dict` passed to `update_row` are left unchanged. Unrecognized keys are skipped with a console warning.

---

## Classes

### `GoogleSheetsClient`

Thin wrapper around the Sheets API v4. Handles service account authentication and exposes three operations:

```python
client = GoogleSheetsClient(credentials_path)

client.read_range(spreadsheet_id, "Sheet1!A1:Z100")   # → list[list]
client.write_range(spreadsheet_id, "Sheet1!A2", rows) # → API response dict
client.append_to_range(spreadsheet_id, "Sheet1", rows)# → API response dict
```

Authentication uses the credentials file at the path resolved relative to this module's directory. The `credentials` constructor parameter is accepted for interface compatibility but the path is always resolved locally.

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
