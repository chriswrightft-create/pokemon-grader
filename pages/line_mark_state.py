import streamlit as st


def initialize_line_mark_defaults() -> None:
    defaults = {
        "line_mark_canvas_nonce": 0,
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
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def persistent_int_input(label: str, state_key: str, widget_key: str, step: int = 1) -> int:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = int(st.session_state.get(state_key, 0))
    value = int(st.number_input(label, step=step, key=widget_key))
    st.session_state[state_key] = value
    return value


def persistent_float_input(label: str, state_key: str, widget_key: str, step: float = 0.1) -> float:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = float(st.session_state.get(state_key, 0.0))
    value = float(st.number_input(label, step=step, key=widget_key))
    st.session_state[state_key] = value
    return value


def reset_line_controls() -> None:
    zero_state_keys = [
        "line_top_y",
        "line_right_x",
        "line_bottom_y",
        "line_left_x",
        "line_top_angle",
        "line_right_angle",
        "line_bottom_angle",
        "line_left_angle",
    ]
    for key in zero_state_keys:
        st.session_state[key] = 0
    widget_keys = [
        "line_top_y_widget",
        "line_right_x_widget",
        "line_bottom_y_widget",
        "line_left_x_widget",
        "line_top_angle_widget",
        "line_right_angle_widget",
        "line_bottom_angle_widget",
        "line_left_angle_widget",
    ]
    for key in widget_keys:
        st.session_state.pop(key, None)


def reset_line_mark_session_state() -> None:
    state_keys_to_remove = [
        "line_mark_locked_points",
        "line_mark_stage",
        "line_mark_adjusted_points",
        "line_mark_canvas_points",
        "line_mark_active_upload_token",
        "line_warp_cache_key",
        "line_warp_cache_card",
        "line_outer_color_label",
        "line_inner_zoom_mode",
        "line_outer_zoom_mode",
        "line_inner_top",
        "line_inner_right",
        "line_inner_bottom",
        "line_inner_left",
        "line_zoom_factor",
    ]
    for key in state_keys_to_remove:
        st.session_state.pop(key, None)
    widget_keys_to_remove = [
        "line_top_y_widget",
        "line_right_x_widget",
        "line_bottom_y_widget",
        "line_left_x_widget",
        "line_top_angle_widget",
        "line_right_angle_widget",
        "line_bottom_angle_widget",
        "line_left_angle_widget",
        "line_inner_top_widget",
        "line_inner_right_widget",
        "line_inner_bottom_widget",
        "line_inner_left_widget",
    ]
    for key in widget_keys_to_remove:
        st.session_state.pop(key, None)
    reset_line_controls()
    st.session_state["line_mark_canvas_nonce"] = int(st.session_state.get("line_mark_canvas_nonce", 0)) + 1
