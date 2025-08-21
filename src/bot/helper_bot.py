from itertools import batched
import json
import math
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from typing import Callable, Iterable, Optional

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
    form_gran_info_to_str,
    form_info_to_query,
    get_granularity_filter_func,
    get_max_student_for_granularity,
)
from src.forms.generation import Granularity
from src.forms.responses import get_num_responses
from src.forms.services import get_forms_service, get_gapi_credentials
from src.teachers_db import Speciality, Stream, TeacherDB, load_teachers_db

NO_FORMS_RESPONSE = "Жодної форми не знайдено"


async def get_group_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.GROUP,
        query=context.args[0],
    )
    await send_links(update, context, forms_info, forms_granularity, False)


async def get_stream_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    spec, year = context.args[0].split("-")
    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.STREAM,
        query=Stream(Speciality(spec), year),
    )
    await send_links(
        update,
        context,
        forms_info,
        forms_granularity,
        forms_granularity < Granularity.STREAM,
    )


async def get_speciality_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.SPECIALITY,
        query=Speciality(context.args[0]),
    )
    await send_links(
        update,
        context,
        forms_info,
        forms_granularity,
        forms_granularity < Granularity.SPECIALITY,
    )


async def get_all_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    forms_info = fitler_forms_info_by_granularity(
        db=teachers_db,
        forms_dict=forms_dict,
        forms_granularity=forms_granularity,
        requested_granularity=Granularity.FACULTY,
        query=None,
    )
    await send_links(
        update,
        context,
        forms_info,
        forms_granularity,
        forms_granularity != Granularity.FACULTY,
    )


async def send_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forms_info: Iterable[tuple[str, str]],
    forms_granulariry: Granularity,
    print_granularity_info: bool,
):
    if print_granularity_info:

        def gran_to_str(form_info: dict[str, str]) -> str:
            text = form_gran_info_to_str(form_info, forms_granulariry)
            return text + " "

    else:

        def gran_to_str(_) -> str:
            return ""

    message = "\n".join(
        [
            f"[{gran_to_str(form_info)}{teacher_name}]({form_info['resp_url']})"
            for teacher_name, form_info in forms_info
        ]
    )
    if message:
        await reply_text(update, context, message, parse_mode="Markdown")
    else:
        await reply_text(update, context, NO_FORMS_RESPONSE)


async def get_teacher_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]

    name = " ".join(context.args)
    messages = []
    for teacher_name, forms in forms_dict.items():
        if teacher_name == name:
            for form in forms:
                url = form["resp_url"]
                text = form_gran_info_to_str(form, forms_granularity)
                messages.append(f"[{text}]({url})")

    if messages:
        await reply_text(update, context, "\n".join(messages), parse_mode="Markdown")
    else:
        await reply_text(update, context, NO_FORMS_RESPONSE)


async def get_group_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    stats_granularity: Optional[Granularity] = context.bot_data["stats_granularity"]
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
        context,
        forms_dict,
        teachers_db,
        forms_service,
        query,
        granularity,
        forms_granularity,
        stats_granularity,
        filter_func,
    )


async def get_stream_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    stats_granularity: Optional[Granularity] = context.bot_data["stats_granularity"]
    forms_service: Resource = context.bot_data["forms_service"]

    spec, year = context.args[0].split("-")
    query = Stream(Speciality(spec), year)
    granularity = Granularity.STREAM
    filter_func = get_granularity_filter_func(
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
        forms_granularity,
        stats_granularity,
        filter_func,
    )


async def get_speciality_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    stats_granularity: Optional[Granularity] = context.bot_data["stats_granularity"]
    forms_service: Resource = context.bot_data["forms_service"]

    query = Speciality(context.args[0])
    granularity = Granularity.SPECIALITY
    filter_func = get_granularity_filter_func(
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
        forms_granularity,
        stats_granularity,
        filter_func,
    )


async def get_all_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    stats_granularity: Optional[Granularity] = context.bot_data["stats_granularity"]
    forms_service: Resource = context.bot_data["forms_service"]

    query = None
    granularity = Granularity.FACULTY
    filter_func = get_granularity_filter_func(
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
        forms_granularity,
        stats_granularity,
        filter_func,
    )


async def get_teacher_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    forms_dict: dict[str, list[dict[str, str]]] = context.bot_data["forms_dict"]
    teachers_db: TeacherDB = context.bot_data["teachers_db"]
    forms_granularity: Granularity = context.bot_data["forms_granularity"]
    stats_granularity: Optional[Granularity] = context.bot_data["stats_granularity"]
    forms_service: Resource = context.bot_data["forms_service"]

    name = " ".join(context.args)

    def filter_func(teacher_name: str, _) -> bool:
        return teacher_name == name

    await send_stats_for_granularity(
        update,
        context,
        forms_dict,
        teachers_db,
        forms_service,
        None,
        None,
        forms_granularity,
        stats_granularity,
        filter_func,
    )


