"""Optional diagnostics for the point-marking canvas (set ``GRADING_DEBUG=1`` or ``?debug=1``)."""

from __future__ import annotations

import os
from typing import Optional

import streamlit as st

from pages.streamlit_canvas_image import jpeg_data_url_from_image


def is_debug_enabled() -> bool:
    if os.environ.get("GRADING_DEBUG", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    query_params = getattr(st, "query_params", None)
    if query_params is not None:
        try:
            return str(query_params.get("debug", "")).lower() in ("1", "true", "yes", "on")
        except Exception:
            return False
    return False


def show_point_stage_canvas_debug(
    canvas_background,
    zoom_source_url: str,
    canvas_width: int,
    canvas_height: int,
    drawable_png_data_url: Optional[str] = None,
) -> None:
    if not is_debug_enabled():
        return
    with st.expander("GRADING_DEBUG — point canvas", expanded=True):
        st.caption("Turn off: unset `GRADING_DEBUG` and remove `?debug=1` from the URL.")
        try:
            from importlib.metadata import PackageNotFoundError, version

            drawable_version = version("streamlit-drawable-canvas")
        except (PackageNotFoundError, Exception):
            drawable_version = "unknown"
        st.write(
            {
                "streamlit": getattr(st, "__version__", "unknown"),
                "streamlit_drawable_canvas": drawable_version,
                "pil_size": getattr(canvas_background, "size", None),
                "canvas_widget_px": (canvas_width, canvas_height),
                "zoom_jpeg_data_url_chars": len(zoom_source_url),
                "drawable_png_data_url_chars": len(drawable_png_data_url) if drawable_png_data_url else None,
            },
        )
        preview_max_width_px = min(420, max(canvas_width, 1))
        preview_data_url = jpeg_data_url_from_image(canvas_background)
        st.markdown(
            f'<img src="{preview_data_url}" alt="Canvas background preview" '
            f'style="display:block;max-width:{preview_max_width_px}px;width:100%;'
            'height:auto;object-fit:contain;" />',
            unsafe_allow_html=True,
        )
        st.caption(
            "Same PIL as `background_image` for `st_canvas` (JPEG data URL avoids `/media/` timing in this panel)."
        )
        if drawable_png_data_url:
            st.code(
                drawable_png_data_url[:160] + ("…" if len(drawable_png_data_url) > 160 else ""),
                language="text",
            )
        st.markdown(
            "**Browser checks:** open DevTools → pick the `st_canvas` iframe → **Console** for red errors; "
            "**Elements** → find `canvas.lower-canvas` and confirm dimensions / stacking."
        )
        st.caption(
            "`drawable_png_data_url_chars` only applies when `GRADING_DRAWABLE_CANVAS_DATA_URL` is on (experimental). "
            "Default canvas uses `/media/` PNG URLs. If that count is near 1e6, the component may drop the background."
        )
