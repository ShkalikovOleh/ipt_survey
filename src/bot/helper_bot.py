import json
from argparse import ArgumentParser, Namespace
from functools import partial
import math
from typing import Callable, Iterable

from googleapiclient.discovery import Resource
from telegram import Update
from telegram.ext import (
    Application,
    # filters,
    CommandHandler,
    ContextTypes,
)

from src.forms.filtering import (
    Granularity,
    fitler_urls,
    get_filter_func,
    get_max_student_for_granularity,
)
from src.forms.responses import get_num_responses
from src.forms.services import get_forms_service, get_gapi_credentials
from src.teachers_db import Speciality, Stream, TeacherDB, load_teachers_db


async def get_group_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    teachers_db: TeacherDB,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    links = fitler_urls(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.GROUP,
        query=context.args[0],
    )
    await send_links(update, context, links)


async def get_stream_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    teachers_db: TeacherDB,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    spec, year = context.args[0].split("-")
    links = fitler_urls(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.STREAM,
        query=Stream(Speciality(spec), year),
    )
    await send_links(update, context, links)


async def get_speciality_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    teachers_db: TeacherDB,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    links = fitler_urls(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.SPECIALITY,
        query=Speciality(context.args[0]),
    )
    await send_links(update, context, links)


async def get_all_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    teachers_db: TeacherDB,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    links = fitler_urls(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.FACULTY,
        query=None,
    )
    await send_links(update, context, links)


async def get_teacher_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    name = " ".join(context.args)
    messages = []
    for teacher_name, forms in forms_dict.items():
        if teacher_name == name:
            for form in forms:
                url = form["resp_url"]
                match forms_granularity:
                    case Granularity.GROUP:
                        messages.append(f"[{form['group']}]({url})")
                    case Granularity.STREAM:
                        messages.append(
                            f"[{form['speciality']}\-{form['year']}]({url})"
                        )
                    case Granularity.SPECIALITY:
                        messages.append(f"[{form['speciality']}]({url})")
                    case Granularity.FACULTY:
                        messages.append(f"[ФТІ]({url})")

    if messages:
        await send_message(
            update, context, "\n".join(messages), parse_mode="MarkdownV2"
        )
    else:
        await send_message(update, context, "No links for this teacher")


async def get_group_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forms_dict: dict[str, list[str, str]],
    teachers_db: TeacherDB,
    forms_granularity: Granularity,
    forms_service: Resource,
):
    query = context.args[0]
    granularity = Granularity.GROUP
    filter_func = get_filter_func(
        form_granularity=forms_granularity,
        requested_granularity=granularity,
        query=query,
        db=teachers_db,
    )
    await send_stats_for_granularity(
        update,
        context,
        forms_dict,
        teachers_db,
        forms_service,
        query,
        granularity,
        filter_func,
    )


async def get_speciality_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forms_dict: dict[str, list[str, str]],
    teachers_db: TeacherDB,
    forms_granularity: Granularity,
    forms_service: Resource,
):
    query = context.args[0]
    granularity = Granularity.SPECIALITY
    filter_func = get_filter_func(
        form_granularity=forms_granularity,
        requested_granularity=granularity,
        query=query,
        db=teachers_db,
    )
    await send_stats_for_granularity(
        update,
        context,
        forms_dict,
        teachers_db,
        forms_service,
        query,
        granularity,
        filter_func,
    )


async def send_stats_for_granularity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forms_dict: dict[str, list[str, str]],
    teachers_db: TeacherDB,
    forms_service: Resource,
    query: str | Speciality | Stream,
    granularity: Granularity,
    filter_func: Callable,
):
    messages = []
    for teacher_name, forms in forms_dict.items():
        num_responses = 0
        do_append = False

        max_num_responses = get_max_student_for_granularity(
            granularity, query, teachers_db, teacher_name
        )
        for form in forms:
            if filter_func(teacher_name, form):
                do_append = True
                num_responses += get_num_responses(
                    form["form_id"], forms_service=forms_service
                )

        if do_append:
            percent = math.floor(num_responses / max_num_responses * 100)
            messages.append(
                f"{teacher_name} - {num_responses}/{max_num_responses} - {percent}%"
            )

    if messages:
        await send_message(update, context, "\n".join(messages))
    else:
        await send_message(update, context, "No forms for this query")


