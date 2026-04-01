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
    adjusted = axis_nudged_points(points, top_y, right_x, bottom_y, left_x)
    line_specs = [(0, 1, top_angle), (2, 3, right_angle), (4, 5, bottom_angle), (6, 7, left_angle)]
    for first_index, second_index, angle_degrees in line_specs:
        if abs(angle_degrees) < 1e-9:
            continue
        adjusted[first_index], adjusted[second_index] = _rotate_line_pair(
            adjusted[first_index], adjusted[second_index], angle_degrees
        )
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
