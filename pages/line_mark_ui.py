from typing import Optional

import streamlit as st
import streamlit.components.v1 as components
import streamlit.elements.image as streamlit_image
from pages.line_mark_canvas_js import get_canvas_enhancement_script, get_stage_image_zoom_script
from pages.line_mark_preview import border_color, draw_visible_inner_border, edge_preview, line_stage_zoom_preview, select_zoomed_inner_preview


def apply_streamlit_canvas_compatibility() -> None:
    try:
        from streamlit.elements.lib import image_utils
        from streamlit.elements.lib.layout_utils import LayoutConfig

        needs_patch = not hasattr(streamlit_image, "image_to_url")
        if not needs_patch:
            needs_patch = "layout_config" in image_utils.image_to_url.__code__.co_varnames

        if needs_patch:
            def _image_to_url_compat(image, width, clamp, channels, output_format, image_id):
                layout_config = width if hasattr(width, "width") else LayoutConfig(width=width)
                return image_utils.image_to_url(image, layout_config, clamp, channels, output_format, image_id)

            streamlit_image.image_to_url = _image_to_url_compat
    except (ImportError, AttributeError):
        return


def point_list_from_canvas(canvas_json: Optional[dict]) -> list[tuple[float, float]]:
    if not canvas_json or "objects" not in canvas_json:
        return []
    points: list[tuple[float, float]] = []
    for item in canvas_json["objects"]:
        if item.get("type") != "circle":
            continue
        radius = float(item.get("radius", 0.0))
        left = float(item.get("left", 0.0))
        top = float(item.get("top", 0.0))
        points.append((left + radius, top + radius))
    return points


def fit_size(width: int, height: int, max_width: int = 900, max_height: int = 700) -> tuple[int, int, float]:
    scale = min(max_width / float(width), max_height / float(height), 1.0)
    fitted_width = max(1, int(round(width * scale)))
    fitted_height = max(1, int(round(height * scale)))
    return fitted_width, fitted_height, scale




def force_canvas_crosshair(source_image_url: str = "", zoom_factor: int = 4) -> None:
    components.html(
        get_canvas_enhancement_script(source_image_url=source_image_url, zoom_factor=zoom_factor),
        height=0,
        width=0,
    )


def force_stage_image_zoom(zoom_factor: int = 7) -> None:
    components.html(get_stage_image_zoom_script(zoom_factor=zoom_factor), height=0, width=0)


def normalized_color_label(raw_value: object, default_label: str = "Red") -> str:
    if isinstance(raw_value, str):
        return raw_value
    if isinstance(raw_value, tuple) and raw_value:
        first_value = raw_value[0]
        if isinstance(first_value, str):
            return first_value
    return default_label


