"""
``streamlit-drawable-canvas`` registers the background in Streamlit's in-memory
``/media/...`` store. Fast reruns or iframe timing often produce
``MediaFileStorageError`` / missing file errors when the browser requests a stale id.

We pass the background as an inline **JPEG** data URL (compressed) so the canvas
never uses the media file manager for that image.

Set ``GRADING_DRAWABLE_CANVAS_DATA_URL=0`` (or ``false`` / ``off``) to restore the
package's stock ``image_to_url`` behavior.
"""

from __future__ import annotations

import base64
import io
import os
from typing import Any, Optional

import numpy as np
from PIL import Image as PILImage
import streamlit_drawable_canvas as drawable_module

_original_st_canvas = drawable_module.st_canvas
_component_func = drawable_module._component_func
_resize_img = drawable_module._resize_img
_data_url_to_image = drawable_module._data_url_to_image
CanvasResult = drawable_module.CanvasResult

try:
    _LANCZOS = PILImage.Resampling.LANCZOS
except AttributeError:
    _LANCZOS = PILImage.LANCZOS

_JPEG_QUALITY = 88
_MAX_BACKGROUND_BYTES = 1_800_000


def prefer_data_url_background() -> bool:
    raw = os.environ.get("GRADING_DRAWABLE_CANVAS_DATA_URL", "").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _encode_canvas_background_jpeg_data_url(resized_image: Any) -> str:
    rgb = resized_image.convert("RGB") if resized_image.mode != "RGB" else resized_image
    quality = _JPEG_QUALITY

    def encode(current_rgb: PILImage.Image, current_quality: int) -> bytes:
        buffer = io.BytesIO()
        current_rgb.save(buffer, format="JPEG", quality=current_quality, optimize=True)
        return buffer.getvalue()

    data = encode(rgb, quality)
    while len(data) > _MAX_BACKGROUND_BYTES and quality > 45:
        quality -= 8
        data = encode(rgb, quality)

    scale = 0.88
    while len(data) > _MAX_BACKGROUND_BYTES and rgb.width > 400 and rgb.height > 300:
        new_width = max(1, int(rgb.width * scale))
        new_height = max(1, int(rgb.height * scale))
        rgb = rgb.resize((new_width, new_height), _LANCZOS)
        data = encode(rgb, quality)

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _st_canvas_data_url_background(
    fill_color: str = "#eee",
    stroke_width: int = 20,
    stroke_color: str = "black",
    background_color: str = "",
    background_image: Any = None,
    update_streamlit: bool = True,
    height: int = 400,
    width: int = 600,
    drawing_mode: str = "freedraw",
    initial_drawing: Optional[dict] = None,
    display_toolbar: bool = True,
    point_display_radius: int = 3,
    key=None,
) -> CanvasResult:
    background_image_url = None
    if background_image is not None:
        resized = _resize_img(background_image, height, width)
        background_image_url = _encode_canvas_background_jpeg_data_url(resized)
        background_color = ""

    initial_drawing = {"version": "4.4.0"} if initial_drawing is None else initial_drawing
    initial_drawing["background"] = background_color

    component_value = _component_func(
        fillColor=fill_color,
        strokeWidth=stroke_width,
        strokeColor=stroke_color,
        backgroundColor=background_color,
        backgroundImageURL=background_image_url,
        realtimeUpdateStreamlit=update_streamlit and (drawing_mode != "polygon"),
        canvasHeight=height,
        canvasWidth=width,
        drawingMode=drawing_mode,
        initialDrawing=initial_drawing,
        displayToolbar=display_toolbar,
        displayRadius=point_display_radius,
        key=key,
        default=None,
    )
    if component_value is None:
        return CanvasResult

    return CanvasResult(
        np.asarray(_data_url_to_image(component_value["data"])),
        component_value["raw"],
    )


def st_canvas(*args: Any, **kwargs: Any) -> CanvasResult:
    if prefer_data_url_background():
        return _st_canvas_data_url_background(*args, **kwargs)
    return _original_st_canvas(*args, **kwargs)


def install_drawable_canvas_data_url_background() -> None:
    drawable_module.st_canvas = st_canvas
