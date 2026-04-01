import io
import importlib

import cv2
import numpy as np
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

from border_measurement import calculate_ratios_from_bounds
from pages import line_mark_utils as line_utils

line_utils = importlib.reload(line_utils)
line_utils.apply_streamlit_canvas_compatibility()


st.set_page_config(page_title="Line Mark Mode", layout="wide")
st.title("Line Mark Mode")
st.write("Click 8 points: top(2), right(2), bottom(2), left(2).")
st.markdown(
    """
    <style>
    canvas.upper-canvas { cursor: crosshair !important; }
    div[data-testid="stImage"] img { max-height: 70vh; object-fit: contain; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "line_mark_canvas_nonce" not in st.session_state:
    st.session_state["line_mark_canvas_nonce"] = 0

_persistent_defaults = {
    "line_top_y": 0,
    "line_right_x": 0,
    "line_bottom_y": 0,
    "line_left_x": 0,
    "line_top_angle": 0.0,
    "line_right_angle": 0.0,
    "line_bottom_angle": 0.0,
    "line_left_angle": 0.0,
    "line_inner_top": 0,
    "line_inner_right": 0,
    "line_inner_bottom": 0,
    "line_inner_left": 0,
    "line_inner_zoom_mode": "full",
    "line_outer_zoom_mode": "full",
}
for _key, _default_value in _persistent_defaults.items():
    st.session_state.setdefault(_key, _default_value)


def _persistent_int_input(label: str, state_key: str, widget_key: str, step: int = 1) -> int:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = int(st.session_state.get(state_key, 0))
    value = int(st.number_input(label, step=step, key=widget_key))
    st.session_state[state_key] = value
    return value


def _persistent_float_input(label: str, state_key: str, widget_key: str, step: float = 0.1) -> float:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = float(st.session_state.get(state_key, 0.0))
    value = float(st.number_input(label, step=step, key=widget_key))
    st.session_state[state_key] = value
    return value

uploaded_file = st.file_uploader("Upload card image", type=["png", "jpg", "jpeg", "webp"], key="line_mark_upload")
if uploaded_file is None:
    st.info("Upload an image to begin.")
    st.stop()

image_bytes = uploaded_file.getvalue()
image_bgr = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
if image_bgr is None:
    st.error("Unable to decode uploaded image.")
    st.stop()

image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
canvas_width, canvas_height, canvas_scale = line_utils.fit_size(pil_image.width, pil_image.height)
canvas_image = pil_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)

left_col, right_col = st.columns([3, 2])
with right_col:
    if st.button("Clear marked points"):
        st.session_state.pop("line_mark_locked_points", None)
        st.session_state.pop("line_mark_stage", None)
        st.session_state.pop("line_mark_adjusted_points", None)
        st.session_state["line_mark_canvas_nonce"] += 1
        st.rerun()

locked_points = st.session_state.get("line_mark_locked_points")
if locked_points is None:
    with left_col:
        line_utils.force_canvas_crosshair()
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=2,
            stroke_color="#00FFFF",
            background_image=canvas_image,
            update_streamlit=True,
            drawing_mode="point",
            point_display_radius=4,
            height=canvas_height,
            width=canvas_width,
            key=f"line_mark_canvas_{st.session_state['line_mark_canvas_nonce']}",
        )

    points = line_utils.point_list_from_canvas(canvas_result.json_data)
    if canvas_scale < 1.0:
        points = [(x_value / canvas_scale, y_value / canvas_scale) for x_value, y_value in points]
    with right_col:
        st.write(f"Points placed: {len(points)} / 8")
        if len(points) < 8:
            st.info("Keep clicking in order: top, right, bottom, left.")
            st.stop()
        if len(points) > 8:
            st.warning("Using first 8 points only.")
            points = points[:8]
        if st.button("Lock points and continue"):
            st.session_state["line_mark_locked_points"] = points
            st.session_state["line_mark_stage"] = "lines"
            st.rerun()
        st.stop()

points = list(locked_points)
stage = st.session_state.get("line_mark_stage", "lines")
with right_col:
    st.write("Points placed: 8 / 8")
    action_cols = st.columns(2)
    with action_cols[0]:
        if st.button("Re-mark points"):
            st.session_state.pop("line_mark_locked_points", None)
            st.session_state.pop("line_mark_stage", None)
            st.session_state.pop("line_mark_adjusted_points", None)
            st.session_state["line_mark_canvas_nonce"] += 1
            st.rerun()
    if stage == "lines":
        st.caption("Outer line zoom")
        zoom_cols = st.columns(5)
        with zoom_cols[0]:
            if st.button("Top", key="outer_zoom_top_button"):
                st.session_state["line_outer_zoom_mode"] = "top"
        with zoom_cols[1]:
            if st.button("Right", key="outer_zoom_right_button"):
                st.session_state["line_outer_zoom_mode"] = "right"
        with zoom_cols[2]:
            if st.button("Bottom", key="outer_zoom_bottom_button"):
                st.session_state["line_outer_zoom_mode"] = "bottom"
        with zoom_cols[3]:
            if st.button("Left", key="outer_zoom_left_button"):
                st.session_state["line_outer_zoom_mode"] = "left"
        with zoom_cols[4]:
            if st.button("Full", key="outer_zoom_full_button"):
                st.session_state["line_outer_zoom_mode"] = "full"
        st.caption("Line controls: drag on axis + rotate")
        axis_cols = st.columns(4)
        with axis_cols[0]:
            top_line_y = _persistent_int_input("Top Y", "line_top_y", "line_top_y_widget")
        with axis_cols[1]:
            right_line_x = _persistent_int_input("Right X", "line_right_x", "line_right_x_widget")
        with axis_cols[2]:
            bottom_line_y = _persistent_int_input("Bottom Y", "line_bottom_y", "line_bottom_y_widget")
        with axis_cols[3]:
            left_line_x = _persistent_int_input("Left X", "line_left_x", "line_left_x_widget")
        angle_cols = st.columns(4)
        with angle_cols[0]:
            top_line_angle = _persistent_float_input("Top Angle", "line_top_angle", "line_top_angle_widget")
        with angle_cols[1]:
            right_line_angle = _persistent_float_input("Right Angle", "line_right_angle", "line_right_angle_widget")
        with angle_cols[2]:
            bottom_line_angle = _persistent_float_input(
                "Bottom Angle", "line_bottom_angle", "line_bottom_angle_widget"
            )
        with angle_cols[3]:
            left_line_angle = _persistent_float_input("Left Angle", "line_left_angle", "line_left_angle_widget")
    else:
        top_line_y = int(st.session_state.get("line_top_y", 0))
        right_line_x = int(st.session_state.get("line_right_x", 0))
        bottom_line_y = int(st.session_state.get("line_bottom_y", 0))
        left_line_x = int(st.session_state.get("line_left_x", 0))
        top_line_angle = float(st.session_state.get("line_top_angle", 0.0))
        right_line_angle = float(st.session_state.get("line_right_angle", 0.0))
        bottom_line_angle = float(st.session_state.get("line_bottom_angle", 0.0))
        left_line_angle = float(st.session_state.get("line_left_angle", 0.0))

adjusted_points = line_utils.line_controlled_points(
    points,
    top_line_y,
    top_line_angle,
    right_line_x,
    right_line_angle,
    bottom_line_y,
    bottom_line_angle,
    left_line_x,
    left_line_angle,
)
with right_col:
    if stage == "lines":
        if st.button("Continue to inner border stage"):
            st.session_state["line_mark_adjusted_points"] = adjusted_points
            st.session_state["line_mark_stage"] = "border"
            st.rerun()
        with left_col:
            st.image(
                line_utils.select_zoomed_line_preview(
                    image_rgb, adjusted_points, st.session_state.get("line_outer_zoom_mode", "full"), padding=5
                ),
                caption="Line stage zoom: outer lines with 5px margin.",
                use_container_width=True,
            )
        st.stop()
    with action_cols[1]:
        if st.button("Back to line stage"):
            st.session_state["line_mark_stage"] = "lines"
            st.rerun()

final_points = st.session_state.get("line_mark_adjusted_points", adjusted_points)
warped_card = line_utils.warp_from_edges(image_bgr, final_points)
if warped_card is None:
    with right_col:
        st.error("Could not build card edges from points. Try clearing and re-marking.")
    st.stop()

card_height, card_width = warped_card.shape[:2]
base_left, base_top = 10, 10
base_right, base_bottom = max(card_width - 11, base_left + 1), max(card_height - 11, base_top + 1)

with right_col:
    nudge_top, nudge_right, nudge_bottom, nudge_left, color_label, zoom_mode = line_utils.render_inner_border_controls()

inner_left = max(1, min(base_left + nudge_left, card_width - 2))
inner_right = max(inner_left + 1, min(base_right - nudge_right, card_width - 1))
inner_top = max(1, min(base_top + nudge_top, card_height - 2))
inner_bottom = max(inner_top + 1, min(base_bottom - nudge_bottom, card_height - 1))

result = calculate_ratios_from_bounds(card_width, card_height, inner_left, inner_right, inner_top, inner_bottom)
visualized = cv2.cvtColor(warped_card, cv2.COLOR_BGR2RGB)
visualized = line_utils.draw_visible_inner_border(
    visualized, inner_left, inner_top, inner_right, inner_bottom, line_utils.border_color(color_label)
)
display_visual = line_utils.select_zoomed_inner_preview(
    visualized, card_width, card_height, inner_left, inner_right, inner_top, inner_bottom, zoom_mode
)

with left_col:
    st.image(
        display_visual,
        caption="Full card by default. Top/Bottom inputs zoom 50% width, Left/Right inputs zoom 50% height.",
        width="stretch" if zoom_mode == "full" else "content",
    )
with right_col:
    line_utils.render_result_summary(result)
