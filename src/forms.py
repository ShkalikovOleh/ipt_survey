import json

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from apiclient import discovery
from httplib2 import Http
from oauth2client import client, file, tools

from src.teachers_db import Role


def generate_form_for_teacher(
    teacher_name: str, template_id: str, parent_id: str, drive_service, form_service
) -> tuple[str, str]:
    copied_file = {"name": teacher_name, "parents": [parent_id]}
    copy_result = (
        drive_service.files()
        .copy(fileId=template_id, body=copied_file, supportsAllDrives=True)
        .execute()
    )

    form_id = copy_result["id"]
    NEW_TITLE_REQ = {
        "includeFormInResponse": True,
        "requests": [
            {
                "updateFormInfo": {
                    "info": {
                        "title": teacher_name,
                    },
                    "updateMask": "title",
                }
            }
        ],
    }
    form_upd_res = (
        form_service.forms().batchUpdate(formId=form_id, body=NEW_TITLE_REQ).execute()
    )

    return form_id, form_upd_res["form"]["responderUri"]


def generate_form_for_teachers(
    teacher2roles: dict[str, Role],
    templates: dict[Role, str],
    folder: str,
    drive_service,
    form_service,
) -> dict[dict[str, str]]:
    teacher2forms = {}
    for teacher_name, role in teacher2roles.items():
        template = templates[role]
        form_id, resp_url = generate_form_for_teacher(
            teacher_name, template, folder, drive_service, form_service
        )
        teacher2forms[teacher_name] = {"form_id": form_id, "responder_url": resp_url}
    return teacher2forms


def generate_forms_for_year_and_store_info_to_json(
    teachers: dict[str, Role],
    year: int,
    templates: dict[int, str],
    year2folder: dict[int, str],
    credentials,
):
    drive_service = build("drive", "v3", credentials=credentials)

    DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
    form_service = discovery.build(
        "forms",
        "v1",
        http=credentials.authorize(Http()),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

    forms = generate_form_for_teachers(
        teachers, templates, year2folder[year], drive_service, form_service
    )
    with open(f"forms_{year}year.json", "w", encoding="utf-8") as file:
        json.dump(forms, file, ensure_ascii=False)


def get_gapi_credentials(cred_file: str, token_store_file: str):
    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/drive",
    ]

    store = file.Storage(token_store_file)
    creds = store.get()
    if not creds or creds.invalid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            store.put(creds)
        else:
            flow = client.flow_from_clientsecrets(cred_file, SCOPES)
            creds = tools.run_flow(flow, store)
    return creds
