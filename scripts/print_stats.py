import argparse
import json
from functools import partial
from typing import Optional

from cli_helpers import EnumAction, ParseStreamAction
from tqdm import tqdm

from src.forms.filtering import Granularity, get_filter_func
from src.forms.responses import get_num_responses
from src.forms.services import get_forms_service, get_gapi_credentials
from src.teachers_db import Speciality, Stream, TeacherDB, load_teachers_db


def print_stats(
    db_jsons: list[str],
    forms_json: str,
    secrets_file: str,
    token_file: str,
    granularity: Optional[Granularity],
    query: Optional[str | Speciality | Stream],
):
    creds = get_gapi_credentials(cred_file=secrets_file, token_store_file=token_file)
    forms_service = get_forms_service(creds)

    with open(forms_json, "r", encoding="utf-8") as file:
        forms_info = json.load(file)
        forms_granularity = forms_info["granularity"]
        forms_dict: dict[str, list[dict[str, str]]] = forms_info["forms"]

    db = load_teachers_db(db_jsons)

    if granularity:
        filter_func = get_filter_func(
            form_granularity=forms_granularity,
            requested_granularity=granularity,
            query=query,
            db=db,
        )
    for teacher_name, forms in tqdm(forms_dict.items()):
        num_responses = 0
        do_print = False

        if granularity:
            max_num_responses = get_max_student_for_granularity(
                granularity, query, db, teacher_name
            )
            for form in forms:
                if filter_func(teacher_name, form):
                    do_print = True
                    num_responses += get_num_responses(
                        form["form_id"], forms_service=forms_service
                    )
        elif teacher_name == query:
            do_print = True
            max_num_responses = db[teacher_name].num_students
            for form in forms:
                num_responses += get_num_responses(
                    form["form_id"], forms_service=forms_service
                )

        if do_print:
            print(
                teacher_name,
                f"{num_responses}/{max_num_responses}",
                num_responses / max_num_responses,
            )


def get_max_student_for_granularity(
    granularity: Granularity,
    query: Optional[str | Speciality | Stream],
    db: TeacherDB,
    teacher_name: str,
):
    teacher = db[teacher_name]
    match granularity:
        case Granularity.GROUP:
            max_num_responses = teacher.num_students_for_group(query)
        case Granularity.STREAM:
            max_num_responses = teacher.num_students_for_stream(query)
        case Granularity.SPECIALITY:
            max_num_responses = teacher.num_students_for_spec(query)
        case Granularity.FACULTY:
            max_num_responses = teacher.num_students

    return max_num_responses


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
        "--forms_json",
        type=str,
        required=True,
        help="Paths to json file with forms info",
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

    granularity_group = parser.add_mutually_exclusive_group(required=True)
    granularity_group.add_argument("--group", type=str)
    granularity_group.add_argument(
        "--speciality",
        type=Speciality,
        action=EnumAction,
    )
    granularity_group.add_argument(
        "--stream",
        action=ParseStreamAction,
    )
    granularity_group.add_argument("--faculty", action="store_true")
    granularity_group.add_argument("--name", type=str)

    args = parser.parse_args()

    print_func = partial(
        print_stats,
        db_jsons=args.teacher_data,
        forms_json=args.forms_json,
        secrets_file=args.secrets_file,
        token_file=args.token_file,
    )
    if args.group:
        print_func(
            granularity=Granularity.GROUP,
            query=args.group,
        )
    elif args.stream:
        print_func(
            granularity=Granularity.STREAM,
            query=args.stream,
        )
    elif args.speciality:
        print_func(
            granularity=Granularity.SPECIALITY,
            query=args.speciality,
        )
    elif args.faculty:
        print_func(
            granularity=Granularity.FACULTY,
            query=None,
        )
    else:
        print_func(
            granularity=None,
            query=args.name,
        )
