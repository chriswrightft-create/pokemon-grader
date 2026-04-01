import cv2
import numpy as np


def border_color(label: str) -> tuple[int, int, int]:
    mapping = {
        "Magenta": (255, 0, 255),
        "Cyan": (255, 255, 0),
        "Yellow": (0, 255, 255),
        "Green": (0, 255, 0),
        "Red": (0, 0, 255),
        "White": (255, 255, 255),
    }
    return mapping[label]


def edge_preview(image_rgb: np.ndarray, points: list[tuple[float, float]]) -> np.ndarray:
    preview = image_rgb.copy()
    overlay = preview.copy()
    edges = [(0, 1), (2, 3), (4, 5), (6, 7)]
    for first_index, second_index in edges:
        first = (int(round(points[first_index][0])), int(round(points[first_index][1])))
        second = (int(round(points[second_index][0])), int(round(points[second_index][1])))
        cv2.line(overlay, first, second, (0, 255, 255), 1, lineType=cv2.LINE_8)
        cv2.circle(overlay, first, 3, (0, 255, 255), 1, lineType=cv2.LINE_8)
        cv2.circle(overlay, second, 3, (0, 255, 255), 1, lineType=cv2.LINE_8)
    return cv2.addWeighted(overlay, 0.45, preview, 0.55, 0.0)


def line_stage_zoom_preview(image_rgb: np.ndarray, points: list[tuple[float, float]], padding: int = 5) -> np.ndarray:
    preview = edge_preview(image_rgb, points)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x = max(0, int(min(xs)) - padding)
    max_x = min(preview.shape[1], int(max(xs)) + padding)
    min_y = max(0, int(min(ys)) - padding)
    max_y = min(preview.shape[0], int(max(ys)) + padding)
    if max_x <= min_x or max_y <= min_y:
        return preview
    return preview[min_y:max_y, min_x:max_x]


def select_zoomed_line_preview(
    image_rgb: np.ndarray, points: list[tuple[float, float]], zoom_mode: str, padding: int = 5
) -> np.ndarray:
    preview = edge_preview(image_rgb, points)
    image_height, image_width = preview.shape[:2]
    if zoom_mode == "top":
        anchor_y = int(round((points[0][1] + points[1][1]) / 2.0))
        zoom_top = max(0, anchor_y - 30)
        zoom_bottom = min(image_height, zoom_top + 60)
        zoom_top = max(0, zoom_bottom - 60)
        zoom_left = int(image_width * 0.25)
        zoom_right = int(image_width * 0.75)
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode == "bottom":
        anchor_y = int(round((points[4][1] + points[5][1]) / 2.0))
        zoom_top = max(0, anchor_y - 30)
        zoom_bottom = min(image_height, zoom_top + 60)
        zoom_top = max(0, zoom_bottom - 60)
        zoom_left = int(image_width * 0.25)
        zoom_right = int(image_width * 0.75)
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode == "left":
        anchor_x = int(round((points[6][0] + points[7][0]) / 2.0))
        zoom_left = max(0, anchor_x - 30)
        zoom_right = min(image_width, zoom_left + 60)
        zoom_left = max(0, zoom_right - 60)
        zoom_top = int(image_height * 0.25)
        zoom_bottom = int(image_height * 0.75)
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    if zoom_mode == "right":
        anchor_x = int(round((points[2][0] + points[3][0]) / 2.0))
        zoom_left = max(0, anchor_x - 30)
        zoom_right = min(image_width, zoom_left + 60)
        zoom_left = max(0, zoom_right - 60)
        zoom_top = int(image_height * 0.25)
        zoom_bottom = int(image_height * 0.75)
        return preview[zoom_top:zoom_bottom, zoom_left:zoom_right]
    return line_stage_zoom_preview(image_rgb, points, padding=padding)


def draw_visible_inner_border(
    image_rgb: np.ndarray,
    left_x: int,
    top_y: int,
    right_x: int,
    bottom_y: int,
    border_bgr: tuple[int, int, int],
) -> np.ndarray:
    outlined = image_rgb.copy()
    overlay = outlined.copy()
    cv2.rectangle(overlay, (left_x, top_y), (right_x, bottom_y), border_bgr, 1, lineType=cv2.LINE_8)
    outlined = cv2.addWeighted(overlay, 0.55, outlined, 0.45, 0.0)
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
