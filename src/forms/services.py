import os
from functools import lru_cache, wraps
import random
import time

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError


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
        run_flow = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                run_flow = True
        else:
            run_flow = True

        if run_flow:
            flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
            creds = flow.run_local_server()
        with open(token_store_file, "w") as token:
            token.write(creds.to_json())

    return creds


def retry_google_api(
    *,
    retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_statuses: tuple[int, ...] = (429, 500, 503),
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except HttpError as e:
                    status = getattr(e.resp, "status", None)

                    if status not in retry_statuses:
                        raise

                    if attempt == retries - 1:
                        raise

                    delay = min(
                        max_delay,
                        base_delay * (2**attempt),
                    )
                    delay *= random.uniform(0.5, 1.5)

                    time.sleep(delay)

        return wrapper

    return decorator
