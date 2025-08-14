import argparse
from functools import partial

import pandas as pd

from src.analysis.aggregators import (
    concat_text_answers,
    count_per_grade,
    mean_if_more_than_half,
    merge_two_text_columns,
)
from src.analysis.filters import filter_empty_text, filter_swear_language


def main(raw_df_path: str, out_path: str):
    df = pd.read_parquet(raw_df_path)

    text_columns = [
        "Які позитивні риси є у викладача (такі, що можна порекомендувати іншим викладачам)?",
        "Які недоліки є у викладанні?",
        "Які шляхи їх вирішення ви бачите?",
        "Поради для студентів. Що краще робити (чи навпаки, не робити) для побудови гарних відносин із викладачем, які характерні особливості є у викладача, про які ви вважаєте варто знати тим, хто буде у нього вчитись?",
        "Відкритий мікрофон. Усе, що ви хочете сказати про викладача, але що не покрив жоден інший пункт",
    ]
    columns_to_agg = {
        "Ввічливість і загальне враження від спілкування": "mean",
        "Прозорість критеріїв оцінювання і їх дотримання": "mean",
        "Доступність комунікації": "mean",
        "Вміння донести матеріал до студентів": "mean",
        "Вимогливість викладача": "mean",
        "Ставлення викладача до перевірки робіт": mean_if_more_than_half,
        "Доступ до оцінок": "mean",
        "Узгодженість лекцій і практик (наскільки курси лекцій і практик доповнюють одне одного)": "mean",
        "Чи хочете ви, щоб викладач продовжував викладати?": "mean",
        "Наскільки ви в загальному задоволені викладанням дисципліни цим викладачем?": count_per_grade,
        "Як ви оціните власні знання з дисципліни?": count_per_grade,
        "Які позитивні риси є у викладача (такі, що можна порекомендувати іншим викладачам)?": concat_text_answers,
        "drawbacks_merged": concat_text_answers,
        "Поради для студентів. Що краще робити (чи навпаки, не робити) для побудови гарних відносин із викладачем, які характерні особливості є у викладача, про які ви вважаєте варто знати тим, хто буде у нього вчитись?": concat_text_answers,
        "Відкритий мікрофон. Усе, що ви хочете сказати про викладача, але що не покрив жоден інший пункт": concat_text_answers,
    }
    swear_words = set(
        "бля",
        "блядь",
        "блять",
        "сука",
        "пізда",
        "піздець",
        "хуй",
        "нахуй",
        "нахуя",
        "жопа",
        "курва",
        "мудак",
        "дебіл",
        "шлюха",
        "говно",
        "лайно",
        "підор",
        "підар",
    )
    filter_swear_language_func = partial(filter_swear_language, swear_words=swear_words)

    df[text_columns] = df[text_columns].map(filter_empty_text, na_action="ignore")
    df[text_columns] = df[text_columns].map(
        filter_swear_language_func, na_action="ignore"
    )

    df["drawbacks_merged"] = df.apply(
        lambda row: merge_two_text_columns(
            row, "Які недоліки є у викладанні?", "Які шляхи їх вирішення ви бачите?"
        ),
        axis=1,
    )
    df.drop(
        ["Які недоліки є у викладанні?", "Які шляхи їх вирішення ви бачите?"],
        axis=1,
        inplace=True,
    )

    grouped_df = df.groupby(by="name", dropna=False)
    counts_per_teacher = grouped_df.size().to_frame("num_responses")
    agg_df = grouped_df.agg(columns_to_agg).join(counts_per_teacher)

    agg_df.to_parquet(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_df_path", required=True, type=str)
    parser.add_argument("--out_path", required=True, type=str)

    args = parser.parse_args()
    main(args.raw_df_path, args.out_path)
