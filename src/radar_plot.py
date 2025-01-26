"""Based on the official

https://matplotlib.org/stable/gallery/specialty_plots/radar_chart.html
"""

from textwrap import wrap
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D


def radar_factory(num_vars, frame="circle"):
    """
    Create a radar chart with `num_vars` Axes.

    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    frame : {'circle', 'polygon'}
        Shape of frame surrounding Axes.

    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarTransform(PolarAxes.PolarTransform):

        def transform_path_non_affine(self, path):
            # Paths with non-unit interpolation steps correspond to gridlines,
            # in which case we force interpolation (to defeat PolarTransform's
            # autoconversion to circular arcs).
            if path._interpolation_steps > 1:
                path = path.interpolated(num_vars)
            return Path(self.transform(path.vertices), path.codes)

    class RadarAxes(PolarAxes):

        name = "radar"
        PolarTransform = RadarTransform

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location("N")

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            # FIXME: markers at x[0], y[0] get doubled-up
            if x[0] != x[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        def _gen_axes_patch(self):
            # The Axes patch must be centered at (0.5, 0.5) and of radius 0.5
            # in axes coordinates.
            if frame == "circle":
                return Circle((0.5, 0.5), 0.5)
            elif frame == "polygon":
                return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="k")
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

        def _gen_axes_spines(self):
            if frame == "circle":
                return super()._gen_axes_spines()
            elif frame == "polygon":
                # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'.
                spine = Spine(
                    axes=self,
                    spine_type="circle",
                    path=Path.unit_regular_polygon(num_vars),
                )
                # unit_regular_polygon gives a polygon of radius 1 centered at
                # (0, 0) but we want a polygon of radius 0.5 centered at (0.5,
                # 0.5) in axes coordinates.
                spine.set_transform(
                    Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes
                )
                return {"polar": spine}
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

    register_projection(RadarAxes)
    return theta


def get_horizontal_alignment(angle: float) -> str:
    CRITICAL_ANGLE = np.pi / 4
    if angle <= CRITICAL_ANGLE:
        h_align = "center"
    elif angle <= 3 * CRITICAL_ANGLE:
        h_align = "right"
    elif angle < 5 * CRITICAL_ANGLE:
        h_align = "center"
    elif angle < 7 * CRITICAL_ANGLE:
        h_align = "left"
    else:
        h_align = "center"
    return h_align


def generate_radar_plot(
    grades: np.ndarray,
    labels: list[float],
    r_paddings: list[float] | None = None,
    theta_paddings: list[float] | None = None,
    background_color=(19 / 255, 20 / 255, 2 / 255),
    text_color="white",
    font_size: int = 16,
    plot_color="y",
    size=900,
    dpi=100,
    start_with_grade_two: bool = False,
    plot_scale: bool = True,
    tight_layout: bool = True,
) -> Figure:
    N = len(grades)

    if not r_paddings:
        r_paddings = [0] * N
    if not theta_paddings:
        theta_paddings = [0] * N

    # Prepare graph layout
    thetas = radar_factory(N, frame="polygon")
    fig = plt.figure(
        figsize=(size / dpi, size / dpi), dpi=dpi, facecolor=background_color
    )
    ax = plt.axes(projection="radar", facecolor=background_color)

    # Ensure scale (r axis labels) will be visible
    ax.set_ylim(0, 1)
    ax.set_axisbelow(True)
    ax.set_yticklabels([])
    for _, spine in ax.spines.items():
        spine.set_zorder(0.5)
        spine.set_linewidth(2)
        spine.set_color(text_color)

    # Adjust radial axes lines
    ax.get_xaxis().set_visible(False)
    num_levels = 5 - start_with_grade_two
    ax.set_rticks(np.arange(1, num_levels + 1) / num_levels)

    # Plot r axis label (with proper occlusion)
    first_r_axis = 1 / num_levels - 0.03
    for level in range(1, num_levels + 1):
        r = level / num_levels - 0.03
        angle = 0.15 * first_r_axis / r
        ax.text(
            angle,
            r,
            str(level + start_with_grade_two),
            zorder=1,
            color=text_color,
            backgroundcolor=background_color,
            fontsize=font_size,
        )

    # Plot lines betweew
    if plot_scale:
        grid_color = ax.get_ygridlines()[0].get_color()
        for theta in thetas:
            ax.plot([theta, theta], [0, 1], color=grid_color, zorder=0.75)

    # Plot radar graph
    scaled_grades = (grades - start_with_grade_two) / (5 - start_with_grade_two)
    ax.plot(thetas, scaled_grades, color=plot_color)
    ax.fill(thetas, scaled_grades, facecolor=plot_color, alpha=0.25, label="_nolegend_")

    labels = ["\n".join(wrap(label, 20)) for label in labels]
    for label, angle, r_pad, theta_pad in zip(
        labels, thetas, r_paddings, theta_paddings
    ):
        h_align = get_horizontal_alignment(angle)
        ax.text(
            angle + theta_pad,
            1 + r_pad,
            label,
            horizontalalignment=h_align,
            color=text_color,
            fontsize=font_size,
        )

    if tight_layout:
        fig.tight_layout()

    return fig
