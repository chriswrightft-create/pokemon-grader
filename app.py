import tempfile

import cv2
import numpy as np
import streamlit as st

from card_detection import detect_card_quad
from pokemon_grader import (
    CardDetectionError,
    analyze_adjusted_card_with_debug,
    analyze_card_borders_with_debug,
    calculate_ratios_from_bounds,
    create_visualization,
    load_image,
)


def _inject_styles() -> None:
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


def _input_px(key: str, label: str, default: int = 0) -> int:
    st.session_state.setdefault(key, default)
    value = int(st.number_input(label, step=1, value=int(st.session_state[key]), key=f"{key}_input"))
    st.session_state[key] = value
    return value


def _seed_corner_inputs_from_auto(image: np.ndarray) -> None:
    image_key = f"{image.shape[1]}x{image.shape[0]}_{int(image.mean())}_{int(image.std())}"
    if st.session_state.get("corner_seed_key") == image_key:
        return

    quad = detect_card_quad(image)
    h, w = image.shape[:2]
    if quad is None:
        defaults = [0, 0, w - 1, 0, w - 1, h - 1, 0, h - 1]
    else:
        defaults = [
            int(quad[0][0]),
            int(quad[0][1]),
            int(quad[1][0]),
            int(quad[1][1]),
            int(quad[2][0]),
            int(quad[2][1]),
            int(quad[3][0]),
            int(quad[3][1]),
        ]
    keys = [
        "corner_tl_x",
        "corner_tl_y",
        "corner_tr_x",
        "corner_tr_y",
        "corner_br_x",
        "corner_br_y",
        "corner_bl_x",
        "corner_bl_y",
    ]
    for key, value in zip(keys, defaults):
        st.session_state[key] = value
    st.session_state["corner_seed_key"] = image_key


