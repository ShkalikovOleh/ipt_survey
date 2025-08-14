import argparse
import json
from functools import partial
from typing import Optional

from cli_helpers import EnumAction, ParseStreamAction

from src.forms.filtering import Granularity, fitler_urls
from src.teachers_db import Speciality, Stream, load_teachers_db


def print_urls(
    db_jsons: list[str],
    forms_json: str,
    format: str,
    granularity: Granularity,
    query: Optional[str | Speciality | Stream],
):
    with open(forms_json, "r", encoding="utf-8") as file:
        forms_info = json.load(file)
        forms_granularity = forms_info["granularity"]
        forms_dict: dict[str, list[dict[str, str]]] = forms_info["forms"]

    db = load_teachers_db(db_jsons)

    for name, url in fitler_urls(
        forms_granularity=forms_granularity,
        requested_granularity=granularity,
        query=query,
        forms_dict=forms_dict,
        db=db,
    ):
        if format == "markdown":
            print(f"[{name}]({url})")
        elif format == "simple":
            print(name, url)


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
        "--format", type=str, choices=["markdown", "simple"], default="markdown"
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

    args = parser.parse_args()

    print_urls_func = partial(
        print_urls,
        db_jsons=args.teacher_data,
        forms_json=args.forms_json,
        format=args.format,
    )
    if args.group:
        print_urls_func(
            granularity=Granularity.GROUP,
            query=args.group,
        )
    elif args.stream:
        print_urls_func(
            granularity=Granularity.STREAM,
            query=args.stream,
        )
    elif args.speciality:
        print_urls_func(
            granularity=Granularity.SPECIALITY,
            query=args.speciality,
        )
    elif args.faculty:
        print_urls_func(
            granularity=Granularity.FACULTY,
            query=None,
        )
