import numpy as np
from src.viz.bar_plot import generate_bar_plot
from src.viz.radar_plot import generate_radar_plot
from src.viz.survey_image import generate_survey_result_picture
from src.viz.utils import convert_matplotlib_fig_to_image

from PIL import ImageFont
from PIL import Image

# Style
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
# color_map = {"background": (19, 20, 2), "text": (255, 255, 255)}
color_map = {"background": (47, 49, 54), "text": (255, 255, 255)}
# graph_color = (78 / 255, 109 / 255, 181 / 255)
graph_color = (106 / 255, 150 / 255, 252 / 255)
# graph_color = (96 / 255, 89 / 255, 73 / 255)

# Data
name = "Surname Name MiddleName"
per_continue_teaching = 57
num_response = 18
max_num_response = 40
criteria = [
    "Ввічливість і загальне враження від спілкування ",
    "Прозорість критеріїв оцінювання",
    "Доступність комунікації",
    "Вміння донести матеріал до студентів",
    "Вимогливість викладача",
    "Ставлення до перевірки робіт (практик)",
    "Доступ до оцінок (практик)",
    "Узгодженість лекцій і практик (лектор)",
]
criteria_grades = np.array([4.7, 3.2, 3.2, 4.4, 5, 3.7, 4.1, 4.9])
num_satisfaction_per_grades = [0, 1, 5, 10, 2]
num_assestment_per_grades = [0, 0, 1, 2, 15]

# Radar plot
r_paddings = [0.1, 0.16, 0.02, 0.17, 0.18, 0.15, 0.02, 0.16]
theta_paddings = [0, 0, 0.05, 0.075, 0, -0.05, -0.09, 0]
spider_fig = generate_radar_plot(
    criteria_grades,
    criteria,
    r_paddings,
    theta_paddings,
    plot_color=graph_color,
    background_color=(47 / 255, 49 / 255, 54 / 255),
)

# Bar plots
bar_fig = generate_bar_plot(
    num_satisfaction_per_grades,
    num_assestment_per_grades,
    plot_color=graph_color,
    background_color=(47 / 255, 49 / 255, 54 / 255),
)

# Generate full picture with empty photo
spider_plot = convert_matplotlib_fig_to_image(spider_fig)
photo = Image.new("RGBA", (400, 400), (255, 255, 255, 255))
bar_plot = convert_matplotlib_fig_to_image(bar_fig)

img = generate_survey_result_picture(
    name,
    "Практик",
    per_continue_teaching,
    num_response,
    max_num_response,
    photo,
    spider_plot,
    bar_plot,
    fonts_map,
    color_map,
)
img.show()
