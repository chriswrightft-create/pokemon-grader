from __future__ import annotations

from typing import Optional

import cv2
import numpy as np


def _order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    summed = points.sum(axis=1)
    diffed = np.diff(points, axis=1)
    rect[0] = points[np.argmin(summed)]
    rect[2] = points[np.argmax(summed)]
    rect[1] = points[np.argmin(diffed)]
    rect[3] = points[np.argmax(diffed)]
    return rect


def _card_ratio_score(width: float, height: float) -> float:
    longer_side = max(width, height)
    if longer_side <= 0:
        return 0.0
    ratio = min(width, height) / longer_side
    pokemon_ratio = 63.0 / 88.0
    return max(0.0, 1.0 - abs(ratio - pokemon_ratio) / 0.2)


def _score_candidate(points: np.ndarray, contour_area: float, image_width: int, image_height: int) -> float:
    ordered = _order_points(points)
    candidate_width = max(np.linalg.norm(ordered[2] - ordered[3]), np.linalg.norm(ordered[1] - ordered[0]))
    candidate_height = max(np.linalg.norm(ordered[1] - ordered[2]), np.linalg.norm(ordered[0] - ordered[3]))
    if candidate_width <= 1 or candidate_height <= 1:
        return -1.0

    x, y, box_width, box_height = cv2.boundingRect(points.astype(np.int32))
    margin_x = int(image_width * 0.02)
    margin_y = int(image_height * 0.02)
    touches_left = x <= margin_x
    touches_top = y <= margin_y
    touches_right = (x + box_width) >= (image_width - margin_x)
    touches_bottom = (y + box_height) >= (image_height - margin_y)
    if touches_left and touches_top and touches_right and touches_bottom:
        return -1.0

    image_area = image_width * image_height
    box_area = candidate_width * candidate_height
    rectangularity = min(contour_area / max(box_area, 1.0), 1.0)
    ratio_score = _card_ratio_score(candidate_width, candidate_height)
    area_score = min(contour_area / (image_area * 0.18), 1.0)
    edge_clearance_x = min(x, image_width - (x + box_width)) / max(image_width, 1)
    edge_clearance_y = min(y, image_height - (y + box_height)) / max(image_height, 1)
    edge_clearance_score = min((edge_clearance_x + edge_clearance_y) * 8.0, 1.0)
    return area_score * 0.20 + ratio_score * 0.40 + rectangularity * 0.25 + edge_clearance_score * 0.15


def _collect_candidates(contours: list[np.ndarray], image_width: int, image_height: int) -> list[tuple[float, np.ndarray]]:
    image_area = image_width * image_height
    candidates: list[tuple[float, np.ndarray]] = []
    for contour in contours:
        contour_area = cv2.contourArea(contour)
        if contour_area < image_area * 0.01 or contour_area > image_area * 0.95:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue

        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) == 4:
            points = polygon.reshape(4, 2).astype(np.float32)
        else:
            rotated_rect = cv2.minAreaRect(contour)
            points = cv2.boxPoints(rotated_rect).astype(np.float32)

        score = _score_candidate(points, contour_area, image_width, image_height)
        if score > 0:
            candidates.append((score, points))
    return candidates


