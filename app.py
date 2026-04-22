import base64
import hashlib
import io
import sys
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Streamlit Cloud can run this page as entrypoint, so ensure repo root is importable.
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from border_measurement import calculate_ratios_from_bounds
import app_ui
from pages import line_mark_line_stage as line_stage_ui
from pages import line_mark_page_helpers as page_helpers
from pages import line_mark_point_stage as point_stage
from pages import line_mark_state as line_mark_state
from pages import line_mark_utils as line_utils
from pages.line_mark_warp import get_cached_warped_card

line_utils.apply_streamlit_canvas_compatibility()

initialize_line_mark_defaults = line_mark_state.initialize_line_mark_defaults
persistent_float_input = line_mark_state.persistent_float_input
persistent_int_input = line_mark_state.persistent_int_input
reset_line_controls = getattr(line_mark_state, "reset_line_controls", lambda: None)
reset_line_mark_session_state = getattr(line_mark_state, "reset_line_mark_session_state", lambda: None)


st.set_page_config(page_title="TCG centering tool", layout="wide", initial_sidebar_state="collapsed")
app_ui.apply_page_chrome()
st.title("TCG centering tool")
st.caption("Click 12 points: top(3), right(3), bottom(3), left(3).")
upload_col, info_col = st.columns(2, gap="small")
with upload_col:
    uploaded_file = st.file_uploader("Upload card image", type=["png", "jpg", "jpeg", "webp"], key="line_mark_upload", label_visibility="collapsed")
line_utils.inject_line_mark_styles()

initialize_line_mark_defaults()
if uploaded_file is None:
    if st.session_state.get("line_mark_active_upload_token") is not None:
        reset_line_mark_session_state()
    with info_col:
        st.info("Upload an image to begin.")
    st.stop()

image_bytes = uploaded_file.getvalue()
upload_token = (uploaded_file.name, len(image_bytes), hashlib.sha1(image_bytes).hexdigest())
if st.session_state.get("line_mark_active_upload_token") != upload_token:
    reset_line_mark_session_state()
    st.session_state["line_mark_active_upload_token"] = upload_token
    st.rerun()
image_bgr = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
if image_bgr is None:
    st.error("Unable to decode uploaded image.")
    st.stop()

image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
canvas_width, canvas_height, canvas_scale = line_utils.fit_size(pil_image.width, pil_image.height)
canvas_image = pil_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
canvas_points = st.session_state.get("line_mark_canvas_points", [])
canvas_drawing_mode = "point"
canvas_preview = line_utils.draw_cross_markers(np.array(canvas_image), canvas_points) if canvas_points else np.array(canvas_image)

# Convert canvas preview to PIL Image for zoom functionality and st_canvas
canvas_background = Image.fromarray(canvas_preview.astype(np.uint8))
zoom_buffer = io.BytesIO()
canvas_background.save(zoom_buffer, format="PNG")
zoom_buffer.seek(0)
zoom_source_url = f"data:image/png;base64,{base64.b64encode(zoom_buffer.getvalue()).decode('ascii')}"

left_col, right_col = st.columns([3, 2])
locked_points = st.session_state.get("line_mark_locked_points")
current_stage = st.session_state.get("line_mark_stage", "lines")
stage_heading = "## Initial Point Placement"
if locked_points is not None:
    stage_heading = "## Outer Border" if current_stage == "lines" else "## Inner Border"
with right_col:
    st.markdown(stage_heading)
    zoom_factor_value = int(st.number_input("Zoom magnification", min_value=2, max_value=12, value=5, step=1, key="line_zoom_factor"))

def clear_all_marked_points() -> None:
    reset_line_controls()
    line_stage_ui.clear_marking_state()
    st.rerun()

