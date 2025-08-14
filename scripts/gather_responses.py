import argparse
import json
from tqdm import tqdm

import pandas as pd

from src.forms.filtering import Granularity
from src.forms.responses import gather_responses_to_pandas
from src.forms.services import (
    get_forms_service,
    get_gapi_credentials,
)
from src.analysis.parsers import parse_bool, parse_nan_grade, parse_str
from src.teachers_db import load_teachers_db


columns_to_parser = {
    "Ввічливість і загальне враження від спілкування": parse_nan_grade,
    "Прозорість критеріїв оцінювання і їх дотримання": parse_nan_grade,
    "Доступність комунікації": parse_nan_grade,
    "Вміння донести матеріал до студентів": parse_nan_grade,
    "Вимогливість викладача": parse_nan_grade,
    "Ставлення викладача до перевірки робіт": parse_nan_grade,
    "Доступ до оцінок": parse_nan_grade,
    "Узгодженість лекцій і практик (наскільки курси лекцій і практик доповнюють одне одного)": parse_nan_grade,
    "Чи хочете ви, щоб викладач продовжував викладати?": parse_bool,
    "Наскільки ви в загальному задоволені викладанням дисципліни цим викладачем?": parse_nan_grade,
    "Як ви оціните власні знання з дисципліни?": parse_nan_grade,
    "Які позитивні риси є у викладача (такі, що можна порекомендувати іншим викладачам)?": parse_str,
    "Які недоліки є у викладанні?": parse_str,
    "Які шляхи їх вирішення ви бачите?": parse_str,
    "Поради для студентів. Що краще робити (чи навпаки, не робити) для побудови гарних відносин із викладачем, які характерні особливості є у викладача, про які ви вважаєте варто знати тим, хто буде у нього вчитись?": parse_str,
    "Відкритий мікрофон. Усе, що ви хочете сказати про викладача, але що не покрив жоден інший пункт": parse_str,
}


def gather_responses(
    teacher_jsons: list[str],
    forms_json: str,
    secrets_file: str,
    token_file: str,
    out_path: str,
):
    db = load_teachers_db(teacher_jsons)

    creds = get_gapi_credentials(cred_file=secrets_file, token_store_file=token_file)
    forms_service = get_forms_service(creds)

    with open(forms_json, "r", encoding="utf-8") as file:
        forms_info = json.load(file)
        forms_granularity = forms_info["granularity"]
        forms_dict: dict[str, list[dict[str, str]]] = forms_info["forms"]

    df = pd.DataFrame()
    for name, forms in tqdm(forms_dict.items()):
        overall_role = db[name].overall_role
        for form in forms:
            form_id = form["form_id"]

            teacher_df = gather_responses_to_pandas(
                form_id, forms_service, columns_to_parser
            )
            teacher_df.insert(0, "name", name)
            teacher_df.insert(1, "role", str(overall_role))

            match forms_granularity:
                case Granularity.GROUP:
                    teacher_df.insert(2, "group", form["group"])
                case Granularity.STREAM:
                    teacher_df.insert(2, "speciality", form["speciality"])
                    teacher_df.insert(3, "year", form["year"])
                case Granularity.SPECIALITY:
                    teacher_df.insert(2, "speciality", form["speciality"])

            df = pd.concat([df, teacher_df], axis=0)

    df.to_parquet(out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--teacher_data",
        nargs="+",
        type=str,
        required=True,
        help="Paths to json files with teacher info",
    )
    parser.add_argument(
        "--forms_json",
        type=str,
        required=True,
        help="Paths to json file with forms info",
    )
    parser.add_argument(
        "--secrets_file",
        type=str,
        required=True,
        help="Path to the Google API secrets",
    )
    parser.add_argument(
        "--token_file",
        type=str,
        required=True,
        help="Where to save/reuse access token",
    )
    parser.add_argument(
        "--out_path",
        type=str,
        default="survey_results.parquet",
        help="Path to parquet file with all responses",
    )

    args = parser.parse_args()

    gather_responses(
        teacher_jsons=args.teacher_data,
        forms_json=args.forms_json,
        secrets_file=args.secrets_file,
        token_file=args.token_file,
        out_path=args.out_path,
    )
