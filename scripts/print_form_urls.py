import argparse
import json
from typing import Optional

from cli_helpers import EnumAction, ParseStreamAction
from tqdm import tqdm

from src.forms.generation import Granularity
from src.teachers_db import Speciality


def get_filter_func(
    granularity: Granularity, query: Optional[str | Speciality | tuple[Speciality, str]]
):
    match granularity:
        case Granularity.GROUP:

            def filter_func(form_info):
                return form_info["group"] == query
        case Granularity.STREAM:

            def filter_func(form_info):
                return (
                    form_info["speciality"] == query[0]
                    and form_info["year"] == query[1]
                )
        case Granularity.SPECIALITY:

            def filter_func(form_info):
                return form_info["speciality"] == query
        case Granularity.FACULTY:

            def filter_func(form_info):
                return True

    return filter_func


def fitler_urls(
    forms_json: str,
    granularity: Granularity,
    query: Optional[str | Speciality | tuple[Speciality, str]],
):
    with open(forms_json, "r", encoding="utf-8") as file:
        forms_dict: dict[str, list[dict[str, str]]] = json.load(file)["forms"]

    filter_func = get_filter_func(granularity, query)
    for teacher_name, forms in tqdm(forms_dict.items()):
        for form in forms:
            if filter_func(form):
                yield (teacher_name, form["resp_url"])


def print_urls(
    forms_json: str,
    format: str,
    granularity: Granularity,
    query: Optional[str | Speciality | tuple[Speciality, str]],
):
    for name, url in fitler_urls(forms_json, granularity, query):
        if format == "markdown":
            print(f"[{name}]({url})")
        elif format == "simple":
            print(name, url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--forms_json",
        type=str,
        required=True,
        help="Paths to json files with forms info",
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

    if args.group:
        print_urls(
            forms_json=args.forms_json,
            format=args.format,
            granularity=Granularity.GROUP,
            query=args.group,
        )
    elif args.stream:
        print_urls(
            forms_json=args.forms_json,
            format=args.format,
            granularity=Granularity.STREAM,
            query=args.stream,
        )
    elif args.speciality:
        print_urls(
            forms_json=args.forms_json,
            format=args.format,
            granularity=Granularity.SPECIALITY,
            query=args.speciality,
        )
    elif args.faculty:
        print_urls(
            forms_json=args.forms_json,
            format=args.format,
            granularity=Granularity.FACULTY,
            query=None,
        )
