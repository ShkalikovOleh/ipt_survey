from argparse import ArgumentParser, Namespace
import json
import dateutil.parser
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes, Application, MessageHandler, filters
import datetime
import dateutil
import time


from src.teachers_db import Course, add_to_db, parse_teacher_json


async def post_next_teacher_results(
    context: ContextTypes.DEFAULT_TYPE,
    channel_id: str,
    viz_folder: str,
    teachers_db: dict[str, dict[str, Course]],
    min_working_hour: int,
    max_working_hour: int,
):
    teacher_name = "Завадська Людмила Олексіївна"
    caption = f"{teacher_name}\n fdas"

    await context.bot.send_photo(
        chat_id=channel_id,
        photo=f"{viz_folder}/{teacher_name}.png",
        caption=caption,
        parse_mode="html",
    )


async def add_comments(
    update: Update, context: ContextTypes.DEFAULT_TYPE, df_results: pd.DataFrame
):
    name = update.message.caption.splitlines()[0]
    if name in df_results.index:
        data = df_results.loc[name]

        columns = [
            "Які позитивні риси є у викладача (такі, що можна порекомендувати іншим викладачам)?",
            "Поради для студентів. Що краще робити (чи навпаки, не робити) для побудови гарних відносин із викладачем, які характерні особливості є у викладача, про які ви вважаєте варто знати тим, хто буде у нього вчитись?",
            "Відкритий мікрофон. Усе, що ви хочете сказати про викладача, але що не покрив жоден інший пункт",
        ]

        for col in columns[:1]:
            await post_comment(update, context, data, col)

        for answer in data["drawbacks_merged"]:
            critic, sugg = answer

            if isinstance(critic, str):
                comment = (
                    "<blockquote>Які недоліки є у викладанні?</blockquote>\n"
                    + critic
                    + "\n\n"
                )
            else:
                comment = ""
            if isinstance(sugg, str):
                comment += (
                    "<blockquote>Які шляхи їх вирішення ви бачите?</blockquote>\n"
                    + sugg
                )

            time.sleep(4)
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=comment,
                reply_to_message_id=update.message.id,
                parse_mode="html",
            )

        for col in columns[1:]:
            await post_comment(update, context, data, col)


async def post_comment(update, context, data, col):
    for answer in data[col]:
        comment = f"<blockquote>{col}</blockquote>\n" + answer

        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=comment,
            reply_to_message_id=update.message.id,
            parse_mode="html",
        )
        time.sleep(4)  # No more than 20 message per minute


def run_bot(
    token: str,
    channel_id: str,
    teachers_db: dict[str, dict[str, Course]],
    df: pd.DataFrame,
    viz_folder: str,
    start_time: datetime.datetime,
    interval_min: int,
    min_working_hour: int,
    max_working_hour: int,
):
    application = (
        Application.builder().read_timeout(120).write_timeout(120).token(token).build()
    )
    job_queue = application.job_queue

    async def post_func(context):
        return await post_next_teacher_results(
            context,
            channel_id=channel_id,
            viz_folder=viz_folder,
            teachers_db=teachers_db,
            min_working_hour=min_working_hour,
            max_working_hour=max_working_hour,
        )

    async def comment_func(update, context):
        return await add_comments(update, context, df)

    timezone = start_time.tzinfo
    now = datetime.datetime.now(timezone)
    if now > start_time:
        first = 5
    else:
        first = int((start_time - now).total_seconds())

    job_queue.run_repeating(post_func, interval=interval_min * 60, first=first)

    channel_post_handler = MessageHandler(
        filters.User(777000),  # TG_ID
        comment_func,
    )
    application.add_handler(channel_post_handler)

    application.run_polling()


def load_teachers_db(files: list[str]):
    teacher_db = {}
    for path in files:
        _, _, data = parse_teacher_json(path)
        add_to_db(teacher_db, data)

    return teacher_db


def main(args: Namespace):
    with open(args.cfg_file) as cfg_file:
        cfg = json.load(cfg_file)

    start_time = dateutil.parser.parse(cfg["start_time"])

    df = pd.read_feather(cfg["survey_results"])
    teachers_db = load_teachers_db(cfg["teachers_info_files"])

    run_bot(
        cfg["TG_TOKEN"],
        cfg["channel_id"],
        teachers_db,
        df,
        cfg["viz_folder"],
        start_time,
        cfg["interval_min"],
        cfg["working_hours"]["min"],
        cfg["working_hours"]["max"],
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("cfg_file", type=str)

    args = parser.parse_args()
    main(args)
