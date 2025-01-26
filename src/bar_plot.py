from matplotlib import pyplot as plt
from matplotlib.figure import Figure
import numpy as np


def generate_bar_plot(
    satisfaction_per_grade: np.ndarray,
    self_assesment_per_grade: np.ndarray,
    width: int = 900,
    height: int = 400,
    nbins: int = 5,
    dpi: int = 100,
    fontsize: int = 16,
    background_color=(19 / 255, 20 / 255, 2 / 255),
    text_color="white",
    tight_layout: bool = True,
) -> Figure:
    dpi = 100
    fig, axs = plt.subplots(
        figsize=(width / dpi, height / dpi),
        nrows=1,
        ncols=2,
        facecolor=background_color,
        sharey=True,
    )

    titles = [
        "Рівень задоволеності \n викладанням дисципліни",
        "Самооцінка рівня знань",
    ]
    data = [satisfaction_per_grade, self_assesment_per_grade]

    total_max_votes = max(
        np.max(satisfaction_per_grade), np.max(self_assesment_per_grade)
    )

    for ax, title, num_per_grade in zip(axs.flat, titles, data):
        ax.set_facecolor(background_color)
        ax.set_title(
            title,
            weight="bold",
            size="medium",
            y=-0.2,
            horizontalalignment="center",
            verticalalignment="top",
        )

        ax.bar(np.arange(1, 6), num_per_grade, facecolor="y")

        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        yticks_delta = int(total_max_votes / nbins)
        if total_max_votes % nbins > yticks_delta // 2:
            yticks_delta += 1
        ax.set_yticks([i * yticks_delta for i in range(nbins + 1)])
        ax.yaxis.grid()
        ax.yaxis.set_tick_params(labelleft=True)

        ax.tick_params(axis="x", colors=text_color)
        ax.tick_params(axis="y", colors=text_color)
        ax.title.set_color(text_color)
        for item in (
            [ax.title, ax.xaxis.label, ax.yaxis.label]
            + ax.get_xticklabels()
            + ax.get_yticklabels()
        ):
            item.set_fontsize(fontsize)

    if tight_layout:
        fig.tight_layout()

    return fig
