import numpy as np
import pandas as pd


def build_question2item_id_map(id: str, form_service):
    cur_form = form_service.forms().get(formId=id).execute()

    def is_question(item) -> bool:
        return "questionItem" in item

    questions = filter(is_question, cur_form["items"])

    mapping = {
        item["title"]: item["questionItem"]["question"]["questionId"]
        for item in questions
    }
    return mapping


def response_json_to_pandas(
    responses,
    teacher_name: str,
    year: int,
    question2id: dict[str, str],
    column2parser: list[str],
) -> pd.DataFrame:
    data = {}
    N = len(responses["responses"])
    data["name"] = [teacher_name] * N
    data["year"] = [year] * N

    for column, parser in column2parser.items():
        qId = question2id.get(column)
        values = []
        if qId is not None:
            for response in responses["responses"]:
                answer = response["answers"].get(qId)
                if answer:
                    values.append(parser(answer["textAnswers"]["answers"][0]["value"]))
                else:
                    values.append(np.nan)
        else:
            values = [np.nan] * len(responses["responses"])

        data[column] = values

    df = pd.DataFrame.from_dict(data)
    return df
