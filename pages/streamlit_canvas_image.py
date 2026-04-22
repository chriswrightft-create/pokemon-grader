"""Helpers for streamlit_drawable_canvas.

The library checks ``if background_image``, which raises ValueError for NumPy
arrays ("truth value of an array is ambiguous"). Always pass an RGB PIL Image.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def pil_background_for_drawable_canvas(image: object) -> Image.Image:
    """Return an RGB PIL image safe to use as ``background_image`` for ``st_canvas``."""
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    if not isinstance(image, np.ndarray):
        raise TypeError(f"canvas background must be PIL Image or ndarray; got {type(image)!r}")
    array = np.asarray(image)
    if array.ndim not in (2, 3):
        raise TypeError(f"expected 2D or 3D array; got shape {array.shape}")
    if array.dtype != np.uint8:
        if np.issubdtype(array.dtype, np.floating) and array.size > 0 and float(np.max(array)) <= 1.0:
            array = (np.clip(array, 0.0, 1.0) * 255).astype(np.uint8)
        else:
            array = np.clip(array, 0, 255).astype(np.uint8)
    if array.ndim == 2:
        return Image.fromarray(array, mode="L").convert("RGB")
    if array.shape[2] == 4:
        return Image.fromarray(array, mode="RGBA").convert("RGB")
    if array.shape[2] == 3:
        return Image.fromarray(array, mode="RGB")
    raise TypeError(f"unsupported channel count: {array.shape[2]}")
