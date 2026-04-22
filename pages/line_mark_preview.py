import cv2
import numpy as np
from typing import Optional


def border_color(label: str) -> tuple[int, int, int]:
    mapping = {
        "Red": (255, 0, 0),
        "Green": (0, 255, 0),
        "Blue": (0, 0, 255),
        "Black": (0, 0, 0),
    }
    return mapping[label]


def edge_preview(
    image_rgb: np.ndarray,
    points: list[tuple[float, float]],
    line_bgr: tuple[int, int, int] = (0, 255, 255),
    line_thickness: int = 1,
    render_scale: int = 1,
) -> np.ndarray:
    scale = max(1, int(render_scale))
    if scale > 1:
        image_height, image_width = image_rgb.shape[:2]
        preview = cv2.resize(image_rgb, (image_width * scale, image_height * scale), interpolation=cv2.INTER_CUBIC)
        scaled_points = [(x_value * scale, y_value * scale) for x_value, y_value in points]
        draw_thickness = max(1, int(line_thickness) * scale)
    else:
        preview = image_rgb.copy()
        scaled_points = points
        draw_thickness = max(1, int(line_thickness))
    edges = _side_indexes(scaled_points)
    image_height, image_width = preview.shape[:2]
    for indexes in edges:
        if len(indexes) == 2:
            first_index, second_index = indexes
            first_point = scaled_points[first_index]
            second_point = scaled_points[second_index]
            first = (int(round(first_point[0])), int(round(first_point[1])))
            second = (int(round(second_point[0])), int(round(second_point[1])))
            dx = second_point[0] - first_point[0]
            dy = second_point[1] - first_point[1]
            if abs(dx) >= 1e-6 or abs(dy) >= 1e-6:
                extend = max(image_width, image_height) * 4
                start_point = (int(round(first_point[0] - dx * extend)), int(round(first_point[1] - dy * extend)))
                end_point = (int(round(second_point[0] + dx * extend)), int(round(second_point[1] + dy * extend)))
                clipped, clip_start, clip_end = cv2.clipLine((0, 0, image_width, image_height), start_point, end_point)
                if clipped:
                    cv2.line(preview, clip_start, clip_end, (0, 0, 0), draw_thickness, lineType=cv2.LINE_AA)
                    cv2.line(preview, clip_start, clip_end, line_bgr, draw_thickness, lineType=cv2.LINE_AA)
                    if draw_thickness == 1:
                        cv2.line(preview, clip_start, clip_end, line_bgr, 1, lineType=cv2.LINE_AA)
            else:
                cv2.line(preview, first, second, (0, 0, 0), draw_thickness, lineType=cv2.LINE_AA)
                cv2.line(preview, first, second, line_bgr, draw_thickness, lineType=cv2.LINE_AA)
                if draw_thickness == 1:
                    cv2.line(preview, first, second, line_bgr, 1, lineType=cv2.LINE_AA)
            continue
        first_index, middle_index, second_index = indexes
        first_point = scaled_points[first_index]
        middle_point = scaled_points[middle_index]
        second_point = scaled_points[second_index]
        first = (int(round(first_point[0])), int(round(first_point[1])))
        middle = (int(round(middle_point[0])), int(round(middle_point[1])))
        second = (int(round(second_point[0])), int(round(second_point[1])))
        curve_points = _quadratic_points(first_point, middle_point, second_point, sample_count=160)
        if len(curve_points) >= 2:
            curve_int = np.array([(int(round(x)), int(round(y))) for x, y in curve_points], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(preview, [curve_int], False, (0, 0, 0), draw_thickness, lineType=cv2.LINE_AA)
            cv2.polylines(preview, [curve_int], False, line_bgr, draw_thickness, lineType=cv2.LINE_AA)
            if draw_thickness == 1:
                cv2.polylines(preview, [curve_int], False, line_bgr, 1, lineType=cv2.LINE_AA)
    if scale > 1:
        original_height, original_width = image_rgb.shape[:2]
        return cv2.resize(preview, (original_width, original_height), interpolation=cv2.INTER_AREA)
    return preview


def line_stage_zoom_preview(
    image_rgb: np.ndarray,
    points: list[tuple[float, float]],
    padding: int = 5,
    line_bgr: tuple[int, int, int] = (0, 255, 255),
    line_thickness: int = 1,
    render_scale: int = 1,
) -> np.ndarray:
    preview = edge_preview(image_rgb, points, line_bgr=line_bgr, line_thickness=line_thickness, render_scale=render_scale)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x = max(0, int(min(xs)) - padding)
    max_x = min(preview.shape[1], int(max(xs)) + padding)
    min_y = max(0, int(min(ys)) - padding)
    max_y = min(preview.shape[0], int(max(ys)) + padding)
    if max_x <= min_x or max_y <= min_y:
        return preview
    return preview[min_y:max_y, min_x:max_x]


def draw_cross_markers(image_rgb: np.ndarray, points: list[tuple[float, float]], size: int = 8) -> np.ndarray:
    preview = image_rgb.copy()
    _draw_infinite_pair_lines(preview, points)
    for x_value, y_value in points:
        center_x = int(round(x_value))
        center_y = int(round(y_value))
        # Render point marker crosshair with exact 1px stroke.
        cv2.line(preview, (center_x - size, center_y), (center_x + size, center_y), (0, 255, 255), 1, lineType=cv2.LINE_AA)
        cv2.line(preview, (center_x, center_y - size), (center_x, center_y + size), (0, 255, 255), 1, lineType=cv2.LINE_AA)
    return preview


def _draw_infinite_pair_lines(image_rgb: np.ndarray, points: list[tuple[float, float]]) -> None:
    image_height, image_width = image_rgb.shape[:2]
    required_triplets = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11)]
    for first_index, middle_index, second_index in required_triplets:
        if second_index >= len(points):
            continue
        first = points[first_index]
        middle = points[middle_index]
        second = points[second_index]
        curve_points = _quadratic_points(first, middle, second, sample_count=160)
        if len(curve_points) < 2:
            continue
        curve_int = np.array([(int(round(x)), int(round(y))) for x, y in curve_points], dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(image_rgb, [curve_int], False, (0, 0, 0), 1, lineType=cv2.LINE_AA)
        cv2.polylines(image_rgb, [curve_int], False, (0, 255, 255), 1, lineType=cv2.LINE_AA)


def select_zoomed_line_preview(
    image_rgb: np.ndarray,
    points: list[tuple[float, float]],
    zoom_mode: str,
    padding: int = 5,
    line_bgr: tuple[int, int, int] = (0, 255, 255),
    line_thickness: int = 1,
    render_scale: int = 1,
) -> np.ndarray:
    preview = edge_preview(image_rgb, points, line_bgr=line_bgr, line_thickness=line_thickness, render_scale=render_scale)
    image_height, image_width = preview.shape[:2]
    side_points = _side_points(points)
    if side_points is None:
        return preview
    top_side, right_side, bottom_side, left_side = side_points
    if zoom_mode == "top":
        anchor_y = int(round((top_side[0][1] + top_side[-1][1]) / 2.0))
        zoom_top = max(0, anchor_y - 30 - padding)
        zoom_bottom = min(image_height, anchor_y + 30 + padding)
        first_x = int(round(top_side[0][0]))
        second_x = int(round(top_side[-1][0]))
        min_x = min(first_x, second_x)
        max_x = max(first_x, second_x)
        line_width = max(1, max_x - min_x)
        middle_left = min_x + int(round(line_width * 0.125))
        middle_right = max_x - int(round(line_width * 0.125))
        zoom_left = max(0, middle_left - padding)
        zoom_right = min(image_width, max(zoom_left + 1, middle_right + padding))
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode == "bottom":
        anchor_y = int(round((bottom_side[0][1] + bottom_side[-1][1]) / 2.0))
        zoom_top = max(0, anchor_y - 30 - padding)
        zoom_bottom = min(image_height, anchor_y + 30 + padding)
        first_x = int(round(bottom_side[0][0]))
        second_x = int(round(bottom_side[-1][0]))
        min_x = min(first_x, second_x)
        max_x = max(first_x, second_x)
        line_width = max(1, max_x - min_x)
        middle_left = min_x + int(round(line_width * 0.125))
        middle_right = max_x - int(round(line_width * 0.125))
        zoom_left = max(0, middle_left - padding)
        zoom_right = min(image_width, max(zoom_left + 1, middle_right + padding))
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode == "left":
        anchor_x = int(round((left_side[0][0] + left_side[-1][0]) / 2.0))
        zoom_left = max(0, anchor_x - 30 - padding)
        zoom_right = min(image_width, anchor_x + 30 + padding)
        first_y = int(round(left_side[0][1]))
        second_y = int(round(left_side[-1][1]))
        min_y = min(first_y, second_y)
        max_y = max(first_y, second_y)
        line_height = max(1, max_y - min_y)
        middle_top = min_y + int(round(line_height * 0.125))
        middle_bottom = max_y - int(round(line_height * 0.125))
        zoom_top = max(0, middle_top - padding)
        zoom_bottom = min(image_height, max(zoom_top + 1, middle_bottom + padding))
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode == "right":
        anchor_x = int(round((right_side[0][0] + right_side[-1][0]) / 2.0))
        zoom_left = max(0, anchor_x - 30 - padding)
        zoom_right = min(image_width, anchor_x + 30 + padding)
        first_y = int(round(right_side[0][1]))
        second_y = int(round(right_side[-1][1]))
        min_y = min(first_y, second_y)
        max_y = max(first_y, second_y)
        line_height = max(1, max_y - min_y)
        middle_top = min_y + int(round(line_height * 0.125))
        middle_bottom = max_y - int(round(line_height * 0.125))
        zoom_top = max(0, middle_top - padding)
        zoom_bottom = min(image_height, max(zoom_top + 1, middle_bottom + padding))
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    return line_stage_zoom_preview(
        image_rgb,
        points,
        padding=padding,
        line_bgr=line_bgr,
        line_thickness=line_thickness,
        render_scale=render_scale,
    )


def _side_indexes(points: list[tuple[float, float]]) -> list[tuple[int, ...]]:
    if len(points) >= 12:
        return [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11)]
    return [(0, 1), (2, 3), (4, 5), (6, 7)]


