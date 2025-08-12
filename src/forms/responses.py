from collections.abc import Callable
from typing import Any, Optional

import pandas as pd
from googleapiclient.discovery import Resource

from src.forms.generation import get_form


def get_responses(form_id: str, forms_service: Resource) -> list[dict[str, Any]]:
    responses = forms_service.forms().responses().list(formId=form_id).execute()  # type: ignore
    if "responses" in responses:
        return responses["responses"]
    else:
        return []


def get_num_responses(form_id: str, forms_service: Resource) -> int:
    return len(get_responses(form_id, forms_service))


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

            question = id2q[qId]
            filled_columns.add(question)

            parser = question_parsers.get(question)
            if parser:
                data[question].append(parser(answer))
        for column in all_columns.difference(filled_columns):
            data[column].append(pd.NA)

    df = pd.DataFrame.from_dict(data)
    return df
