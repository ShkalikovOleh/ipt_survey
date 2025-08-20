import json
import math
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from typing import Callable, Iterable

from googleapiclient.discovery import Resource
from telegram import Update
from telegram.ext import (
    AIORateLimiter,
    Application,
    # filters,
    CommandHandler,
    ContextTypes,
)

from src.forms.filtering import (
    fitler_forms_info_by_granularity,
    get_granularity_filter_func,
    get_max_student_for_granularity,
)
from src.forms.generation import Granularity
from src.forms.responses import get_num_responses, get_responses
from src.forms.services import get_forms_service, get_gapi_credentials
from src.teachers_db import Speciality, Stream, TeacherDB, load_teachers_db

NO_FORMS_RESPONSE = "Жодної форми не знайдено"


async def get_group_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.GROUP,
        query=context.args[0],
    )
    await send_links(update, forms_info)


async def get_stream_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    spec, year = context.args[0].split("-")
    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.STREAM,
        query=Stream(Speciality(spec), year),
    )
    await send_links(update, forms_info)


async def get_speciality_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.SPECIALITY,
        query=Speciality(context.args[0]),
    )
    await send_links(update, forms_info)


async def get_all_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.FACULTY,
        query=None,
    )
    await send_links(update, forms_info)


async def send_links(update: Update, forms_info: Iterable[tuple[str, str]]):
    message = "\n".join(
        [
            f"[{teacher_name}]({form_info['resp_url']})"
            for teacher_name, form_info in forms_info
        ]
    )
    if message:
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(NO_FORMS_RESPONSE)


async def get_teacher_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

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
                        stream = Stream(Speciality(form["speciality"]), form["year"])
                        messages.append(f"[{stream}]({url})")
                    case Granularity.SPECIALITY:
                        spec = Speciality(form["speciality"])
                        messages.append(f"[{spec}]({url})")
                    case Granularity.FACULTY:
                        messages.append(f"[ФТІ]({url})")

    if messages:
        await update.message.reply_text("\n".join(messages), parse_mode="Markdown")
    else:
        await update.message.reply_text(NO_FORMS_RESPONSE)


async def get_group_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    forms_service: Resource = context.bot_data["forms_service"]

    query = context.args[0]
    granularity = Granularity.GROUP
    filter_func = get_granularity_filter_func(
        form_granularity=forms_granularity,
        requested_granularity=granularity,
        query=query,
        db=teachers_db,
    )
    await send_stats_for_granularity(
        update,
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
):
    forms_dict: dict[str, list[str, str]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    forms_service: Resource = context.bot_data["forms_service"]

    query = context.args[0]
    granularity = Granularity.SPECIALITY
    filter_func = get_granularity_filter_func(
        form_granularity=forms_granularity,
        requested_granularity=granularity,
        query=query,
        db=teachers_db,
    )
    await send_stats_for_granularity(
        update,
        forms_dict,
        teachers_db,
        forms_service,
        query,
        granularity,
        filter_func,
    )


async def send_stats_for_granularity(
    update: Update,
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
                get_responses(form_id=form["form_id"], forms_service=forms_service)
                num_responses += get_num_responses(
                    form["form_id"], forms_service=forms_service
                )

        if do_append:
            percent = math.floor(num_responses / max_num_responses * 100)
            messages.append(
                f"{teacher_name} - {num_responses}/{max_num_responses} - {percent}%"
            )

    if messages:
        await update.message.reply_text("\n".join(messages))
    else:
        await update.message.reply_text(NO_FORMS_RESPONSE)


def run_bot(
    token: str,
    teachers_db: TeacherDB,
    forms_service: Resource,
    forms_dict: dict[str, list[str, str]],
    forms_granularity: Granularity,
):
    rate_limiter = AIORateLimiter()
    application = (
        Application.builder()
        .read_timeout(30)
        .rate_limiter(rate_limiter)
        .token(token)
        .build()
    )
    application.bot_data["forms_dict"] = forms_dict
    application.bot_data["teachers_db"] = teachers_db
    application.bot_data["forms_granularity"] = forms_granularity
    application.bot_data["forms_service"] = forms_service

    # Links commands
    application.add_handler(CommandHandler("lgroup", get_group_links))
    application.add_handler(CommandHandler("lstream", get_stream_links))
    application.add_handler(CommandHandler("lspec", get_speciality_links))
    application.add_handler(CommandHandler("lall", get_all_links))
    application.add_handler(CommandHandler("lname", get_teacher_links))

    # Stats commands
    application.add_handler(CommandHandler("sgroup", get_group_stats))
    application.add_handler(CommandHandler("sspec", get_speciality_stats))

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
