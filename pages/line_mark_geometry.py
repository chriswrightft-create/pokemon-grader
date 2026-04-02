from typing import Optional
import math

import cv2
import numpy as np


def line_from_points(first_point: tuple[float, float], second_point: tuple[float, float]) -> tuple[float, float, float]:
    x_one, y_one = first_point
    x_two, y_two = second_point
    return y_one - y_two, x_two - x_one, (x_one * y_two) - (x_two * y_one)


def intersection(
    first_line: tuple[float, float, float], second_line: tuple[float, float, float]
) -> Optional[tuple[float, float]]:
    a_one, b_one, c_one = first_line
    a_two, b_two, c_two = second_line
    determinant = (a_one * b_two) - (a_two * b_one)
    if abs(determinant) < 1e-6:
        return None
    x_value = ((b_one * c_two) - (b_two * c_one)) / determinant
    y_value = ((c_one * a_two) - (c_two * a_one)) / determinant
    return x_value, y_value


def warp_from_edges(image_bgr: np.ndarray, points: list[tuple[float, float]]) -> Optional[np.ndarray]:
    if len(points) >= 12:
        return _warp_from_side_triplets(image_bgr, points[:12])
    top_line = line_from_points(points[0], points[1])
    right_line = line_from_points(points[2], points[3])
    bottom_line = line_from_points(points[4], points[5])
    left_line = line_from_points(points[6], points[7])

    top_left = intersection(top_line, left_line)
    top_right = intersection(top_line, right_line)
    bottom_right = intersection(bottom_line, right_line)
    bottom_left = intersection(bottom_line, left_line)
    if not all([top_left, top_right, bottom_right, bottom_left]):
        return None

    source = np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)
    top_width = np.linalg.norm(source[1] - source[0])
    bottom_width = np.linalg.norm(source[2] - source[3])
    left_height = np.linalg.norm(source[3] - source[0])
    right_height = np.linalg.norm(source[2] - source[1])
    warped_width = max(int(max(top_width, bottom_width)), 20)
    warped_height = max(int(max(left_height, right_height)), 20)
    destination = np.array(
        [[0, 0], [warped_width - 1, 0], [warped_width - 1, warped_height - 1], [0, warped_height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(
        image_bgr,
        matrix,
        (warped_width, warped_height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    if warped_width > warped_height:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    return warped


def axis_nudged_points(
    points: list[tuple[float, float]], top_y: int, right_x: int, bottom_y: int, left_x: int
) -> list[tuple[float, float]]:
    adjusted = list(points)
    adjusted[0] = (adjusted[0][0], adjusted[0][1] + top_y)
    adjusted[1] = (adjusted[1][0], adjusted[1][1] + top_y)
    adjusted[2] = (adjusted[2][0] + right_x, adjusted[2][1])
    adjusted[3] = (adjusted[3][0] + right_x, adjusted[3][1])
    adjusted[4] = (adjusted[4][0], adjusted[4][1] + bottom_y)
    adjusted[5] = (adjusted[5][0], adjusted[5][1] + bottom_y)
    adjusted[6] = (adjusted[6][0] + left_x, adjusted[6][1])
    adjusted[7] = (adjusted[7][0] + left_x, adjusted[7][1])
    return adjusted


def line_controlled_points(
    points: list[tuple[float, float]],
    top_y: int,
    top_angle: float,
    right_x: int,
    right_angle: float,
    bottom_y: int,
    bottom_angle: float,
    left_x: int,
    left_angle: float,
) -> list[tuple[float, float]]:
    adjusted = list(points)
    side_indexes = _side_indexes(adjusted)
    offset_values = [top_y, right_x, bottom_y, left_x]
    angle_values = [top_angle, right_angle, bottom_angle, left_angle]
    for side_index, indexes in enumerate(side_indexes):
        offset_value = offset_values[side_index]
        adjusted = _offset_side_points(adjusted, indexes, offset_value)
    for side_index, indexes in enumerate(side_indexes):
        angle_degrees = angle_values[side_index]
        if abs(angle_degrees) < 1e-9:
            continue
        adjusted = _rotate_side_points(adjusted, indexes, angle_degrees)
    return adjusted


def _rotate_line_pair(
    first_point: tuple[float, float], second_point: tuple[float, float], angle_degrees: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    center_x = (first_point[0] + second_point[0]) / 2.0
    center_y = (first_point[1] + second_point[1]) / 2.0
    angle_radians = math.radians(angle_degrees)
    cos_value = math.cos(angle_radians)
    sin_value = math.sin(angle_radians)
    rotated_first = _rotate_point(first_point, center_x, center_y, cos_value, sin_value)
    rotated_second = _rotate_point(second_point, center_x, center_y, cos_value, sin_value)
    return rotated_first, rotated_second


def _rotate_point(
    point: tuple[float, float], center_x: float, center_y: float, cos_value: float, sin_value: float
) -> tuple[float, float]:
    dx = point[0] - center_x
    dy = point[1] - center_y
    return center_x + (dx * cos_value) - (dy * sin_value), center_y + (dx * sin_value) + (dy * cos_value)


def _side_indexes(points: list[tuple[float, float]]) -> list[list[int]]:
    if len(points) >= 12:
        return [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]
    return [[0, 1], [2, 3], [4, 5], [6, 7]]


def _offset_side_points(points: list[tuple[float, float]], indexes: list[int], offset_value: int) -> list[tuple[float, float]]:
    if offset_value == 0:
        return points
    adjusted = list(points)
    x_values = [points[index][0] for index in indexes]
    y_values = [points[index][1] for index in indexes]
    is_horizontal = (max(x_values) - min(x_values)) >= (max(y_values) - min(y_values))
    for index in indexes:
        x_value, y_value = adjusted[index]
        if is_horizontal:
            adjusted[index] = (x_value, y_value + offset_value)
        else:
            adjusted[index] = (x_value + offset_value, y_value)
    return adjusted


def _rotate_side_points(points: list[tuple[float, float]], indexes: list[int], angle_degrees: float) -> list[tuple[float, float]]:
    center_x = sum(points[index][0] for index in indexes) / float(len(indexes))
    center_y = sum(points[index][1] for index in indexes) / float(len(indexes))
    angle_radians = math.radians(angle_degrees)
    cos_value = math.cos(angle_radians)
    sin_value = math.sin(angle_radians)
    adjusted = list(points)
    for index in indexes:
        adjusted[index] = _rotate_point(points[index], center_x, center_y, cos_value, sin_value)
    return adjusted


def _warp_from_side_triplets(image_bgr: np.ndarray, points: list[tuple[float, float]]) -> Optional[np.ndarray]:
    top_side = _ordered_side_triplet(points[0:3], axis="x", ascending=True)
    right_side = _ordered_side_triplet(points[3:6], axis="y", ascending=True)
    bottom_side = _ordered_side_triplet(points[6:9], axis="x", ascending=True)
    left_side = _ordered_side_triplet(points[9:12], axis="y", ascending=True)

    top_line = _fit_line_from_triplet(top_side)
    right_line = _fit_line_from_triplet(right_side)
    bottom_line = _fit_line_from_triplet(bottom_side)
    left_line = _fit_line_from_triplet(left_side)

    top_left = intersection(top_line, left_line)
    top_right = intersection(top_line, right_line)
    bottom_right = intersection(bottom_line, right_line)
    bottom_left = intersection(bottom_line, left_line)
    if not all([top_left, top_right, bottom_right, bottom_left]):
        return None

    source = np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)
    top_width = np.linalg.norm(source[1] - source[0])
    bottom_width = np.linalg.norm(source[2] - source[3])
    left_height = np.linalg.norm(source[3] - source[0])
    right_height = np.linalg.norm(source[2] - source[1])
    output_width = max(20, int(round(max(top_width, bottom_width))))
    output_height = max(20, int(round(max(left_height, right_height))))
    destination = np.array(
        [[0, 0], [output_width - 1, 0], [output_width - 1, output_height - 1], [0, output_height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(
        image_bgr,
        matrix,
        (output_width, output_height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    transformed_points = cv2.perspectiveTransform(
        np.array(points, dtype=np.float32).reshape(1, len(points), 2), matrix
    ).reshape(len(points), 2)
    warped = _apply_triplet_straightening(warped, transformed_points.tolist())
    if output_width > output_height:
        warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
    return warped


def _fit_line_from_triplet(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    if len(points) < 2:
        return 0.0, 0.0, 0.0
    return line_from_points(points[0], points[-1])


def _ordered_side_triplet(
    triplet: list[tuple[float, float]], axis: str, ascending: bool
) -> list[tuple[float, float]]:
    if len(triplet) != 3:
        return triplet
    axis_index = 0 if axis == "x" else 1
    sorted_points = sorted(triplet, key=lambda point: point[axis_index], reverse=not ascending)
    return sorted_points


def _apply_triplet_straightening(
    warped_image: np.ndarray, transformed_points: list[list[float]]
) -> np.ndarray:
    image_height, image_width = warped_image.shape[:2]
    if image_height < 2 or image_width < 2 or len(transformed_points) < 12:
        return warped_image
    top_middle = transformed_points[1]
    right_middle = transformed_points[4]
    bottom_middle = transformed_points[7]
    left_middle = transformed_points[10]

    sag_top = float(top_middle[1] - 0.0)
    sag_bottom = float(bottom_middle[1] - float(image_height - 1))
    sag_left = float(left_middle[0] - 0.0)
    sag_right = float(right_middle[0] - float(image_width - 1))

    row_axis = np.linspace(0.0, 1.0, image_height, dtype=np.float32).reshape(image_height, 1)
    column_axis = np.linspace(0.0, 1.0, image_width, dtype=np.float32).reshape(1, image_width)
    horizontal_peak = 4.0 * column_axis * (1.0 - column_axis)
    vertical_peak = 4.0 * row_axis * (1.0 - row_axis)
    top_influence = np.square(1.0 - row_axis)
    bottom_influence = np.square(row_axis)
    left_influence = np.square(1.0 - column_axis)
    right_influence = np.square(column_axis)

    y_adjustment = horizontal_peak * ((sag_top * top_influence) + (sag_bottom * bottom_influence))
    x_adjustment = vertical_peak * ((sag_left * left_influence) + (sag_right * right_influence))

    source_x = np.tile(np.arange(image_width, dtype=np.float32).reshape(1, image_width), (image_height, 1)) + x_adjustment
    source_y = np.tile(np.arange(image_height, dtype=np.float32).reshape(image_height, 1), (1, image_width)) + y_adjustment
    source_x = np.clip(source_x, 0.0, float(image_width - 1))
    source_y = np.clip(source_y, 0.0, float(image_height - 1))
    straightened = cv2.remap(
        warped_image,
        source_x.astype(np.float32),
        source_y.astype(np.float32),
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return straightened