async def send_links(
    update: Update, context: ContextTypes.DEFAULT_TYPE, links: Iterable[tuple[str, str]]
):
    message = "\n".join([f"[{teacher_name}]({link})" for teacher_name, link in links])
    if message:
        await send_message(update, context, message, parse_mode="MarkdownV2")
    else:
        await send_message(update, context, "No links for this query")


async def send_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    parse_mode: str = "html",
):
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=message,
        reply_to_message_id=update.message.id,
        parse_mode=parse_mode,
    )


LinkCallable = Callable[
    [
        Update,
        ContextTypes.DEFAULT_TYPE,
        TeacherDB,
        dict[str, list[str, str]],
        Granularity,
    ],
    None,
]


def create_links_command(
    name: str,
    func: LinkCallable,
    teachers_db: TeacherDB,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
) -> CommandHandler:
    callback_func = partial(
        func,
        teachers_db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
    )
    return CommandHandler(
        name,
        callback=callback_func,
        # filters=filters.User(username="ShkalikovOleh"),
    )


def create_stats_command(
    name: str,
    func: LinkCallable,
    teachers_db: TeacherDB,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
    forms_service: Resource,
) -> CommandHandler:
    callback_func = partial(
        func,
        teachers_db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        forms_service=forms_service,
    )
    return CommandHandler(
        name,
        callback=callback_func,
        # filters=filters.User(username="ShkalikovOleh"),
    )


def run_bot(
    token: str,
    teachers_db: TeacherDB,
    forms_service: Resource,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    application = (
        Application.builder().read_timeout(120).write_timeout(120).token(token).build()
    )

    # Links commands
    application.add_handler(
        create_links_command(
            "lgroup",
            get_group_links,
            teachers_db=teachers_db,
            forms_dict=forms_dict,
            forms_granularity=forms_granularity,
        )
    )
    application.add_handler(
        create_links_command(
            "lstream",
            get_stream_links,
            teachers_db=teachers_db,
            forms_dict=forms_dict,
            forms_granularity=forms_granularity,
        )
    )
    application.add_handler(
        create_links_command(
            "lspec",
            get_speciality_links,
            teachers_db=teachers_db,
            forms_dict=forms_dict,
            forms_granularity=forms_granularity,
        )
    )
    application.add_handler(
        create_links_command(
            "lall",
            get_all_links,
            teachers_db=teachers_db,
            forms_dict=forms_dict,
            forms_granularity=forms_granularity,
        )
    )
    application.add_handler(
        CommandHandler(
            "lname",
            callback=partial(
                get_teacher_links,
                forms_dict=forms_dict,
                forms_granularity=forms_granularity,
            ),
        )
    )

    # Stats commands
    application.add_handler(
        create_stats_command(
            "sgroup",
            get_group_stats,
            teachers_db=teachers_db,
            forms_dict=forms_dict,
            forms_granularity=forms_granularity,
            forms_service=forms_service,
        )
    )
    application.add_handler(
        create_stats_command(
            "sspec",
            get_speciality_stats,
            teachers_db=teachers_db,
            forms_dict=forms_dict,
            forms_granularity=forms_granularity,
            forms_service=forms_service,
        )
    )

    application.run_polling()


def main(args: Namespace):
    with open(args.forms_json) as file:
        forms_info = json.load(file)
        forms_granularity = forms_info["granularity"]
        forms_dict: dict[str, list[dict[str, str]]] = forms_info["forms"]

    teachers_db = load_teachers_db(args.teacher_data)

    creds = get_gapi_credentials(
        cred_file=args.secrets_file, token_store_file=args.token_file
    )
    forms_service = get_forms_service(creds)

    run_bot(
        token=args.token,
        teachers_db=teachers_db,
        forms_service=forms_service,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
    )


if __name__ == "__main__":
    parser = ArgumentParser()
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
    parser.add_argument(
        "--token",
        type=str,
        required=True,
        help="TG Token",
    )

    args = parser.parse_args()
    main(args)
