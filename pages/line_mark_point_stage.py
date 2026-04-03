from __future__ import annotations

from math import hypot


MAX_POINTS = 12
MIN_POINT_DISTANCE_PX = 20.0


def _distance(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    return hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


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
    if len(committed_points) >= max_points:
        return committed_points

    accepted_points = list(committed_points)
    for candidate_point in raw_points:
        if len(accepted_points) >= max_points:
            break
        if any(_distance(candidate_point, existing_point) <= min_point_distance_px for existing_point in accepted_points):
            continue
        accepted_points.append(candidate_point)

    return accepted_points
