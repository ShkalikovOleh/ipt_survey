import re

import pandas as pd
from pandas.api.typing import NAType


def num_responses_filter(
    num_responses: int,
    num_respondents: int,
    min_fraction: float = 0.2,
    min_responses: int = 5,
) -> bool:
    if num_responses < min_responses:
        return False
    fraction = num_responses / num_respondents
    if fraction < min_fraction:
        return False
    return True


def filter_swear_language(answer: str | NAType, swear_words: set[str]) -> str | NAType:
    if pd.isna(answer):
        return pd.NA
    else:
        pattern = r"\b(" + "|".join(re.escape(word) for word in swear_words) + r")\b"

        def replacer(match: re.Match):
            return "*" * len(match.group(0))

        censored_text = re.sub(pattern, replacer, answer, flags=re.IGNORECASE)
        return censored_text
