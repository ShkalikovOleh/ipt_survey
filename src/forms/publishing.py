from googleapiclient.discovery import Resource


def __change_publish_settings(
    form_id: str, forms_service: Resource, publish: bool, accept_responses: bool
) -> None:
    forms_service.forms().setPublishSettings(
        formId=form_id,
        body={
            "publishSettings": {
                "publishState": {
                    "isPublished": publish,
                    "isAcceptingResponses": accept_responses,
                }
            }
        },
    ).execute()


def publish_form(form_id: str, forms_service: Resource) -> None:
    __change_publish_settings(
        form_id, forms_service, publish=True, accept_responses=True
    )


def stop_accepting_responses(form_id: str, forms_service: Resource) -> None:
    __change_publish_settings(
        form_id, forms_service, publish=True, accept_responses=False
    )


def unpublish_form(form_id: str, forms_service: Resource) -> None:
    __change_publish_settings(
        form_id, forms_service, publish=False, accept_responses=False
    )


def give_access_to_organization(
    form_id: str, drive_service: Resource, domain: str = "lll.kpi.ua"
) -> None:
    new_permission = {
        "type": "domain",
        "role": "reader",
        "view": "published",
        "domain": domain,
    }

    drive_service.permissions().create(
        fileId=form_id,
        body=new_permission,
        supportsAllDrives=True,
    ).execute()
