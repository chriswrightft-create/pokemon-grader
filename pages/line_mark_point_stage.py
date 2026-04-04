from __future__ import annotations

from math import hypot
from typing import Optional


MAX_POINTS = 12
MIN_POINT_DISTANCE_PX = 15.0


def _distance(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    return hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


def _nearest_point_index(
    points: list[tuple[float, float]],
    candidate_point: tuple[float, float],
    max_distance_px: float,
) -> int:
    nearest_index = -1
    nearest_distance = float("inf")
    for index, existing_point in enumerate(points):
        distance = _distance(candidate_point, existing_point)
        if distance <= max_distance_px and distance < nearest_distance:
            nearest_distance = distance
            nearest_index = index
    return nearest_index


def get_filtered_points(
    raw_points: list[tuple[float, float]],
    previous_points: list[tuple[float, float]],
    min_point_distance_px: float = MIN_POINT_DISTANCE_PX,
    max_points: int = MAX_POINTS,
) -> list[tuple[float, float]]:
    """
    Keep committed points stable and only accept new points that are
    farther than `min_point_distance_px` from all previously accepted points.
    """
    committed_points = list(previous_points[:max_points])
    accepted_points = list(committed_points)
    if not raw_points:
        return accepted_points

    pending_move_index: Optional[int] = None
    for candidate_point in raw_points:
        if pending_move_index is not None:
            accepted_points[pending_move_index] = candidate_point
            pending_move_index = None
            continue
        nearest_index = _nearest_point_index(accepted_points, candidate_point, min_point_distance_px)
        if nearest_index >= 0:
            # Arm a move: the next candidate point becomes the destination for this index.
            pending_move_index = nearest_index
            continue
        if len(accepted_points) >= max_points:
            # At cap: block adding new points, but keep allowing near-point reposition.
            continue
        accepted_points.append(candidate_point)

    return accepted_points
