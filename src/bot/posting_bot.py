import datetime
import json
import os
import time
from argparse import ArgumentParser, Namespace
from collections.abc import Generator, Iterable, Mapping
from typing import Optional, TypeVar

import dateutil
import dateutil.parser
import pandas as pd
import pytz
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
    AIORateLimiter,
)

from src.teachers_db import TeacherDB, load_teachers_db

T = TypeVar("T")


def batched(iterable: Iterable[T], n) -> Generator[T]:
    current_batch = []
    for item in iterable:
        current_batch.append(item)
        if len(current_batch) == n:
            yield current_batch
            current_batch = []
    if current_batch:
        yield current_batch


class PersistentState:
    def __init__(
        self,
        min_working_hour: int,
        max_working_hour: int,
    ) -> None:
        self.curr_pos_file = "pers_state.json"
        self.min_working_hour = min_working_hour
        self.max_working_hour = max_working_hour

    @property
    def publication_allowed(self) -> bool:
        tmzinfo = pytz.timezone("Europe/Kyiv")
        curr_hour = datetime.datetime.now(tmzinfo).hour
        return curr_hour < self.min_working_hour or curr_hour >= self.max_working_hour

    @property
    def idx(self) -> int:
        if os.path.exists(self.curr_pos_file):
            with open(self.curr_pos_file, "r") as pers_state_file:
                return json.load(pers_state_file)["curr_pos"]
        else:
            return 0

    @idx.setter
    def idx(self, value: int) -> None:
        with open(self.curr_pos_file, "w") as pers_state_file:
            json.dump({"curr_pos": value}, pers_state_file)


async def post_next_teacher_results(
    context: ContextTypes.DEFAULT_TYPE,
    channel_id: str,
    viz_folder: str,
    teachers_db: TeacherDB,
    order_of_publication: list[str],
    persistent_state: PersistentState,
):
    curr_pos = persistent_state.idx
    if not persistent_state.publication_allowed or curr_pos >= len(
        order_of_publication
    ):
        return

    teacher_name = order_of_publication[curr_pos]
    teacher = teachers_db[teacher_name]

    caption = f"{teacher.name}\n"
    marks = "🔹🔸"
    for idx, course in enumerate(teacher.courses):
        mark = marks[idx % 2]
        caption += f"\n{mark} {course.name} - {course.overall_role}"

    await context.bot.send_photo(
        chat_id=channel_id,
        photo=f"{viz_folder}/{teacher.name}.png",
        caption=caption,
        parse_mode="html",
    )

    persistent_state.idx = curr_pos + 1


async def add_comments(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    df_results: pd.DataFrame,
    n_batch: int,
    col2desc: dict[str, list[str] | str],
    col2emoji: dict[str, list[str] | str],
    prev_surveys_links: Optional[dict[str, list[dict[str, str]]]] = None,
):
    name = update.message.caption.splitlines()[0]
    if name in df_results.index:
        data = df_results.loc[name]
        for col, desc in col2desc.items():
            if isinstance(desc, str):
                await add_comments_batch(
                    update, context, data, col, n_batch, col2desc, col2emoji
                )
            else:
                await add_paired_comments_batch(
                    update, context, data, col, n_batch, col2desc, col2emoji
                )

        if prev_surveys_links:
            await add_prev_links(update, context, prev_surveys_links, name)


async def add_prev_links(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prev_surveys_links: dict[str, list[dict[str, str]]],
    name: str,
):
    links_messages = ["Посилання на минулі опитування:\n"]
    for links_info in prev_surveys_links.get(name, []):
        links_messages.append(
            f"🔻 [{links_info['channel_name']} \\- {links_info['semester']}]({links_info['link']})"
        )

    if len(links_messages) > 1:
        await post_comment(
            update, context, "\n".join(links_messages), parse_mode="MarkdownV2"
        )


async def add_paired_comments_batch(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    data: Mapping[str, str],
    column: str,
    n_batch: int,
    col2desc: dict[str, list[str] | str],
    col2emoji: dict[str, list[str] | str],
):
    for answers in batched(data[column], n_batch):
        comment = (
            f"<blockquote>{col2desc[column][0]}</blockquote>\n"
            f"<blockquote>{col2desc[column][1]}</blockquote>\n"
        )
        for answer in answers:
            ans0, ans1 = answer

            comment += "\n"
            if isinstance(ans0, str):
                comment += f"{col2emoji[column][0]} {ans0}\n"
            if isinstance(ans1, str):
                comment += f"{col2emoji[column][1]} {ans1}\n"

        await post_comment(update, context, comment)


