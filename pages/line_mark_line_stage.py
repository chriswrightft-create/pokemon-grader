from typing import Callable, Optional

import streamlit as st


def render_stage_actions(stage: str, clear_points: Callable[[], None], reset_line_controls: Callable[[], None]) -> Optional[str]:
    if stage == "lines":
        action_cols = st.columns(2, gap="small")
        with action_cols[0]:
            if st.button("Back to modify points", use_container_width=True):
                return "modify"
        with action_cols[1]:
            if st.button("Next to Inner Border", use_container_width=True):
                return "continue"
        return None

    action_cols = st.columns(2, gap="small")
    with action_cols[0]:
        if st.button("Back to modify points", use_container_width=True):
            return "modify"
    with action_cols[1]:
        if st.button("Back to outer border", use_container_width=True):
            return "back"
    return None


def render_line_stage_controls(
    persistent_int_input: Callable[[str, str, str], int],
    persistent_float_input: Callable[[str, str, str], float],
) -> str:
    st.caption("Outer line zoom")
    outer_line_color_label = st.selectbox("Outer line color", ["Red", "Green", "Blue", "Black"], key="line_outer_color_label")
    _render_zoom_buttons()
    st.caption("Line controls: drag on axis + rotate")
    _render_axis_controls(persistent_int_input)
    _render_angle_controls(persistent_float_input)
    return outer_line_color_label


def _render_zoom_buttons() -> None:
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


def _render_axis_controls(persistent_int_input: Callable[[str, str, str], int]) -> None:
    axis_cols = st.columns(4)
    with axis_cols[0]:
        persistent_int_input("Top Y", "line_top_y", "line_top_y_widget")
    with axis_cols[1]:
        persistent_int_input("Right X", "line_right_x", "line_right_x_widget")
    with axis_cols[2]:
        persistent_int_input("Bottom Y", "line_bottom_y", "line_bottom_y_widget")
    with axis_cols[3]:
        persistent_int_input("Left X", "line_left_x", "line_left_x_widget")


def _render_angle_controls(persistent_float_input: Callable[[str, str, str], float]) -> None:
    angle_cols = st.columns(4)
    with angle_cols[0]:
        persistent_float_input("Top Rotation", "line_top_angle", "line_top_angle_widget")
    with angle_cols[1]:
        persistent_float_input("Right Rotation", "line_right_angle", "line_right_angle_widget")
    with angle_cols[2]:
        persistent_float_input("Bottom Rotation", "line_bottom_angle", "line_bottom_angle_widget")
    with angle_cols[3]:
        persistent_float_input("Left Rotation", "line_left_angle", "line_left_angle_widget")


def _clear_marking_state() -> None:
    st.session_state.pop("line_mark_locked_points", None)
    st.session_state.pop("line_mark_stage", None)
    st.session_state.pop("line_mark_adjusted_points", None)
    st.session_state.pop("line_mark_canvas_points", None)
    st.session_state["line_mark_canvas_nonce"] += 1


def clear_marking_state() -> None:
    _clear_marking_state()
