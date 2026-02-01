from collections import defaultdict
from collections.abc import Callable
from typing import Any, Optional

import pandas as pd
from googleapiclient.discovery import Resource

from src.forms.generation import (
    Granularity,
    get_form,
    get_stats_question,
    get_stats_question_options,
)
from src.forms.services import retry_google_api
from src.teachers_db import Teacher


@retry_google_api()
def get_responses(form_id: str, forms_service: Resource) -> list[dict[str, Any]]:
    responses = forms_service.forms().responses().list(formId=form_id).execute()  # type: ignore
    if "responses" in responses:
        return responses["responses"]
    else:
        return []


def get_num_responses(
    form_id: str,
    forms_service: Resource,
    stats_granularity: Optional[Granularity] = None,
    teacher: Optional[Teacher] = None,
) -> tuple[int, dict[str, int]]:
    responses = get_responses(form_id, forms_service)

    total_num_resp = len(responses)
    num_gran_resp = defaultdict(lambda: 0)

    if stats_granularity:
        stats_question = get_stats_question(stats_granularity)
        id2q = build_id_to_question_map(form_id, forms_service)
        options = get_stats_question_options(teacher, stats_granularity)
        for opt in options:
            num_gran_resp[opt["value"]] = 0

        for response in responses:
            if stats_granularity < Granularity.FACULTY and len(options) == 1:
                key = options[0]["value"]
            else:
                key = "Anonymous"

            for qId, answer_item in response["answers"].items():
                question = id2q[qId]
                if question == stats_question:
                    key = answer_item["textAnswers"]["answers"][0]["value"]

            num_gran_resp[key] += 1

    return total_num_resp, num_gran_resp


def build_id_to_question_map(form_id: str, forms_service: Resource) -> dict[str, str]:
    cur_form = get_form(forms_service, form_id)

    def is_question(item) -> bool:
        return "questionItem" in item

    questions = filter(is_question, cur_form["items"])

    mapping = {
        item["questionItem"]["question"]["questionId"]: item["title"]
        for item in questions
    }
    return mapping


def gather_responses_to_pandas(
    form_id: str,
    forms_service: Resource,
    question_parsers: dict[str, Callable[[str], Any]],
) -> pd.DataFrame:
    data = {q: [] for q in question_parsers}

    all_columns = set(question_parsers)
    id2q = build_id_to_question_map(form_id, forms_service)

    responses = get_responses(form_id, forms_service)
    for response in responses:
        filled_columns = set()
        for qId, answer_item in response["answers"].items():
            answer = answer_item["textAnswers"]["answers"][0]["value"]

            question = id2q.get(qId)
            if not question:
                continue

            parser = question_parsers.get(question)
            if parser:
                filled_columns.add(question)
                data[question].append(parser(answer))
        for column in all_columns.difference(filled_columns):
            data[column].append(pd.NA)

    df = pd.DataFrame.from_dict(data)

    return df
