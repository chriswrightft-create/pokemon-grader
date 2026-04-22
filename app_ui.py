from __future__ import annotations

import io
from pathlib import Path

import streamlit as st
from PIL import Image, ImageSequence

_QUICKSTART_GIF = Path(__file__).resolve().parent / "assets" / "quickstart.gif"
_QUICKSTART_DISPLAY_GIF = Path(__file__).resolve().parent / "assets" / "quickstart_display.gif"
_QUICKSTART_DISPLAY_BINARY_BYTE_CAP = 1_900_000
_QUICKSTART_DISPLAY_PARAMETER_SEQUENCE = (
    (400, 8),
    (360, 10),
    (360, 12),
    (320, 14),
    (480, 12),
    (400, 12),
)


def read_quickstart_gif_bytes() -> bytes:
    """Return the full quickstart GIF bytes from disk (very large)."""
    return _QUICKSTART_GIF.read_bytes()


def _build_scaled_quickstart_gif_bytes(
    source_path: Path,
    max_bound: int,
    frame_stride: int,
) -> bytes:
    rgba_frames: list[Image.Image] = []
    frame_duration_ms_list: list[int] = []
    with Image.open(source_path) as source_image:
        for frame_index, frame in enumerate(ImageSequence.Iterator(source_image)):
            if frame_index % frame_stride != 0:
                continue
            rgba_frame = frame.convert("RGBA")
            width, height = rgba_frame.size
            longest_edge = max(width, height)
            if longest_edge > max_bound:
                scale_ratio = max_bound / longest_edge
                resized_width = max(1, int(width * scale_ratio))
                resized_height = max(1, int(height * scale_ratio))
                rgba_frame = rgba_frame.resize(
                    (resized_width, resized_height),
                    Image.Resampling.LANCZOS,
                )
            rgba_frames.append(rgba_frame)
            frame_duration_ms_list.append(int(frame.info.get("duration", 80)))
    if not rgba_frames:
        raise ValueError("Quickstart GIF decoding produced no frames.")
    gif_buffer = io.BytesIO()
    rgba_frames[0].save(
        gif_buffer,
        format="GIF",
        save_all=True,
        append_images=rgba_frames[1:],
        duration=frame_duration_ms_list,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return gif_buffer.getvalue()


@st.cache_data(show_spinner=False)
def read_quickstart_display_gif_bytes() -> bytes:
    """Small quickstart GIF for UI (prebuilt asset on deploy; avoids huge ``data:`` HTML on Cloud)."""
    if _QUICKSTART_DISPLAY_GIF.is_file():
        return _QUICKSTART_DISPLAY_GIF.read_bytes()
    last_encoded: bytes = b""
    for max_bound, frame_stride in _QUICKSTART_DISPLAY_PARAMETER_SEQUENCE:
        last_encoded = _build_scaled_quickstart_gif_bytes(
            _QUICKSTART_GIF,
            max_bound,
            frame_stride,
        )
        if len(last_encoded) <= _QUICKSTART_DISPLAY_BINARY_BYTE_CAP:
            return last_encoded
    return last_encoded


def render_quickstart_gif(*, caption: str | None = None, width: str = "stretch") -> None:
    """Show the quickstart animation (small GIF via ``st.image`` for Cloud compatibility)."""
    st.image(
        read_quickstart_display_gif_bytes(),
        output_format="GIF",
        caption=caption,
        width=width,
    )


def apply_page_chrome() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {display: none !important;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        div[data-testid="collapsedControl"] {display: none !important;}
        .block-container {padding-top: 2rem !important;}
        h1 {margin-top: 0 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 3.25rem; padding-bottom: 0.4rem;}
        h1 {margin-top: 0; margin-bottom: 0.2rem; font-size: 2rem;}
        p {margin-bottom: 0.5rem;}
        div[data-testid="stNumberInput"] {margin-bottom: 0.25rem;}
        div[data-testid="stMetricValue"] {font-size: 2rem;}
        div[data-testid="stImage"] img {max-height: 70vh; width: auto; object-fit: contain;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_quickstart() -> None:
    st.subheader("How to use")
    render_quickstart_gif(
        caption="Quick walkthrough of initial setup.",
        width="stretch",
    )
