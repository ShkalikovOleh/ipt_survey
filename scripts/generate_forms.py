import argparse
import json
from collections import defaultdict
from typing import Optional

from pyparsing import Group
from tqdm import tqdm

from src.forms.generation import Granularity, adapt_form_from_template
from src.forms.publishing import give_access_to_organization, publish_form
from src.forms.services import (
    get_drive_service,
    get_forms_service,
    get_gapi_credentials,
)
from src.teachers_db import Speciality, Stream, TeacherDB, load_teachers_db
from src.utils.cli_helpers import EnumAction


def prepare_funcs(db: TeacherDB, granularity: Granularity):
    match granularity:
        case Granularity.GROUP:

            def options_func():
                return db.get_all_groups()

            def metadata_func(group: Group):
                return {"group": group.name}

            def filter_func(group: Group):
                return db.filter_by_group(group.name)
        case Granularity.STREAM:

            def options_func():
                return db.get_all_streams()

            def metadata_func(stream: Stream):
                return {"speciality": stream.speciality, "year": stream.year}

            def filter_func(stream: Stream):
                return db.filter_by_stream(stream)
        case Granularity.SPECIALITY:

            def options_func():
                return db.get_all_specialities()

            def metadata_func(spec: Speciality):
                return {"speciality": spec}

            def filter_func(spec: Speciality):
                return db.filter_by_speciality(spec)
        case Granularity.FACULTY:

            def options_func():
                return ["ФТІ"]

            def metadata_func(faculty: str) -> dict:
                return {"faculty": faculty}

            def filter_func(faculty: str):
                return db

    return options_func, filter_func, metadata_func


def generate_forms(
    teacher_jsons: list[str],
    template_id: str,
    dest_folder_id: str,
    granularity: Granularity,
    stats_granularity: Optional[Granularity],
    secrets_file: str,
    token_file: str,
    out_path: str,
):
    db = load_teachers_db(teacher_jsons)

    if stats_granularity:
        assert stats_granularity < granularity

    ops_func, filter_func, meta_func = prepare_funcs(db, granularity)

    creds = get_gapi_credentials(cred_file=secrets_file, token_store_file=token_file)
    forms_service = get_forms_service(creds)
    drive_serive = get_drive_service(creds)

    forms_dict: dict[str, list[dict[str, str]]] = defaultdict(lambda: [])
    options = list(ops_func())
    for option in tqdm(options):
        for teacher in tqdm(filter_func(option)):
            form_id, resp_url = adapt_form_from_template(
                teacher=teacher,
                forms_service=forms_service,
                drive_service=drive_serive,
                template_id=template_id,
                dest_folder_id=dest_folder_id,
                stats_granularity=stats_granularity,
            )
            publish_form(form_id=form_id, forms_service=forms_service)
            give_access_to_organization(form_id=form_id, drive_service=drive_serive)

            form_info = meta_func(option)
            form_info["form_id"] = form_id
            form_info["resp_url"] = resp_url
            forms_dict[teacher.name].append(form_info)

    with open(out_path, "w") as file:
        forms_info = {
            "granularity": granularity,
            "forms": forms_dict,
        }
        if stats_granularity:
            forms_info["stats_granularity"] = stats_granularity

        json.dump(
            forms_info,
            file,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--teacher_data",
        nargs="+",
        type=str,
        required=True,
        help="Paths to json files with teacher info",
    )
    parser.add_argument(
        "--template_id",
        type=str,
        required=True,
        help="Id of the universal template (take from url of the form)",
    )
    parser.add_argument(
        "--dest_folder_id",
        type=str,
        required=True,
        help="Id of the drive folder where to place generated forms",
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
    parser.add_argument(
        "--granularity",
        type=Granularity,
        action=EnumAction,
        default=Granularity.FACULTY,
        help="Specify the granularity level of forms",
    )
    parser.add_argument(
        "--stats_granularity",
        type=Granularity,
        action=EnumAction,
        required=False,
        help="Specify the granularity level of optional question for statistics",
    )
    parser.add_argument(
        "--out_path",
        type=str,
        required=True,
        help="Path to generated json file with links to forms",
    )

    args = parser.parse_args()

    generate_forms(
        teacher_jsons=args.teacher_data,
        template_id=args.template_id,
        dest_folder_id=args.dest_folder_id,
        granularity=args.granularity,
        stats_granularity=args.stats_granularity,
        secrets_file=args.secrets_file,
        token_file=args.token_file,
        out_path=args.out_path,
    )