def _find_color_contours(image: np.ndarray) -> list[np.ndarray]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    color_mask = cv2.inRange(saturation, 55, 255)
    brightness_mask = cv2.inRange(value, 35, 255)
    combined_mask = cv2.bitwise_and(color_mask, brightness_mask)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=1)
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def _find_foreground_contours(image: np.ndarray) -> list[np.ndarray]:
    image_height, image_width = image.shape[:2]
    patch_size = max(10, min(image_width, image_height) // 12)
    corner_patches = [
        image[:patch_size, :patch_size],
        image[:patch_size, -patch_size:],
        image[-patch_size:, :patch_size],
        image[-patch_size:, -patch_size:],
    ]
    background_pixels = np.concatenate([patch.reshape(-1, 3) for patch in corner_patches], axis=0)
    background_color = np.median(background_pixels, axis=0).astype(np.float32)
    diff_map = np.linalg.norm(image.astype(np.float32) - background_color, axis=2)
    diff_mask = (diff_map > 35).astype(np.uint8) * 255
    diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=1)
    contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def _best_foreground_quad(image: np.ndarray) -> Optional[np.ndarray]:
    image_height, image_width = image.shape[:2]
    contours = _find_foreground_contours(image)
    if not contours:
        return None

    image_area = image_width * image_height
    best_score = -1.0
    best_points: Optional[np.ndarray] = None
    for contour in contours:
        contour_area = cv2.contourArea(contour)
        if contour_area < image_area * 0.03 or contour_area > image_area * 0.75:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) == 4:
            points = polygon.reshape(4, 2).astype(np.float32)
        else:
            points = cv2.boxPoints(cv2.minAreaRect(contour)).astype(np.float32)

        score = _score_candidate(points, contour_area, image_width, image_height)
        if score > best_score:
            best_score = score
            best_points = points

    if best_points is None or best_score < 0.50:
        return None
    return best_points


def _warp_card(image: np.ndarray, card_corners: np.ndarray) -> np.ndarray:
    ordered_corners = _order_points(card_corners)
    width_a = np.linalg.norm(ordered_corners[2] - ordered_corners[3])
    width_b = np.linalg.norm(ordered_corners[1] - ordered_corners[0])
    height_a = np.linalg.norm(ordered_corners[1] - ordered_corners[2])
    height_b = np.linalg.norm(ordered_corners[0] - ordered_corners[3])
    warped_width = int(max(width_a, width_b))
    warped_height = int(max(height_a, height_b))
    if warped_width < 10 or warped_height < 10:
        return image.copy()

    destination = np.array(
        [[0, 0], [warped_width - 1, 0], [warped_width - 1, warped_height - 1], [0, warped_height - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(ordered_corners, destination)
    warped_image = cv2.warpPerspective(
        image,
        transform,
        (warped_width, warped_height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    if warped_width > warped_height:
        warped_image = cv2.rotate(warped_image, cv2.ROTATE_90_CLOCKWISE)
    return warped_image


def _best_card_quad(image: np.ndarray) -> Optional[np.ndarray]:
    foreground_quad = _best_foreground_quad(image)
    if foreground_quad is not None:
        return foreground_quad

    grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(grayscale_image, (5, 5), 0)
    edge_map = cv2.Canny(blurred_image, 40, 140)
    dilated_edges = cv2.dilate(edge_map, np.ones((3, 3), np.uint8), iterations=1)
    edge_contours, _ = cv2.findContours(dilated_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    color_contours = _find_color_contours(image)
    foreground_contours = _find_foreground_contours(image)
    if not edge_contours and not color_contours and not foreground_contours:
        return None

    image_height, image_width = image.shape[:2]
    scored_candidates = _collect_candidates(edge_contours, image_width, image_height)
    color_candidates = _collect_candidates(color_contours, image_width, image_height)
    foreground_candidates = _collect_candidates(foreground_contours, image_width, image_height)
    scored_candidates.extend((score + 0.08, points) for score, points in color_candidates)
    scored_candidates.extend((score + 0.12, points) for score, points in foreground_candidates)

    if not scored_candidates:
        return None
    best_score, best_points = max(scored_candidates, key=lambda item: item[0])
    if best_score < 0.45:
        return None
    return best_points


def detect_card_and_warp(image: np.ndarray) -> np.ndarray:
    card_quad = _best_card_quad(image)
    if card_quad is None:
        return image.copy()
    return _warp_card(image, card_quad)


def detect_card_quad(image: np.ndarray) -> Optional[np.ndarray]:
    card_quad = _best_card_quad(image)
    if card_quad is None:
        return None
    return _order_points(card_quad)
