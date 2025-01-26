from textwrap import wrap
from PIL import Image
from PIL import ImageDraw
from PIL.ImageFont import FreeTypeFont


def get_continue_teaching_color(percent: int) -> tuple[int, int, int]:
    green_intensity = percent / 100
    red_intensity = (1 - green_intensity) ** 0.3
    R = int(red_intensity * 255)
    G = int(green_intensity * 255)
    return (R, G, 0)


def generate_survey_result_picture(
    name: str,
    position: str,
    per_continue_teaching: int,
    num_response: int,
    max_num_response: int,
    photo: Image,
    spider_plot: Image,
    bar_plot: Image,
    fonts_map: dict[str, FreeTypeFont],
    color_map: dict[str, tuple],
    semester_label: str = "2024-2025, I семестр",
):
    img = Image.new("RGBA", (1500, 1500), color_map["background"])

    img.paste(photo, (95, 95))
    img.paste(spider_plot, (95 + 400 + 50, 95))
    img.paste(bar_plot, (95 + 400 + 50, 95 + 900 + 10))

    draw = ImageDraw.Draw(img)
    for i, name_lines in enumerate(wrap(name, 16)):
        last_line_ypos = 400 + 95 + 20 + i * 40
        draw.text(
            (95, last_line_ypos), name_lines, color_map["text"], font=fonts_map["name"]
        )

    position_pos = last_line_ypos + 60
    draw.text((95, position_pos), position, color_map["text"], font=fonts_map["text"])

    perc_color = get_continue_teaching_color(per_continue_teaching)
    draw.text(
        (95, position_pos + 200),
        f"{per_continue_teaching}%",
        perc_color,
        font=fonts_map["percent"],
    )

    for i, desc_line in enumerate(
        wrap("опитаних хочуть, щоб викладач продовжив викладати", 20)
    ):
        last_desc_line_pos = position_pos + 300 + i * 40
        draw.text(
            (95, last_desc_line_pos),
            desc_line,
            color_map["text"],
            font=fonts_map["text"],
        )

    term_pos = 1500 - 95 - 40
    draw.text(
        (95, term_pos - 170),
        f"{num_response}/{max_num_response}",
        color_map["text"],
        font=fonts_map["num_resp"],
    )
    draw.text(
        (95, term_pos - 100),
        "кількість опитаних",
        color_map["text"],
        font=fonts_map["text"],
    )
    draw.text(
        (95, term_pos),
        semester_label,
        color_map["text"],
        font=fonts_map["text"],
    )

    return img
