"""Helpers for streamlit_drawable_canvas and compact inline images.

The library checks ``if background_image``, which raises ValueError for NumPy
arrays ("truth value of an array is ambiguous"). Always pass an RGB PIL Image.

Streamlit Community Cloud limits how large ``components.html`` / custom-component
payloads can be; huge PNG data URLs often fail silently. Use ``jpeg_data_url_from_image``
for crosshair/zoom scripts and similar.
"""

from __future__ import annotations

import base64
import io
from typing import Union

import numpy as np
from PIL import Image

try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    _LANCZOS = Image.LANCZOS

# Hosted Streamlit is stricter than a laptop on iframe / component message size.
DEFAULT_MAX_JPEG_DATA_URL_BYTES = 600_000
COMPONENT_HTML_JPEG_MAX_BYTES = 380_000
# streamlit-drawable-canvas / Fabric reliably loads PNG data URLs for backgrounds; JPEG often renders blank.
# Custom-component JSON props truncate around ~1M+ chars; ~1.02M caused a black canvas with no Python error.
DRAWABLE_CANVAS_BACKGROUND_MAX_DATA_URL_CHARS = 380_000


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


def jpeg_data_url_from_image(
    image: Union[Image.Image, np.ndarray],
    *,
    max_payload_bytes: int = DEFAULT_MAX_JPEG_DATA_URL_BYTES,
    initial_quality: int = 88,
) -> str:
    """Return a ``data:image/jpeg;base64,...`` URL, shrinking until under ``max_payload_bytes``."""
    rgb = pil_background_for_drawable_canvas(image)
    quality = int(initial_quality)

    def encode(current_rgb: Image.Image, current_quality: int) -> bytes:
        buffer = io.BytesIO()
        current_rgb.save(buffer, format="JPEG", quality=current_quality, optimize=True)
        return buffer.getvalue()

    data = encode(rgb, quality)
    while len(data) > max_payload_bytes and quality > 40:
        quality -= 10
        data = encode(rgb, quality)

    scale = 0.86
    while len(data) > max_payload_bytes and rgb.width > 320 and rgb.height > 240:
        new_width = max(1, int(rgb.width * scale))
        new_height = max(1, int(rgb.height * scale))
        rgb = rgb.resize((new_width, new_height), _LANCZOS)
        data = encode(rgb, quality)

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def jpeg_data_url_for_component_html(
    image: Union[Image.Image, np.ndarray],
    *,
    initial_quality: int = 82,
) -> str:
    """JPEG data URL sized for ``st.components.html`` (stricter than drawable-canvas props)."""
    return jpeg_data_url_from_image(
        image,
        max_payload_bytes=COMPONENT_HTML_JPEG_MAX_BYTES,
        initial_quality=initial_quality,
    )


def png_data_url_for_drawable_canvas(
    image: Union[Image.Image, np.ndarray],
    *,
    max_data_url_chars: int = DRAWABLE_CANVAS_BACKGROUND_MAX_DATA_URL_CHARS,
) -> str:
    """PNG ``data:`` URL for ``st_canvas`` backgrounds (Fabric-friendly).

    Caps the **entire** ``data:image/png;base64,...`` string length. Raw PNG byte
    limits are not enough: a ~760KB PNG becomes ~1M base64 chars and Streamlit's
    component bridge can drop it, leaving a black canvas.
    """
    rgb = pil_background_for_drawable_canvas(image)
    working = rgb
    prefix = "data:image/png;base64,"

    while True:
        buffer = io.BytesIO()
        working.save(buffer, format="PNG", optimize=True, compress_level=9)
        data = buffer.getvalue()
        encoded = base64.b64encode(data).decode("ascii")
        data_url = prefix + encoded
        if len(data_url) <= max_data_url_chars:
            return data_url
        if working.width < 200 or working.height < 150:
            return data_url
        working = working.resize(
            (max(1, int(working.width * 0.86)), max(1, int(working.height * 0.86))),
            _LANCZOS,
        )
