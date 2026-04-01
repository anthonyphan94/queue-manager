"""
Google Sheets Service - Fetches phone numbers from Google Sheets.

Uses gspread with Application Default Credentials on Cloud Run,
or a credentials.json file for local development.
"""

import os
import logging

import gspread
from google.auth.default import default as google_auth_default

logger = logging.getLogger(__name__)


def _get_gspread_client() -> gspread.Client:
    """Get an authenticated gspread client.

    On Cloud Run: uses Application Default Credentials (service account).
    Locally: uses GOOGLE_CREDENTIALS_FILE (defaults to credentials.json).
    """
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")

    if creds_file and os.path.exists(creds_file):
        return gspread.service_account(filename=creds_file)

    # Cloud Run: use Application Default Credentials
    creds, _ = google_auth_default(scopes=[
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ])
    return gspread.Client(auth=creds)


def fetch_phone_numbers() -> list[dict]:
    """Pull phone numbers and names from Google Sheets.

    Reads the configured sheet/worksheet. Expects columns:
    - 'name' (or 'Name')
    - 'phone' (or 'Phone')

    Auto-adds US country code to 10-digit numbers.

    Returns:
        List of dicts with 'name' and 'phone' keys.
    """
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    worksheet_gid = os.environ.get("GOOGLE_WORKSHEET_GID")

    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is not configured.")
    if not worksheet_gid:
        raise ValueError("GOOGLE_WORKSHEET_GID is not configured.")

    gc = _get_gspread_client()
    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet_by_id(int(worksheet_gid))
    rows = worksheet.get_all_records()

    contacts = []
    for row in rows:
        # Support both lowercase and capitalized column names
        name = str(row.get("name", row.get("Name", ""))).strip()
        phone = str(row.get("phone", row.get("Phone", ""))).strip()

        if not phone:
            continue

        # Auto-add US country code
        if len(phone) == 10 and phone.isdigit():
            phone = "+1" + phone
        elif len(phone) == 11 and phone.startswith("1") and phone.isdigit():
            phone = "+" + phone
        elif not phone.startswith("+"):
            phone = "+" + phone

        if not name:
            name = "Customer"

        contacts.append({"name": name, "phone": phone})

    logger.info(f"Fetched {len(contacts)} contacts from Google Sheets")
    return contacts