def _apply_corner_nudges(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    st.caption("Corner points (absolute px)")

    y_cols = st.columns(4)
    with y_cols[0]:
        tl_y = _input_px("corner_tl_y", "Top left Y", 0)
    with y_cols[1]:
        tr_y = _input_px("corner_tr_y", "Top right Y", 0)
    with y_cols[2]:
        bl_y = _input_px("corner_bl_y", "Bottom left Y", h - 1)
    with y_cols[3]:
        br_y = _input_px("corner_br_y", "Bottom right Y", h - 1)

    x_cols = st.columns(4)
    with x_cols[0]:
        tl_x = _input_px("corner_tl_x", "Top left X", 0)
    with x_cols[1]:
        tr_x = _input_px("corner_tr_x", "Top right X", w - 1)
    with x_cols[2]:
        bl_x = _input_px("corner_bl_x", "Bottom left X", 0)
    with x_cols[3]:
        br_x = _input_px("corner_br_x", "Bottom right X", w - 1)

    source = np.array([[tl_x, tl_y], [tr_x, tr_y], [br_x, br_y], [bl_x, bl_y]], dtype=np.float32)
    padding = 220
    padded = cv2.copyMakeBorder(image, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    source[:, 0] += padding
    source[:, 1] += padding
    destination = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(
        padded,
        matrix,
        (w, h),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )


def _apply_outer_border_nudges(image: np.ndarray) -> np.ndarray:
    st.caption("Outer nudges (+in, -out)")
    cols = st.columns(4)
    with cols[0]:
        top = _input_px("outer_top", "Top", 0)
    with cols[1]:
        right = _input_px("outer_right", "Right", 0)
    with cols[2]:
        bottom = _input_px("outer_bottom", "Bottom", 0)
    with cols[3]:
        left = _input_px("outer_left", "Left", 0)

    h, w = image.shape[:2]
    c_left, c_top = max(left, 0), max(top, 0)
    c_right = max(w - max(right, 0), c_left + 1)
    c_bottom = max(h - max(bottom, 0), c_top + 1)
    cropped = image[c_top:c_bottom, c_left:c_right]
    return cv2.copyMakeBorder(
        cropped,
        max(-top, 0),
        max(-bottom, 0),
        max(-left, 0),
        max(-right, 0),
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0),
    )


def _apply_inner_border_nudges(debug):
    st.caption("Inner nudges (+in, -out)")
    cols = st.columns(4)
    with cols[0]:
        top = _input_px("inner_top", "Top", 0)
    with cols[1]:
        right = _input_px("inner_right", "Right", 0)
    with cols[2]:
        bottom = _input_px("inner_bottom", "Bottom", 0)
    with cols[3]:
        left = _input_px("inner_left", "Left", 0)

    h, w = debug.warped_card_image.shape[:2]
    left_x = max(1, min(debug.inner_left_x + left, w - 2))
    right_x = max(left_x + 1, min(debug.inner_right_x - right, w - 1))
    top_y = max(1, min(debug.inner_top_y + top, h - 2))
    bottom_y = max(top_y + 1, min(debug.inner_bottom_y - bottom, h - 1))
    adjusted_debug = type(debug)(
        warped_card_image=debug.warped_card_image,
        inner_left_x=left_x,
        inner_right_x=right_x,
        inner_top_y=top_y,
        inner_bottom_y=bottom_y,
    )
    adjusted_result = calculate_ratios_from_bounds(w, h, left_x, right_x, top_y, bottom_y)
    return adjusted_result, adjusted_debug


def _selected_inner_border_color() -> tuple[int, int, int]:
    color_map = {
        "Magenta": (255, 0, 255),
        "Cyan": (255, 255, 0),
        "Yellow": (0, 255, 255),
        "Green": (0, 255, 0),
        "Red": (0, 0, 255),
        "White": (255, 255, 255),
    }
    selected_label = st.selectbox("Inner border color", list(color_map.keys()), index=0)
    return color_map[selected_label]


st.set_page_config(page_title="Pokemon Card Border Grader", layout="wide")
st.title("Pokemon Card Border Grader")
st.write("Auto-detects outer and inner borders, then lets you nudge with 1px controls.")
_inject_styles()
uploaded_file = st.file_uploader("Upload card image", type=["png", "jpg", "jpeg", "webp"])
if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1].lower()}") as temp_file:
        temp_file.write(uploaded_file.read())
        temp_path = temp_file.name
    try:
        image = load_image(temp_path)
        image_col, controls_col = st.columns([3, 3])
        with controls_col:
            st.subheader("Adjustments")
            manual_corner = st.checkbox("Manual corner nudges", value=False)
            if manual_corner:
                _seed_corner_inputs_from_auto(image)
                image = _apply_corner_nudges(image)
            manual_outer = st.checkbox("Manual outer-border nudges", value=False)
            if manual_outer:
                image = _apply_outer_border_nudges(image)

            if manual_corner or manual_outer:
                result, debug = analyze_adjusted_card_with_debug(image)
            else:
                result, debug = analyze_card_borders_with_debug(image)

            if st.checkbox("Manual inner-border nudges", value=False):
                result, debug = _apply_inner_border_nudges(debug)
            inner_border_color = _selected_inner_border_color()
    except (CardDetectionError, FileNotFoundError, ValueError) as error:
        st.error(f"Unable to grade image: {error}")
    else:
        with image_col:
            st.subheader("Measurement Visualization")
            st.image(
                create_visualization(debug, inner_border_bgr=inner_border_color),
                caption="Magenta = detected inner frame.",
                width=760,
            )
        with controls_col:
            st.metric("Left/Right Centering", f"{result.left_right_ratio[0]}/{result.left_right_ratio[1]}")
            st.metric("Top/Bottom Centering", f"{result.top_bottom_ratio[0]}/{result.top_bottom_ratio[1]}")
            st.write(
                f"Border widths (px): left={result.left_px}, right={result.right_px}, "
                f"top={result.top_px}, bottom={result.bottom_px}"
            )
            if result.in_45_55_range:
                st.success("Pass: card is within 45/55 on both axes.")
            else:
                st.warning("Fail: card is outside 45/55 on at least one axis.")
