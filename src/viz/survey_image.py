from textwrap import wrap

from PIL import Image, ImageDraw
from PIL.ImageFont import FreeTypeFont

from src.teachers_db import Role


def get_continue_teaching_color(percent: int) -> tuple[int, int, int]:
    green_intensity = percent / 100
    red_intensity = (1 - green_intensity) ** 0.3
    R = int(red_intensity * 255)
    G = int(green_intensity * 255)
    return (R, G, 0)


def create_photo_mask(img: Image.Image, radius_percent=10):
    img = img.convert("RGBA")
    width, height = img.size

    radius = int(min(width, height) * (radius_percent / 100))

    scale = 4
    mask = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(mask)

    draw.rounded_rectangle(
        (0, 0, width * scale, height * scale), radius=radius * scale, fill=255
    )

    mask = mask.resize((width, height), resample=Image.LANCZOS)
    return mask


def generate_survey_result_picture(
    name: str,
    role: Role,
    per_continue_teaching: int,
    num_response: int,
    max_num_response: int,
    photo: Image.Image,
    spider_plot: Image.Image,
    bar_plot: Image.Image,
    fonts_map: dict[str, FreeTypeFont],
    color_map: dict[str, tuple],
    width: int = 1500,
    height: int = 1500,
    name_num_wrap: int = 16,
    margin: int = 95,
    gap_spider_top: int = 0,
    gap_left_right_part: int = 25,
    rounded_photo_mask_radius_percent: float = 10,
    semester_label: str = "2024-2025, I семестр",
):
    img = Image.new("RGBA", (width, height), color_map["background"])

    mask = create_photo_mask(photo, rounded_photo_mask_radius_percent)
    img.paste(photo, (margin, margin), mask)
    img.paste(
        spider_plot, (margin + 400 + gap_left_right_part, margin - 75 + gap_spider_top)
    )
    img.paste(
        bar_plot,
        (margin + 400 + gap_left_right_part, height - margin - 400),
    )

    draw = ImageDraw.Draw(img)
    for i, name_lines in enumerate(wrap(name, name_num_wrap)):
        last_line_ypos = 400 + margin + 20 + i * 40
        draw.text(
            (margin, last_line_ypos),
            name_lines,
            color_map["text"],
            font=fonts_map["name"],
        )

    position_pos = last_line_ypos + 60
    draw.text(
        (margin, position_pos), str(role), color_map["text"], font=fonts_map["text"]
    )

    perc_pos = height - 550 - margin
    perc_color = get_continue_teaching_color(per_continue_teaching)
    draw.text(
        (margin, perc_pos),
        f"{per_continue_teaching}%",
        perc_color,
        font=fonts_map["percent"],
    )

    for i, desc_line in enumerate(
        wrap("опитаних хочуть, щоб викладач продовжив викладати", 20)
    ):
        last_desc_line_pos = perc_pos + 100 + i * 40
        draw.text(
            (margin, last_desc_line_pos),
            desc_line,
            color_map["text"],
            font=fonts_map["text"],
        )

    term_pos = height - margin - 40
    draw.text(
        (margin, term_pos - 170),
        f"{num_response}/{max_num_response}",
        color_map["text"],
        font=fonts_map["num_resp"],
    )
    draw.text(
        (margin, term_pos - 100),
        "кількість опитаних",
        color_map["text"],
        font=fonts_map["text"],
    )
    draw.text(
        (margin, term_pos), semester_label, color_map["text"], font=fonts_map["text"]
    )

    return img
