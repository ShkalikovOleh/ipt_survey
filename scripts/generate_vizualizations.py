import argparse
import os
import numpy as np
import pandas as pd
from PIL import Image, ImageFont

from src.teachers_db import Role, Teacher, load_teachers_db
from src.viz.bar_plot import generate_bar_plot
from src.viz.radar_plot import generate_radar_plot
from src.viz.survey_image import generate_survey_result_picture
from src.viz.utils import convert_matplotlib_fig_to_image

font_name = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
font_main = ImageFont.truetype("DejaVuSans.ttf", 32)
font_num_resp = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)
font_percent = ImageFont.truetype("DejaVuSans-Bold.ttf", 100)
fonts_map = {
    "name": font_name,
    "text": font_main,
    "percent": font_percent,
    "num_resp": font_num_resp,
}
color_map = {"background": (19, 20, 2), "text": (255, 255, 255)}

template_to_columns = {
    Role.LECTURER: [
        "Ввічливість і загальне враження від спілкування",
        "Прозорість критеріїв оцінювання і їх дотримання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Ставлення викладача до перевірки робіт",
        "Вимогливість викладача",
        "Узгодженість лекцій і практик (наскільки курси лекцій і практик доповнюють одне одного)",
    ],
    Role.PRACTICE: [
        "Ввічливість і загальне враження від спілкування",
        "Прозорість критеріїв оцінювання і їх дотримання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Ставлення викладача до перевірки робіт",
        "Вимогливість викладача",
        "Доступ до оцінок",
    ],
    Role.BOTH: [
        "Ввічливість і загальне враження від спілкування",
        "Прозорість критеріїв оцінювання і їх дотримання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Вимогливість викладача",
        "Ставлення викладача до перевірки робіт",
        "Доступ до оцінок",
        "Узгодженість лекцій і практик (наскільки курси лекцій і практик доповнюють одне одного)",
    ],
    "LECTURER_NO_EVAL": [
        "Ввічливість і загальне враження від спілкування",
        "Прозорість критеріїв оцінювання і їх дотримання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Вимогливість викладача",
        "Узгодженість лекцій і практик (наскільки курси лекцій і практик доповнюють одне одного)",
    ],
}

template_to_labels = {
    Role.LECTURER: [
        "Ввічливість і загальне враження від спілкування ",
        "Прозорість критеріїв оцінювання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Ставлення до перевірки робіт",
        "Вимогливість викладача",
        "Узгодженість лекцій і практик",
    ],
    Role.PRACTICE: [
        "Ввічливість і загальне враження від спілкування ",
        "Прозорість критеріїв оцінювання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Ставлення до перевірки робіт",
        "Вимогливість викладача",
        "Доступ до оцінок",
    ],
    Role.BOTH: [
        "Ввічливість і загальне враження від спілкування ",
        "Прозорість критеріїв оцінювання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Вимогливість викладача",
        "Ставлення до перевірки робіт",
        "Доступ до оцінок (практик)",
        "Узгодженість лекцій і практик (лектор)",
    ],
    "LECTURER_NO_EVAL": [
        "Ввічливість і загальне враження від спілкування ",
        "Прозорість критеріїв оцінювання",
        "Доступність комунікації",
        "Вміння донести матеріал до студентів",
        "Вимогливість викладача",
        "Узгодженість лекцій і практик",
    ],
}

template_to_paddings = {
    Role.LECTURER: (
        [0.1, 0, 0.05, 0.3, 0.2, 0.05, -0.01],
        [0, 0.1, 0.05, 0, -0.05, -0.05, -0.08],
    ),
    Role.PRACTICE: (
        [0.1, 0, 0.05, 0.3, 0.2, 0.05, -0.01],
        [0, 0.1, 0.05, 0, -0.05, -0.05, -0.08],
    ),
    Role.BOTH: (
        [0.1, 0.16, 0.02, 0.17, 0.18, 0.15, 0.02, 0.16],
        [0, 0, 0.05, 0.075, 0, -0.05, -0.09, 0],
    ),
    "LECTURER_NO_EVAL": (
        [0.1, 0.05, 0.1, 0.25, 0.075, 0.01],
        [0, 0.05, 0.05, 0, -0.05, -0.05],
    ),
}

template_to_shift = {
    Role.LECTURER: 0,
    Role.PRACTICE: 0,
    Role.BOTH: 25,
    "LECTURER_NO_EVAL": 50,
}


def generate_vizualization(
    row: pd.Series, teacher: Teacher, photo_dir: str, save_dir: str
):
    per_continue_teaching = int(
        np.floor(row["Чи хочете ви, щоб викладач продовжував викладати?"] * 100)
    )

    template = teacher.overall_role
    if template == Role.LECTURER:
        if np.isnan(row["Ставлення викладача до перевірки робіт"]):
            template = "LECTURER_NO_EVAL"

    grade_columns = template_to_columns[template]
    grades = np.array([row[col] for col in grade_columns])
    r_pad, theta_pad = template_to_paddings[template]
    fig_spider = generate_radar_plot(
        grades,
        template_to_labels[template],
        r_paddings=r_pad,
        theta_paddings=theta_pad,
        tight_layout=True,
    )
    spider_plot = convert_matplotlib_fig_to_image(fig_spider)

    bar_fig = generate_bar_plot(
        row[
            "Наскільки ви в загальному задоволені викладанням дисципліни цим викладачем?"
        ],
        row["Як ви оціните власні знання з дисципліни?"],
    )
    bar_plot = convert_matplotlib_fig_to_image(bar_fig)

    photo_path = os.path.join(photo_dir, f"{teacher.name}.png")
    if os.path.exists(photo_path):
        photo = Image.open(photo_path)
    else:
        photo = Image.open(os.path.join(photo_dir, "none.png"))

    img = generate_survey_result_picture(
        name=teacher.name,
        role=teacher.overall_role,
        per_continue_teaching=per_continue_teaching,
        num_response=row["num_responses"],
        max_num_response=teacher.num_students,
        photo=photo,
        spider_plot=spider_plot,
        bar_plot=bar_plot,
        fonts_map=fonts_map,
        color_map=color_map,
        gap_spider_top=template_to_shift[template],
    )

    img.save(os.path.join(save_dir, f"{teacher.name}.png"))


def generate_vizualizations(
    teacher_jsons: list[str], df_path: str, photo_dir: str, save_dir: str
):
    db = load_teachers_db(teacher_jsons)
    df = pd.read_parquet(df_path)

    for teacher_name, row in df.iterrows():
        teacher = db[teacher_name]
        generate_vizualization(row, teacher, photo_dir, save_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--teacher_data",
        nargs="+",
        type=str,
        required=True,
        help="Paths to json files with teacher info",
    )
    parser.add_argument("--aggr_df_path", required=True, type=str)
    parser.add_argument("--photo_dir", required=True, type=str)
    parser.add_argument("--save_dir", required=True, type=str)

    args = parser.parse_args()

    generate_vizualizations(
        teacher_jsons=args.teacher_data,
        df_path=args.aggr_df_path,
        photo_dir=args.photo_dir,
        save_dir=args.save_dir,
    )
