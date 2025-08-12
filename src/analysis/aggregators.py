import numpy as np
import pandas as pd
from pandas.api.typing import NAType


def count_per_grade(grades: pd.Series, num_grades: int = 5):
    nums = [0] * num_grades
    for grade in grades:
        nums[grade - 1] += 1
    return nums


def mean_if_more_than_half(answers: pd.Series) -> np.floating | NAType:
    num_nan = np.sum(pd.isna(answers))
    if num_nan * 2 >= len(answers):
        return pd.NA
    else:
        return np.nanmean(answers)


def concat_text_answers(answers: pd.Series) -> list[str]:
    actual_answers = answers.dropna()
    return list(actual_answers)


def merge_two_text_columns(
    row: pd.Series, first_column: str, second_column: str
) -> NAType | tuple[str | NAType, str | NAType]:
    value_first = row[first_column]
    value_second = row[second_column]
    if pd.notna(value_first):
        if pd.notna(value_second):
            return (value_first, value_second)
        return (value_first, pd.NA)
    elif pd.notna(value_second):
        return (pd.NA, value_second)
    else:
        return pd.NA
