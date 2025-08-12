import pandas as pd
from pandas.api.typing import NAType


def parse_nan_grade(grade: str) -> int | NAType:
    try:
        return int(grade)
    except ValueError:
        return pd.NA


def parse_bool(answer: str, false_answer: str = "Ні") -> bool:
    if answer == false_answer:
        return False
    return True


def parse_str(answer: str) -> str | NAType:
    stripped_answer = answer.strip()
    if len(stripped_answer) > 0:
        return stripped_answer
    else:
        return pd.NA
