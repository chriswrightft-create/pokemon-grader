import base64
import io
import importlib
import sys
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Streamlit Cloud can run this page as entrypoint, so ensure repo root is importable.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from border_measurement import calculate_ratios_from_bounds
from pages import line_mark_line_stage as line_stage_ui
from pages import line_mark_state as line_mark_state
from pages import line_mark_utils as line_utils
from pages.line_mark_warp import get_cached_warped_card

try:
    line_mark_state = importlib.reload(line_mark_state)
except ImportError:
    pass
try:
    line_stage_ui = importlib.reload(line_stage_ui)
except ImportError:
    pass
try:
    line_utils = importlib.reload(line_utils)
except ImportError:
    pass
line_utils.apply_streamlit_canvas_compatibility()

initialize_line_mark_defaults = line_mark_state.initialize_line_mark_defaults
persistent_float_input = line_mark_state.persistent_float_input
persistent_int_input = line_mark_state.persistent_int_input
reset_line_controls = getattr(line_mark_state, "reset_line_controls", lambda: None)


st.set_page_config(page_title="Line Mark Mode", layout="wide", initial_sidebar_state="collapsed")
st.title("Line Mark Mode")
st.caption("Click 12 points: top(3), right(3), bottom(3), left(3).")
upload_col, info_col = st.columns(2, gap="small")
with upload_col:
    uploaded_file = st.file_uploader("Upload card image", type=["png", "jpg", "jpeg", "webp"], key="line_mark_upload", label_visibility="collapsed")
line_utils.inject_line_mark_styles()

initialize_line_mark_defaults()
if uploaded_file is None:
    with info_col:
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
canvas_points = st.session_state.get("line_mark_canvas_points", [])
canvas_preview = line_utils.draw_cross_markers(np.array(canvas_image), canvas_points) if canvas_points else np.array(canvas_image)
canvas_background = Image.fromarray(canvas_preview)
zoom_buffer = io.BytesIO()
canvas_background.save(zoom_buffer, format="PNG")
zoom_source_url = f"data:image/png;base64,{base64.b64encode(zoom_buffer.getvalue()).decode('ascii')}"

left_col, right_col = st.columns([3, 2])
with right_col:
    zoom_factor_value = int(st.number_input("Zoom magnification", min_value=2, max_value=12, value=5, step=1, key="line_zoom_factor"))


def clear_all_marked_points() -> None:
    reset_line_controls()
    line_stage_ui.clear_marking_state()
    st.rerun()
locked_points = st.session_state.get("line_mark_locked_points")
if locked_points is None:
    with left_col:
        line_utils.force_canvas_crosshair(source_image_url=zoom_source_url, zoom_factor=zoom_factor_value)
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=1,
            stroke_color="#00FFFF",
            background_image=canvas_background,
            update_streamlit=True,
            drawing_mode="point",
            point_display_radius=0,
            height=canvas_height,
            width=canvas_width,
            key=f"line_mark_canvas_{st.session_state['line_mark_canvas_nonce']}",
        )

    points = line_utils.point_list_from_canvas(canvas_result.json_data)
    previous_points = st.session_state.get("line_mark_canvas_points", [])
    st.session_state["line_mark_canvas_points"] = points
    if points != previous_points:
        st.rerun()
    if canvas_scale < 1.0:
        points = [(x_value / canvas_scale, y_value / canvas_scale) for x_value, y_value in points]
    with right_col:
        st.write(f"Points placed: {len(points)} / 12")
        st.caption("Live cursor zoom panel is shown on the canvas area.")
        if len(points) < 12:
            row_cols = st.columns(2, gap="small")
            with row_cols[0]:
                if st.button("Clear marked points"):
                    clear_all_marked_points()
            st.info("Keep clicking in order: top(3), right(3), bottom(3), left(3).")
            st.caption("Quickstart")
            st.image("assets/quickstart.gif", use_container_width=True)
            st.stop()
        if len(points) > 12:
            st.warning("Using first 12 points only.")
            points = points[:12]
        row_cols = st.columns(2, gap="small")
        with row_cols[0]:
            if st.button("Clear marked points"):
                clear_all_marked_points()
        with row_cols[1]:
            if st.button("Lock points and continue"):
                reset_line_controls()
                st.session_state["line_mark_locked_points"] = points
                st.session_state["line_mark_stage"] = "lines"
                st.rerun()
        st.caption("Quickstart")
        st.image("assets/quickstart.gif", use_container_width=True)
        st.stop()

points = list(locked_points)
stage = st.session_state.get("line_mark_stage", "lines")
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
    st.write("Points placed: 12 / 12")
    stage_action = line_stage_ui.render_stage_actions(stage, clear_all_marked_points, reset_line_controls)
    if stage == "lines":
        outer_line_color_label = line_utils.normalized_color_label(
            line_stage_ui.render_line_stage_controls(persistent_int_input, persistent_float_input)
        )
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
        outer_line_color_label = line_utils.normalized_color_label(st.session_state.get("line_outer_color_label", "Red"))
    if stage_action == "continue":
        st.session_state["line_mark_adjusted_points"] = adjusted_points
        st.session_state["line_mark_stage"] = "border"
        st.rerun()
    if stage_action == "back":
        st.session_state["line_mark_stage"] = "lines"
        st.rerun()
with right_col:
    if stage == "lines":
        with left_col:
            line_utils.force_stage_image_zoom(zoom_factor=zoom_factor_value)
            st.image(
                line_utils.select_zoomed_line_preview(
                    image_rgb,
                    adjusted_points,
                    st.session_state.get("line_outer_zoom_mode", "full"),
                    padding=12,
                    line_bgr=line_utils.border_color(outer_line_color_label),
                ),
                caption="Line stage zoom: outer lines with 12px margin.",
                width="content",
            )
        st.stop()

final_points = st.session_state.get("line_mark_adjusted_points", adjusted_points)
warped_card = get_cached_warped_card(image_bytes, image_bgr, final_points, line_utils.warp_from_edges)
if warped_card is None:
    with right_col:
        st.error("Could not build card edges from points. Try clearing and re-marking.")
    st.stop()

card_height, card_width = warped_card.shape[:2]
base_left, base_top = 30, 30
base_right, base_bottom = max(card_width - 31, base_left + 1), max(card_height - 31, base_top + 1)

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
    stage_image_col, stage_summary_col = st.columns([4, 2], gap="small")
    with stage_image_col:
        line_utils.force_stage_image_zoom(zoom_factor=zoom_factor_value)
        st.image(
            display_visual,
            caption="Full card by default. Top/Bottom inputs zoom 50% width, Left/Right inputs zoom 50% height.",
            width="content",
        )
    with stage_summary_col:
        line_utils.render_result_summary(result)