async def add_comments_batch(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    data: Mapping[str, str],
    column: str,
    n_batch: int,
    col2desc: dict[str, list[str] | str],
    col2emoji: dict[str, list[str] | str],
):
    for answers in batched(data[column], n_batch):
        comment = f"<blockquote>{col2desc[column]}</blockquote>"
        for answer in answers:
            comment += f"\n\n{col2emoji[column]} {answer}"
        await post_comment(update, context, comment)


async def post_comment(
    update: Update, context: ContextTypes.DEFAULT_TYPE, comment: str, parse_mode="html"
):
    await update.message.reply_text(text=comment, parse_mode=parse_mode)
    # time.sleep(4)  # No more than 20 message per minute


def run_bot(
    token: str,
    channel_id: str,
    teachers_db: TeacherDB,
    df: pd.DataFrame,
    viz_folder: str,
    start_time: datetime.datetime,
    interval_min: int,
    order_of_publication: list[str],
    n_batch: int,
    col2desc: dict[str, list[str] | str],
    col2emoji: dict[str, list[str] | str],
    persistent_state: PersistentState,
    prev_surveys_links: Optional[dict[str, list[dict[str, str]]]] = None,
):
    rate_limiter = AIORateLimiter(max_retries=10)
    application = (
        Application.builder()
        .read_timeout(120)
        .write_timeout(120)
        .rate_limiter(rate_limiter)
        .token(token)
        .build()
    )

    # Schedule posting every interval_min
    async def post_func(context):
        return await post_next_teacher_results(
            context,
            channel_id=channel_id,
            viz_folder=viz_folder,
            teachers_db=teachers_db,
            order_of_publication=order_of_publication,
            persistent_state=persistent_state,
        )

    job_queue = application.job_queue
    schedule_posting(start_time, interval_min, job_queue, post_func)

    # Add comments to new posts
    async def comment_func(update, context):
        return await add_comments(
            update,
            context,
            df_results=df,
            n_batch=n_batch,
            col2desc=col2desc,
            col2emoji=col2emoji,
            prev_surveys_links=prev_surveys_links,
        )

    channel_post_handler = MessageHandler(
        filters.User(777000) & filters.Caption(),  # TG_ID
        comment_func,
    )
    application.add_handler(channel_post_handler)

    # Start listening
    application.run_polling()


def schedule_posting(start_time, interval_min: int, job_queue, post_func):
    timezone = start_time.tzinfo
    now = datetime.datetime.now(timezone)
    if now > start_time:
        first = 5
    else:
        first = int((start_time - now).total_seconds())
    job_queue.run_repeating(post_func, interval=interval_min * 60, first=first)


def main(args: Namespace):
    with open(args.cfg_file) as cfg_file:
        cfg = json.load(cfg_file)

    df = pd.read_feather(cfg["survey_results"])
    teachers_db = load_teachers_db(cfg["teachers_info_files"])

    if "prev_surveys_links" in cfg:
        with open(cfg["prev_surveys_links"]) as file:
            prev_surveys_links = json.load(file)
    else:
        prev_surveys_links = None

    run_bot(
        token=cfg["TG_TOKEN"],
        channel_id=cfg["channel_id"],
        teachers_db=teachers_db,
        df=df,
        viz_folder=cfg["viz_folder"],
        start_time=dateutil.parser.parse(cfg["start_time"]),
        interval_min=cfg["interval_min"],
        order_of_publication=cfg.get("order_of_publication", df.index.to_list()),
        n_batch=cfg["n_batch"],
        col2desc=cfg["col2desc"],
        col2emoji=cfg["col2emoji"],
        persistent_state=PersistentState(
            cfg["working_hours"]["min"], cfg["working_hours"]["max"]
        ),
        prev_surveys_links=prev_surveys_links,
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("cfg_file", type=str)

    args = parser.parse_args()
    main(args)