def inject_line_mark_styles() -> None:
    st.markdown(
        """
        <style>
        canvas.upper-canvas { cursor: crosshair !important; }
        div[data-testid="stImage"] img { max-height: 70vh; object-fit: contain; }
        iframe[srcdoc] svg,
        iframe[srcdoc] button svg,
        iframe[srcdoc] [class*="toolbar"] svg {
          stroke: #f3f4f6 !important;
          fill: #f3f4f6 !important;
        }
        iframe[srcdoc] button {
          color: #f3f4f6 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_inner_border_controls() -> tuple[int, int, int, int, str, str]:
    st.subheader("Inner Border Nudges")
    st.caption("Zoom target")
    button_cols = st.columns(5)
    with button_cols[0]:
        if st.button("Top", key="zoom_top_button"):
            st.session_state["line_inner_zoom_mode"] = "top"
    with button_cols[1]:
        if st.button("Right", key="zoom_right_button"):
            st.session_state["line_inner_zoom_mode"] = "right"
    with button_cols[2]:
        if st.button("Bottom", key="zoom_bottom_button"):
            st.session_state["line_inner_zoom_mode"] = "bottom"
    with button_cols[3]:
        if st.button("Left", key="zoom_left_button"):
            st.session_state["line_inner_zoom_mode"] = "left"
    with button_cols[4]:
        if st.button("Full", key="zoom_full_button"):
            st.session_state["line_inner_zoom_mode"] = "full"

    st.caption("Top, Right, Bottom, Left in pixels (+in, -out)")
    cols = st.columns(4)
    with cols[0]:
        top_value = _persistent_int_input("Top", "line_inner_top", "line_inner_top_widget")
    with cols[1]:
        right_value = _persistent_int_input("Right", "line_inner_right", "line_inner_right_widget")
    with cols[2]:
        bottom_value = _persistent_int_input("Bottom", "line_inner_bottom", "line_inner_bottom_widget")
    with cols[3]:
        left_value = _persistent_int_input("Left", "line_inner_left", "line_inner_left_widget")
    color_label = st.selectbox("Inner border color", ["Red", "Green", "Blue", "Black"], index=0)
    zoom_mode = st.session_state.get("line_inner_zoom_mode", "full")
    return top_value, right_value, bottom_value, left_value, color_label, zoom_mode


def _persistent_int_input(label: str, state_key: str, widget_key: str, step: int = 1) -> int:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = int(st.session_state.get(state_key, 0))
    value = int(st.number_input(label, step=step, key=widget_key))
    st.session_state[state_key] = value
    return value


def render_result_summary(result) -> None:
    st.markdown("<div style='height: 190px;'></div>", unsafe_allow_html=True)
    st.markdown(
        (
            "<div style='text-align:center;'>"
            f"<div style='font-size:30px;font-weight:700;line-height:1.1;'>"
            f"L/R {result.left_right_ratio[0]}%/{result.left_right_ratio[1]}%</div>"
            f"<div style='font-size:30px;font-weight:700;line-height:1.1;margin-top:8px;'>"
            f"T/B {result.top_bottom_ratio[0]}%/{result.top_bottom_ratio[1]}%</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    render_grader_badges(result)


def render_grader_badges(result) -> None:
    centering_thresholds = {
        "PSA": {"min": 45, "max": 55},
        "TAG": {"min": 45, "max": 55},
        "BGS": {"min": 45, "max": 55},
        "ACE": {"min": 40, "max": 60},
    }
    pristine_thresholds = {
        "TAG": {"min": 49, "max": 51},
        "BGS": {"min": 48, "max": 52},
    }
    bgs_black_label_threshold = {"min": 50, "max": 50}
    badge_markup = []
    for grader_label, threshold in centering_thresholds.items():
        badge_color = "#10b981" if _passes_centering_threshold(result, threshold) else "#ef4444"
        display_label = grader_label
        if grader_label == "BGS" and _passes_centering_threshold(result, bgs_black_label_threshold):
            display_label = "BGS BLACK"
            badge_color = "#111111"
        elif grader_label in pristine_thresholds and _passes_centering_threshold(result, pristine_thresholds[grader_label]):
            display_label = f"{grader_label} PRISTINE"
        badge_markup.append(
            (
                grader_label,
                f'<div style="width:112px;height:84px;border-radius:10px;display:flex;align-items:center;justify-content:center;'
                f'padding:8px;background:{badge_color};color:#ffffff;box-sizing:border-box;">'
                f'<span style="font-size:14px;font-weight:800;line-height:1.0;text-align:center;white-space:normal;">{display_label}</span>'
                "</div>",
            )
        )
    ordered_badges = sorted(
        badge_markup,
        key=lambda item: ["PSA", "TAG", "BGS", "ACE"].index(item[0]) if item[0] in {"PSA", "TAG", "BGS", "ACE"} else 999,
    )
    badges_html = "".join(markup for _, markup in ordered_badges)
    st.markdown(
        (
            '<div style="display:grid;grid-template-columns:repeat(2,minmax(112px,1fr));gap:10px;'
            'justify-items:center;align-items:stretch;margin:12px 0 4px 0;">'
            f"{badges_html}</div>"
        ),
        unsafe_allow_html=True,
    )


def _passes_centering_threshold(result, threshold: dict[str, int]) -> bool:
    minimum_percent = threshold["min"]
    maximum_percent = threshold["max"]
    left_percent = result.left_right_ratio[0]
    top_percent = result.top_bottom_ratio[0]
    left_in_range = minimum_percent <= left_percent <= maximum_percent
    top_in_range = minimum_percent <= top_percent <= maximum_percent
    return left_in_range and top_in_range


