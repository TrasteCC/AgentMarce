"""
AgentMarce - Google API Tools
Gmail, Google Calendar and Google Drive (read-only access)

First-time setup:
    python3 -c "from tools.google_tools import get_today_calendar_events; print(get_today_calendar_events())"
    A browser will open to authorize. The resulting token is saved automatically.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

TOKEN_PATH = os.getenv(
    'GOOGLE_TOKEN_PATH',
    '/home/agentuser/agent-services/antigravity-agent/config/google_token.json'
)
CREDENTIALS_PATH = os.getenv(
    'GOOGLE_CREDENTIALS_PATH',
    '/home/agentuser/agent-services/antigravity-agent/config/google_credentials.json'
)


def _get_google_service(service_name: str, version: str):
    """Returns an authenticated Google service client. Handles token refresh."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Credentials file not found at {CREDENTIALS_PATH}. "
                    "Download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build(service_name, version, credentials=creds)


def get_unread_emails(max_results: int = 10) -> str:
    """
    Retrieves unread emails from Gmail.

    Args:
        max_results: Maximum number of emails to retrieve (default: 10, max: 20)

    Returns:
        List of unread emails with sender, subject, and date.
    """
    max_results = min(max_results, 20)

    try:
        service = _get_google_service('gmail', 'v1')
        results = service.users().messages().list(
            userId='me',
            labelIds=['UNREAD'],
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            return "No unread emails."

        emails_info = []
        for msg in messages[:5]:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            emails_info.append(
                f"- From: {headers.get('From', 'N/A')}\n"
                f"  Subject: {headers.get('Subject', 'No subject')}\n"
                f"  Date: {headers.get('Date', 'N/A')}"
            )

        total = len(messages)
        shown = min(5, total)
        header = f"Unread emails: {total} total (showing {shown}):\n"
        return header + "\n".join(emails_info)

    except Exception as e:
        return f"Error retrieving emails: {e}"


def get_today_calendar_events() -> str:
    """
    Retrieves today's events from Google Calendar.

    Returns:
        List of today's events with time and title.
    """
    from datetime import datetime, timezone

    try:
        service = _get_google_service('calendar', 'v3')

        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return "No events scheduled for today."

        eventos = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:
                time_str = start.split('T')[1][:5]  # HH:MM
            else:
                time_str = "All day"
            title = event.get('summary', 'No title')
            location = event.get('location', '')
            location_str = f" @ {location}" if location else ""
            eventos.append(f"  {time_str} - {title}{location_str}")

        today_str = now.strftime('%A, %B %d')
        return f"Today's events ({today_str}):\n" + "\n".join(eventos)

    except Exception as e:
        return f"Error retrieving calendar: {e}"


def search_drive_files(query: str, max_results: int = 5) -> str:
    """
    Searches for files in Google Drive.

    Args:
        query: Search term (e.g. "budget report 2024")
        max_results: Maximum number of results (default: 5)

    Returns:
        List of matching files with name and link.
    """
    try:
        service = _get_google_service('drive', 'v3')

        results = service.files().list(
            q=f"name contains '{query}' and trashed=false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)"
        ).execute()

        files = results.get('files', [])
        if not files:
            return f"No files found for: '{query}'"

        files_info = []
        for f in files:
            modified = f.get('modifiedTime', 'N/A')[:10]
            file_type = f.get('mimeType', '').split('.')[-1]
            link = f.get('webViewLink', 'no link')
            files_info.append(
                f"- {f['name']} ({file_type})\n"
                f"  Modified: {modified}\n"
                f"  Link: {link}"
            )

        return f"Files found ({len(files)}):\n" + "\n".join(files_info)

    except Exception as e:
        return f"Error searching Drive: {e}"
