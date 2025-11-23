# Google Sheets Integration Module

An interface for interacting with Google Sheets, abstracting API complexity and handling dynamic row mapping.

## Structure

| Component | File | Description |
| :--- | :--- | :--- |
| **Client** | `sheets_client.py` | Low-level wrapper for the Google Sheets API. Handles authentication and raw read/write operations. |
| **Manager** | `sheets_manager.py` | High-level controller. Contains the business logic for formatting data and managing workflows. |

## Functions

These functions are located in `SheetManager` and are intended for general workflow use.

### `add_entry(data_dict, sheet_name)`
* Appends a full row of data to the bottom of the sheet.
* Dynamically maps keys in `data_dict` to the column headers in the sheet.

### `update_row(data_dict, sheet_name)`
* Updates the **most recent row** (the last row with data).
* Non-destructive. It only updates the columns specified in `data_dict`; existing data in other columns is preserved.