async def send_stats_for_granularity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forms_dict: dict[str, list[dict[str, str]]],
    teachers_db: TeacherDB,
    forms_service: Resource,
    query: Optional[str | Speciality | Stream],
    req_granularity: Optional[Granularity],
    forms_granularity: Granularity,
    stats_granularity: Optional[Granularity],
    filter_func: Callable[[str, dict[str, str]], bool],
):
    messages = []
    for teacher_name, forms in forms_dict.items():
        num_responses = 0
        do_append = False

        nums_per_forms: dict[str, tuple[int, int]] = {}
        num_per_stats_entity: dict[str, int] = defaultdict(int)
        for form in forms:
            if filter_func(teacher_name, form):
                do_append = True

                total_num_resp, stats_resp = get_num_responses(
                    form["form_id"],
                    forms_service=forms_service,
                    stats_granularity=stats_granularity,
                )

                if (
                    req_granularity != forms_granularity
                    and forms_granularity != Granularity.FACULTY
                ):
                    entity = form_info_to_query(form, forms_granularity)
                    max_form_resp = get_max_student_for_granularity(
                        forms_granularity, entity, teachers_db, teacher_name
                    )
                    nums_per_forms[str(entity)] = (total_num_resp, max_form_resp)

                num_responses += total_num_resp
                for k, v in stats_resp.items():
                    num_per_stats_entity[k] += v

        if do_append:
            if req_granularity == forms_granularity:
                max_num_responses = get_max_student_for_granularity(
                    req_granularity, query, teachers_db, teacher_name
                )
                percent = math.floor(num_responses / max_num_responses * 100)

                if req_granularity == Granularity.FACULTY:
                    emoji = get_satisfy_emoji(num_responses, percent)
                else:
                    emoji = ""

                messages.append(
                    f"{emoji}{teacher_name} - {num_responses}/{max_num_responses} - {percent}%"
                )
            else:
                if req_granularity == Granularity.FACULTY:
                    max_num_responses = get_max_student_for_granularity(
                        req_granularity, None, teachers_db, teacher_name
                    )
                    percent = math.floor(num_responses / max_num_responses * 100)
                    emoji = get_satisfy_emoji(num_responses, percent)
                    messages.append(
                        f"{emoji}{teacher_name} - {num_responses} - {percent}%"
                    )
                else:
                    messages.append(f"{teacher_name} - {num_responses}")

                for entity_name, (n_curr, n_max) in nums_per_forms.items():
                    percent = math.floor(n_curr / n_max * 100)
                    messages.append(f"{entity_name} - {n_curr}/{n_max} - {percent}%")

            add_optional_stats_info(
                teachers_db,
                stats_granularity,
                messages,
                teacher_name,
                num_per_stats_entity,
            )
            messages.append("---------")

    if messages:
        await reply_text(update, context, "\n".join(messages))
    else:
        await reply_text(update, context, NO_FORMS_RESPONSE)


def get_satisfy_emoji(num_responses: int, percent: int):
    if num_responses < 5:
        emoji = "⛔️"
    elif percent >= 20:
        emoji = "✅"
    elif percent >= 15:
        emoji = "⚠️"
    else:
        emoji = "⛔️"
    return emoji


def add_optional_stats_info(
    teachers_db: TeacherDB,
    stats_granularity: Optional[Granularity],
    messages: list[str],
    teacher_name: str,
    num_per_stats_entity: dict[str, int],
):
    num_per_stats_entity = dict(sorted(num_per_stats_entity.items()))
    stats_messages = []
    for key, num in num_per_stats_entity.items():
        match stats_granularity:
            case Granularity.GROUP:
                stats_query = key
            case Granularity.STREAM:
                stats_query = Stream.from_str(key)
            case Granularity.SPECIALITY:
                stats_query = Speciality.from_str(key)

        if key != "Anonymous":
            num_max_gran = get_max_student_for_granularity(
                stats_granularity, stats_query, teachers_db, teacher_name
            )
            stats_messages.append(f"{key} - {num}/{num_max_gran}")
        else:
            stats_messages.append(f"{key} - {num}")
    if stats_messages:
        messages.append("\n".join(stats_messages))


async def reply_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    parse_mode: Optional[str] = None,
):
    for msg_batch in batched(message, 4096):
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=msg_batch,
            reply_to_message_id=update.message.id,
            parse_mode=parse_mode,
        )


def run_bot(
    token: str,
    teachers_db: TeacherDB,
    forms_service: Resource,
    forms_dict: dict[str, list[dict[str, str]]],
    forms_granularity: Granularity,
    stats_granularity: Optional[Granularity],
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
    application.bot_data["stats_granularity"] = stats_granularity
    application.bot_data["forms_service"] = forms_service

    # Links commands
    application.add_handler(CommandHandler("lgroup", get_group_links))
    application.add_handler(CommandHandler("lstream", get_stream_links))
    application.add_handler(CommandHandler("lspec", get_speciality_links))
    application.add_handler(CommandHandler("lall", get_all_links))
    application.add_handler(CommandHandler("lname", get_teacher_links))

    # Stats commands
    application.add_handler(CommandHandler("sgroup", get_group_stats))
    application.add_handler(CommandHandler("sstream", get_stream_stats))
    application.add_handler(CommandHandler("sspec", get_speciality_stats))
    application.add_handler(CommandHandler("sname", get_teacher_stats))
    application.add_handler(CommandHandler("sall", get_all_stats))

    application.run_polling()


def main(args: Namespace):
    with open(args.forms_json) as file:
        forms_info = json.load(file)
        forms_granularity = Granularity(forms_info["granularity"])
        forms_dict: dict[str, list[dict[str, str]]] = forms_info["forms"]
        stats_granularity = forms_info.get("stats_granularity")
        if stats_granularity:
            stats_granularity = Granularity(stats_granularity)

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
        stats_granularity=stats_granularity,
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
