import os
from functools import lru_cache

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build


@lru_cache(maxsize=1)
def get_drive_service(credentials: Credentials) -> Resource:
    return build("drive", "v3", credentials=credentials)


@lru_cache(maxsize=1)
def get_forms_service(credentials: Credentials) -> Resource:
    DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
    return build(
        "forms", "v1", credentials=credentials, discoveryServiceUrl=DISCOVERY_DOC
    )


def get_gapi_credentials(cred_file: str, token_store_file: str) -> Credentials:
    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = None
    if os.path.exists(token_store_file):
        creds = Credentials.from_authorized_user_file(token_store_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
            creds = flow.run_local_server()
        with open(token_store_file, "w") as token:
            token.write(creds.to_json())

    return creds