if locked_points is None:
    previous_points = st.session_state.get("line_mark_canvas_points", [])
    # Generate a stable key based on the upload token to ensure canvas reinitializes on new upload
    canvas_key_suffix = upload_token[2][:8] if upload_token else str(st.session_state.get('line_mark_canvas_nonce', 0))
    with left_col:
        line_utils.force_canvas_crosshair(
            source_image_url=zoom_source_url,
            zoom_factor=zoom_factor_value,
            points=previous_points,
            move_radius_px=15.0,
        )
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=1,
            stroke_color="#00FFFF",
            background_image=canvas_background,
            display_toolbar=False,
            update_streamlit=True,
            drawing_mode=canvas_drawing_mode,
            point_display_radius=0,
            height=canvas_height,
            width=canvas_width,
            key=f"line_mark_canvas_{canvas_key_suffix}",
        )
        raw_points = line_utils.point_list_from_canvas(canvas_result.json_data)
        previous_raw_points = st.session_state.get("line_mark_canvas_raw_points", [])
        new_raw_points = raw_points
        if previous_raw_points and len(raw_points) >= len(previous_raw_points) and raw_points[: len(previous_raw_points)] == previous_raw_points:
            new_raw_points = raw_points[len(previous_raw_points):]
        points = point_stage.get_filtered_points(new_raw_points, previous_points)
        st.session_state["line_mark_canvas_raw_points"] = raw_points
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
                if st.button("Clear marked points", use_container_width=True):
                    clear_all_marked_points()
            st.info("Keep clicking in order: top(3), right(3), bottom(3), left(3).")
            st.caption("Quickstart")
            st.image("assets/quickstart.gif", use_container_width=True)
            st.stop()
        row_cols = st.columns(2, gap="small")
        with row_cols[0]:
            if st.button("Clear marked points", use_container_width=True):
                clear_all_marked_points()
        with row_cols[1]:
            if st.button("Lock points and continue", use_container_width=True):
                reset_line_controls()
                st.session_state["line_mark_locked_points"] = points
                st.session_state["line_mark_stage"] = "lines"
                st.rerun()
        st.caption("Quickstart")
        st.image("assets/quickstart.gif", use_container_width=True)
        st.stop()

points = list(locked_points)
stage = st.session_state.get("line_mark_stage", "lines")
top_line_y, right_line_x, bottom_line_y, left_line_x, top_line_angle, right_line_angle, bottom_line_angle, left_line_angle = (
    page_helpers.get_line_controls_from_state()
)
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
        top_line_y, right_line_x, bottom_line_y, left_line_x, top_line_angle, right_line_angle, bottom_line_angle, left_line_angle = (
            page_helpers.get_line_controls_from_state()
        )
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
    if stage_action == "modify":
        page_helpers.return_to_point_edit(points, canvas_scale)
    if stage_action == "back":
        st.session_state["line_mark_stage"] = "lines"
        st.rerun()
if stage == "lines":
    with left_col:
        page_helpers.render_outer_line_preview(
            image_rgb,
            adjusted_points,
            outer_line_color_label,
            zoom_factor_value,
            line_utils,
        )
    st.stop()

final_points = st.session_state.get("line_mark_adjusted_points", adjusted_points)
warped_card = get_cached_warped_card(image_bytes, image_bgr, final_points, line_utils.warp_from_edges)
if warped_card is None:
    with right_col:
        st.error("Could not build card edges from points. Try clearing and re-marking.")
    st.stop()

with right_col:
    nudge_top, nudge_right, nudge_bottom, nudge_left, color_label, zoom_mode = line_utils.render_inner_border_controls()
    st.session_state["line_inner_top"] = int(nudge_top)
    st.session_state["line_inner_right"] = int(nudge_right)
    st.session_state["line_inner_bottom"] = int(nudge_bottom)
    st.session_state["line_inner_left"] = int(nudge_left)
    st.session_state["line_inner_color_label"] = str(color_label)
    st.session_state["line_inner_zoom_mode"] = str(zoom_mode)

with left_col:
    page_helpers.render_inner_border_result_view(
        warped_card,
        zoom_factor_value,
        calculate_ratios_from_bounds,
        line_utils,
    )
