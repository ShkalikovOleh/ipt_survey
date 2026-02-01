import argparse

import pandas as pd

from src.analysis.filters import (
    num_responses_filter,
)
from src.teachers_db import load_teachers_db


def main(teacher_jsons: list[str], df_path: str, out_path: str):
    teacher_db = load_teachers_db(teacher_jsons)

    agg_df = pd.read_parquet(df_path)

    def passes_filter(row):
        teacher_name = row.name
        teacher = teacher_db[teacher_name]

        if teacher is None:
            return False

        return num_responses_filter(
            num_responses=row["num_responses"],
            num_respondents=teacher.num_students,
            min_fraction=0.15,
            min_responses=5,
            min_num_pass=10,
        )

    filtered_df = agg_df[agg_df.apply(passes_filter, axis=1)]

    filtered_df.to_parquet(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--teacher_data",
        nargs="+",
        type=str,
        required=True,
        help="Paths to json files with teacher info",
    )
    parser.add_argument("--df_path", required=True, type=str)
    parser.add_argument("--out_path", required=True, type=str)

    args = parser.parse_args()
    main(args.teacher_data, args.df_path, args.out_path)
