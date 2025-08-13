import argparse
import json

from tqdm import tqdm

from src.forms.publishing import stop_accepting_responses
from src.forms.services import (
    get_forms_service,
    get_gapi_credentials,
)


def stop_accepting(
    forms_json: str,
    secrets_file: str,
    token_file: str,
):
    creds = get_gapi_credentials(cred_file=secrets_file, token_store_file=token_file)
    forms_service = get_forms_service(creds)

    with open(forms_json, "r", encoding="utf-8") as file:
        forms_dict: dict[str, list[dict[str, str]]] = json.load(file)["forms"]

    for _, forms in tqdm(forms_dict.items()):
        for form in forms:
            stop_accepting_responses(
                form_id=form["form_id"], forms_service=forms_service
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--forms_json",
        type=str,
        required=True,
        help="Paths to json files with forms info",
    )
    parser.add_argument(
        "--secrets_file",
        type=str,
        required=True,
        help="Path to the Google API secrets",
    )
    parser.add_argument(
        "--token_file",
        type=str,
        required=True,
        help="Where to save/reuse access token",
    )

    args = parser.parse_args()

    stop_accepting(
        forms_json=args.forms_json,
        secrets_file=args.secrets_file,
        token_file=args.token_file,
    )