def _side_points(
    points: list[tuple[float, float]],
) -> Optional[tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]]]:
    if len(points) >= 12:
        return points[0:3], points[3:6], points[6:9], points[9:12]
    if len(points) >= 8:
        return points[0:2], points[2:4], points[4:6], points[6:8]
    return None


def _quadratic_points(
    start: tuple[float, float], middle: tuple[float, float], end: tuple[float, float], sample_count: int
) -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []
    control_x = 2.0 * middle[0] - 0.5 * (start[0] + end[0])
    control_y = 2.0 * middle[1] - 0.5 * (start[1] + end[1])
    for t_value in np.linspace(0.0, 1.0, sample_count):
        one_minus_t = 1.0 - float(t_value)
        x_value = (
            (one_minus_t * one_minus_t * start[0])
            + (2.0 * one_minus_t * float(t_value) * control_x)
            + (float(t_value) * float(t_value) * end[0])
        )
        y_value = (
            (one_minus_t * one_minus_t * start[1])
            + (2.0 * one_minus_t * float(t_value) * control_y)
            + (float(t_value) * float(t_value) * end[1])
        )
        samples.append((x_value, y_value))
    return samples


def draw_visible_inner_border(
    image_rgb: np.ndarray,
    left_x: int,
    top_y: int,
    right_x: int,
    bottom_y: int,
    border_bgr: tuple[int, int, int],
    border_thickness: int = 1,
    render_scale: int = 1,
) -> np.ndarray:
    scale = max(1, int(render_scale))
    if scale > 1:
        image_height, image_width = image_rgb.shape[:2]
        outlined = cv2.resize(image_rgb, (image_width * scale, image_height * scale), interpolation=cv2.INTER_CUBIC)
        cv2.rectangle(
            outlined,
            (left_x * scale, top_y * scale),
            (right_x * scale, bottom_y * scale),
            border_bgr,
            max(1, int(border_thickness) * scale),
            lineType=cv2.LINE_AA,
        )
        return cv2.resize(outlined, (image_width, image_height), interpolation=cv2.INTER_AREA)
    outlined = image_rgb.copy()
    cv2.rectangle(outlined, (left_x, top_y), (right_x, bottom_y), border_bgr, border_thickness, lineType=cv2.LINE_AA)
    if border_thickness == 1:
        cv2.rectangle(outlined, (left_x, top_y), (right_x, bottom_y), border_bgr, 1, lineType=cv2.LINE_AA)
    return outlined


def select_zoomed_inner_preview(
    visualized: np.ndarray,
    card_width: int,
    card_height: int,
    inner_left: int,
    inner_right: int,
    inner_top: int,
    inner_bottom: int,
    zoom_mode: str,
) -> np.ndarray:
    if zoom_mode in {"top", "bottom"}:
        zoom_left = int(card_width * 0.25)
        zoom_right = int(card_width * 0.75)
        anchor_y = inner_top if zoom_mode == "top" else inner_bottom
        zoom_top = max(0, anchor_y - 30)
        zoom_bottom = min(card_height, zoom_top + 60)
        zoom_top = max(0, zoom_bottom - 60)
        return visualized[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode in {"left", "right"}:
        zoom_top = int(card_height * 0.25)
        zoom_bottom = int(card_height * 0.75)
        anchor_x = inner_left if zoom_mode == "left" else inner_right
        zoom_left = max(0, anchor_x - 30)
        zoom_right = min(card_width, zoom_left + 60)
        zoom_left = max(0, zoom_right - 60)
        return visualized[zoom_top:zoom_bottom, zoom_left:zoom_right]
    return visualized
