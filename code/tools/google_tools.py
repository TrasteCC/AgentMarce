"""
AgentMarce - Herramientas de Google APIs
Gmail, Google Calendar y Google Drive (acceso de solo lectura)

Primera vez:
    python3 -c "from tools.google_tools import get_today_calendar_events; print(get_today_calendar_events())"
    Se abrira el navegador para autorizar. Guarda el token resultante.
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
    """Obtiene un servicio autenticado de Google. Maneja refresh de tokens."""
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
                    f"No se encontro el archivo de credenciales en {CREDENTIALS_PATH}. "
                    "Descargalo desde Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build(service_name, version, credentials=creds)


def get_unread_emails(max_results: int = 10) -> str:
    """
    Obtiene los emails no leidos de Gmail.

    Args:
        max_results: Numero maximo de emails a recuperar (default: 10, maximo: 20)

    Returns:
        Lista de emails no leidos con remitente, asunto y fecha.
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
            return "No hay emails no leidos."

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
                f"- De: {headers.get('From', 'N/A')}\n"
                f"  Asunto: {headers.get('Subject', 'Sin asunto')}\n"
                f"  Fecha: {headers.get('Date', 'N/A')}"
            )

        total = len(messages)
        shown = min(5, total)
        header = f"Emails no leidos: {total} total (mostrando {shown}):\n"
        return header + "\n".join(emails_info)

    except Exception as e:
        return f"Error obteniendo emails: {e}"


def get_today_calendar_events() -> str:
    """
    Obtiene los eventos del calendario de Google de hoy.

    Returns:
        Lista de eventos del dia con hora y titulo.
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
            return "No tienes eventos programados para hoy."

        eventos = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            # Simplificar formato de hora
            if 'T' in start:
                hora = start.split('T')[1][:5]  # HH:MM
            else:
                hora = "Todo el dia"
            titulo = event.get('summary', 'Sin titulo')
            location = event.get('location', '')
            location_str = f" @ {location}" if location else ""
            eventos.append(f"  {hora} - {titulo}{location_str}")

        today_str = now.strftime('%A %d de %B')
        return f"Eventos de hoy ({today_str}):\n" + "\n".join(eventos)

    except Exception as e:
        return f"Error obteniendo calendario: {e}"


def search_drive_files(query: str, max_results: int = 5) -> str:
    """
    Busca archivos en Google Drive.

    Args:
        query: Termino de busqueda (ej: "informe presupuesto 2024")
        max_results: Numero maximo de resultados (default: 5)

    Returns:
        Lista de archivos encontrados con nombre y enlace.
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
            return f"No se encontraron archivos para: '{query}'"

        files_info = []
        for f in files:
            modified = f.get('modifiedTime', 'N/A')[:10]
            file_type = f.get('mimeType', '').split('.')[-1]
            link = f.get('webViewLink', 'sin enlace')
            files_info.append(
                f"- {f['name']} ({file_type})\n"
                f"  Modificado: {modified}\n"
                f"  Enlace: {link}"
            )

        return f"Archivos encontrados ({len(files)}):\n" + "\n".join(files_info)

    except Exception as e:
        return f"Error buscando en Drive: {e}"
