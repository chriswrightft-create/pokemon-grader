import cv2
import numpy as np
import streamlit as st


def get_line_controls_from_state() -> tuple[int, int, int, int, float, float, float, float]:
    return (
        int(st.session_state.get("line_top_y", 0)),
        int(st.session_state.get("line_right_x", 0)),
        int(st.session_state.get("line_bottom_y", 0)),
        int(st.session_state.get("line_left_x", 0)),
        float(st.session_state.get("line_top_angle", 0.0)),
        float(st.session_state.get("line_right_angle", 0.0)),
        float(st.session_state.get("line_bottom_angle", 0.0)),
        float(st.session_state.get("line_left_angle", 0.0)),
    )


def return_to_point_edit(points: list[tuple[float, float]], canvas_scale: float) -> None:
    editable_points = list(points)
    if canvas_scale < 1.0:
        editable_points = [(x_value * canvas_scale, y_value * canvas_scale) for x_value, y_value in editable_points]
    st.session_state["line_mark_canvas_points"] = editable_points
    st.session_state.pop("line_mark_locked_points", None)
    st.session_state.pop("line_mark_stage", None)
    st.session_state.pop("line_mark_adjusted_points", None)
    st.session_state["line_mark_canvas_nonce"] = int(st.session_state.get("line_mark_canvas_nonce", 0)) + 1
    st.rerun()


def render_outer_line_preview(
    image_rgb: np.ndarray,
    adjusted_points: list[tuple[float, float]],
    outer_line_color_label: str,
    zoom_factor_value: int,
    line_utils,
) -> None:
    outer_zoom_mode = st.session_state.get("line_outer_zoom_mode", "full")
    line_preview = line_utils.select_zoomed_line_preview(
        image_rgb,
        adjusted_points,
        outer_zoom_mode,
        padding=12,
        line_bgr=line_utils.border_color(outer_line_color_label),
        line_thickness=1,
    )
    st.image(line_preview, caption="Line stage zoom: outer lines with 12px margin.", width="content")
    line_utils.force_stage_image_zoom(zoom_factor=zoom_factor_value)


def render_inner_border_result_view(
    warped_card: np.ndarray,
    zoom_factor_value: int,
    calculate_ratios_from_bounds,
    line_utils,
) -> None:
    card_height, card_width = warped_card.shape[:2]
    base_left, base_top = 30, 30
    base_right, base_bottom = max(card_width - 31, base_left + 1), max(card_height - 31, base_top + 1)

    nudge_top = int(st.session_state.get("line_inner_top", 0))
    nudge_right = int(st.session_state.get("line_inner_right", 0))
    nudge_bottom = int(st.session_state.get("line_inner_bottom", 0))
    nudge_left = int(st.session_state.get("line_inner_left", 0))
    color_label = str(st.session_state.get("line_inner_color_label", "Red"))
    zoom_mode = str(st.session_state.get("line_inner_zoom_mode", "full"))

    inner_left = max(1, min(base_left + nudge_left, card_width - 2))
    inner_right = max(inner_left + 1, min(base_right - nudge_right, card_width - 1))
    inner_top = max(1, min(base_top + nudge_top, card_height - 2))
    inner_bottom = max(inner_top + 1, min(base_bottom - nudge_bottom, card_height - 1))

    result = calculate_ratios_from_bounds(card_width, card_height, inner_left, inner_right, inner_top, inner_bottom)
    visualized = cv2.cvtColor(warped_card, cv2.COLOR_BGR2RGB)
    visualized_inner = line_utils.draw_visible_inner_border(
        visualized,
        inner_left,
        inner_top,
        inner_right,
        inner_bottom,
        line_utils.border_color(color_label),
        border_thickness=1,
    )
    display_visual = line_utils.select_zoomed_inner_preview(
        visualized_inner, card_width, card_height, inner_left, inner_right, inner_top, inner_bottom, zoom_mode
    )

    stage_image_col, stage_summary_col = st.columns([4, 2], gap="small")
    with stage_image_col:
        st.image(
            display_visual,
            caption="Full card by default. Top/Bottom inputs zoom 50% width, Left/Right inputs zoom 50% height.",
            width="content",
        )
        line_utils.force_stage_image_zoom(zoom_factor=zoom_factor_value)
    with stage_summary_col:
        line_utils.render_result_summary(result)
