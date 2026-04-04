from __future__ import annotations

from dataclasses import dataclass


OUTER_LINE_COLOR_OPTIONS: tuple[str, ...] = ("Red", "Green", "Blue", "Black")
INNER_LINE_COLOR_OPTIONS: tuple[str, ...] = ("Red", "Green", "Blue", "Black")
BADGE_ORDER: tuple[str, ...] = ("PSA", "TAG", "BGS", "ACE")


CENTERING_THRESHOLDS: dict[str, dict[str, int]] = {
    "PSA": {"min": 45, "max": 55},
    "TAG": {"min": 45, "max": 55},
    "BGS": {"min": 45, "max": 55},
    "ACE": {"min": 40, "max": 60},
}

PRISTINE_THRESHOLDS: dict[str, dict[str, int]] = {
    "TAG": {"min": 49, "max": 51},
    "BGS": {"min": 48, "max": 52},
}

BGS_BLACK_LABEL_THRESHOLD: dict[str, int] = {"min": 50, "max": 50}


@dataclass(frozen=True)
class InnerFrameDetectionConfig:
    color_threshold: float = 14.0
    left_window_start_ratio: float = 0.01
    left_window_end_ratio: float = 0.16
    right_window_start_ratio: float = 0.84
    right_window_end_ratio: float = 0.99
    top_window_start_ratio: float = 0.01
    top_window_end_ratio: float = 0.16
    bottom_window_start_ratio: float = 0.84
    bottom_window_end_ratio: float = 0.99


INNER_FRAME_DETECTION = InnerFrameDetectionConfig()
