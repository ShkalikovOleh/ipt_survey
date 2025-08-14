import io

from PIL import Image
from matplotlib.figure import Figure
import numpy as np


def convert_matplotlib_fig_to_image(fig: Figure) -> Image.Image:
    with io.BytesIO() as io_buf:
        fig.savefig(io_buf, format="raw")
        io_buf.seek(0)
        img_arr = np.reshape(
            np.frombuffer(io_buf.getvalue(), dtype=np.uint8),
            shape=(int(fig.bbox.bounds[3]), int(fig.bbox.bounds[2]), -1),
        )
    return Image.fromarray(img_arr)
